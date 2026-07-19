"""Qualification Q / DNQ classification — PHASES.md §4.1 / §5.1.

A qualification phase's qheats select which boats reach the finals: the **top
`count`** of each qheat are `Q` (qualified), the rest `DNQ` — a hardcoded rule, no
scoring system (§4.1). The per-qheat counts come from the class pattern's
``!qualification[N,N,M]`` hint (tuple length = number of qheats; the **last** qheat
is the repechage / second-chance heat).

``classify(eventdata, cl)`` returns, per boat id, one of:
- ``"primary"``   — Q from a selection qheat (qheat1/qheat2), or
- ``"repechage"`` — Q from the last (second-chance) qheat, or
- ``"dnq"``       — did not qualify.

Primary-vs-repechage is derived from the **source qheat** (§4.1): a boat's Q comes
from exactly one qheat (the primaries are disjoint and the repechage runs only their
non-qualifiers), so a second-chance qualifier's ``"repechage"`` (assigned last, when
the last qheat is processed) wins over its earlier ``"dnq"``.

Consumers: the derived seeding (qualification → finals, §5.1) and the finals report's
DNQ tail (UIM 209). Pure and read-only.
"""
import re

from cozer.analyzer import analyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import canonical_record, class_phase_map
from cozer.racepattern import class_pattern

# The tuple of per-qheat qualifier counts, e.g. '...!qualification[3,3,2]'.
_QUAL_TUPLE = re.compile(r"qualification\[([\d,\s]+)\]", re.I)

# Outcome codes (by analyze `notes` key name, §209 and legacy spellings) whose qheat3
# membership is an OPERATOR call — a disqualification, or a did-not-start / accident.
# A DNF/IR (raced and failed) and a plain finisher are NOT here: they are auto-included.
_GATED_CODES = frozenset(("DSQ", "DQ", "RC",           # disqualified (incl. red card)
                          "DNS", "DS", "DNR", "ACC"))  # did-not-start / accident family


def qualification_counts(pattern):
    """Per-qheat qualifier counts from a ``!qualification[N,N,M]`` pattern hint, as a
    tuple, or ``None``. The tuple length is the number of qheats; the last entry is the
    repechage count (§5.1)."""
    if not pattern:
        return None
    m = _QUAL_TUPLE.search(pattern)
    if not m:
        return None
    try:
        counts = tuple(int(x) for x in m.group(1).split(",") if x.strip())
    except ValueError:
        return None
    return counts or None


def classify(eventdata, cl):
    """``{boat_id: "primary" | "repechage" | "dnq"}`` for qualification class ``cl``.

    Each qheat (by heat number) is analyzed for its finishing order; its top ``count``
    boats are Q, everyone else DNQ. The last qheat's Q boats are ``"repechage"``,
    earlier qheats' are ``"primary"``. Returns ``{}`` if ``cl`` has no qualification
    record or no ``!qualification[...]`` counts."""
    ph = class_phase_map(eventdata).get(cl)
    counts = qualification_counts(class_pattern(eventdata, cl))
    if ph is None or not counts:
        return {}
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    nq = len(counts)
    out = {}
    for number in range(1, nq + 1):
        canon = canonical_record(ph, number)
        if canon is None:
            continue
        hid, rec = canon
        # copy info (analyze memoizes racetime); boats are shared (analyze is pure on them)
        order = [str(b) for b in getresorder(analyze(hid, [dict(rec[0]), rec[1]], ss, rc))]
        top = counts[number - 1]
        label = "repechage" if (nq >= 2 and number == nq) else "primary"
        for i, boat in enumerate(order):
            out.setdefault(boat, "dnq")
            if i < top:
                out[boat] = label
    return out


def finalists(eventdata, cl):
    """The qualified boat ids (``"primary"`` or ``"repechage"``) — the finals field."""
    return [b for b, s in classify(eventdata, cl).items() if s != "dnq"]


# --- qheat membership (§5.1: qheat1/qheat2 split + repechage field) ---------------
# The **organizer** provides the qheat1/qheat2 split (rule-compliant, incl. the
# 305.04.03 nationality balancing); the operator records it as a per-boat qheat1 flag
# (``eventdata['qheat1'][base] = [boat_ids]``). From that single flag the rest derives:
# qheat1 = the flagged boats, qheat2 = the class's other participants, the repechage
# (last) qheat = the non-qualifiers of the selection qheats.


def participant_boats(eventdata, cl):
    """The class's participant boat-ids, in Classes & Participants list order. ``cl``
    may be suffixed; matches on the base class."""
    base = getclass(cl)
    return [str(p[5]) for p in eventdata.get("participants", [])
            if len(p) > 5 and p[4] == base and str(p[5]) != ""]


def qheat1_members(eventdata, cl):
    """The boat-ids the operator flagged as qheat1 members (the organizer's split), from
    ``eventdata['qheat1'][base]``; empty if unset. Read-only."""
    base = getclass(cl)
    return [str(b) for b in (eventdata.get("qheat1") or {}).get(base) or []]


def qheat_boats(eventdata, cl, number):
    """The boat-ids in qualification qheat ``number`` for class ``cl``:

    - the **last** qheat (repechage) = the non-qualifiers of the selection qheats;
    - with a single selection qheat, qheat1 = **all** the class's participants (no split);
    - with two selection qheats, qheat1 = the operator's **flag**, qheat2 = the rest.

    ``[]`` if ``cl`` has no ``!qualification[...]`` counts, ``number`` is out of range,
    or the split needs more than two selection qheats (three+ would need a flag per
    selection qheat — a later extension)."""
    counts = qualification_counts(class_pattern(eventdata, cl))
    if not counts or not (1 <= number <= len(counts)):
        return []
    if number == len(counts):                            # repechage (the last qheat)
        return _repechage_field(eventdata, cl)
    nsel = len(counts) - 1                               # selection qheats (last is repechage)
    boats = participant_boats(eventdata, cl)
    if nsel == 1:                                        # one selection qheat -> all, no split
        return boats
    if nsel == 2:                                        # two selection qheats -> the flag split
        flagged = set(qheat1_members(eventdata, cl))
        return ([b for b in boats if b in flagged] if number == 1
                else [b for b in boats if b not in flagged])
    return []                                            # 3+ selection qheats: needs a flag each


def _repechage_gated(notes):
    """True if a below-cutoff boat's qheat3 membership is an **operator call**
    (default-include, operator-exclude): a **DSQ** / **DNS** / **DNR** / **ACC** outcome
    (owner resolution via 7948e787). A **DNF/IR** (raced and failed) and a plain finisher
    are **not** gated — always in the repechage. Read from the analyze ``notes`` keys,
    the reliable signal — never ``place``/lap count (a DSQ or ACC boat can have a full or
    partial lap count). A gated key wins even if the boat also carries a DNF key."""
    return bool(set(notes or ()) & _GATED_CODES)


def qheat3_excluded(eventdata, cl):
    """Boat-ids the operator EXCLUDED from the repechage, from
    ``eventdata['qheat3_exclude'][base]``; empty if unset. Read-only.

    The default is **include**: a gated (DSQ / DNS / DNR / ACC) boat still starts qheat3
    until a protest is resolved against it — a boat may protest, and until then it has the
    right to start — so the operator removes it here only once the ruling stands (a
    heat-scoped DSQ or a dead-engine DNS may simply stay in). A DNF and a plain finisher
    are always included, never gated."""
    base = getclass(cl)
    return [str(b) for b in (eventdata.get("qheat3_exclude") or {}).get(base) or []]


def _repechage_field(eventdata, cl):
    """The boats that raced a **selection** qheat but finished outside its top ``count``
    — the field for the repechage (second-chance) qheat.

    A plain non-qualifier (finished, ranked below the cutoff) and a **DNF** are
    auto-included. A **DSQ / DNS / DNR / ACC** is **included by default** but the operator
    can exclude it (:func:`qheat3_excluded`) once a protest is resolved against it (owner
    resolution via 7948e787). Outcomes are read from the analyze ``notes`` keys."""
    ph = class_phase_map(eventdata).get(cl)
    counts = qualification_counts(class_pattern(eventdata, cl))
    if ph is None or not counts:
        return []
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    excluded = set(qheat3_excluded(eventdata, cl))
    field = []
    for number in range(1, len(counts)):                 # selection qheats (exclude the last)
        canon = canonical_record(ph, number)
        if canon is None:
            continue
        hid, rec = canon
        res = analyze(hid, [dict(rec[0]), rec[1]], ss, rc)
        for boat in getresorder(res)[counts[number - 1]:]:   # boats outside the top `count`
            b = str(boat)
            if b in excluded and _repechage_gated((res[boat] or {}).get("notes")):
                continue                                 # operator removed it (protest upheld)
            field.append(b)
    return field
