"""Tests for the non-fatal results-validation layer (cozer/validate.py)."""
import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer import store
from cozer.native import to_native
from cozer.validate import check_results, format_findings

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_EVENTS = sorted(glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")) +
                 glob.glob(os.path.join(REPO, "legacy", "cozer", "data", "*.coz")))


def _complete_event(course_laps, boat_laps, ss=(400, 300, 225)):
    """A class whose boats each complete `boat_laps[i]` clean laps of a
    `course_laps`-lap course."""
    rec = {str(i): [(1, 30.0 + i * 0.1)] * nl for i, nl in enumerate(boat_laps, 1)}
    return {"record": {"C": {"1": [{"course": [1000] * course_laps}, rec]}},
            "classes": [["", "C", "1*(%d*1000):1" % course_laps]],
            "scoringsystem": list(ss), "races": [], "rules": [], "participants": []}


def _stopped_heat(course, lap_secs, ss=(400, 300, 225), extra=None, cfg=None, classname="C"):
    """A stopped heat: each boat runs `nl` laps at a constant `sec`/lap, so the
    fastest boat finishes first (defining the race-stop time) and slower boats
    cross AFTER it -- so they score while the fast 'leader' is DNF (no lap after
    the stop line). This is the real shape of a stopped fixed-lap heat."""
    rec = {str(i): [(1, float(sec))] * nl for i, (nl, sec) in enumerate(lap_secs, 1)}
    heats = {"1": [{"course": [1000] * course}, rec]}
    if extra:
        heats.update(extra)
    ed = {"record": {classname: heats},
          "classes": [["", classname, "1*(%d*1000):1" % course]],
          "scoringsystem": list(ss), "races": [], "rules": [], "participants": []}
    if cfg is not None:
        ed["configure"] = cfg
    return ed


def _codes(findings):
    return sorted(f.code for f in findings)


# a leader 6/10 laps = 60% < the UIM 70% threshold (int(0.7*10)=7)
_SUB70 = [(6, 20.0), (6, 22.0), (6, 24.0)]


def test_complete_heat_is_clean():
    assert check_results(_complete_event(course_laps=2, boat_laps=[2, 2, 2])) == []


def test_stopped_heat_below_threshold_warns():
    codes = _codes(check_results(_stopped_heat(10, _SUB70)))
    assert "incomplete-heat" in codes                      # leader < 70% -> a restart is missing


def test_restart_suppresses_incomplete_heat():
    restart = {"1r": [{"course": [1000] * 10}, {"1": [(1, 20.0)] * 10}]}
    assert "incomplete-heat" not in _codes(check_results(_stopped_heat(10, _SUB70, extra=restart)))


def test_inserted_lap_stop_crossing_suppresses_incomplete_heat():
    ed = _stopped_heat(10, _SUB70)
    ed["record"]["C"]["1"][1]["2"] = [(1, 22.0)] * 5 + [(2, 22.0)]   # inserted lap after the stop line
    assert "incomplete-heat" not in _codes(check_results(ed))


def test_threshold_is_discipline_configurable():
    # a non-UIM 50% threshold -> int(0.5*10)=5; leader did 6 >= 5 -> no restart needed
    ed = _stopped_heat(10, _SUB70, cfg={"requiredlapscoef": 0.5})
    assert "incomplete-heat" not in _codes(check_results(ed))


def test_endurance_heat_not_flagged_incomplete():
    ed = _stopped_heat(10, _SUB70)
    ed["record"]["C"]["1"][0]["duration"] = 3600           # duration race: not lap-completion
    assert "incomplete-heat" not in _codes(check_results(ed))


def test_qualification_heat_gets_circuit_machinery():
    # §4.1: a qheat is a mass start analyzed like a circuit heat -> a stopped qheat below
    # the restart threshold now WARNS (no longer skipped as it was pre-§4.1).
    ed = _stopped_heat(10, _SUB70, classname="C/Q")
    ed["record"]["C/Q"] = {"1q": ed["record"]["C/Q"].pop("1")}
    assert "incomplete-heat" in _codes(check_results(ed))


def test_empty_scoring_system_warns():
    assert "empty-scoring" in _codes(check_results(_complete_event(2, [2, 2], ss=())))


def test_liepaja_real_place_gap_but_not_incomplete():
    ed = store.read_legacy_coz(os.path.join(REPO, "legacy", "events", "Liepaja_2006.coz"))
    f2h3 = {x.code for x in check_results(ed) if x.cl == "F-2" and x.heat == "3"}
    assert "place-gap" in f2h3                 # places [2,3], no 1st: leader has no post-stop-line lap
    assert "incomplete-heat" not in f2h3       # leader did 10/12 (>=70%) -> no restart required


def test_messages_are_actionable():
    lines = format_findings(check_results(_stopped_heat(10, _SUB70)))
    joined = " ".join(lines)
    assert "stop" in joined and "restart" in joined and all(l for l in lines)


def test_never_raises_on_garbage():
    for bad in ({}, {"record": None}, {"record": {"C": {"1": "nonsense"}}},
                {"record": {"C": {"1": [{}, {"x": [("?",)]}]}}, "scoringsystem": None}):
        assert isinstance(check_results(bad), list)


# --- mis-click detection -----------------------------------------------------

from cozer.validate import _misclick_findings  # noqa: E402
from cozer.racepattern import race_kind  # noqa: E402


def _race_event(marks_by_boat, pattern="1*(6*1000):1", classname="C"):
    return {"record": {classname: {"1": [{"course": [1000] * 6}, marks_by_boat]}},
            "classes": [["", classname, pattern]],
            "scoringsystem": [400, 300, 225], "races": [], "rules": [], "participants": []}


def test_misclick_too_short_flagged():
    # median-based (self-calibrating): a 10s lap among ~40s laps is far shorter than the boat's own
    # median -> a mis-click. Needs a few laps for a stable median (the first lap is the start leg).
    rec = {"7": [(1, 40.0), (1, 10.0), (1, 41.0), (1, 40.0)]}
    assert [f.code for f in _misclick_findings("C", "1", rec, 6, "circuit")] == ["misclick"]


def test_misclick_disabled_click_absorbed_not_flagged():
    # a spurious click the operator already disabled: gettimes rolls its time into the
    # next lap, so nothing looks off -- no false positive
    rec = {"7": [(1, 40.0), (-1, 10.0), (1, 31.0), (1, 40.0), (1, 40.0)]}   # effective 40, 41, 40, 40
    assert _misclick_findings("C", "1", rec, 6, "circuit") == []


def test_misclick_out_of_order_flagged():
    # a crossing whose time does not advance (duration 0) is an impossible ordering -> flagged
    rec = {"7": [(1, 40.0), (1, 40.0), (1, 0.0), (1, 41.0), (1, 40.0)]}
    assert [f.code for f in _misclick_findings("C", "1", rec, 6, "circuit")] == ["misclick"]


def test_missed_click_circuit_is_unbounded():
    # circuit boats don't pit: both a 2x and a 5x lap read as a possible missed crossing
    for slow in (80.0, 200.0):
        rec = {"7": [(1, 40.0)] * 3 + [(1, slow)]}
        assert [f.code for f in _misclick_findings("C", "1", rec, 6, "circuit")] == ["missed-click"]


def test_missed_click_endurance_bands_out_pit_stops():
    # endurance: a 2x lap is a possible missed click; a 5x lap is a pit/breakdown, NOT
    # flagged -- the two disciplines use separate rules so pits don't shape circuit
    assert [f.code for f in _misclick_findings(
        "P", "1", {"7": [(1, 40.0)] * 3 + [(1, 80.0)]}, 6, "endurance")] == ["missed-click"]
    assert _misclick_findings("P", "1", {"7": [(1, 40.0)] * 3 + [(1, 200.0)]}, 6, "endurance") == []


def test_check_results_flags_circuit_misclick():
    ed = _race_event({"7": [(1, 40.0), (1, 10.0), (1, 41.0), (1, 40.0)]})
    assert "misclick" in _codes(check_results(ed))


def test_time_trial_gets_misclick_not_missed_click():
    # a time trial IS checked for a too-short lap (it would corrupt the best-lap metric) but not the
    # median missed-click -- a solo best-lap run has no useful missed-click distribution (§4.1).
    ed = _race_event({"7": [(1, 40.0), (1, 10.0), (1, 41.0), (1, 40.0)]}, classname="C/T")
    assert race_kind(ed, "C/T") == "timetrial"
    codes = _codes(check_results(ed))
    assert "misclick" in codes                                     # too-short lap flagged
    assert "missed-click" not in codes                             # no missed-click for a solo run


def test_time_trial_skips_median_missed_click():
    # a ~2x-median lap a circuit heat flags as a missed click is NOT flagged for a time trial
    marks = {"7": [(1, 40.0), (1, 40.0), (1, 40.0), (1, 40.0), (1, 90.0)]}
    assert "missed-click" in _codes(check_results(_race_event(marks)))                        # circuit
    assert "missed-click" not in _codes(check_results(_race_event(marks, classname="C/T")))   # time trial


def test_qualification_heat_gets_misclick():
    # §4.1: a qheat is a mass start -> the mis-click check applies (like a circuit heat)
    ed = _race_event({"7": [(1, 40.0), (1, 10.0), (1, 41.0), (1, 40.0)]}, classname="C/Q")
    assert race_kind(ed, "C/Q") == "qualification"
    assert "misclick" in _codes(check_results(ed))


def test_misclick_needs_a_stable_median_not_a_physics_limit():
    # self-calibrating: a boat whose laps are all ~40s is NEVER flagged, even if an (over-large)
    # entered course length would make a physics minimum call them "impossible" -- the false-positive
    # that motivated the switch away from the physics check (issue #26 had 26s minimums vs 11s laps).
    steady = {"7": [(1, 40.0), (1, 40.0), (1, 41.0), (1, 39.0), (1, 40.0)]}
    assert _codes(check_results(_race_event(steady))) == []
    # but a single lap far off that median still stands out
    off = {"7": [(1, 40.0), (1, 40.0), (1, 12.0), (1, 39.0), (1, 40.0)]}
    assert "misclick" in _codes(check_results(_race_event(off)))


def test_acknowledged_lap_is_not_flagged():
    # right-click ▸ Acknowledge: a genuinely slow lap the operator confirmed is kept scored but no
    # longer flagged. The ack key is the lap's CROSSING TIME (cumulative), so it targets exactly one lap.
    from cozer.validate import suspect_marks, enabled_laps
    marks = [(1, 40.0), (1, 40.0), (1, 40.0), (1, 80.0)]           # three ~40s laps + a slow 80s lap
    flagged = suspect_marks(marks, 6, "circuit")
    assert [c for c, _ in flagged.values()] == ["long"]            # the 80s lap is a missed-click
    cross = enabled_laps(marks, 6)[3][2]                           # its lap-line crossing time
    assert cross == 200.0
    assert suspect_marks(marks, 6, "circuit", acked=[cross]) == {}  # acknowledged -> silent
    # and the status-bar summary drops it too, fed from info['ack']
    rec = {"7": marks}
    assert [f.code for f in _misclick_findings("C", "1", rec, 6, "circuit")] == ["missed-click"]
    assert _misclick_findings("C", "1", rec, 6, "circuit", {"7": [cross]}) == []


def test_acknowledge_targets_one_lap_not_the_others():
    # acknowledging one outlier's crossing time leaves a DIFFERENT outlier still flagged
    from cozer.validate import suspect_marks
    marks = [(1, 40.0), (1, 40.0), (1, 12.0), (1, 40.0), (1, 90.0)]   # a short (12) AND a long (90)
    assert sorted(c for c, _ in suspect_marks(marks, 6, "circuit").values()) == ["long", "short"]
    left = suspect_marks(marks, 6, "circuit", acked=[92.0])          # 40+40+12 = crossing of the short lap
    assert sorted(c for c, _ in left.values()) == ["long"]           # the 90s long lap is still flagged


def test_acknowledgement_survives_a_mark_inserted_before_it():
    # the acknowledgement is keyed by the lap's CROSSING TIME, not its list index, so inserting a mark
    # before it (which shifts every later index but preserves the running time) keeps the same lap
    # acknowledged -- it is structurally immune to the cached-index shift behind #42/#43.
    from cozer.validate import suspect_marks, enabled_laps
    from cozer.app.editor import insert_lap_split
    marks = [[1, 40.0], [1, 40.0], [1, 40.0], [1, 80.0]]
    cross = enabled_laps(marks, 6)[3][2]                            # 200.0 -- the slow lap
    assert {i: c for i, (c, _h) in suspect_marks(marks, 6, "circuit", acked=[cross]).items()} == {}
    insert_lap_split(marks, 50.0)                                   # insert a lap BEFORE the slow one
    laps = enabled_laps(marks, 6)
    assert [i for i, _d, c in laps if round(c, 2) == 200.0] == [4]  # slow lap: index 3 -> 4, crossing kept
    flagged = {i: c for i, (c, _h) in suspect_marks(marks, 6, "circuit", acked=[cross]).items()}
    assert 4 not in flagged                                         # still acknowledged (crossing matched)
    assert flagged.get(1) == "short"                                # the new short split lap flags fresh


def test_acknowledgement_rides_the_native_reshape():
    # info['ack'] lives in the heat info dict -> survives to_native (the heat slot is copied verbatim);
    # check_results honours it identically on the legacy and native models.
    from cozer.native import to_native
    ed = _race_event({"7": [(1, 40.0), (1, 40.0), (1, 40.0), (1, 80.0)]})
    assert "missed-click" in _codes(check_results(ed))
    ed["record"]["C"]["1"][0]["ack"] = {"7": [200.0]}               # acknowledge the slow lap
    assert "missed-click" not in _codes(check_results(ed))
    assert check_results(ed) == check_results(to_native(ed))


def test_dsq_in_some_but_not_all_heats_flagged():
    # §317.08: a post-race technical DSQ (illegal boat/motor) applies to EVERY heat the boat raced, so
    # cozer flags a boat disqualified in some-but-not-all of its heats (operator may have missed the rest).
    from cozer.records import DQ
    from cozer.native import to_native
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}
    laps = [(1, 20.0)] * 3
    dsq = [[DQ, 65.0, "504"]]                                    # a disqualification mark
    ed = {"kind": "event", "title": "X", "scoringsystem": [400, 300, 225], "rules": [], "races": [],
          "classes": [["", "C", "2*(3*1000):2"]],
          "participants": [["", "N", "S", "FIN", "C", str(b)] for b in (5, 7)],
          "record": {"C": {
              "1": [dict(info), {"5": laps + dsq, "7": laps}],    # boat 5 DSQ in heat 1...
              "2": [dict(info), {"5": laps, "7": laps}]}}}        # ...but NOT in heat 2 -> flag
    assert "dsq-heats" in _codes(check_results(ed))
    assert check_results(ed) == check_results(to_native(ed))     # identical on the native model
    # DSQ in BOTH heats -> consistent, no flag
    ed["record"]["C"]["2"][1]["5"] = laps + dsq
    assert "dsq-heats" not in _codes(check_results(ed))
    # DSQ in neither -> no flag
    ed["record"]["C"]["1"][1]["5"] = laps
    ed["record"]["C"]["2"][1]["5"] = laps
    assert "dsq-heats" not in _codes(check_results(ed))


@pytest.mark.parametrize("path", _EVENTS, ids=[os.path.basename(p) for p in _EVENTS])
def test_check_results_native_matches_legacy(path):
    # check_results reads the record via the phase view, so validation is identical whether the
    # in-memory model is native (base/kind/number) or the legacy suffixed heat-ids. (It used to
    # read record.get(cl) by synthesized class name -> no findings on the native model.)
    ed = store.read_legacy_coz(path)
    assert check_results(ed) == check_results(to_native(ed))


def test_validate_sees_events():
    assert _EVENTS, "no legacy events found -- native/legacy validate parity would pass vacuously"
