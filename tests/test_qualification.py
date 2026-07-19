"""Tests for the qualification Q/DNQ machinery (cozer/qualification.py) — §4.1 / §5.1.

The bundled corpus has no qualification events, so these are synthetic fixtures.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.qualification import classify, finalists, qualification_counts  # noqa: E402


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
