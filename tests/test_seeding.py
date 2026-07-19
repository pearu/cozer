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


def test_does_not_mutate_eventdata():
    ed = _ev(_PARTS, {"C": {"1": _heat(("3", "7"))}})
    before = repr(ed)
    start_order(ed, "C", "2")
    assert repr(ed) == before
