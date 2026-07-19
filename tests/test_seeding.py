"""Tests for the derived start order (cozer/seeding.py) — PHASES.md §8 step 3 / §5.

Covers this increment's scope: the base case (participant order) and the circuit
heat N -> N+1 transition (seed by the previous number's canonical ranking), incl.
the take-last restart canonical and the unraced-predecessor fallback.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.seeding import start_order  # noqa: E402

_INFO = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}


def _ev(participants, record, classes=None, ss=(400, 300, 225)):
    return {"classes": classes or [["", "C", "2*(3*1000):1"]],
            "participants": participants, "record": record,
            "scoringsystem": list(ss), "races": [], "rules": []}


# boat 3 finishes ahead of boat 7 (faster laps over the same 3-lap course)
def _heat(winner_first):
    fast, slow = winner_first
    return [dict(_INFO), {fast: [(1, 20.0)] * 3, slow: [(1, 25.0)] * 3}]


_PARTS = [["", "A", "One", "X", "C", "7"], ["", "B", "Two", "Y", "C", "3"]]


def test_base_case_is_participant_order():
    ed = _ev(_PARTS, {})                                  # class not raced at all
    assert start_order(ed, "C", "1") == ["7", "3"]        # participant list order, not sorted


def test_first_heat_of_phase_is_base_case():
    ed = _ev(_PARTS, {"C": {"1": _heat(("3", "7"))}})
    assert start_order(ed, "C", "1") == ["7", "3"]        # heat 1 -> base case (participants)


def test_heat2_seeds_from_heat1_ranking():
    ed = _ev(_PARTS, {"C": {"1": _heat(("3", "7"))}})     # 3 beat 7 in heat 1
    assert start_order(ed, "C", "2") == ["3", "7"]        # heat 2 grid = heat 1 finishing order


def test_heat2_seeds_from_last_nonempty_restart():
    # heat 1 original: 7 ahead; restart 1r: 3 ahead -> canonical is 1r (take-last, §5.2)
    ed = _ev(_PARTS, {"C": {"1": _heat(("7", "3")), "1r": _heat(("3", "7"))}})
    assert start_order(ed, "C", "2") == ["3", "7"]        # seeds from the restart, where 3 won


def test_empty_restart_is_skipped():
    # a trailing empty restart (Timer defect) must not become canonical
    empty = [dict(_INFO), {"7": [], "3": []}]
    ed = _ev(_PARTS, {"C": {"1": _heat(("3", "7")), "1r": empty}})
    assert start_order(ed, "C", "2") == ["3", "7"]        # still seeds from heat 1 (3 won)


def test_unraced_predecessor_falls_back_to_base_case():
    empty = [dict(_INFO), {"7": [], "3": []}]
    ed = _ev(_PARTS, {"C": {"1": empty}})                 # heat 1 has no laps
    assert start_order(ed, "C", "2") == ["7", "3"]        # can't seed -> participant order


# --- cross-phase: time-trial -> finals (decision A / 307.01) ---------------------

_TT_INFO = {"course": [1000], "sheats": 1, "duration": None}
_TT_CLASSES = [["", "C/T", "1*(1000):1"], ["", "C", "2*(3*1000):1"]]


def test_finals_heat1_seeds_from_preceding_timetrial():
    # boat 3's best time-trial lap (18) beats boat 7's (22) -> 3 seeds ahead in the final
    tt = [dict(_TT_INFO), {"7": [(1, 22.0)], "3": [(1, 18.0)]}]
    ed = _ev(_PARTS, {"C/T": {"1t": tt}}, classes=_TT_CLASSES)   # only the time-trial is raced
    assert start_order(ed, "C", "1") == ["3", "7"]              # final grid = time-trial order


def test_timetrial_ranking_takes_best_lap_across_heats():
    # two time-trial heats; boat 7's best (17 in 2t) beats boat 3's best (19 in 1t)
    tt1 = [dict(_TT_INFO), {"7": [(1, 22.0)], "3": [(1, 19.0)]}]
    tt2 = [dict(_TT_INFO), {"7": [(1, 17.0)], "3": [(1, 30.0)]}]
    classes = [["", "C/T", "2*(1000):1"], ["", "C", "2*(3*1000):1"]]
    ed = _ev(_PARTS, {"C/T": {"1t": tt1, "2t": tt2}}, classes=classes)
    assert start_order(ed, "C", "1") == ["7", "3"]              # best-lap across heats


def test_timetrial_ranking_skips_empty_heats():
    tt1 = [dict(_TT_INFO), {"7": [(1, 22.0)], "3": [(1, 18.0)]}]
    empty = [dict(_TT_INFO), {"7": [], "3": []}]                 # materialized, no laps
    classes = [["", "C/T", "2*(1000):1"], ["", "C", "2*(3*1000):1"]]
    ed = _ev(_PARTS, {"C/T": {"1t": tt1, "2t": empty}}, classes=classes)
    assert start_order(ed, "C", "1") == ["3", "7"]              # empty 2t skipped; 3 fastest in 1t


def test_finals_heat1_base_case_when_timetrial_not_raced():
    ed = _ev(_PARTS, {}, classes=_TT_CLASSES)                    # time-trial phase has no record
    assert start_order(ed, "C", "1") == ["7", "3"]              # -> base case (participant order)


def test_qualification_predecessor_falls_back_to_base_case():
    # qualification -> finals is deferred (needs Q/DNQ); a qual predecessor -> base case
    q = [dict(_INFO), {"3": [(1, 20.0)] * 3, "7": [(1, 25.0)] * 3}]
    classes = [["", "C/Q", "3*(1000):1"], ["", "C", "2*(3*1000):1"]]
    ed = _ev(_PARTS, {"C/Q": {"1q": q}}, classes=classes)
    assert start_order(ed, "C", "1") == ["7", "3"]              # deferred -> participant order


# --- cross-phase: qualification -> finals (§5.1) ---------------------------------

def _qh(fast, slow):
    """A 3-lap qheat where `fast` finishes ahead of `slow`."""
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    return [info, {fast: [(1, 20.0)] * 3, slow: [(1, 25.0)] * 3}]


def _tt_one_lap(secs_by_boat):
    return [dict(_TT_INFO), {b: [(1, s)] for b, s in secs_by_boat.items()}]


def _qual_ev(record, with_tt):
    classes = [["", "C/Q", "3*(1000):1!qualification[1,1,1]"], ["", "C", "2*(3*1000):1"]]
    if with_tt:
        classes.insert(0, ["", "C/T", "1*(1000):1"])
    parts = [["", "A", "One", "X", "C", str(b)] for b in (10, 20, 30, 40)]
    return {"classes": classes, "record": record, "scoringsystem": [400, 300, 225],
            "participants": parts, "races": [], "rules": []}


# 1q: 10>20 ; 2q: 30>40 ; repechage 3q: 20>40  ->  10,30 primary; 20 repechage; 40 DNQ
_QHEATS = {"C/Q": {"1q": _qh("10", "20"), "2q": _qh("30", "40"), "3q": _qh("20", "40")}}


def test_qualification_to_finals_ordered_by_timetrial():
    # time-trial best laps: 10 fastest, then 30, then 20, then 40
    rec = dict(_QHEATS)
    rec["C/T"] = {"1t": _tt_one_lap({"10": 18.0, "30": 19.0, "20": 20.0, "40": 22.0})}
    ed = _qual_ev(rec, with_tt=True)
    # [primary by TT: 10,30] then [repechage by TT: 20]; DNQ 40 excluded
    assert start_order(ed, "C", "1") == ["10", "30", "20"]


def test_qualification_to_finals_dnq_excluded():
    rec = dict(_QHEATS)
    rec["C/T"] = {"1t": _tt_one_lap({"10": 18.0, "30": 19.0, "20": 20.0, "40": 22.0})}
    ed = _qual_ev(rec, with_tt=True)
    assert "40" not in start_order(ed, "C", "1")           # DNQ boat is not in the grid


def test_qualification_to_finals_no_timetrial_fallback():
    # no time-trial phase -> order by the qualification's own best-lap rank, same split
    ed = _qual_ev(dict(_QHEATS), with_tt=False)
    grid = start_order(ed, "C", "1")
    assert grid[-1] == "20"                                # repechage last
    assert set(grid[:-1]) == {"10", "30"} and "40" not in grid   # primaries first, DNQ out


def test_qualification_qheat_not_seeded_from_previous_qheat():
    # finding 1 (7948e787): a qualifying heat's N>1 must NOT seed from the previous qheat
    # (disjoint groups). With a preceding time trial, a qualifying heat is TT-seeded (307.01).
    rec = dict(_QHEATS)
    rec["C/T"] = {"1t": _tt_one_lap({"10": 18.0, "30": 19.0, "20": 20.0, "40": 22.0})}
    classes = [["", "C/T", "1*(1000):1"], ["", "C/Q", "3*(1000):1!qualification[1,1,1]"]]
    parts = [["", "A", "One", "X", "C", str(b)] for b in (10, 20, 30, 40)]
    ed = {"classes": classes, "record": rec, "scoringsystem": [400, 300, 225],
          "participants": parts, "races": [], "rules": []}
    # 2q is TT-seeded (the TT order), NOT qheat1's finishers ["10","20"]
    assert start_order(ed, "C/Q", "2q") == ["10", "30", "20", "40"]


def test_class_not_in_catalog_falls_back_to_base_case():
    ed = {"classes": [], "record": {}, "scoringsystem": [400, 300, 225],
          "participants": _PARTS, "races": [], "rules": []}
    assert start_order(ed, "C", "1") == ["7", "3"]         # no catalog -> participant order


def test_does_not_mutate_eventdata():
    ed = _ev(_PARTS, {"C": {"1": _heat(("3", "7"))}})
    before = repr(ed)
    start_order(ed, "C", "2")
    assert repr(ed) == before
