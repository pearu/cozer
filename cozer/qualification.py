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


def finalists(eventdata, cl):
    """The qualified boat ids (``"primary"`` or ``"repechage"``) — the finals field."""
    return [b for b, s in classify(eventdata, cl).items() if s != "dnq"]
