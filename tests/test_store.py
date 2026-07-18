"""Tests for the crash-safe persistence layer (cozer/store.py), including
atomic-write failure and power-loss (journal replay) simulations."""
import copy
import glob
import json
import os
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import golden_io  # noqa: E402

from cozer import store  # noqa: E402
from cozer import analyzer  # noqa: E402
from cozer.store import (  # noqa: E402
    EventStore, apply_op, to_jsonable, from_jsonable, dumps, loads,
    atomic_write, read_legacy_coz,
)


# --- JSON codec ------------------------------------------------------------

def test_codec_roundtrip_and_idempotent():
    ed = {
        "title": "T",
        "record": {"O-125": {"1": [{"starttime": 1.0, "course": [1000, 1000]},
                                    {1: [(1, 10.0)], "F2": [(1, 11.0), (-1, 2.0)]}]}},
        "savechecked": {"O-125": 1, ("O-125", "1"): 1},   # mixed str + tuple keys
    }
    j = to_jsonable(ed)
    back = from_jsonable(json.loads(json.dumps(j)))
    # tuple marks -> lists; int id key -> str id
    assert back["record"]["O-125"]["1"][1]["1"] == [[1, 10.0]]
    assert back["record"]["O-125"]["1"][1]["F2"] == [[1, 11.0], [-1, 2.0]]
    # tuple dict key preserved losslessly via $map
    assert back["savechecked"][("O-125", "1")] == 1
    assert back["savechecked"]["O-125"] == 1
    # re-encoding is stable (idempotent)
    assert to_jsonable(back) == j


def test_codec_reserved_map_key_roundtrips():
    # A dict that literally contains the reserved "$map" tag must not be mistaken
    # for a tuple-keyed encoding on decode -- it used to crash ({"$map": "x"}) or
    # silently corrupt ({"$map": [["a", 1]]} -> {"a": 1}).
    for x in [{store._MAP: "hello"}, {store._MAP: [["a", 1]]},
              {store._MAP: "v", "other": 2}, {"configure": {store._MAP: "x"}},
              {("a", "b"): 1}]:
        assert loads(dumps(x)) == x, x
        assert loads(dumps(loads(dumps(x)))) == x         # stable under re-encoding


def test_codec_idempotent_fuzz():
    import random

    def gen(rng, depth=0):
        r = rng.random()
        if depth > 3 or r < 0.3:
            return rng.choice([0, 1, -5, 3.5, "s", store._MAP, True, False, None, ""])
        if r < 0.55:
            return [gen(rng, depth + 1) for _ in range(rng.randint(0, 3))]
        out = {}
        for _ in range(rng.randint(0, 4)):
            kt = rng.random()
            if kt < 0.4:
                k = rng.choice(["a", "b", store._MAP, "x", "1"])
            elif kt < 0.6:
                k = rng.randint(0, 5)
            elif kt < 0.72:
                k = rng.choice([True, False])
            else:
                k = tuple(rng.choice(["p", "q", 1, 2]) for _ in range(rng.randint(1, 2)))
            out[k] = gen(rng, depth + 1)
        return out

    rng = random.Random(20260722)
    for _ in range(1500):
        d1 = dumps(gen(rng))
        assert dumps(loads(d1)) == d1                     # idempotent; never raises


def test_dumps_loads_roundtrip():
    ed = {"a": [1, 2, (3, 4)], "b": {"x": None, "y": True}}
    assert loads(dumps(ed)) == {"a": [1, 2, [3, 4]], "b": {"x": None, "y": True}}


# --- legacy import + analyze-through-store equivalence ---------------------

def _a_legacy_event():
    return sorted(glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")))[0]


def test_read_legacy_coz():
    ed = read_legacy_coz(_a_legacy_event())
    assert isinstance(ed, dict) and "record" in ed


def test_analyze_survives_store_roundtrip():
    ed = read_legacy_coz(_a_legacy_event())
    ss = ed.get("scoringsystem", [])
    ed2 = loads(dumps(ed))   # through the JSON store form
    cl = sorted(ed["record"])[0]
    h = sorted(ed["record"][cl])[0]
    import copy
    r1 = analyzer.analyze(h, copy.deepcopy(ed["record"][cl][h]), ss)
    r2 = analyzer.analyze(h, copy.deepcopy(ed2["record"][cl][h]), ss)
    assert golden_io.canon(r1) == golden_io.canon(r2)


# --- atomic write ----------------------------------------------------------

def test_atomic_write_writes_and_cleans_up(tmp_path):
    p = str(tmp_path / "f.txt")
    atomic_write(p, "hello")
    assert open(p, encoding="utf-8").read() == "hello"
    atomic_write(p, b"bytes-ok")
    assert open(p, "rb").read() == b"bytes-ok"
    assert not [n for n in os.listdir(str(tmp_path)) if n.startswith(".coztmp-")]


def _raise(*a, **k):
    raise OSError("simulated failure")


def test_atomic_write_failure_preserves_original(tmp_path, monkeypatch):
    p = str(tmp_path / "f.txt")
    atomic_write(p, "ORIGINAL")
    monkeypatch.setattr(os, "replace", _raise)
    with pytest.raises(OSError):
        atomic_write(p, "NEW-should-not-land")
    assert open(p, encoding="utf-8").read() == "ORIGINAL"          # untouched
    assert not [n for n in os.listdir(str(tmp_path)) if n.startswith(".coztmp-")]


def test_atomic_write_cleanup_unlink_failure_still_raises(tmp_path, monkeypatch):
    p = str(tmp_path / "f.txt")
    atomic_write(p, "ORIG")
    monkeypatch.setattr(os, "replace", _raise)   # trigger the except branch
    monkeypatch.setattr(os, "unlink", _raise)    # and the cleanup unlink also fails
    with pytest.raises(OSError):
        atomic_write(p, "NEW")
    assert open(p, encoding="utf-8").read() == "ORIG"


def test_atomic_write_survives_dir_fsync_open_failure(tmp_path, monkeypatch):
    p = str(tmp_path / "f.txt")
    real_open = os.open

    def fake_open(path, flags, *a, **k):
        if flags == os.O_RDONLY:          # the directory-fsync open only
            raise OSError("no dir fd")
        return real_open(path, flags, *a, **k)

    monkeypatch.setattr(os, "open", fake_open)
    atomic_write(p, "data")               # must still succeed (dir fsync skipped)
    assert open(p, encoding="utf-8").read() == "data"


# --- apply_op --------------------------------------------------------------

def test_apply_op_all_kinds_and_unknown():
    ed = {}
    apply_op(ed, {"op": "field", "key": "title", "value": "T"})
    assert ed["title"] == "T"
    apply_op(ed, {"op": "heat", "cl": "C", "h": "1", "info": {"course": [1000]}, "ids": ["1"]})
    assert ed["record"]["C"]["1"] == [{"course": [1000]}, {"1": []}]
    apply_op(ed, {"op": "info", "cl": "C", "h": "1", "key": "starttime", "value": 5.0})
    assert ed["record"]["C"]["1"][0]["starttime"] == 5.0
    apply_op(ed, {"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": [1, 10.0]})
    assert ed["record"]["C"]["1"][1]["1"] == [[1, 10.0]]
    apply_op(ed, {"op": "replace", "cl": "C", "h": "1", "id": "1", "marks": [[1, 9.0], [1, 8.0]]})
    assert ed["record"]["C"]["1"][1]["1"] == [[1, 9.0], [1, 8.0]]
    apply_op(ed, {"op": "editmark", "cl": "C", "h": "1", "id": "1", "index": 0, "mark": [-1, 9.0]})
    assert ed["record"]["C"]["1"][1]["1"][0] == [-1, 9.0]
    apply_op(ed, {"op": "editmark", "cl": "C", "h": "1", "id": "1", "index": 0, "mark": None})
    assert ed["record"]["C"]["1"][1]["1"] == [[1, 8.0]]
    with pytest.raises(ValueError):
        apply_op(ed, {"op": "nope"})


# --- EventStore: recovery / power loss -------------------------------------

def test_journal_replay_recovers_laps_after_power_loss(tmp_path):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {}})
    s.record({"op": "heat", "cl": "O-125", "h": "1", "info": {"course": [1000]}, "ids": ["1", "2"]})
    s.snapshot()                       # durable snapshot WITH the heat, journal cleared
    s.record({"op": "lap", "cl": "O-125", "h": "1", "id": "1", "mark": [1, 10.0]})
    s.record({"op": "lap", "cl": "O-125", "h": "1", "id": "1", "mark": [1, 11.0]})
    assert os.path.exists(s.journal_path)
    # CRASH: no snapshot after the laps, so they live only in the journal. Recovery
    # normally runs in a FRESH process (the crashed one's file handles are gone);
    # release this store's handle to match, so the journal can be rewritten on any
    # OS (Windows refuses to remove a file another handle still holds open).
    s.close()
    s2 = EventStore.open(p)
    assert s2.eventdata["record"]["O-125"]["1"][1]["1"] == [[1, 10.0], [1, 11.0]]
    assert not os.path.exists(s2.journal_path)   # folded into the snapshot on open


def test_truncated_final_journal_line_is_skipped(tmp_path):
    p = str(tmp_path / "e.cozj")
    EventStore(p, {"record": {"C": {"1": [{}, {"1": []}]}}}).snapshot()
    with open(p + ".journal", "w", encoding="utf-8") as f:
        f.write(json.dumps({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": [1, 9.0]}) + "\n")
        f.write("\n")                                              # blank line (skipped)
        f.write('{"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": [1, ')   # torn line
    s = EventStore.open(p)
    assert s.eventdata["record"]["C"]["1"][1]["1"] == [[1, 9.0]]   # complete op only


# --- EventStore: crash INSIDE snapshot() (staged-snapshot fence) -----------

def _crash_snapshot_before_install(s, p, monkeypatch):
    """Run snapshot() but simulate a power loss at the final atomic install: the
    new state reaches ``<path>.new`` and the journal is removed, but ``<path>`` is
    not swapped. Restores os.replace afterwards so the recovery open() works."""
    real = os.replace

    def flaky(src, dst):
        if os.path.abspath(dst) == os.path.abspath(p):     # the final install step only
            raise RuntimeError("power loss")
        return real(src, dst)

    monkeypatch.setattr(os, "replace", flaky)
    with pytest.raises(RuntimeError):
        s.snapshot()
    monkeypatch.undo()                                     # recovery open() needs real os.replace


def test_snapshot_crash_before_install_no_double_apply_editmark(tmp_path, monkeypatch):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": [["A"], ["B"], ["C"]]}]}}})
    s.snapshot()                                           # marks in snapshot, journal cleared
    s.record({"op": "editmark", "cl": "C", "h": "1", "id": "1", "index": 1, "mark": None})
    assert s.eventdata["record"]["C"]["1"][1]["1"] == [["A"], ["C"]]
    _crash_snapshot_before_install(s, p, monkeypatch)
    assert os.path.exists(p + ".new")                      # staged snapshot survived the crash
    got = EventStore.open(p).eventdata["record"]["C"]["1"][1]["1"]
    assert got == [["A"], ["C"]]                           # NOT [["A"]] -- delete not re-applied
    assert not os.path.exists(p + ".new") and not os.path.exists(p + ".journal")


def test_snapshot_crash_before_install_no_double_apply_lap(tmp_path, monkeypatch):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"7": [["M1"]]}]}}})
    s.snapshot()
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "7", "mark": ["M2"]})
    _crash_snapshot_before_install(s, p, monkeypatch)
    got = EventStore.open(p).eventdata["record"]["C"]["1"][1]["7"]
    assert got == [["M1"], ["M2"]]                         # NOT [["M1"], ["M2"], ["M2"]]


def test_torn_staged_snapshot_is_discarded(tmp_path):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": [["A"]]}]}}})
    s.snapshot()                                           # good snapshot [A], no journal
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["B"]})
    with open(p + ".new", "w", encoding="utf-8") as f:
        f.write('{"record": {"C": {"1": [{}, {"1": [["A"], ["B"')   # torn write: invalid JSON
    s2 = EventStore.open(p)
    assert s2.eventdata["record"]["C"]["1"][1]["1"] == [["A"], ["B"]]  # snapshot + journal recover
    assert not os.path.exists(p + ".new")


def test_journal_creation_dir_fsync_is_deferred_once(tmp_path, monkeypatch):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": []}]}}}, sync_interval=3600)  # syncer idle
    s.snapshot()                                           # no journal yet
    calls = []
    monkeypatch.setattr(store, "_fsync_dir", lambda d: calls.append(d))
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["A"]})   # creates the journal
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["B"]})   # appends
    assert calls == []                                     # record() defers the dir fsync too
    s._flush()
    assert len(calls) == 1                                 # dir fsync once (on creation), via the syncer
    s._flush()
    assert len(calls) == 1                                 # nothing new -> no extra dir fsync
    s.close()


# --- EventStore: systematic crash fault-injection --------------------------

_FI_SYS = {"fsync": os.fsync, "replace": os.replace, "remove": os.remove}


class _Boom(Exception):
    pass


class _CrashAt:
    """Raise _Boom on the N-th fsync/replace/remove call -- a simulated crash at
    that exact durability syscall."""
    def __init__(self, at):
        self.at, self.n = at, 0

    def _wrap(self, name):
        f = _FI_SYS[name]

        def w(*a, **k):
            self.n += 1
            if self.n == self.at:
                raise _Boom("%s#%d" % (name, self.n))
            return f(*a, **k)
        return w

    def __enter__(self):
        for name in _FI_SYS:
            setattr(os, name, self._wrap(name))
        return self

    def __exit__(self, *exc):
        for name, f in _FI_SYS.items():
            setattr(os, name, f)


def _release(store):
    """Simulate the process dying: the OS closes the store's file handles."""
    store._stop.set()
    if store._jfh is not None:
        try:
            store._jfh.close()
        except OSError:
            pass
        store._jfh = None


def _disk(d):
    out = {}
    for f in os.listdir(d):
        with open(os.path.join(d, f), "rb") as fh:
            out[f] = fh.read()
    return out


def _restore(d, snap):
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    for f, data in snap.items():
        with open(os.path.join(d, f), "wb") as fh:
            fh.write(data)


_FI_HEAT = {"record": {"C": {"1": [{}, {"1": [["A"], ["B"], ["C"]], "2": [["X"]]}]}}}
_FI_SCENARIOS = [
    # non-idempotent ops (the corruption-catchers): a re-applied delete / lap-append
    ("editmark-delete", _FI_HEAT,
     [{"op": "editmark", "cl": "C", "h": "1", "id": "1", "index": 1, "mark": None}]),
    ("lap-append", _FI_HEAT,
     [{"op": "lap", "cl": "C", "h": "1", "id": "2", "mark": ["Y"]},
      {"op": "lap", "cl": "C", "h": "1", "id": "2", "mark": ["Z"]}]),
    # a heat op resets its marks (re-apply reconstructs), replace is idempotent
    ("new-heat", {"record": {}},
     [{"op": "heat", "cl": "C", "h": "1", "info": {"course": [1000]}, "ids": ["1", "2"]},
      {"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["A"]}]),
    ("replace", _FI_HEAT,
     [{"op": "replace", "cl": "C", "h": "1", "id": "1", "marks": [["P"], ["Q"]]}]),
]


def test_snapshot_and_recovery_crash_at_every_syscall(tmp_path):
    """Crash at every fsync/replace/remove during snapshot() AND during the
    recovery open(), then a clean reopen must reconstruct the exact pre-snapshot
    state -- never a lost or duplicated op. Guards the ordering fences in both
    snapshot() and _install_staged (this found a recovery-path double-apply)."""
    def build(path, baseline, ops):
        s = EventStore(path, copy.deepcopy(baseline), sync_interval=3600)  # syncer idle
        s.snapshot()                       # durable baseline, journal cleared
        for op in ops:
            s.record(op)                   # journaled (write+flush)
        return s

    mismatches = []
    for i, (label, baseline, ops) in enumerate(_FI_SCENARIOS):
        d = str(tmp_path / ("sc%d" % i))
        os.makedirs(d)
        p = os.path.join(d, "e.cozj")
        s0 = build(p, baseline, ops)
        expect = copy.deepcopy(s0.eventdata)                        # S1 snapshot() must persist
        _release(s0)   # close its journal handle: Windows won't remove/rewrite an open file
        for at in range(1, 25):
            s2 = build(p, baseline, ops)
            _release(s2)
            crashed = False
            try:
                with _CrashAt(at):
                    s2.snapshot()
            except _Boom:
                crashed = True
            _release(s2)
            crashed_disk = _disk(d)

            rec = EventStore.open(p)                       # clean recovery -> must be S1
            if copy.deepcopy(rec.eventdata) != expect:
                mismatches.append((label, "snap@%d" % at))
            _release(rec)

            for rat in range(1, 20):                       # crash during recovery too
                _restore(d, crashed_disk)
                rcrashed = False
                try:
                    with _CrashAt(rat):
                        _release(EventStore.open(p))
                except _Boom:
                    rcrashed = True
                r2 = EventStore.open(p)                     # clean reopen after recovery-crash
                if copy.deepcopy(r2.eventdata) != expect:
                    mismatches.append((label, "snap@%d+rec@%d" % (at, rat)))
                _release(r2)
                if not rcrashed:
                    break
            if not crashed:
                break
    assert not mismatches, mismatches


# --- EventStore: background fsync (responsive recording) -------------------

def _count_fsyncs(monkeypatch):
    """Count os.fsync calls, ignoring the directory fsync so only JOURNAL fsyncs
    are counted."""
    monkeypatch.setattr(store, "_fsync_dir", lambda d: None)
    n = [0]
    real = os.fsync
    monkeypatch.setattr(os, "fsync", lambda fd: [n.__setitem__(0, n[0] + 1), real(fd)][1])
    return n


def test_record_defers_fsync_and_flush_coalesces(tmp_path, monkeypatch):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": []}]}}}, sync_interval=3600)  # syncer idle
    s.snapshot()
    n = _count_fsyncs(monkeypatch)
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["A"]})
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["B"]})
    assert n[0] == 0                     # record() never fsyncs the journal itself
    s._flush()
    assert n[0] == 1                     # one coalesced fsync for both appends
    s.close()


def test_deferred_op_survives_app_crash(tmp_path):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": []}]}}}, sync_interval=3600)
    s.snapshot()
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["A"]})
    # APP CRASH: no close(), no snapshot, no fsync. write()+flush() already put the
    # line in the journal file, so a fresh open() still recovers it.
    got = EventStore.open(p).eventdata["record"]["C"]["1"][1]["1"]
    assert got == [["A"]]


def test_background_thread_fsyncs_within_interval(tmp_path):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": []}]}}}, sync_interval=0.01)
    s.snapshot()
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["A"]})
    for _ in range(200):                 # the daemon syncer clears _dirty within a few ticks
        if not s._dirty:
            break
        time.sleep(0.01)
    assert s._dirty is False
    s.close()


def test_close_flushes_pending_and_is_idempotent(tmp_path, monkeypatch):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"record": {"C": {"1": [{}, {"1": []}]}}}, sync_interval=3600)
    s.snapshot()
    n = _count_fsyncs(monkeypatch)
    s.record({"op": "lap", "cl": "C", "h": "1", "id": "1", "mark": ["A"]})
    assert n[0] == 0                     # deferred
    s.close()
    assert n[0] == 1                     # close() fsyncs the pending write
    s.close()                            # idempotent: no error, nothing left to do
    assert n[0] == 1


def test_open_missing_file_uses_default(tmp_path):
    p = str(tmp_path / "new.cozj")
    s = EventStore.open(p, default={"record": {}, "title": "fresh"})
    assert s.eventdata["title"] == "fresh"


def test_snapshot_rotates_backups(tmp_path):
    p = str(tmp_path / "e.cozj")
    s = EventStore(p, {"n": 0})
    s.snapshot()
    s.eventdata["n"] = 1
    s.snapshot()
    s.eventdata["n"] = 2
    s.snapshot()
    assert loads(open(p, encoding="utf-8").read())["n"] == 2
    assert loads(open(p + ".bak1", encoding="utf-8").read())["n"] == 1
    assert loads(open(p + ".bak2", encoding="utf-8").read())["n"] == 0
