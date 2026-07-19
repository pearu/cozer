"""Phase view over the legacy record — PHASES.md §8 step 1 (build & validate only).

A **bidirectional, lossless** transform between the two shapes:

* legacy — ``record[class][heat_id] = [info, boats]``, where the *class* name
  carries a ``/T`` (time-trial) or ``/Q`` (qualification) suffix and the
  *heat id* carries a ``t``/``q`` (sub-kind) or ``r``/``R`` (restart) suffix;
* phases — ``record[base_class] = [Phase, ...]`` (PHASES.md §2/§3), one phase per
  kind, each an ordered results list where a **restart is a repeated number**.

This module does NOT touch the load path or any consumer (analyzer, reports,
timer). It only proves the §3 "blast-radius" claim empirically: ``to_legacy(
to_phases(ed))`` reproduces ``ed['record']`` exactly (same class names, same heat
ids, same ``[info, boats]`` objects), so ``analyze``/``sumanalyze`` and the golden
equivalence tests are unaffected. Making phases the *primary* in-memory shape, and
moving ``analyze``'s ``heat[-1]`` sub-kind switch onto ``phase.kind``, is step 2.

The heat record ``[info, boats]`` is carried through **untouched** — ``info`` is
heterogeneous across events (old files lack ``duration``; some heats have no
``starttime``), so nothing here reads or rewrites its schema. The phase ``number``
that PHASES.md §2 proposes to store in ``info`` is kept in a parallel list here so
the round-trip stays byte-identical; it moves into ``info`` in step 2.
"""
import re

from cozer.classes import getclass
from cozer.racepattern import class_pattern, race_kind

# Phase order within a class (PHASES.md §1: time-trial → qualification → finals).
# Anything else (circuit, endurance) sorts last.
_KIND_ORDER = {"timetrial": 0, "qualification": 1}

# Occurrence rank (0=original, 1=1st restart, 2=2nd restart) → legacy heat-id
# suffix, for a circuit/endurance heat. A 3rd restart never occurs (PHASES.md §1,
# UIM 311.02.2); an out-of-range rank raises, and the round-trip test flags it.
_CIRCUIT_RESTART = ["", "r", "R"]

_HEAT_RE = re.compile(r"^(\d+)([a-zA-Z]?)$")


class Phase(object):
    """One phase of a class: its ``kind``, race ``pattern``, an ordered results
    list of ``[info, boats]`` heat records (``heats``), and the parallel heat
    ``numbers`` (a repeated number marks a restart)."""

    __slots__ = ("kind", "pattern", "heats", "numbers")

    def __init__(self, kind, pattern, heats, numbers):
        self.kind = kind
        self.pattern = pattern
        self.heats = heats            # [[info, boats], ...] — legacy heat records, untouched
        self.numbers = numbers        # [int, ...] parallel to heats; repeats = restarts

    def __repr__(self):
        return "Phase(%r, heats=%d)" % (self.kind, len(self.heats))

    def __eq__(self, other):
        return (isinstance(other, Phase) and self.kind == other.kind and
                self.pattern == other.pattern and self.heats == other.heats and
                self.numbers == other.numbers)

    def __ne__(self, other):
        return not self.__eq__(other)


def _parse_heat_id(hid):
    """``(number, suffix)`` for a legacy heat id — ``'1'``→(1,''), ``'1r'``→(1,'r'),
    ``'3R'``→(3,'R'), ``'2t'``→(2,'t'), ``'1q'``→(1,'q'). Raises ``ValueError`` on
    an unrecognized id (surfaced by the round-trip test rather than silently lost)."""
    m = _HEAT_RE.match(str(hid))
    if not m:
        raise ValueError("unrecognized heat id %r" % (hid,))
    return int(m.group(1)), m.group(2)


def _restart_rank(suffix):
    """Occurrence rank of a circuit heat-id suffix: ``''``→0, ``'r'``→1, ``'R'``→2."""
    return {"": 0, "r": 1, "R": 2}.get(suffix, 0)


def synth_heat_id(kind, number, rank):
    """The legacy heat id for a phase heat — inverse of :func:`_parse_heat_id`.

    ``'2t'``/``'3q'`` for a time-trial/qualification heat; ``'1'``/``'1r'``/``'1R'``
    for a circuit (or endurance) original / 1st restart / 2nd restart. Step 2 uses
    this when phases become primary and legacy-addressed consumers (``analyze``, the
    goldens) still need a heat-id string whose last char encodes the sub-kind."""
    if kind == "timetrial":
        return "%dt" % number
    if kind == "qualification":
        return "%dq" % number
    return "%d%s" % (number, _CIRCUIT_RESTART[rank])


def to_phases(eventdata):
    """Group ``eventdata['record']`` into ``{base_class: [Phase, ...]}``.

    Classes sharing a base (``F-4`` and ``F-4/T``) collapse to one entry whose
    phases are ordered time-trial → qualification → finals. Reads ``eventdata`` for
    each class's kind/pattern (``race_kind``/``class_pattern``); does not mutate it.
    Lossless — :func:`to_legacy` inverts it exactly."""
    record = eventdata.get("record", {}) or {}
    bases = []                        # base-class order = first appearance in record
    by_base = {}                      # base → [legacy_class, ...]
    for cl in record:
        base = getclass(cl)
        if base not in by_base:
            by_base[base] = []
            bases.append(base)
        by_base[base].append(cl)

    out = {}
    for base in bases:
        phases = []
        for cl in by_base[base]:
            kind = race_kind(eventdata, cl)
            pattern = class_pattern(eventdata, cl)
            heatmap = record[cl]      # {heat_id: [info, boats]}
            # Order the results list by (number, restart rank) so a restart follows
            # its original — the sensible phase view; round-trip equality (a dict)
            # is order-independent regardless.
            ordered = sorted(heatmap, key=lambda h: (_parse_heat_id(h)[0],
                                                      _restart_rank(_parse_heat_id(h)[1])))
            heats = [heatmap[h] for h in ordered]
            numbers = [_parse_heat_id(h)[0] for h in ordered]
            phases.append(Phase(kind, pattern, heats, numbers))
        phases.sort(key=lambda p: _KIND_ORDER.get(p.kind, 2))
        out[base] = phases
    return out


def to_legacy(phases_by_base):
    """Reconstruct the legacy ``{class: {heat_id: [info, boats]}}`` record from a
    phase grouping — the **compat view**. Exact inverse of :func:`to_phases`: the
    same class names (re-suffixed from ``phase.kind``) and the same heat ids
    (re-synthesized from number + occurrence rank), so a legacy-addressed consumer
    sees no change."""
    record = {}
    for base, phases in phases_by_base.items():
        for ph in phases:
            cl = _legacy_class_name(base, ph.kind)
            heatmap = {}
            seen = {}                 # number → occurrences so far → restart rank
            for rec, number in zip(ph.heats, ph.numbers):
                rank = seen.get(number, 0)
                seen[number] = rank + 1
                heatmap[synth_heat_id(ph.kind, number, rank)] = rec
            record[cl] = heatmap
    return record


def _legacy_class_name(base, kind):
    """Re-attach the legacy class suffix for a phase kind (``F-4`` → ``F-4/T`` for a
    time-trial phase). Canonical ``/T``/``/Q``; a non-canonical variant (``\\T``)
    would fail the round-trip test rather than pass silently."""
    if kind == "timetrial":
        return base + "/T"
    if kind == "qualification":
        return base + "/Q"
    return base
