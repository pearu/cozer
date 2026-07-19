"""Derived start order — PHASES.md §8 step 3 / §5.

``start_order(eventdata, cl, heat)`` returns the ordered boat-id list for a heat's
**start / jetty positions**, DERIVED (never stored) from earlier results.

Rules implemented (§5 / §5.1):
- **base case** (a phase's first heat, no predecessor) = the participant order in
  Classes & Participants;
- **circuit heat N → N+1** = the finishing order (``getresorder``) of heat N-1's
  canonical (last non-empty) record — take-last restart (§5.2), empties skipped;
- **time-trial → finals** = the time-trial ranking, fastest best-lap first (307.01 /
  decision A);
- **qualification → finals** = ``[primary-Q by time-trial time]`` then
  ``[repechage-Q by time-trial time]``, DNQ excluded (§5.1). The **time-trial** phase
  supplies the *ordering* (decision A, even through an intervening qualification
  phase); the **qualification** phase supplies *membership + the repechage split*
  (``cozer.qualification.classify``). If no time-trial phase is recorded, ordering
  falls back to the qualification's best-lap rank under the same split (rare — a time
  trial is mandatory whenever qualification runs, 305.04.03).

Phase structure + predecessors come from the **class catalog** (``eventdata['classes']``)
so a heat can be seeded *before it is raced*; rankings come from the preceding phases'
**records**. Consumers (report start-list, timer ladder) are a later increment; the
timer button grid stays boat-number (§5, rev 29). Pure and read-only.
"""
from cozer.analyzer import analyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import canonical_record, class_phase_map, heat_number, phase_heat_ids
from cozer.qualification import classify
from cozer.racepattern import get_classes, race_kind

_KIND_ORDER = {"timetrial": 0, "qualification": 1}   # finals/endurance sort last


def start_order(eventdata, cl, heat):
    """Ordered boat-id list (strings) for class ``cl``'s ``heat`` start positions."""
    ph = class_phase_map(eventdata).get(cl)
    # Intra-phase heat N -> N+1 seeding applies ONLY to a CONTINUATION phase (circuit /
    # finals / endurance): heat N is seeded by heat N-1's finishing order. A qualification
    # phase's qheats are DISJOINT groups, not a sequence (§5.1), and time-trial sessions
    # run solo -- so those are seeded cross-phase (from the time trial), never from the
    # previous heat number.
    if heat_number(heat) > 1 and ph is not None and ph.kind in ("circuit", "endurance"):
        prev = canonical_record(ph, heat_number(heat) - 1)
        if prev is not None:
            return _rank(eventdata, *prev)
    # first heat, or a non-continuation phase: cross-phase seed, else base case.
    seeded = _cross_phase_seed(eventdata, cl)
    return seeded if seeded is not None else _participant_order(eventdata, cl)


def _cross_phase_seed(eventdata, cl):
    """First-heat cross-phase seed, or ``None`` (caller falls back to the base case).
    A qualification predecessor -> qualification -> finals; else a time-trial
    predecessor -> time-trial -> finals."""
    seq = _catalog_phases(eventdata).get(getclass(cl), [])
    idx = next((i for i, (c, _k) in enumerate(seq) if c == cl), None)
    if idx is None:
        return None
    preds = seq[:idx]
    qual_cl = next((c for c, k in preds if k == "qualification"), None)
    tt_cl = next((c for c, k in preds if k == "timetrial"), None)
    if qual_cl is not None:
        return _qualification_seed(eventdata, qual_cl, tt_cl)
    if tt_cl is not None:
        tt_ph = class_phase_map(eventdata).get(tt_cl)
        if tt_ph is not None:
            return _best_lap_ranking(eventdata, tt_ph) or None
    return None


def _qualification_seed(eventdata, qual_cl, tt_cl):
    """qualification -> finals grid: ``[primary-Q by TT]`` then ``[repechage-Q by TT]``,
    DNQ excluded. Ordering from the time-trial phase (decision A); if none is recorded,
    fall back to the qualification's own best-lap rank under the same split."""
    labels = classify(eventdata, qual_cl)
    if not labels:
        return None
    src = class_phase_map(eventdata).get(tt_cl) if tt_cl else None
    if src is None:
        src = class_phase_map(eventdata).get(qual_cl)          # no time-trial -> qual rank
    order = _best_lap_ranking(eventdata, src) if src is not None else []
    order = _with_leftovers(order, labels)
    primary = [b for b in order if labels.get(b) == "primary"]
    repechage = [b for b in order if labels.get(b) == "repechage"]
    return primary + repechage                                 # DNQ excluded from the grid


def _with_leftovers(order, labels):
    """Append any qualified boat missing from ``order`` (e.g. no time-trial lap), by
    boat number, so no finalist is dropped from the grid."""
    seen = set(order)
    extra = sorted((b for b in labels if labels[b] != "dnq" and b not in seen), key=_numkey)
    return list(order) + extra


def _catalog_phases(eventdata):
    """``{base_class: [(legacy_class, kind), ...]}`` from the CLASS CATALOG (not the
    record), ordered time-trial → qualification → finals. Lets seeding find a heat's
    phase + predecessors even before that heat is raced."""
    groups = {}
    for cl in get_classes(eventdata):
        groups.setdefault(getclass(cl), []).append((cl, race_kind(eventdata, cl)))
    for seq in groups.values():
        seq.sort(key=lambda ck: _KIND_ORDER.get(ck[1], 2))
    return groups


def _best_lap_ranking(eventdata, phase):
    """A phase's boats by their best lap, fastest first — the analyzer's ``maxlapspeed``
    (higher = better lap; the cross-heat-aggregatable best-lap scalar), taken as the max
    across all the phase's heats. Ties break by boat number. Used for the time-trial
    ranking (307.01) and the no-time-trial qualification fallback."""
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    best = {}
    for hid, rec in zip(phase_heat_ids(phase), phase.heats):
        if not any(rec[1].values()):
            continue
        res = analyze(hid, [dict(rec[0]), rec[1]], ss, rc)     # copy info: analyze memoizes racetime
        for boat, r in res.items():
            sp = r.get("maxlapspeed")
            if sp and sp > 0:
                b = str(boat)
                if b not in best or sp > best[b]:
                    best[b] = sp
    return [b for b in sorted(best, key=lambda b: (-best[b], _numkey(b)))]   # fastest first


def _rank(eventdata, hid, rec):
    """The finishing order (boat-id strings) of a heat record. Read-only: analyze
    memoizes 'racetime' into info, so it runs on a copied info (the boats, rec[1], are
    not mutated -- §6.6 -- so they are shared)."""
    res = analyze(hid, [dict(rec[0]), rec[1]], eventdata.get("scoringsystem", []),
                  rule_action_codes(eventdata))
    return [str(pid) for pid in getresorder(res)]


def _participant_order(eventdata, cl):
    """Base-case start order: the class's participants in Classes & Participants list
    order (the drag-reorderable lot-draw order, §5)."""
    base = getclass(cl)
    return [str(p[5]) for p in eventdata.get("participants", [])
            if len(p) > 5 and p[4] == base and str(p[5]) != ""]


def _numkey(bid):
    """Boat-id sort key: numeric ids ascending, non-numeric ids after them."""
    s = str(bid)
    return (0, int(s)) if s.isdigit() else (1, s)
