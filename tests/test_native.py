"""Stage 1 of the suffix refactor: the lossless native converter (cozer/native.py).

The whole bundled corpus must round-trip through the suffix-free shape with the RECORD
byte-identical (so the analyze/golden equivalence is untouched) and races exact; class
rows are preserved as a name -> (col0, pattern) mapping (grouping intentionally pulls a
base's phases together, so the list order may change).
"""
import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.store import read_legacy_coz  # noqa: E402
from cozer.native import to_native, from_native, SCHEMA, schema_of, is_native  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _events():
    return sorted(glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")) +
                  glob.glob(os.path.join(REPO, "legacy", "cozer", "data", "*.coz")))


def _cls_map(classes):
    return {r[1]: (r[0], r[2]) for r in (classes or []) if len(r) > 2}


_EVENTS = _events()


@pytest.mark.parametrize("path", _EVENTS, ids=[os.path.basename(p) for p in _EVENTS])
def test_native_round_trips_the_corpus(path):
    ed = read_legacy_coz(path)
    rt = from_native(to_native(ed))
    assert rt["record"] == ed["record"]              # byte-exact record -> goldens unaffected
    assert rt["races"] == ed["races"]                # scheduled heats exact (incl. restart refs)
    # classes are content-preserving but order-CANONICALIZED (base-grouped) -- compare as a
    # name -> (col0, pattern) map; the explicit order behaviour is locked below.
    assert _cls_map(rt["classes"]) == _cls_map(ed["classes"])
    for k in ("sheats", "savechecked"):              # suffix-keyed caches round-trip exactly
        assert rt.get(k) == ed.get(k)


@pytest.mark.parametrize("path", _EVENTS, ids=[os.path.basename(p) for p in _EVENTS])
def test_native_has_no_class_suffixes(path):
    from cozer.classes import getclass
    nat = to_native(read_legacy_coz(path))
    for c in nat.get("classes", []):                 # class names are bases (no /T,/Q)
        assert getclass(c["name"]) == c["name"], c["name"]
    for base in nat.get("record", {}):               # record keys are bases
        assert getclass(base) == base, base
    for key in ("sheats", "savechecked"):            # class-keyed caches are bases
        for base in nat.get(key, {}):
            assert getclass(base) == base, (key, base)


def test_native_sees_the_corpus():
    assert _EVENTS, "no legacy events found -- corpus round-trip would pass vacuously"


@pytest.mark.parametrize("path", _EVENTS, ids=[os.path.basename(p) for p in _EVENTS])
def test_to_phases_reads_native_identically(path):
    # the phases hub builds identical Phase objects from the native shape and the legacy shape,
    # so every phases-based consumer is unchanged when the in-memory model goes native.
    from cozer.phases import to_phases
    ed = read_legacy_coz(path)
    assert to_phases(to_native(ed)) == to_phases(ed)


@pytest.mark.parametrize("path", _EVENTS, ids=[os.path.basename(p) for p in _EVENTS])
def test_racepattern_helpers_read_native_identically(path):
    # get_classes / class_pattern / race_kind answer the same on the native model (addressed by
    # synthesized legacy names) as on the legacy model.
    from cozer.racepattern import get_classes, class_pattern, race_kind
    ed = read_legacy_coz(path)
    nat = to_native(ed)
    assert set(get_classes(nat)) == set(get_classes(ed))
    for cl in get_classes(ed):
        assert class_pattern(nat, cl) == class_pattern(ed, cl), cl
        assert race_kind(nat, cl) == race_kind(ed, cl), cl


def test_native_shape_is_suffix_free():
    ed = {"classes": [["", "F 500/T", "1*(1000):1"],
                      ["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"],
                      ["", "F 500", "4*(1400):3"]],
          "record": {"F 500": {"1": [{"c": 1}, {"10": []}], "1r": [{"c": 1}, {"10": []}]},
                     "F 500/Q": {"1q": [{"c": 1}, {"10": []}]}},
          "races": [[["", "F 500/Q", "1q"], ["", "F 500", "1r"]]], "participants": []}
    nat = to_native(ed)
    # classes: one entry per base, explicit kinds, qualifiers split off the pattern
    assert [c["name"] for c in nat["classes"]] == ["F 500"]
    assert [p["kind"] for p in nat["classes"][0]["phases"]] == ["timetrial", "qualification", "circuit"]
    q = next(p for p in nat["classes"][0]["phases"] if p["kind"] == "qualification")
    assert q["pattern"] == "3*(1000):1" and q["qualifiers"] == [4, 4, 4]
    # record: base -> kind -> number -> [records]; a restart is an extra list entry (no "1r" key)
    assert set(nat["record"]["F 500"]) == {"circuit", "qualification"}
    assert list(nat["record"]["F 500"]["circuit"]) == ["1"]
    assert len(nat["record"]["F 500"]["circuit"]["1"]) == 2          # original + restart
    # races: suffix-free heat refs (occurrence carries the restart rank)
    assert nat["races"][0][0] == {"name": "F 500", "kind": "qualification", "number": 1, "occurrence": 0}
    assert nat["races"][0][1] == {"name": "F 500", "kind": "circuit", "number": 1, "occurrence": 1}
    assert from_native(nat)["record"] == ed["record"]               # and it inverts


def test_native_round_trips_a_new_qualification_event():
    # a suffix-free authored event: the qualifiers token splits out and rejoins exactly
    ed = {"classes": [["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"],
                      ["", "F 500", "4*(1400):3"]], "record": {}, "races": []}
    assert from_native(to_native(ed))["classes"] == ed["classes"]


def test_native_canonicalizes_class_order_base_grouped():
    # a legacy flat layout (all bases, then all /T) regroups to base-grouped -- each base
    # followed by its phases. Intended: the native model nests phases under a base, so
    # base-grouped IS its canonical order (and matches the base-grouped Classes tab).
    ed = {"classes": [["", "A", "1*(1000):1"], ["", "B", "1*(1000):1"],
                      ["", "A/T", "1*(1000):1"], ["", "B/T", "1*(1000):1"]],
          "record": {}, "races": []}
    assert [r[1] for r in ed["classes"]] == ["A", "B", "A/T", "B/T"]        # interleaved before
    rt = from_native(to_native(ed))
    assert [r[1] for r in rt["classes"]] == ["A", "A/T", "B", "B/T"]        # base-grouped after
    assert _cls_map(rt["classes"]) == _cls_map(ed["classes"])              # same content though


def test_native_carries_a_schema_version():
    ed = {"classes": [], "record": {}, "races": []}
    nat = to_native(ed)
    assert nat["schema"] == SCHEMA and SCHEMA >= 2       # native is tagged, version 2+
    assert is_native(nat) and not is_native(ed)          # legacy/untagged reads as v1
    assert schema_of(ed) == 1
    assert "schema" not in from_native(nat)              # the suffixed shape carries no tag


def test_dump_event_writes_suffix_free_and_round_trips():
    from cozer.store import dump_event, load_event
    ed = {"classes": [["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"], ["", "F 500", "4*(1400):3"]],
          "record": {"F 500/Q": {"1q": [{"course": [1000]}, {"10": [[1, 20.0]]}]},
                     "F 500": {"1": [{"course": [1400]}, {"10": [[1, 30.0]]}]}},
          "races": [[["", "F 500/Q", "1q"], ["", "F 500", "1"]]], "participants": []}
    text = dump_event(ed)
    assert '"schema"' in text                              # tagged native (self-describing)
    assert "/Q" not in text and "/T" not in text           # no class-name suffixes on disk
    assert '"1q"' not in text                               # no heat-id suffixes on disk
    rt = load_event(text)                                  # store loads the native shape back
    assert rt["record"] == to_native(ed)["record"]         # native record byte-identical through the store


def test_to_native_and_from_native_are_idempotent():
    ed = {"classes": [["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"], ["", "F 500", "4*(1400):3"]],
          "record": {}, "races": []}
    nat = to_native(ed)
    assert to_native(nat) == nat            # already native -> returned as-is (no double-encode)
    suf = from_native(nat)
    assert from_native(suf) == suf          # already suffixed -> returned as-is


def test_apply_op_and_record_heat_on_native():
    from cozer.store import apply_op
    nat = to_native({"classes": [["", "C", "2*(3*1000):1"]], "record": {}, "races": []})
    apply_op(nat, {"op": "heat", "cl": "C", "h": "1", "info": {"course": [1000]}, "ids": ["7", "3"]})
    apply_op(nat, {"op": "lap", "cl": "C", "h": "1", "id": "7", "mark": [1, 20.0]})
    apply_op(nat, {"op": "heat", "cl": "C", "h": "1r", "info": {}, "ids": ["7"]})   # restart -> occ 1
    apply_op(nat, {"op": "lap", "cl": "C", "h": "1r", "id": "7", "mark": [1, 19.0]})
    from cozer.native import record_heat
    assert record_heat(nat, "C", "1")[1]["7"] == [[1, 20.0]]                        # original
    assert record_heat(nat, "C", "1r")[1]["7"] == [[1, 19.0]]                       # restart (occ 1)
    assert len(nat["record"]["C"]["circuit"]["1"]) == 2                             # both under number 1


def test_native_passes_other_keys_through():
    ed = {"classes": [], "record": {}, "races": [], "participants": [["", "A", "B", "C", "F 500", "10"]],
          "scoringsystem": [400, 300], "rules": [["", "DQ"]], "qheat1": {"F 500": ["10"]}, "title": "T"}
    nat = to_native(ed)
    for k in ("participants", "scoringsystem", "rules", "qheat1", "title"):
        assert nat[k] == ed[k]
