"""Tests for the non-fatal results-validation layer (cozer/validate.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer import store
from cozer.validate import check_results, format_findings

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _event(course_laps, boat_laps, ss=(400, 300, 225), classname="C", extra_heats=None):
    """One class with heat '1': a `course_laps`-lap course where boat i completes
    boat_laps[i] laps (clean laps ~30s apart)."""
    rec = {str(i): [(1, 30.0 + i * 0.1)] * nl for i, nl in enumerate(boat_laps, 1)}
    heats = {"1": [{"course": [1000] * course_laps}, rec]}
    if extra_heats:
        heats.update(extra_heats)
    return {"record": {classname: heats},
            "classes": [["", classname, "1*(%d*1000):1" % course_laps]],
            "scoringsystem": list(ss), "races": [], "rules": [], "participants": []}


def _codes(findings):
    return sorted(f.code for f in findings)


def test_complete_heat_is_clean():
    ed = _event(course_laps=2, boat_laps=[2, 2, 2])       # everyone finishes the 2-lap course
    assert check_results(ed) == []


def test_incomplete_heat_without_restart_warns():
    ed = _event(course_laps=3, boat_laps=[2, 2, 2])       # nobody finishes the 3-lap course
    codes = _codes(check_results(ed))
    assert "incomplete-heat" in codes


def test_incomplete_heat_with_restart_is_ok():
    restart = {"1r": [{"course": [1000] * 3}, {"1": [(1, 30.0)] * 3}]}   # a restart was run
    ed = _event(course_laps=3, boat_laps=[2, 2, 2], extra_heats=restart)
    assert "incomplete-heat" not in _codes(check_results(ed))


def test_endurance_heat_not_flagged_incomplete():
    ed = _event(course_laps=3, boat_laps=[2, 2, 2])
    ed["record"]["C"]["1"][0]["duration"] = 3600          # duration race: not lap-completion
    assert "incomplete-heat" not in _codes(check_results(ed))


def test_qualification_heat_skipped():
    ed = _event(course_laps=3, boat_laps=[2, 2], classname="C/Q")
    ed["record"]["C/Q"] = {"1q": ed["record"]["C/Q"].pop("1")}
    assert check_results(ed) == []                        # q heat: scored differently, not flagged


def test_empty_scoring_system_warns():
    ed = _event(course_laps=2, boat_laps=[2, 2], ss=())
    assert "empty-scoring" in _codes(check_results(ed))


def test_liepaja_real_incomplete_and_no_first_place():
    ed = store.read_legacy_coz(os.path.join(REPO, "legacy", "events", "Liepaja_2006.coz"))
    f = check_results(ed)
    f2h3 = [x for x in f if x.cl == "F-2" and x.heat == "3"]
    assert {x.code for x in f2h3} == {"incomplete-heat", "no-first-place"}
    assert all(isinstance(line, str) and line for line in format_findings(f))


def test_never_raises_on_garbage():
    for bad in ({}, {"record": None}, {"record": {"C": {"1": "nonsense"}}},
                {"record": {"C": {"1": [{}, {"x": [("?",)]}]}}, "scoringsystem": None}):
        assert isinstance(check_results(bad), list)       # returns a list, never raises
