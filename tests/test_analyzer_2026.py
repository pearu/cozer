"""Tests for the 2026 UIM record-code additions (GitHub #11):

- ``BC`` blue card: note-only, no effect on points/placement (a *second* blue
  card is recorded manually as ``DQ``).
- ``NC`` not-classified (endurance 902.47): excluded from classification.
- ``PL3`` / ``PL4`` / ``PL15``: endurance penalty-lap magnitudes 3 / 4 / 15.

Each uses a with/without comparison so it asserts exactly the new code's effect.
"""
import copy

from cozer import analyzer
from cozer.records import (
    BC, NC, PL3, PL4, PL15, LP2, DS, DQ, NQ, IR, DNS, DNR, ACC, DSQ, DNQ, DNF,
)


def _circuit_record(marks_by_pid, nlaps=5):
    return ({"course": [1000] * nlaps, "racetime": 100000.0}, marks_by_pid)


def _endurance_record(marks_by_pid):
    return ({"course": [1000], "duration": 100000.0, "racetime": 100000.0}, marks_by_pid)


def test_bc_is_note_only():
    base = {"A": [(1, 20.0)] * 5, "B": [(1, 22.0)] * 5}
    ss = [400, 300]
    res_plain = analyzer.analyze("1", _circuit_record(copy.deepcopy(base)), ss)
    withbc = copy.deepcopy(base)
    withbc["B"].append((BC, 30.0, "dangerous driving"))
    res_bc = analyzer.analyze("1", _circuit_record(withbc), ss)

    # a blue card changes neither points nor placement...
    assert res_bc["B"]["points"] == res_plain["B"]["points"] > 0
    assert res_bc["B"]["place"] == res_plain["B"]["place"] > 0
    # ...it is only recorded as a note
    assert res_bc["B"]["notes"].get("BC") == ["dangerous driving"]
    assert "BC" not in res_plain["B"]["notes"]

    # Two blue cards are STILL note-only: a repeat-offence DSQ is a manual
    # decision (cards accumulate across events, so cozer never auto-DQs a 2nd).
    two = copy.deepcopy(base)
    two["B"].extend([(BC, 30.0, "first"), (BC, 60.0, "second")])
    res_two = analyzer.analyze("1", _circuit_record(two), ss)
    assert res_two["B"]["place"] == res_plain["B"]["place"] > 0
    assert res_two["B"]["points"] == res_plain["B"]["points"]
    assert res_two["B"]["notes"].get("BC") == ["first", "second"]


def test_endurance_penalty_lap_magnitudes():
    ss = [20, 17]
    for code, laps in [(PL3, 3), (PL4, 4), (PL15, 15)]:
        base = {"A": [(1, 10.0)] * 20}
        res_plain = analyzer.analyze("1", _endurance_record(copy.deepcopy(base)), ss)
        withpen = copy.deepcopy(base)
        withpen["A"].append((code, 5.0, "infringement"))
        res_pen = analyzer.analyze("1", _endurance_record(withpen), ss)

        plain_laps = res_plain["A"]["totallaps"][1]
        pen_laps = res_pen["A"]["totallaps"][1]
        assert pen_laps == plain_laps - laps, (code, plain_laps, pen_laps)


def test_nc_excludes_from_classification():
    ss = [20, 17]
    base = {"A": [(1, 10.0)] * 10, "B": [(1, 11.0)] * 10}
    res_plain = analyzer.analyze("1", _endurance_record(copy.deepcopy(base)), ss)
    assert res_plain["B"]["place"] > 0          # B is normally classified

    withnc = copy.deepcopy(base)
    withnc["B"].append((NC, 5.0, "red flag"))
    res_nc = analyzer.analyze("1", _endurance_record(withnc), ss)

    assert res_nc["B"]["place"] == -1           # not classified
    assert res_nc["B"]["points"] == -1
    assert res_nc["B"]["notes"].get("NC") == ["red flag"]
    assert res_nc["A"]["place"] > 0             # the other boat is unaffected


def test_lp2_loses_two_positions():
    ss = [400, 300, 225, 169]
    # four boats finishing A(1) B(2) C(3) D(4) by speed (A fastest)
    base = {"A": [(1, 20.0)] * 5, "B": [(1, 21.0)] * 5,
            "C": [(1, 22.0)] * 5, "D": [(1, 23.0)] * 5}
    res_plain = analyzer.analyze("1", _circuit_record(copy.deepcopy(base)), ss)
    assert [res_plain[x]["place"] for x in "ABCD"] == [1, 2, 3, 4]
    assert [res_plain[x]["points"] for x in "ABCD"] == [400, 300, 225, 169]

    withlp2 = copy.deepcopy(base)
    withlp2["B"].append((LP2, 5.0, "not keeping the lane"))
    res = analyzer.analyze("1", _circuit_record(withlp2), ss)
    # B drops two places (2 -> 4); C and D each move up one
    assert res["A"]["place"] == 1 and res["A"]["points"] == 400
    assert res["C"]["place"] == 2 and res["C"]["points"] == 300
    assert res["D"]["place"] == 3 and res["D"]["points"] == 225
    assert res["B"]["place"] == 4 and res["B"]["points"] == 169
    assert res["B"]["notes"].get("LP2") == ["not keeping the lane"]


def test_209_codes_score_identically_to_deprecated():
    """The 2026 §209 codes have the same scoring effect as their pre-§209
    equivalents (DSQ==DQ, DNS/DNR/ACC==DS, DNQ==NQ) -- only the label differs."""
    ss = [400, 300]

    def place_pts(heat, code):
        base = {"A": [(1, 20.0)] * 5, "B": [(1, 22.0)] * 5}
        base["B"].append((code, 30.0, "x"))
        r = analyzer.analyze(heat, _circuit_record(base), ss)["B"]
        return (r["place"], r["points"])

    assert place_pts("1", DSQ) == place_pts("1", DQ)          # disqualified
    for c in (DNS, DNR, ACC):                                 # excluded outcomes
        assert place_pts("1", c) == place_pts("1", DS)
    assert place_pts("1", DNF) == place_pts("1", IR)          # did not finish == interruption
    assert place_pts("1q", DNQ) == place_pts("1q", NQ)        # not qualified (qual heat)

    # the new code records its OWN label, not the deprecated one
    base = {"A": [(1, 20.0)] * 5, "B": [(1, 22.0)] * 5}
    base["B"].append((DSQ, 30.0, "fouling"))
    notes = analyzer.analyze("1", _circuit_record(base), ss)["B"]["notes"]
    assert notes.get("DSQ") == ["fouling"] and "DQ" not in notes


def test_auto_insert_follows_the_ruleset():
    """The auto-inserted non-finisher / non-starter mark follows the event's
    rules: §209 DNF/DNS when the ruleset defines them, else legacy IR/DS
    (the default, so the golden legacy events are unaffected)."""
    from cozer.analyzer import rule_action_codes
    ss = [400, 300]

    def autonote(b_marks, rulecodes):
        rec = ({"course": [1000] * 5, "racetime": 100000.0},
               {"A": [(1, 20.0)] * 5, "B": list(b_marks)})
        return sorted(analyzer.analyze("1", rec, ss, rulecodes)["B"]["notes"])

    started_no_finish = [(1, 20.0), (1, 20.0)]   # 2 of 5 laps -> auto non-finish
    never_started = []                            # no laps -> auto non-start
    assert autonote(started_no_finish, ()) == ["IR"]              # default -> legacy
    assert autonote(started_no_finish, {"IR", "DS"}) == ["IR"]    # legacy ruleset
    assert autonote(started_no_finish, {"DNF", "DNS"}) == ["DNF"]  # 2026 ruleset
    assert autonote(never_started, ()) == ["DS"]
    assert autonote(never_started, {"DNF", "DNS"}) == ["DNS"]

    assert rule_action_codes({"rules": [["", "DNF", " ", "x"],
                                        ["", "DSQ", "406", "y"]]}) == {"DNF", "DSQ"}


def test_auto_score_does_not_mutate_rec():
    """A boat short of the required laps with no explicit outcome mark is auto-scored
    as a non-finisher / non-starter -- DNF/DNS when the ruleset defines them, else
    legacy IR/DS. analyze() does this by setting the result's code + note WITHOUT
    touching rec: it must stay pure so every caller can pass the LIVE record (no
    load-bearing deepcopy). This pins that the input marks are untouched and repeated
    calls are identical -- the invariant the goldens don't cover (they analyze once
    and never re-read rec)."""
    ss = [400, 300, 225]
    for marks, rulecodes, note in (
        ([(1, 1000.0), (1, 1050.0)], {"DNF", "DNS"}, "DNF"),   # 2026 non-finisher
        ([(1, 1000.0), (1, 1050.0)], set(),          "IR"),    # legacy non-finisher
        ([],                          {"DNF", "DNS"}, "DNS"),   # 2026 never-started
        ([],                          set(),          "DS"),    # legacy never-started
    ):
        rec = ({"course": [1000] * 5, "racetime": 100000.0}, {"B": list(marks)})
        live = rec[1]["B"]
        r1 = analyzer.analyze("1", rec, ss, rulecodes)["B"]
        assert live == list(marks)                     # analyze did NOT mutate rec
        r2 = analyzer.analyze("1", rec, ss, rulecodes)["B"]
        assert live == list(marks)                     # still untouched on repeat
        assert sorted(r1["notes"]) == [note]           # non-finisher auto-scored anyway
        assert r1 == r2                                # pure -> identical repeat


def test_deprecation_warning():
    """A 2026 event (rules use §209 codes) flags deprecated DQ/DS/NQ/IR use;
    a legacy event never does (backward compatible)."""
    from cozer.analyzer import deprecation_warning
    ev2026 = {"rules": [["", "DSQ", "406", "x"], ["", "DNS", " ", "y"]]}
    evlegacy = {"rules": [["", "DQ", "406", "x"], ["", "DS", " ", "y"]]}
    assert deprecation_warning(ev2026, "DQ") == "DSQ"
    assert deprecation_warning(ev2026, "IR") == "DNF"
    assert deprecation_warning(ev2026, "DSQ") is None    # already §209
    assert deprecation_warning(ev2026, "PL") is None     # not an outcome code
    assert deprecation_warning(evlegacy, "DQ") is None   # legacy: never flagged
