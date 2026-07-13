"""Robust, crash-safe persistence for cozer events (see MAINTENANCE_PLAN.md
sections 3 and 9). This is the *safety kernel*: recording durability must not
depend on analysis, reporting, or the GUI.

Guarantees:

- **Atomic snapshots** — the canonical event file is written temp + ``fsync`` +
  ``os.replace`` (atomic on Linux and Windows), so an interrupted write can
  never corrupt the last good file. Rotating backups (``.bak1..N``) are kept.
- **Append-only journal** — every recorded mutation is appended to a JSONL
  journal and ``fsync``-ed immediately, so a power loss between snapshots loses
  nothing: on open, snapshot + journal replay reconstructs the full state. A
  partially written final journal line (torn by a crash) is skipped.
- **Human-readable** — the snapshot is JSON (UTF-8), inspectable and
  hand-recoverable. Legacy ``.coz`` (pickle) remains importable.
"""
import json
import os
import pickle
import shutil
import tempfile

_MAP = "$map"   # reserved tag for dicts with non-string/int (e.g. tuple) keys


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

    ``record(op)`` mutates the in-memory eventdata and durably journals the op.
    ``snapshot()`` writes an atomic snapshot, rotates backups, and clears the
    journal. ``open()`` loads the snapshot and replays any journal (recovery).
    """

    def __init__(self, path, eventdata):
        self.path = path
        self.journal_path = path + ".journal"
        self.eventdata = eventdata

    @classmethod
    def open(cls, path, default=None):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                eventdata = loads(f.read())
        else:
            eventdata = {} if default is None else default
        store = cls(path, eventdata)
        if store._replay_journal():
            store.snapshot()   # fold recovered ops into a fresh snapshot
        return store

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
        """Apply an op in memory AND append it durably (fsync) to the journal."""
        apply_op(self.eventdata, op)
        line = json.dumps(op, ensure_ascii=False) + "\n"
        with open(self.journal_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def snapshot(self):
        """Atomically persist eventdata, rotate backups, and clear the journal."""
        _rotate_backups(self.path)
        atomic_write(self.path, dumps(self.eventdata))
        try:
            os.remove(self.journal_path)
        except OSError:
            pass
