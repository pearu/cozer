"""Robust, crash-safe persistence for cozer events (see MAINTENANCE_PLAN.md
sections 3 and 9). This is the *safety kernel*: recording durability must not
depend on analysis, reporting, or the GUI.

Guarantees:

- **Atomic snapshots** — the canonical event file is written temp + ``fsync`` +
  ``os.replace`` (atomic on Linux and Windows), so an interrupted write can
  never corrupt the last good file. Rotating backups (``.bak1..N``) are kept.
- **Append-only journal** — every recorded mutation is appended to a JSONL
  journal (``write`` + ``flush``, so it survives an app/process crash at once)
  and ``fsync``-ed by a background thread within a bounded interval, so a power
  loss between snapshots can lose at most the last few unsynced clicks while
  recording never blocks the GUI thread on ``fsync``. On open, snapshot +
  journal replay reconstructs the full state; a partially written final journal
  line (torn by a crash) is skipped.
- **Human-readable** — the snapshot is JSON (UTF-8), inspectable and
  hand-recoverable. Legacy ``.coz`` (pickle) remains importable.
"""
import json
import os
import pickle
import shutil
import tempfile
import threading
import weakref

_MAP = "$map"   # reserved tag for dicts with non-string/int (e.g. tuple) keys
_JOURNAL = ".journal"   # append-only op-log sidecar
_STAGED = ".new"        # a snapshot captured but not yet installed (crash fence)


# --------------------------------------------------------------------------- #
# JSON codec for eventdata
# --------------------------------------------------------------------------- #
# Tuples serialize as lists and int dict keys as strings (the port indexes race
# marks positionally and uses ids as labels, so neither distinction matters);
# dicts with tuple keys (e.g. legacy ``savechecked``) use the ``$map`` tag so
# they round-trip losslessly. The result is idempotent under re-encoding.

def to_jsonable(obj):
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        if all(isinstance(k, str) for k in obj):
            return {k: to_jsonable(v) for k, v in obj.items()}
        if all(isinstance(k, int) and not isinstance(k, bool) or isinstance(k, str)
               for k in obj):
            return {str(k): to_jsonable(v) for k, v in obj.items()}
        return {_MAP: [[to_jsonable(k), to_jsonable(v)] for k, v in obj.items()]}
    return obj


def from_jsonable(obj):
    if isinstance(obj, list):
        return [from_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        if set(obj) == {_MAP}:
            return {_hashable(from_jsonable(k)): from_jsonable(v) for k, v in obj[_MAP]}
        return {k: from_jsonable(v) for k, v in obj.items()}
    return obj


def _hashable(k):
    return tuple(k) if isinstance(k, list) else k


def dumps(eventdata):
    return json.dumps(to_jsonable(eventdata), ensure_ascii=False, indent=1, sort_keys=True)


def loads(text):
    return from_jsonable(json.loads(text))


def read_legacy_coz(path):
    """Read a legacy ``.coz`` (Python-2 pickle) into an eventdata dict."""
    with open(path, "rb") as f:
        return pickle.load(f, encoding="latin-1")


# --------------------------------------------------------------------------- #
# Atomic file write
# --------------------------------------------------------------------------- #

def atomic_write(path, data):
    """Atomically write ``data`` (str or bytes) to ``path``.

    Writes to a temp file in the same directory, fsyncs it, then ``os.replace``s
    it into place (atomic on POSIX and Windows). On any failure the temp file is
    removed and the original ``path`` is left untouched.
    """
    if isinstance(data, str):
        data = data.encode("utf-8")
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".coztmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    _fsync_dir(directory)


def _fsync_dir(directory):
    # Durability of the rename (POSIX). Not supported on Windows -> ignore.
    try:
        dfd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dfd)
    except OSError:  # pragma: no cover - best-effort dir fsync, platform-dependent
        pass
    finally:
        os.close(dfd)


def _rotate_backups(path, keep=3):
    for i in range(keep, 1, -1):
        src = "%s.bak%d" % (path, i - 1)
        if os.path.exists(src):
            os.replace(src, "%s.bak%d" % (path, i))
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak1")


# --------------------------------------------------------------------------- #
# Journal operations
# --------------------------------------------------------------------------- #

def apply_op(eventdata, op):
    """Apply one journal operation to ``eventdata`` in place."""
    kind = op["op"]
    if kind == "field":
        eventdata[op["key"]] = op["value"]
    elif kind == "heat":
        rec = eventdata.setdefault("record", {})
        rec.setdefault(op["cl"], {})[op["h"]] = [
            dict(op.get("info", {})),
            {i: [] for i in op.get("ids", [])},
        ]
    elif kind == "info":
        eventdata["record"][op["cl"]][op["h"]][0][op["key"]] = op["value"]
    elif kind == "lap":
        eventdata["record"][op["cl"]][op["h"]][1].setdefault(op["id"], []).append(op["mark"])
    elif kind == "replace":
        eventdata["record"][op["cl"]][op["h"]][1][op["id"]] = list(op["marks"])
    elif kind == "editmark":
        marks = eventdata["record"][op["cl"]][op["h"]][1][op["id"]]
        if op.get("mark") is None:
            del marks[op["index"]]
        else:
            marks[op["index"]] = op["mark"]
    else:
        raise ValueError("unknown journal op: %r" % (kind,))


# --------------------------------------------------------------------------- #
# Event store
# --------------------------------------------------------------------------- #

class EventStore:
    """A crash-safe handle to an event's on-disk state.

    ``record(op)`` mutates the in-memory eventdata and journals the op.
    ``snapshot()`` writes an atomic snapshot, rotates backups, and clears the
    journal. ``open()`` loads the snapshot and replays any journal (recovery).

    Recording durability is split so that rapid lap clicks never block the
    caller (the GUI thread) on ``fsync``: ``record()`` appends and ``flush()``es
    the op immediately -- so it survives an app/process crash at once -- and a
    background daemon thread ``fsync``s within ``sync_interval`` seconds, so a
    hard power loss can lose at most the last few unsynced clicks. ``snapshot()``
    and ``close()`` ``fsync`` synchronously, and are the guaranteed-durable
    checkpoints. Callers should ``close()`` on shutdown (or ``snapshot()``); if
    neither runs, a clean process exit still leaves flushed ops in the OS cache.
    """

    # Every live store, so a shutdown hook can flush them and tests can stop the
    # background syncer threads on teardown. WeakSet => no lifetime impact.
    _live = weakref.WeakSet()

    def __init__(self, path, eventdata, sync_interval=0.05):
        self.path = path
        self.journal_path = path + _JOURNAL
        self.eventdata = eventdata
        EventStore._live.add(self)
        self._sync_interval = sync_interval
        self._io_lock = threading.RLock()   # guards _jfh / _dirty across record/snapshot/syncer
        self._jfh = None                    # open journal handle (append mode), or None
        self._dirty = False                 # writes appended but not yet fsynced
        self._dir_fsync_pending = False     # a new journal file whose dir entry needs fsync
        self._stop = threading.Event()
        self._syncer = None                 # background fsync thread, started on first record()

    @classmethod
    def open(cls, path, default=None):
        staged = path + _STAGED
        if os.path.exists(staged):
            recovered = cls._install_staged(path, staged)
            if recovered is not None:
                return cls(path, recovered)   # a snapshot interrupted mid-install, finished
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                eventdata = loads(f.read())
        else:
            eventdata = {} if default is None else default
        store = cls(path, eventdata)
        if store._replay_journal():
            store.snapshot()   # fold recovered ops into a fresh snapshot
        return store

    @staticmethod
    def _install_staged(path, staged):
        """Finish a ``snapshot()`` that a crash interrupted mid-install.

        ``<path>.new`` holds the new state, written and fsynced in full BEFORE the
        old journal was removed, so if it parses it is authoritative: install it
        and drop the now-redundant journal (never replay those ops on top of it).
        A torn ``.new`` (crash mid-write) is discarded, leaving the previous
        snapshot + journal to recover normally. Returns the recovered eventdata,
        or None if ``.new`` was unusable."""
        try:
            with open(staged, encoding="utf-8") as f:
                eventdata = loads(f.read())
        except (ValueError, OSError):
            try:
                os.remove(staged)
            except OSError:
                pass
            return None
        os.replace(staged, path)
        try:
            os.remove(path + _JOURNAL)
        except OSError:
            pass
        _fsync_dir(os.path.dirname(os.path.abspath(path)))
        return eventdata

    def _replay_journal(self):
        if not os.path.exists(self.journal_path):
            return 0
        applied = 0
        with open(self.journal_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    op = json.loads(line)
                except ValueError:
                    break   # torn final line from a crash: stop, keep the rest
                apply_op(self.eventdata, op)
                applied += 1
        return applied

    def record(self, op):
        """Apply an op in memory and append it to the journal.

        The append is ``write`` + ``flush`` (durable against an app/process crash
        immediately) but NOT ``fsync``ed here; the background syncer fsyncs it
        within ``sync_interval`` (durable against power loss). This keeps the
        caller (GUI thread) from ever blocking on ``fsync`` during rapid clicks.
        """
        apply_op(self.eventdata, op)
        line = json.dumps(op, ensure_ascii=False) + "\n"
        with self._io_lock:
            if self._jfh is None:
                if not os.path.exists(self.journal_path):
                    self._dir_fsync_pending = True   # new journal file: its directory entry
                self._jfh = open(self.journal_path, "a", encoding="utf-8")  # needs fsync too
            self._jfh.write(line)
            self._jfh.flush()          # -> OS page cache: survives an app/process crash now
            self._dirty = True         # -> all fsync (data + dir on creation) deferred to the syncer
        self._start_syncer()           # record() itself never fsyncs -> never stalls the caller

    def _start_syncer(self):
        if self._syncer is None:
            self._stop.clear()
            self._syncer = threading.Thread(target=self._sync_loop,
                                            name="cozer-journal-fsync", daemon=True)
            self._syncer.start()

    def _sync_loop(self):
        while not self._stop.wait(self._sync_interval):
            self._flush()

    def _flush(self):
        """fsync unsynced journal writes, holding the lock across the whole fsync.

        The lock is held (rather than fsyncing a dup'd fd outside it) so a
        concurrent ``snapshot()``/``close()`` cannot close the handle or remove the
        journal mid-fsync: on Windows a second open handle blocks the remove, which
        would leave the journal to be replayed a second time. On a healthy disk
        fsync is ~ms; a ``record()`` that collides waits for one fsync, and that
        never compounds across a burst (the burst's writes coalesce into one)."""
        with self._io_lock:
            if not (self._dirty and self._jfh is not None):
                return
            try:
                os.fsync(self._jfh.fileno())
                self._dirty = False
                if self._dir_fsync_pending:   # durably link a freshly created journal file
                    _fsync_dir(os.path.dirname(os.path.abspath(self.path)))
                    self._dir_fsync_pending = False
            except OSError:
                pass                          # transient: stays dirty, retried next tick

    def close(self):
        """Stop the background syncer, fsync anything pending, and close the
        journal handle. Idempotent; safe to call even if nothing was recorded."""
        self._stop.set()
        syncer, self._syncer = self._syncer, None
        if syncer is not None:
            syncer.join(timeout=1.0)
        self._flush()
        with self._io_lock:
            if self._jfh is not None:
                self._jfh.close()
                self._jfh = None

    def snapshot(self):
        """Atomically persist eventdata, rotate backups, and clear the journal.

        Crash-safe against a mid-snapshot power loss. The new state is written in
        full to ``<path>.new`` and fsynced, THEN the now-redundant journal is
        removed, THEN ``.new`` is atomically installed. If a crash interrupts this,
        ``open()`` finds the completed ``.new`` and installs it (dropping the
        journal), so journaled ops are never replayed on top of a snapshot that
        already contains them (which duplicated laps / mis-applied edits)."""
        staged = self.path + _STAGED
        atomic_write(staged, dumps(self.eventdata))   # new state durable before we touch the journal
        _rotate_backups(self.path)
        with self._io_lock:                           # drop the journal atomically vs the syncer
            if self._jfh is not None:
                self._jfh.close()
                self._jfh = None
            self._dirty = False
            try:
                os.remove(self.journal_path)          # journal now redundant (folded into .new)
            except OSError:
                pass
        os.replace(staged, self.path)                 # atomic install
        _fsync_dir(os.path.dirname(os.path.abspath(self.path)))
