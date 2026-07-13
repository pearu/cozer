"""Unit tests for the record helpers (cozer/records.py)."""
from cozer.records import insertmark, gettimes, reccodemap, invreccodemap


def test_reccode_maps_are_inverses():
    assert invreccodemap[reccodemap["DS"]] == "DS"
    assert reccodemap["IR"] == 11 and invreccodemap[11] == "IR"


def test_insertmark_append_past_end():
    rec = [(1, 10.0), (1, 12.0)]
    insertmark(rec, 11, 100.0, "late")
    assert rec == [(1, 10.0), (1, 12.0), (11, 100.0, "late")]


def test_insertmark_inserts_between_laps():
    rec = [(1, 10.0), (1, 12.0)]
    insertmark(rec, 11, 15.0, "mid")   # 15 < cumulative 22 -> insert before 2nd lap
    assert rec == [(1, 10.0), (11, 15.0, "mid"), (1, 12.0)]


def test_insertmark_handles_event_mark_branch():
    rec = [(11, 50.0, "a")]            # first mark is a non-lap event mark
    insertmark(rec, 12, 30.0, "b")
    assert rec == [(12, 30.0, "b"), (11, 50.0, "a")]


def test_gettimes_with_disabled_and_inserted():
    rec = [(1, 10.0), (2, 5.0), (-1, 3.0), (1, 7.0)]
    assert gettimes(rec) == [10.0, 5.0, 10.0]     # disabled -1 folds into next lap


def test_gettimes_stops_at_stime():
    rec = [(1, 10.0), (1, 5.0), (1, 7.0)]
    assert gettimes(rec, stime=20) == [10.0, 5.0]  # cumulative 25 for 3rd excluded
