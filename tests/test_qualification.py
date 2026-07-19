"""Tests for the qualification Q/DNQ machinery (cozer/qualification.py) — §4.1 / §5.1.

The bundled corpus has no qualification events, so these are synthetic fixtures.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.qualification import (classify, finalists, participant_boats,  # noqa: E402
                                 qheat1_members, qheat3_excluded, qheat_boats,
                                 qualification_counts)


def _q(fast, slow):
    """A 3-lap qheat where `fast` finishes ahead of `slow`."""
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    return [info, {fast: [(1, 20.0)] * 3, slow: [(1, 25.0)] * 3}]


def _ev(record, pattern="3*(1000):1!qualification[1,1,1]"):
    return {"classes": [["", "C/Q", pattern]], "record": {"C/Q": record},
            "scoringsystem": [400, 300, 225], "participants": [], "races": [], "rules": []}


def test_qualification_counts_parsing():
    assert qualification_counts("3*(1000):1!qualification[3,3,2]") == (3, 3, 2)
    assert qualification_counts("2*(1600):2@150!qualification[8, 8, 4]") == (8, 8, 4)
    assert qualification_counts("3*(1000):1") is None            # no hint
    assert qualification_counts("x!qualification[]") is None     # empty tuple
    assert qualification_counts("x!qualification[3 3 2]") is None  # space-separated, not comma
    assert qualification_counts(None) is None


def test_classify_primary_repechage_dnq():
    # qheat1: 10 beats 20; qheat2: 30 beats 40; repechage qheat3: 20 beats 40.
    # top-1 each -> 10,30 primary; 20 repechage (second chance); 40 DNQ.
    ed = _ev({"1q": _q("10", "20"), "2q": _q("30", "40"), "3q": _q("20", "40")})
    assert classify(ed, "C/Q") == {"10": "primary", "30": "primary",
                                   "20": "repechage", "40": "dnq"}


def test_finalists_excludes_dnq():
    ed = _ev({"1q": _q("10", "20"), "2q": _q("30", "40"), "3q": _q("20", "40")})
    assert set(finalists(ed, "C/Q")) == {"10", "30", "20"}       # DNQ boat 40 excluded


def test_repechage_only_labels_the_last_qheat():
    # two qheats, top-1 each: qheat1 primary, qheat2 (last) = repechage
    ed = _ev({"1q": _q("10", "20"), "2q": _q("30", "40")},
             pattern="2*(1000):1!qualification[1,1]")
    labels = classify(ed, "C/Q")
    assert labels["10"] == "primary" and labels["30"] == "repechage"
    assert labels["20"] == "dnq" and labels["40"] == "dnq"


def test_missing_qheat_is_skipped():
    # counts say 3 qheats, but the repechage (3q) hasn't run yet -> no repechage assigned
    ed = _ev({"1q": _q("10", "20"), "2q": _q("30", "40")})
    assert classify(ed, "C/Q") == {"10": "primary", "20": "dnq",
                                   "30": "primary", "40": "dnq"}


def test_classify_empty_without_counts():
    ed = _ev({"1q": _q("10", "20")}, pattern="3*(1000):1")       # no !qualification[...]
    assert classify(ed, "C/Q") == {}


def test_higher_counts_qualify_more():
    # qheat1 has 3 boats, top-2 qualify (10, 20 primary; 50 drops to the repechage)
    q1 = [{"course": [1000, 1000, 1000], "sheats": 1, "duration": None},
          {"10": [(1, 20.0)] * 3, "20": [(1, 22.0)] * 3, "50": [(1, 28.0)] * 3}]
    ed = _ev({"1q": q1, "2q": _q("30", "40"), "3q": _q("50", "60")},
             pattern="3*(1000):1!qualification[2,1,1]")
    labels = classify(ed, "C/Q")
    assert labels["10"] == "primary" and labels["20"] == "primary"  # top-2 of qheat1
    assert labels["50"] == "repechage"                              # missed qheat1, won repechage
    assert labels["60"] == "dnq"


# --- qheat membership (organizer split via the qheat1 flag) -----------------------

def _members_ev(record, qheat1=None, pattern="3*(1000):1!qualification[1,1,1]", boats=(10, 20, 30, 40)):
    ed = {"classes": [["", "C/Q", pattern]], "record": {"C/Q": record},
          "scoringsystem": [400, 300, 225],
          "participants": [["", "A", "One", "X", "C", str(b)] for b in boats],
          "races": [], "rules": []}
    if qheat1 is not None:
        ed["qheat1"] = {"C": qheat1}
    return ed


def test_qheat1_members_reads_flag():
    assert qheat1_members(_members_ev({}, qheat1=["10", "30"]), "C/Q") == ["10", "30"]
    assert qheat1_members(_members_ev({}), "C/Q") == []       # no flag -> empty list


def test_qheat1_flag_split_qheat2_complement():
    ed = _members_ev({}, qheat1=["10", "30"])            # organizer's split: qheat1 = {10, 30}
    assert qheat_boats(ed, "C/Q", 1) == ["10", "30"]     # flagged, in participant order
    assert qheat_boats(ed, "C/Q", 2) == ["20", "40"]     # the complement


def test_repechage_field_is_selection_non_qualifiers():
    # 1q: 10>20 (top1 -> 10 Q); 2q: 30>40 (top1 -> 30 Q). Repechage field = {20, 40}.
    ed = _members_ev({"1q": _q("10", "20"), "2q": _q("30", "40")}, qheat1=["10", "20"])
    assert set(qheat_boats(ed, "C/Q", 3)) == {"20", "40"}


def test_single_selection_qheat_no_split():
    ed = _members_ev({}, pattern="2*(1000):1!qualification[2,2]")   # 1 selection + repechage
    assert qheat_boats(ed, "C/Q", 1) == ["10", "20", "30", "40"]    # all boats, no split


def test_three_selection_qheats_unsupported():
    ed = _members_ev({}, qheat1=["10"], pattern="4*(1000):1!qualification[1,1,1,1]")
    assert qheat_boats(ed, "C/Q", 2) == []              # single flag can't split 3 groups
    assert qheat_boats(ed, "C/Q", 1) == []


def test_qheat_boats_out_of_range_or_no_counts():
    assert qheat_boats(_members_ev({}), "C/Q", 9) == []             # out of range
    ed = _members_ev({}, pattern="3*(1000):1")                      # no !qualification[...]
    assert qheat_boats(ed, "C/Q", 1) == []


def test_participant_boats_matches_base_class():
    ed = _members_ev({})
    assert participant_boats(ed, "C/Q") == ["10", "20", "30", "40"]   # /Q -> base C


def test_repechage_field_edge_cases():
    assert qheat_boats(_members_ev({}), "C/Q", 3) == []     # empty qual phase -> empty repechage
    ed = _members_ev({"1q": _q("10", "20")})                # only qheat1 run so far
    assert qheat_boats(ed, "C/Q", 3) == ["20"]              # 1q non-qualifier; missing 2q skipped
    # a qualification class with counts but no record at all (not yet raced) -> empty
    unrecorded = {"classes": [["", "D/Q", "3*(1000):1!qualification[1,1,1]"]], "record": {},
                  "scoringsystem": [400, 300, 225], "participants": [], "races": [], "rules": []}
    assert qheat_boats(unrecorded, "D/Q", 3) == []


# --- repechage outcome-code handling (DNF auto; DSQ/DNS default-include, op-exclude) ---

def _outcome_qheat(winner, others):
    """A 3-lap qheat where `winner` finishes top; `others` = {boat: 'finish'|'dnf'|'dns'|'dsq'}."""
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    boats = {winner: [(1, 20.0)] * 3}
    for b, o in others.items():
        boats[b] = {"finish": [(1, 25.0)] * 3,
                    "dnf": [(1, 25.0), (27, 50.0, "")],           # DNF mark (code 27)
                    "dns": [],                                    # no laps -> DNS
                    "dsq": [(1, 25.0), (22, 50.0, "409.01")],     # DSQ mark (code 22)
                    "acc": [(1, 25.0), (25, 50.0, "")],           # ACC mark (code 25)
                    "dnr": [(1, 25.0), (24, 50.0, "")]            # DNR mark (code 24)
                    }[o]
    return [info, boats]


def _outcome_ev(qheat1, exclude=None, boats=(10, 20, 30, 40, 50)):
    ed = _members_ev({"1q": qheat1}, pattern="2*(1000):1!qualification[1,1]", boats=boats)
    if exclude is not None:
        ed["qheat3_exclude"] = {"C": exclude}
    return ed


def test_repechage_auto_includes_finishers_and_dnf_default_includes_dsq_dns():
    q1 = _outcome_qheat("10", {"20": "finish", "30": "dnf", "40": "dns", "50": "dsq"})
    ed = _outcome_ev(q1)                                # top-1 (10) qualifies
    assert set(qheat_boats(ed, "C/Q", 2)) == {"20", "30", "40", "50"}   # all in by default


def test_repechage_operator_excludes_only_dsq_dns():
    q1 = _outcome_qheat("10", {"20": "finish", "30": "dnf", "40": "dns", "50": "dsq"})
    ed = _outcome_ev(q1, exclude=["40", "50"])         # protests upheld against DNS 40, DSQ 50
    assert set(qheat_boats(ed, "C/Q", 2)) == {"20", "30"}


def test_repechage_exclude_ignored_for_finisher_and_dnf():
    q1 = _outcome_qheat("10", {"20": "finish", "30": "dnf"})
    ed = _outcome_ev(q1, exclude=["20", "30"], boats=(10, 20, 30))     # can't gate these
    assert set(qheat_boats(ed, "C/Q", 2)) == {"20", "30"}


def test_qheat3_excluded_reads_flag():
    assert qheat3_excluded(_members_ev({}), "C/Q") == []
    ed = _members_ev({})
    ed["qheat3_exclude"] = {"C": ["40"]}
    assert qheat3_excluded(ed, "C/Q") == ["40"]


def test_repechage_acc_is_operator_gated_like_dsq_dns():
    q1 = _outcome_qheat("10", {"20": "finish", "60": "acc"})
    ed = _outcome_ev(q1, boats=(10, 20, 60))
    assert set(qheat_boats(ed, "C/Q", 2)) == {"20", "60"}          # ACC in by default
    ed2 = _outcome_ev(q1, exclude=["60"], boats=(10, 20, 60))
    assert set(qheat_boats(ed2, "C/Q", 2)) == {"20"}               # protest upheld -> ACC excluded


def test_repechage_all_four_gated_codes_default_include_and_excludable():
    # DSQ, DNS, ACC, DNR all gated (default include, operator can exclude); DNF/finisher never gated
    others = {"20": "finish", "30": "dnf", "40": "dns", "50": "dsq", "60": "acc", "70": "dnr"}
    q1 = _outcome_qheat("10", others)
    boats = (10, 20, 30, 40, 50, 60, 70)
    ed = _outcome_ev(q1, boats=boats)
    assert set(qheat_boats(ed, "C/Q", 2)) == {"20", "30", "40", "50", "60", "70"}   # all default-in
    ed2 = _outcome_ev(q1, exclude=["40", "50", "60", "70"], boats=boats)            # protests upheld
    assert set(qheat_boats(ed2, "C/Q", 2)) == {"20", "30"}      # only finisher + DNF remain (ungatable)
