"""Tests for the non-destructive ruleset merge (cozer/app/ruleset.py).

Both the GUI import (import_ruleset) and the CLI accumulate (accumulate_ruleset)
merge additively and NEVER overwrite existing event data: the scoring system is
filled only when the event has none, and rules dedupe by (action, paragraph) so a
reworded same-paragraph rule is not duplicated.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.app.ruleset import import_ruleset, accumulate_ruleset


def _ev(**kw):
    ed = {"kind": "event", "scoringsystem": [], "rules": [], "classnames": [], "classes": []}
    ed.update(kw)
    return ed


def test_bundled_circuit_ruleset_marks_all_heats_scope():
    # Rule descriptions carry a scope only when it is NOT the default "this heat": the §317.08 DSQ
    # (illegal boat/motor at post-race inspection) applies to ALL heats, so its description says so —
    # the operator sees the scope in the insert-rule menu (which shows the article as a suffix).
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "cozer", "rulesets", "uim_circuit_2026.cozj")
    rules = json.load(open(path, encoding="utf-8"))["rules"]
    r317 = next(r for r in rules if len(r) > 2 and r[2] == "317.08")
    assert "all heats" in r317[3]


def test_bundled_general_ruleset_marks_fuel_dsq_scope():
    # §508.09: an illegal-fuel DSQ reaches beyond one heat — the first offence disqualifies every run up
    # to the test, a further offence the whole event — so both descriptions carry a scope (not this-heat).
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "cozer", "rulesets", "uim_general_2026.cozj")
    fuel = [r[3] for r in json.load(open(path, encoding="utf-8"))["rules"]
            if len(r) > 3 and r[2] == "508.09"]
    assert any("all runs up to the test" in d for d in fuel)      # first illegal-fuel offence
    assert any("whole event" in d for d in fuel)                  # a further infringement


def test_import_fills_empty_scoring():
    ev = _ev()
    import_ruleset(ev, {"scoringsystem": [10, 5]})
    assert ev["scoringsystem"] == [10, 5]


def test_import_never_overwrites_existing_scoring():
    ev = _ev(scoringsystem=[400, 300, 225])
    changed = import_ruleset(ev, {"scoringsystem": [10, 5]})
    assert ev["scoringsystem"] == [400, 300, 225]        # kept, not replaced
    assert "scoringsystem" not in changed


def test_import_dedups_rule_by_action_paragraph():
    ev = _ev(rules=[["", "DQ", "313", "original wording"]])
    import_ruleset(ev, {"rules": [["", "DQ", "313", "reworded"]]})   # same (DQ, 313)
    assert [r[3] for r in ev["rules"]] == ["original wording"]        # no duplicate entry


def test_import_adds_new_class_names_and_rules():
    ev = _ev(classnames=["A"], rules=[["", "DQ", "1", "x"]])
    changed = import_ruleset(ev, {"classnames": ["A", "B"], "rules": [["", "DS", "2", "y"]]})
    assert ev["classnames"] == ["A", "B"] and len(ev["rules"]) == 2
    assert set(changed) == {"classnames", "rules"}


def test_accumulate_non_destructive():
    tgt = _ev(scoringsystem=[400], rules=[["", "DQ", "1", "AA"]])
    reports = accumulate_ruleset(tgt, {"scoringsystem": [10], "rules": [["", "DQ", "1", "BB"]]})
    assert tgt["scoringsystem"] == [400]                 # kept
    assert [r[3] for r in tgt["rules"]] == ["AA"]        # kept; source's reworded rule dropped
    assert len(reports) == 2                             # both conflicts reported


def test_malformed_rules_do_not_crash():
    for bad in ([[""]], [["x"]], [[]], ["notalist"], [["", "DQ"]]):
        assert isinstance(import_ruleset(_ev(), {"rules": bad}), list)
        assert isinstance(accumulate_ruleset(_ev(), {"rules": bad}), list)


def test_import_and_accumulate_agree():
    # both are now non-destructive: same inputs -> same kept scoring + rules
    src = {"scoringsystem": [9], "rules": [["", "DQ", "1", "reworded"]]}
    a = _ev(scoringsystem=[400], rules=[["", "DQ", "1", "orig"]])
    b = _ev(scoringsystem=[400], rules=[["", "DQ", "1", "orig"]])
    import_ruleset(a, src)
    accumulate_ruleset(b, src)
    assert a["scoringsystem"] == b["scoringsystem"] == [400]
    assert [r[3] for r in a["rules"]] == [r[3] for r in b["rules"]] == ["orig"]
