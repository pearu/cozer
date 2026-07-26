"""Timer running-order seeding (PHASES.md §5): the ladder's pre-Start order follows the derived
START ORDER (``seeding.start_order``) instead of boat number -- so heat 2 shows in heat 1's finishing
order, a final in qualifying order, etc. ``standings``/``ladder`` take an optional ``start_rank``
tie-break; ``_build_ladder`` feeds it from ``start_order``. Covers the pure tie-break and the panel
wiring seam (issue #44)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QPushButton

from cozer.app.timer import standings, ladder
from cozer.native import to_native
from cozer.store import apply_op


def _app():
    return QApplication.instance() or QApplication(["test"])


def _prestart_rec(ids, need=3):
    return [{"course": [1000] * need}, {pid: [] for pid in ids}]


def test_standings_prestart_uses_start_rank_not_boat_number():
    # before Start every boat is at 0 laps -> the order must follow the derived start order (grid),
    # not boat number. start_rank = {boat: grid position}.
    rec = _prestart_rec(["11", "22", "33"])
    assert [r["id"] for r in standings(rec)] == ["11", "22", "33"]      # no seed -> boat-number order
    seeded = [r["id"] for r in standings(rec, {"33": 0, "11": 1, "22": 2})]
    assert seeded == ["33", "11", "22"]                                 # grid order (heat 1 finish)


def test_standings_joiner_missing_from_seed_sorts_to_back():
    # a mid-series joiner with no prior ranking isn't in the seed -> it goes to the back (by number)
    rec = _prestart_rec(["11", "22", "99"])
    assert [r["id"] for r in standings(rec, {"22": 0, "11": 1})] == ["22", "11", "99"]


def test_standings_progress_beats_seed():
    # once boats are lapping, progress leads; the seed only breaks a same-progress tie
    rec = [{"course": [1000, 1000]}, {"11": [], "22": [[1, 20.0]]}]     # 22 has a lap, 11 none
    assert [r["id"] for r in standings(rec, {"11": 0, "22": 1})] == ["22", "11"]   # 22 leads on laps


def test_ladder_prestart_lists_boats_in_seed_order():
    rec = _prestart_rec(["11", "22", "33"])
    rows, need = ladder(rec, {"33": 0, "11": 1, "22": 2})
    assert rows[0] == ("marker", "Ready to Start")
    assert [r[1]["id"] for r in rows if r[0] == "boat"] == ["33", "11", "22"]


def _event(participants):
    return to_native({"title": "T", "scoringsystem": [10, 8, 6], "rules": [],
                      "participants": participants,
                      "classes": [["", "GT", "3*(3*1000):3"]], "record": {}, "races": []})


def _two_heat_event():
    # participant order 11,22,33; heat 1 finishing order 33,11,22 (33 fastest laps, then 11, then 22)
    ed = _event([["", "A", "1", "", "GT", "11"], ["", "B", "2", "", "GT", "22"],
                 ["", "C", "3", "", "GT", "33"]])
    apply_op(ed, {"op": "heat", "cl": "GT", "h": "1", "info": {"course": [1000, 1000, 1000]},
                  "ids": ["11", "22", "33"]})
    for pid, dt in [("33", 20.0), ("11", 21.0), ("22", 22.0)]:
        for _ in range(3):
            apply_op(ed, {"op": "lap", "cl": "GT", "h": "1", "id": pid, "mark": [1, dt]})
    return ed


def _ladder_boat_order(panel, cl, h):
    lv = panel._ladder_layouts[(cl, h)]
    return [lv.itemAt(i).widget().text() for i in range(lv.count())
            if isinstance(lv.itemAt(i).widget(), QPushButton)]


def test_timer_ladder_base_heat_uses_participant_order():
    # the wiring seam, base case: with no predecessor, heat 1's pre-Start ladder follows the
    # participant-list order (here 22,33,11) fed through start_order -- NOT boat-number order.
    _app()
    from cozer.app.main import MainWindow
    w = MainWindow(_event([["", "B", "2", "", "GT", "22"], ["", "C", "3", "", "GT", "33"],
                           ["", "A", "1", "", "GT", "11"]]))
    p = w.timer_panel
    p._heats = [("GT", "1")]
    p._build()
    assert _ladder_boat_order(p, "GT", "1") == ["22", "33", "11"]   # participant order, not [11,22,33]


def test_timer_ladder_seeds_heat2_from_heat1_finish():
    # the wiring seam: _build_ladder must feed start_order into ladder(), so heat 2's pre-Start ladder
    # lists boats in heat 1's finishing order (33,11,22) -- NOT boat-number order (issue #44).
    _app()
    from cozer.app.main import MainWindow
    w = MainWindow(_two_heat_event())
    p = w.timer_panel
    p._heats = [("GT", "2")]
    p._build()
    assert _ladder_boat_order(p, "GT", "2") == ["33", "11", "22"]   # heat 2 seeded by heat 1 finish


def test_broadcast_prestart_order_matches_the_ladder_grid_order():
    # The pre-start broadcast order now uses the derived start order (like the ladder), not boat number:
    # heat 2's field is published in heat 1's finishing order (33,11,22), not [11,22,33] (owner).
    _app()
    from cozer.app.main import MainWindow
    w = MainWindow(_two_heat_event())
    p = w.timer_panel
    assert p._broadcast_order("GT", "2") == ["33", "11", "22"]      # grid order, matching the ladder
    # heat 1's OWN pre-start order is the base case = participant order (11,22,33), not boat-sorted-by-value
    # (here identical, but the point is it comes from start_order); once heat 1 has crossings it returns
    # standings dicts, unchanged.
    st = p._broadcast_order("GT", "1")
    assert isinstance(st[0], dict) and st[0]["id"] == "33"          # racing -> standings dicts (33 leads)
