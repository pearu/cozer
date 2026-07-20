"""Class-name predicates, ported from legacy cozer/prefs.py.

A class name may carry a ``/Q`` (qualification) or ``/T`` (time-trial) suffix.
Return ints (1/0) to match legacy exactly.
"""

_Q = ('/Q', r'\Q', '/q', r'\q')
_T = ('/T', r'\T', '/t', r'\t')


# --- diagnostic: legacy-shape decode tracer ---------------------------------
# The suffix refactor (through stage 3d) left a small "dual-shape" layer: a few decoders that
# read the legacy (suffixed) event shape. The in-memory model is fully native now, so those
# decoders must run ONLY while importing a legacy `.coz` (via native.to_native) — never in normal
# native operation. Each such branch calls note_legacy_read(); the guard test
# (test_legacy_decoders_are_import_only) asserts a full native workflow leaves this empty while a
# `.coz` import populates it. Cost is zero in native operation — the calls live inside the legacy
# branches, which native data never enters.
legacy_reads = []


def note_legacy_read(where):
    """Record that a legacy-shape decoder ran; ``where`` is a short tag (see the module note)."""
    legacy_reads.append(where)


def isqclass(cl):
    return 1 if cl[-2:] in _Q else 0


def istclass(cl):
    return 1 if cl[-2:] in _T else 0


def gettclass(cl):
    return cl[:-2] if cl[-2:] in _T else cl


def getqclass(cl):
    return cl[:-2] if cl[-2:] in _Q else cl


def getclass(cl):
    return cl[:-2] if (isqclass(cl) or istclass(cl)) else cl
