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


def qheat_qualify_count(eventdata, cl, number):
    """How many boats qualify from qheat ``number`` (its ``!qualification[…]`` count), or 0."""
    counts = qualification_counts(class_pattern(eventdata, cl))
    return counts[number - 1] if counts and 1 <= number <= len(counts) else 0


def classify_qheat(eventdata, cl, number):
    """Per-qheat Q / DNQ for a SINGLE qualification qheat ``number``: its top-``count`` finishers
    are ``"Q"``, the rest ``"DNQ"`` (§4.1). ``{boat_id: "Q"|"DNQ"}`` in no particular order;
    ``{}`` if ``cl`` has no such qheat / counts / record. This is the per-qheat view for the
    report printed after each qheat; :func:`classify` aggregates across all qheats for the
    finals feed (a repechage Q there can override an earlier DNQ)."""
    ph = class_phase_map(eventdata).get(cl)
    counts = qualification_counts(class_pattern(eventdata, cl))
    if ph is None or not counts or not (1 <= number <= len(counts)):
        return {}
    canon = canonical_record(ph, number)
    if canon is None:
        return {}
    hid, rec = canon
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    order = [str(b) for b in getresorder(analyze(hid, [dict(rec[0]), rec[1]], ss, rc))]
    top = counts[number - 1]
    return {b: ("Q" if i < top else "DNQ") for i, b in enumerate(order)}


def finalists(eventdata, cl):
    """The qualified boat ids (``"primary"`` or ``"repechage"``) — the finals field."""
    return [b for b, s in classify(eventdata, cl).items() if s != "dnq"]


def qualification_class(eventdata, cl):
    """The qualification-phase class name for ``cl``'s base (the sibling ``/Q`` phase), or
    ``None`` if the base has no qualification phase. Lets the finals report find the Q/DNQ
    split that feeds it (§5.1 step 4 — the UIM 209 DNQ tail)."""
    base = getclass(cl)
    for c, ph in class_phase_map(eventdata).items():
        if ph.kind == "qualification" and getclass(c) == base:
            return c
    return None


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


def _repechage_field(eventdata, cl):
    """The boats that raced a **selection** qheat but finished outside its top ``count`` —
    the field for the repechage (second-chance) qheat.

    Every below-cutoff non-qualifier is in the field, **whatever its outcome** — a plain
    non-finish, a DNF, a DSQ / DNS / DNR / ACC all get the second chance. The field never
    pre-excludes anyone (that would be a *default-exclude*): a boat the jury rules out is
    handled downstream by the operator marking it ``DNQ`` in Edit Records (disable ``Q`` /
    insert ``DNQ`` — DNQ is a first-class §209 code that :func:`classify` respects)."""
    ph = class_phase_map(eventdata).get(cl)
    counts = qualification_counts(class_pattern(eventdata, cl))
    if ph is None or not counts:
        return []
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    field = []
    for number in range(1, len(counts)):                 # selection qheats (exclude the last)
        canon = canonical_record(ph, number)
        if canon is None:
            continue
        hid, rec = canon
        res = analyze(hid, [dict(rec[0]), rec[1]], ss, rc)
        field.extend(str(boat) for boat in getresorder(res)[counts[number - 1]:])   # below top `count`
    return field
