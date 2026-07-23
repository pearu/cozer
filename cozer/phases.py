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

from cozer.classes import getclass, note_legacy_read
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
    ``numbers`` (a repeated number marks a restart).

    A phase read from a legacy record also carries **provenance** — the original
    ``legacy_class`` name and the per-heat ``heatids`` strings — so the compat view
    (:func:`to_legacy`) reproduces the *exact* legacy identity instead of a
    canonicalized guess. This matters because legacy class/heat suffixes have
    non-canonical variants (``cozer/classes.py`` accepts ``/Q \\Q /q \\q`` and the
    ``/T`` family "to match legacy exactly"), and a kind can also come from a
    ``!hint`` on an unsuffixed name — re-synthesizing would rename such a class (or,
    if two collapse onto one, drop a class's heats). Forward-created phases (step 2+,
    no legacy origin) leave these ``None`` and :func:`to_legacy` synthesizes canonical
    ids via :func:`synth_heat_id` / :func:`_legacy_class_name`."""

    __slots__ = ("kind", "pattern", "heats", "numbers", "legacy_class", "heatids")

    def __init__(self, kind, pattern, heats, numbers, legacy_class=None, heatids=None):
        self.kind = kind
        self.pattern = pattern
        self.heats = heats            # [[info, boats], ...] — legacy heat records, untouched
        self.numbers = numbers        # [int, ...] parallel to heats; repeats = restarts
        self.legacy_class = legacy_class  # original class-name string, or None (forward-created)
        self.heatids = heatids        # original heat-id strings parallel to heats, or None

    def __repr__(self):
        return "Phase(%r, heats=%d)" % (self.kind, len(self.heats))

    def __eq__(self, other):
        return (isinstance(other, Phase) and self.kind == other.kind and
                self.pattern == other.pattern and self.heats == other.heats and
                self.numbers == other.numbers and
                self.legacy_class == other.legacy_class and self.heatids == other.heatids)

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
    for a circuit (or endurance) original / 1st restart / 2nd restart. This is the
    **forward** direction — the compat view for a legacy-read phase reuses that phase's
    preserved ``heatids`` instead. Step 2 uses this to mint ids for phases that have no
    legacy origin, where legacy-addressed consumers still need a heat-id string whose
    last char encodes the sub-kind."""
    if kind == "timetrial":
        return "%dt" % number
    if kind == "qualification":
        return "%dq" % number
    return "%d%s" % (number, _CIRCUIT_RESTART[rank])


def heat_number(heat_id):
    """The heat number encoded in a legacy heat id: ``'1'``/``'1r'``/``'1R'`` → 1,
    ``'2t'`` → 2, ``'3q'`` → 3. Centralizes the suffix decoding so a consumer (e.g.
    the timer) does not special-case ``h[-1]``."""
    return _parse_heat_id(heat_id)[0]


def heat_label(heat_id):
    """A heat id as *displayed*: the bare number for a time-trial/qualification heat (``'1t'``→``'1'``,
    ``'3q'``→``'3'`` — the phase kind is shown separately, so the ``t``/``q`` would be a redundant leak),
    and UIM restart notation for a circuit heat (``'1'``→``'1'``, ``'1r'``→``'1R'``, ``'1R'``→``'1R2'``).
    The single source for this mapping (reports + the live feed both use it)."""
    number, suffix = _parse_heat_id(heat_id)
    return "%d%s" % (number, {"r": "R", "R": "R2", "t": "", "q": ""}.get(suffix, suffix))


def phase_heat_ids(phase):
    """The legacy heat id per heat record in this phase, in results-list order — the
    phase's preserved originals, or canonically synthesized (:func:`synth_heat_id`)
    for a forward-created phase. This is the sequence a consumer iterates in place of
    ``sorted(record[cl].keys())``, and each id still carries the sub-kind/restart last
    char that ``analyze`` dispatches on."""
    if phase.heatids is not None:
        return list(phase.heatids)
    ids, seen = [], {}
    for number in phase.numbers:
        rank = seen.get(number, 0)
        seen[number] = rank + 1
        ids.append(synth_heat_id(phase.kind, number, rank))
    return ids


def canonical_record(phase, number):
    """``(heat_id, [info, boats])`` for ``number``'s canonical record in ``phase`` —
    the **last non-empty** one (an empty restart is skipped, §5.2) — or ``None`` if the
    number has no non-empty record. Shared by the seeding and qualification layers."""
    same = [(h, rec) for h, rec, num in zip(phase_heat_ids(phase), phase.heats, phase.numbers)
            if num == number]
    for h, rec in reversed(same):
        if any(rec[1].values()):                 # rec = [info, boats]; some boat has marks
            return h, rec
    return None


def phase_heat_map(phase):
    """``{heat_id: [info, boats]}`` for this phase — the legacy per-class heat dict
    restricted to this phase. For a legacy-read phase this is exactly the original
    ``record[legacy_class]`` (same heat-id keys, same record objects), so a consumer
    can swap ``record[cl]`` for ``phase_heat_map(phase)`` with no change in behavior."""
    ids = phase_heat_ids(phase)
    if len(set(ids)) != len(ids):
        # Legacy-read phases can't collide (ids are preserved dict keys). This only
        # trips a forward-created time-trial/qualification phase with a *repeated*
        # number: synth_heat_id ignores rank for t/q, so its ids would clash and a
        # record would be silently dropped. Fail loudly instead (a t/q phase has no
        # restarts, so repeated numbers are a construction bug). (7948e787 review.)
        raise ValueError("phase %r has duplicate heat ids %r" % (phase.kind, ids))
    return dict(zip(ids, phase.heats))


def to_phases(eventdata):
    """Group ``eventdata['record']`` into ``{base_class: [Phase, ...]}``.

    Classes sharing a base (``F-4`` and ``F-4/T``) collapse to one entry whose
    phases are ordered time-trial → qualification → finals. Reads ``eventdata`` for
    each class's kind/pattern (``race_kind``/``class_pattern``); does not mutate it.
    Lossless — :func:`to_legacy` inverts it exactly.

    Handles BOTH event shapes during the suffix migration: the suffix-free native shape
    (``schema >= 2``: ``classes`` grouped, ``record[base][kind][number]``) and the legacy
    suffixed shape. Either way the returned ``Phase`` objects carry a synthesized
    ``legacy_class``/``heatids`` so every phases-based consumer sees an unchanged interface."""
    if eventdata.get("schema", 1) >= 2:
        return _to_phases_native(eventdata)
    note_legacy_read("to_phases")     # legacy shape -> import path / equivalence tests only
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
            # Preserve the exact legacy class name and heat ids so to_legacy is a
            # true inverse for every input, not only canonically-suffixed ones.
            phases.append(Phase(kind, pattern, heats, numbers,
                                legacy_class=cl, heatids=ordered))
        phases.sort(key=lambda p: _KIND_ORDER.get(p.kind, 2))
        out[base] = phases
    return out


def _native_pattern(ph):
    """The full pattern string of a native phase dict (re-appends the qualifiers token)."""
    pat = ph.get("pattern", "") or ""
    if ph.get("qualifiers"):
        pat = "%s!qualification[%s]" % (pat, ",".join(str(c) for c in ph["qualifiers"]))
    return pat


def _to_phases_native(eventdata):
    """``to_phases`` for the suffix-free native shape: ``classes`` = ``[{name, phases:[…]}]``
    and ``record[base][kind][number] = [records]`` (a restart is an extra list entry). Like the
    legacy path this is **record-based** — a phase appears only if it has a record — and builds
    the same ``Phase`` objects with a *synthesized* canonical ``legacy_class``/``heatids``, so
    phases-based consumers are unchanged while the storage is native."""
    record = eventdata.get("record", {}) or {}
    patterns = {}                                        # (base, kind) -> full pattern, from classes
    for entry in eventdata.get("classes", []) or []:
        for ph in entry.get("phases", []) or []:
            patterns[(entry.get("name"), ph["kind"])] = _native_pattern(ph)
    out = {}
    for base, kinds in record.items():
        phases = []
        for kind, kd in kinds.items():                   # kd = {number: [records]}
            heats, numbers, heatids = [], [], []
            for num in sorted(kd, key=int):
                for rank, rec in enumerate(kd[num]):
                    heats.append(rec)
                    numbers.append(int(num))
                    heatids.append(synth_heat_id(kind, int(num), rank))
            phases.append(Phase(kind, patterns.get((base, kind)), heats, numbers,
                                legacy_class=_legacy_class_name(base, kind), heatids=heatids))
        phases.sort(key=lambda p: _KIND_ORDER.get(p.kind, 2))
        out[base] = phases
    return out


def class_phase_map(eventdata):
    """``{legacy_class_name: Phase}`` for every class in the record — the per-class
    phase lookup a consumer uses to dispatch on ``phase.kind`` and address a class's
    heats without re-inferring the kind from the class/heat suffix."""
    out = {}
    for phases in to_phases(eventdata).values():
        for ph in phases:
            out[ph.legacy_class] = ph
    return out


def to_legacy(phases_by_base):
    """Reconstruct the legacy ``{class: {heat_id: [info, boats]}}`` record from a
    phase grouping — the **compat view**. Exact inverse of :func:`to_phases`: each
    class re-suffixed from its preserved ``legacy_class`` (or ``phase.kind`` for a
    forward-created phase) and its heats keyed by :func:`phase_heat_ids`, so a
    legacy-addressed consumer sees no change."""
    record = {}
    for base, phases in phases_by_base.items():
        for ph in phases:
            # Prefer preserved provenance (exact legacy identity); synthesize only for
            # a forward-created phase with no legacy origin (step 2+).
            cl = ph.legacy_class if ph.legacy_class is not None else _legacy_class_name(base, ph.kind)
            record[cl] = phase_heat_map(ph)
    return record


def _legacy_class_name(base, kind):
    """Canonical legacy class name for a phase kind (``F-4`` → ``F-4/T``). The
    **forward** path only — used for a forward-created phase with no legacy origin
    (step 2+). A phase read from a legacy record preserves its original
    ``legacy_class`` (see :func:`to_legacy`), so non-canonical variants (``\\T``,
    ``/q``) and hint-derived kinds round-trip exactly rather than being renamed."""
    if kind == "timetrial":
        return base + "/T"
    if kind == "qualification":
        return base + "/Q"
    return base
