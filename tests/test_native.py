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
    assert _cls_map(rt["classes"]) == _cls_map(ed["classes"])   # class name -> (col0, pattern) kept


def test_native_sees_the_corpus():
    assert _EVENTS, "no legacy events found -- corpus round-trip would pass vacuously"


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


def test_native_carries_a_schema_version():
    ed = {"classes": [], "record": {}, "races": []}
    nat = to_native(ed)
    assert nat["schema"] == SCHEMA and SCHEMA >= 2       # native is tagged, version 2+
    assert is_native(nat) and not is_native(ed)          # legacy/untagged reads as v1
    assert schema_of(ed) == 1
    assert "schema" not in from_native(nat)              # the suffixed shape carries no tag


def test_native_passes_other_keys_through():
    ed = {"classes": [], "record": {}, "races": [], "participants": [["", "A", "B", "C", "F 500", "10"]],
          "scoringsystem": [400, 300], "rules": [["", "DQ"]], "qheat1": {"F 500": ["10"]}, "title": "T"}
    nat = to_native(ed)
    for k in ("participants", "scoringsystem", "rules", "qheat1", "title"):
        assert nat[k] == ed[k]
