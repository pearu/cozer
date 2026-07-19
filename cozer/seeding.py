"""Derived start order — PHASES.md §8 step 3 / §5.

``start_order(eventdata, cl, heat)`` returns the ordered boat-id list for a heat's
**start / jetty positions**, DERIVED (never stored) from the previous heat's ranking::

    start_order(heat) = seed( previous_heat, ranking(previous_heat) )
    ranking           = the analyzer's finishing order (getresorder) of the previous
                        heat's canonical (last non-empty) record.

Base case (a phase's first heat, no predecessor) = the **participant order** in
Classes & Participants. Consumers are the **reports** (start list / jetty positions)
and the timer **ladder** (§5, owner clarification rev 29); the timer's button grid
stays boat-number and is NOT a consumer.

This increment implements the base case + the **circuit heat N → N+1** transition
(seed by the previous number's canonical ranking). The cross-phase transitions —
time-trial → finals (best time) and qualification → finals (§5.1) — are a later
increment; a first heat with a preceding phase currently falls back to the base case.
Pure and read-only: it never mutates ``eventdata``.
"""
from cozer.analyzer import analyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, heat_number, phase_heat_ids


def start_order(eventdata, cl, heat):
    """Ordered boat-id list (strings) for class ``cl``'s ``heat`` start positions."""
    ph = class_phase_map(eventdata).get(cl)
    if ph is not None and heat_number(heat) > 1:
        prev = _canonical_record(ph, heat_number(heat) - 1)
        if prev is not None:
            hid, rec = prev
            # analyze memoizes 'racetime' into info; copy info so start_order stays
            # read-only (the boats, rec[1], are not mutated -- §6.6 -- so sharing them).
            res = analyze(hid, [dict(rec[0]), rec[1]], eventdata.get("scoringsystem", []),
                          rule_action_codes(eventdata))
            return [str(pid) for pid in getresorder(res)]
    # first heat of the phase (or the predecessor is unraced/missing) -> base case
    return _participant_order(eventdata, cl)


def _canonical_record(phase, number):
    """``(heat_id, [info, boats])`` for ``number``'s canonical record in ``phase`` —
    the **last non-empty** one (an empty restart is skipped, §5.2) — or ``None`` if
    the number has no non-empty record yet."""
    hids = phase_heat_ids(phase)
    same = [(h, rec) for h, rec, num in zip(hids, phase.heats, phase.numbers)
            if num == number]
    for h, rec in reversed(same):
        if any(rec[1].values()):                 # rec = [info, boats]; some boat has marks
            return h, rec
    return None


def _participant_order(eventdata, cl):
    """Base-case start order: the class's participants in Classes & Participants list
    order (the drag-reorderable lot-draw order, §5). ``cl`` may be suffixed; match on
    the base class, as the timer's ``class_ids`` does."""
    base = getclass(cl)
    return [str(p[5]) for p in eventdata.get("participants", [])
            if len(p) > 5 and p[4] == base and str(p[5]) != ""]
