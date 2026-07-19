"""Derived start order — PHASES.md §8 step 3 / §5.

``start_order(eventdata, cl, heat)`` returns the ordered boat-id list for a heat's
**start / jetty positions**, DERIVED (never stored) from earlier results::

    start_order(heat) = seed( previous_heat, ranking(previous_heat) )

Rules implemented (§5 / §5.1):
- **base case** (a phase's first heat, no predecessor) = the participant order in
  Classes & Participants;
- **circuit heat N → N+1** = the finishing order (``getresorder``) of heat N-1's
  canonical (last non-empty) record — take-last restart (§5.2), empties skipped;
- **time-trial → finals** (a first heat whose phase is immediately preceded by a
  time-trial phase) = the time-trial ranking, fastest best-lap first (UIM 307.01 /
  decision A).

Because a heat is seeded *before it is raced* (its record does not exist yet), the
phase structure + predecessors come from the **class catalog** (``eventdata['classes']``),
while rankings come from the preceding phase's **record**.

Deferred to a later increment: **qualification → finals** (§5.1) — it needs the
Q/DNQ + repechage machinery, not yet built; a finals whose immediate predecessor is a
qualification phase currently falls back to the base case. Consumers (report
start-list, timer ladder) are also later. The timer button grid stays boat-number
(§5, rev 29) — not a consumer. Pure and read-only: never mutates ``eventdata``.
"""
from cozer.analyzer import analyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, heat_number, phase_heat_ids
from cozer.racepattern import get_classes, race_kind

_KIND_ORDER = {"timetrial": 0, "qualification": 1}   # finals/endurance sort last


def start_order(eventdata, cl, heat):
    """Ordered boat-id list (strings) for class ``cl``'s ``heat`` start positions."""
    if heat_number(heat) > 1:
        # intra-phase: heat N seeded by heat N-1's canonical finishing order.
        ph = class_phase_map(eventdata).get(cl)
        if ph is not None:
            prev = _canonical_record(ph, heat_number(heat) - 1)
            if prev is not None:
                return _rank(eventdata, *prev)
        return _participant_order(eventdata, cl)
    # first heat: seed from an immediately-preceding time-trial phase (decision A),
    # else the base case (participant order).
    tt = _timetrial_seed(eventdata, cl)
    return tt if tt is not None else _participant_order(eventdata, cl)


def _timetrial_seed(eventdata, cl):
    """Time-trial ranking if ``cl``'s phase is immediately preceded by a time-trial
    phase (per the class catalog), else ``None``. UIM 307.01 / decision A: the
    time-trial is the master ordering signal for the first final (and qualifying) heat."""
    seq = _catalog_phases(eventdata).get(getclass(cl), [])
    idx = next((i for i, (c, _k) in enumerate(seq) if c == cl), None)
    if idx is None or idx == 0 or seq[idx - 1][1] != "timetrial":
        return None
    tt_ph = class_phase_map(eventdata).get(seq[idx - 1][0])
    if tt_ph is None:
        return None                              # time-trial not raced yet -> base case
    return _timetrial_ranking(eventdata, tt_ph) or None


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


def _timetrial_ranking(eventdata, phase):
    """Boats by best time-trial lap, fastest first (307.01). The best-lap metric is
    the analyzer's ``maxlapspeed`` (fastest lap speed; higher = better); it is taken
    across all the phase's time-trial heats. Ties break by boat number."""
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    best = {}                                    # boat -> best (max) lap speed
    for hid, rec in zip(phase_heat_ids(phase), phase.heats):
        if not any(rec[1].values()):
            continue
        res = analyze(hid, [dict(rec[0]), rec[1]], ss, rc)   # copy info: analyze memoizes racetime
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


def _canonical_record(phase, number):
    """``(heat_id, [info, boats])`` for ``number``'s canonical record in ``phase`` —
    the **last non-empty** one (an empty restart is skipped, §5.2) — or ``None``."""
    same = [(h, rec) for h, rec, num in zip(phase_heat_ids(phase), phase.heats, phase.numbers)
            if num == number]
    for h, rec in reversed(same):
        if any(rec[1].values()):                 # rec = [info, boats]; some boat has marks
            return h, rec
    return None


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
