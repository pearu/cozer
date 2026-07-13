"""Tests for the crash-safe persistence layer (cozer/store.py), including
atomic-write failure and power-loss (journal replay) simulations."""
import glob
import json
import os
import sys

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
    # CRASH: no snapshot after the laps. A fresh open must recover them.
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
