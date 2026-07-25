"""Tests for cozer/app/heatxfer.py — exporting/importing a heat's measured records between two
instances of the same event (owner feature). Pure logic: no GUI."""
from cozer.app import heatxfer
from cozer.native import to_native, ensure_heat, record_heat
from cozer.store import apply_op, dumps, loads


def _event(record=True, races=None, boats=("7", "51")):
    ed = to_native({
        "classes": [["", "F 500", "3*(1000):1"], ["", "F 500/T", "2*(1000):1"]],
        "participants": [["", "A", "One", "X", "F 500", b] for b in boats],
        "record": {}, "races": races if races is not None else [],
        "scoringsystem": [10, 5, 3], "rules": [],
    })
    if record:
        ensure_heat(ed, "F 500/T", "1t",
                    [{"course": [1000, 1000], "sheats": 1, "duration": None, "racetime": 1000.0},
                     {"7": [[1, 20.0], [1, 21.0]], "51": [[1, 22.0], [1, 23.0]]}])
    return ed


def _apply_op(ed):
    return lambda op: apply_op(ed, op)          # a store.record stand-in: applies to eventdata


def test_export_carries_address_pattern_and_record():
    payload = heatxfer.export_heats(_event(), [("F 500/T", "1t"), ("F 500/T", "2t")])
    assert payload["kind"] == "cozer-heat-records"
    assert len(payload["heats"]) == 1                       # only 1t has a record; 2t is skipped
    h = payload["heats"][0]
    assert h["class"] == "F 500/T" and h["phase"] == "timetrial" and h["heat"] == "1t"
    assert h["pattern"] == "2*(1000):1"
    assert h["record"][1]["7"] == [[1, 20.0], [1, 21.0]]


def test_round_trip_into_a_clean_target_adds_record_and_race_entry():
    payload = loads(dumps(heatxfer.export_heats(_event(), [("F 500/T", "1t")])))   # via JSON, like a file
    tgt = _event(record=False, races=[])                    # same classes, no record, empty schedule
    imported, rejected = heatxfer.import_heats(tgt, payload, _apply_op(tgt), confirm=lambda cl, h: True)
    assert imported == ["F 500/T 1t"] and rejected == []
    assert record_heat(tgt, "F 500/T", "1t")[1]["7"] == [[1, 20.0], [1, 21.0]]      # record landed
    assert record_heat(tgt, "F 500/T", "1t")[0]["racetime"] == 1000.0              # info too
    # the missing Races-tab entry was added (schedule metadata)
    entries = [e for race in tgt["races"] for e in race]
    assert any(e["name"] == "F 500" and e["kind"] == "timetrial" and e["number"] == 1 for e in entries)


def test_reject_missing_class_pattern_mismatch_and_missing_boat():
    payload = heatxfer.export_heats(_event(), [("F 500/T", "1t")])

    no_class = _event(record=False)
    no_class["classes"] = [c for c in no_class["classes"] if c.get("name") != "F 500"]  # drop the class
    _, rej = heatxfer.import_heats(no_class, payload, _apply_op(no_class), lambda *a: True)
    assert rej and "no class/phase" in rej[0]

    bad_pat = to_native({"classes": [["", "F 500", "3*(1000):1"], ["", "F 500/T", "3*(1000):1"]],  # differs
                         "participants": [["", "A", "One", "X", "F 500", "7"],
                                          ["", "B", "Two", "Y", "F 500", "51"]],
                         "record": {}, "races": [], "scoringsystem": [10, 5, 3], "rules": []})
    _, rej = heatxfer.import_heats(bad_pat, payload, _apply_op(bad_pat), lambda *a: True)
    assert rej and "race pattern" in rej[0]

    missing_boat = _event(record=False, boats=("7",))       # 51 is not a participant here
    _, rej = heatxfer.import_heats(missing_boat, payload, _apply_op(missing_boat), lambda *a: True)
    assert rej and "51" in rej[0] and "not in" in rej[0]
    assert record_heat(missing_boat, "F 500/T", "1t") is None    # nothing written on a rejected heat


def test_confirm_before_overwriting_existing_measured_data():
    payload = heatxfer.export_heats(_event(), [("F 500/T", "1t")])
    tgt = _event(record=True)                               # target ALREADY has measured data at 1t
    tgt["record"]["F 500"]["timetrial"]["1"][0][1]["7"] = [[1, 99.0]]   # a distinct existing value

    imported, rejected = heatxfer.import_heats(tgt, payload, _apply_op(tgt), confirm=lambda cl, h: False)
    assert imported == [] and rejected == ["F 500/T 1t: kept existing measured data"]
    assert record_heat(tgt, "F 500/T", "1t")[1]["7"] == [[1, 99.0]]     # untouched

    imported, _ = heatxfer.import_heats(tgt, payload, _apply_op(tgt), confirm=lambda cl, h: True)
    assert imported == ["F 500/T 1t"]
    assert record_heat(tgt, "F 500/T", "1t")[1]["7"] == [[1, 20.0], [1, 21.0]]      # overwritten


def test_valid_heats_import_even_when_others_are_rejected():
    good = heatxfer.export_heats(_event(), [("F 500/T", "1t")])["heats"][0]
    bad = dict(good, heat="1t", class_="F 500/T")           # a second, malformed-ish entry
    bad = {"class": "GHOST/T", "phase": "timetrial", "heat": "1t",
           "pattern": "2*(1000):1", "record": good["record"]}
    payload = {"kind": "cozer-heat-records", "heats": [bad, good]}
    tgt = _event(record=False)
    imported, rejected = heatxfer.import_heats(tgt, payload, _apply_op(tgt), lambda *a: True)
    assert imported == ["F 500/T 1t"] and len(rejected) == 1 and "GHOST" in rejected[0]


def test_ensure_race_entry_is_idempotent():
    payload = heatxfer.export_heats(_event(), [("F 500/T", "1t")])
    tgt = _event(record=False,                              # the heat is ALREADY scheduled
                 races=[[{"name": "F 500", "kind": "timetrial", "number": 1, "occurrence": 0}]])
    heatxfer.import_heats(tgt, payload, _apply_op(tgt), lambda *a: True)
    tt = [e for race in tgt["races"] for e in race
          if e["name"] == "F 500" and e["kind"] == "timetrial" and e["number"] == 1]
    assert len(tt) == 1                                     # not duplicated


def test_not_a_heat_records_file_is_rejected():
    imported, rejected = heatxfer.import_heats(_event(record=False), {"kind": "something-else"},
                                               lambda op: None, lambda *a: True)
    assert imported == [] and rejected == ["not a cozer heat-records file"]
