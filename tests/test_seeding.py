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


def test_does_not_mutate_eventdata():
    ed = _ev(_PARTS, {"C": {"1": _heat(("3", "7"))}})
    before = repr(ed)
    start_order(ed, "C", "2")
    assert repr(ed) == before
