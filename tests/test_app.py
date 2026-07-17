"""Offscreen (headless) smoke tests for the PySide6 GUI."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from cozer.store import read_legacy_coz  # noqa: E402
from cozer.racepattern import get_classes  # noqa: E402
import cozer.app.main as appmain  # noqa: E402
from cozer.app.main import MainWindow  # noqa: E402

EVENT = os.path.join(REPO, "legacy", "events", "wc2000.coz")


def _app():
    return QApplication.instance() or QApplication(["test"])


def test_window_builds_and_populates():
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    assert w._fields["title"].text()                       # event form populated
    assert w.class_list.count() == len(get_classes(ed))    # class checklist populated
    assert w.report_combo.count() == 9                     # all reports offered


def test_event_field_edits_update_eventdata():
    _app()
    w = MainWindow()
    w._fields["venue"].setText("Lake Harku")
    assert w.eventdata["venue"] == "Lake Harku"


def test_new_and_save_and_reopen(tmp_path, monkeypatch):
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    out = str(tmp_path / "event.cozj")
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (out, "")))
    w.on_save_as()
    assert os.path.exists(out) and w.store is not None
    w.on_save()                                            # store exists -> snapshot
    # reopen the saved .cozj
    w2 = MainWindow()
    w2.load(out)
    assert w2.eventdata["title"] == ed["title"]
    # New resets
    w2.on_new()
    assert w2.eventdata["title"] == "" and w2.store is None


def test_generate_report_writes_and_opens(tmp_path, monkeypatch):
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    # check one class so selected_classes() is exercised
    w.class_list.item(0).setCheckState(Qt.Checked)
    assert w.selected_classes() == [w.class_list.item(0).text()]
    out = str(tmp_path / "full_final.pdf")
    opened = []
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (out, "")))
    monkeypatch.setattr(appmain, "open_in_viewer", opened.append)
    w.report_combo.setCurrentIndex(2)                      # Full Final
    w.on_generate()
    assert os.path.exists(out) and opened == [out]


def test_open_and_import_via_dialog(tmp_path, monkeypatch):
    import shutil
    _app()
    w = MainWindow()
    monkeypatch.setattr(appmain.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (EVENT, "")))
    w.on_import()
    assert w.eventdata["record"] and w.store is None       # import stages only, no store
    coz = str(tmp_path / "ev.coz")
    shutil.copy(EVENT, coz)
    monkeypatch.setattr(appmain.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (coz, "")))
    w.on_open()                                            # opening a .coz auto-persists
    assert w.eventdata["record"]
    assert w.store is not None and os.path.exists(str(tmp_path / "ev.cozj"))


def test_open_coz_edits_buffer_then_save_without_prompt(tmp_path, monkeypatch):
    import shutil
    _app()
    coz = str(tmp_path / "ev.coz")
    shutil.copy(EVENT, coz)
    w = MainWindow()
    # any Save-As prompt would be a bug now -> make it fail loudly
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (_ for _ in ()).throw(AssertionError("prompted"))))
    w.load(coz)
    assert w.store is not None and os.path.exists(str(tmp_path / "ev.cozj"))
    ep = w.editor_panel
    ep.reload()
    assert ep.heat_combo.count() > 0
    jpath = str(tmp_path / "ev.cozj.journal")
    before = os.path.getsize(jpath) if os.path.exists(jpath) else 0
    ep.commit_racetime(123.0)                              # buffered edit, no dialog
    assert ep._dirty is True
    assert (os.path.getsize(jpath) if os.path.exists(jpath) else 0) == before   # not yet journaled
    assert ep.save_draft() is True                         # snapshot clears the journal
    assert ep._dirty is False
    # reopening the .coz continues the working copy with the saved edit
    cl, h = ep._draft_key
    w2 = MainWindow()
    w2.load(coz)
    assert w2.store is not None
    assert w2.eventdata["record"][cl][h][0]["racetime"] == 123.0


def test_open_in_viewer_linux(monkeypatch):
    calls = []
    monkeypatch.setattr(appmain.sys, "platform", "linux")
    monkeypatch.setattr(appmain.subprocess, "Popen", lambda args: calls.append(args))
    appmain.open_in_viewer("/tmp/x.pdf")
    assert calls == [["xdg-open", "/tmp/x.pdf"]]


def test_generate_cancelled_dialog_is_noop(monkeypatch):
    _app()
    w = MainWindow(read_legacy_coz(EVENT))
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: ("", "")))
    w.on_generate()                                        # cancelled -> returns, no error


def test_data_grids_populate_and_edit():
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    cm = w.classes_grid.model
    assert cm.rowCount() == len(ed["classes"]) and cm.columnCount() == 2
    cm.setData(cm.index(0, 1), "9*(2*1000):3")     # col 1 = pattern -> row index 2
    assert ed["classes"][0][2] == "9*(2*1000):3"
    n = cm.rowCount()
    cm.add_row()
    assert cm.rowCount() == n + 1
    cm.delete_row(n)
    assert cm.rowCount() == n
    assert w.participants_grid.model.rowCount() == len(ed["participants"])
    assert w.rules_grid.model.rowCount() == len(ed["rules"])


def test_races_tab():
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    rt = w.races_tab
    assert rt.race_list.count() == len(ed["races"])
    before = len(ed["races"])
    rt._add_race()
    assert len(ed["races"]) == before + 1 and rt.race_list.count() == before + 1
    rt._delete_race()
    assert len(ed["races"]) == before


def test_race_label_unit():
    from cozer.app.grids import race_label
    assert race_label(0, [["", "", ""]]) == "Race 1"           # empty -> bare label
    assert race_label(0, []) == "Race 1"
    assert race_label(0, [["x", "GT", "1"]]) == "Race 1: GT 1"
    assert race_label(1, [["x", "GT", "1"], ["x", "OSY-400", "2"]]) == \
        "Race 2: GT 1, OSY-400 2"
    # blank / short rows are skipped
    assert race_label(2, [["x", "GT", "1"], ["x", "", ""], ["x"]]) == "Race 3: GT 1"


def test_races_tab_label_shows_class_heat_and_updates_live():
    _app()
    ed = {
        "title": "T", "venue": "V", "date": "D", "officer": "O", "secretary": "S",
        "scoringsystem": [10], "classes": [], "participants": [],
        "races": [[["x", "GT", "1"], ["x", "OSY-400", "2"]]],
        "rules": [], "record": {}, "configure": {},
    }
    w = MainWindow(ed)
    rt = w.races_tab
    assert rt.race_list.item(0).text() == "Race 1: GT 1, OSY-400 2"
    # editing a class cell in the grid updates the list label live
    rt.race_list.setCurrentRow(0)
    rt.grid.model.setData(rt.grid.model.index(0, 0), "S-250")
    assert rt.race_list.item(0).text() == "Race 1: S-250 1, OSY-400 2"


def test_timer_race_combo_label_has_class_heat():
    _app()
    w = MainWindow(_timer_event())
    tp = w.timer_panel
    tp.reload()
    assert tp.race_combo.itemText(0) == "Race 1: GT 1"


def test_scoring_field_parses():
    _app()
    w = MainWindow()
    w.scoring_edit.setText("400 300 225 0.5 x")
    assert w.eventdata["scoringsystem"] == [400, 300, 225, 0.5]


def test_parse_scoring_unit():
    from cozer.app.grids import parse_scoring
    assert parse_scoring("10 5 2.5 abc") == [10, 5, 2.5]
    assert parse_scoring("") == []


def _timer_event():
    return {
        "title": "T", "venue": "V", "date": "D", "officer": "O", "secretary": "S",
        "scoringsystem": [10, 5, 3],
        "classes": [["x", "GT", "1*(3*1000):1"]],
        "participants": [["x", "A", "One", "EST", "GT", "1"],
                         ["x", "B", "Two", "FIN", "GT", "2"]],
        "races": [[["x", "GT", "1"]]],
        "record": {}, "configure": {"language": "English"},
    }


def _save_as(w, path, monkeypatch):
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (path, "")))
    w.on_save_as()


def test_timer_records_laps_and_journals(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_timer_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    tp = w.timer_panel
    clock = [1000.0]
    tp._clock = lambda: clock[0]
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    assert tp._started and ("GT", "1", "1") in tp._buttons
    for t in (1020.0, 1041.0, 1063.0):
        clock[0] = t
        tp.record_lap("GT", "1", "1")
    marks = w.eventdata["record"]["GT"]["1"][1]["1"]
    assert [m[0] for m in marks] == [1, 1, 1]
    assert [m[1] for m in marks] == [20.0, 21.0, 22.0]
    assert os.path.getsize(str(tmp_path / "e.cozj.journal")) > 0     # journaled + fsync'd
    import copy
    from cozer.analyzer import analyze
    res = analyze("1", copy.deepcopy(w.eventdata["record"]["GT"]["1"]), [10, 5, 3])
    assert "1" in res and "2" in res


def test_standings_orders_by_progress():
    from cozer.app.timer import standings
    rec = [{"course": [1000, 1000, 1000]},
           {"1": [[1, 20.0], [1, 21.0]],                 # 2 laps, 41s
            "2": [[1, 19.0], [1, 20.0], [1, 22.0]],       # 3 laps -> finished, 61s
            "3": [[1, 25.0]]}]                             # 1 lap
    order = standings(rec)
    assert [s["id"] for s in order] == ["2", "1", "3"]    # finished, then 2 laps, then 1
    by = {s["id"]: s for s in order}
    assert by["2"]["finished"] and by["2"]["laps"] == 3 and not by["1"]["finished"]


def test_standings_same_laps_by_time():
    from cozer.app.timer import standings
    rec = [{"course": [1000, 1000]}, {"1": [[1, 30.0]], "2": [[1, 25.0]]}]
    assert [s["id"] for s in standings(rec)] == ["2", "1"]     # equal laps -> faster leads


def test_calclayout_keeps_all_ids():
    from cozer.app.timer import calclayout
    rows = calclayout(["1", "2", "3", "11", "12", "23"])
    flat = [x for row in rows for x in row]
    assert sorted(flat) == sorted(["1", "2", "3", "11", "12", "23"]) and all(rows)


def test_ladder_marker_zones():
    from cozer.app.timer import ladder
    rec = [{"course": [1000, 1000, 1000]},                 # 3-lap course
           {"1": [[1, 20.0]],                               # 1 lap
            "2": [[1, 19.0], [1, 20.0], [1, 22.0]],          # finished
            "3": []}]                                        # 0 laps
    rows, need = ladder(rec)
    assert need == 3
    seq = [(r[0], r[1] if r[0] == "marker" else r[1]["id"]) for r in rows]
    # Ready -> [boat 3 (0 laps)] -> Lap 1 -> [boat 1 (1 lap)] -> Lap 2 -> Lap 3 (no 2-lap) ->
    #   finished boat 2 -> Finish
    assert seq[0] == ("marker", "Ready to Start")
    assert ("boat", "3") in seq[:3] and seq[-1] == ("marker", "Finish")
    order = [x for kind, x in seq if kind == "boat"]
    assert order.index("3") < order.index("1") < order.index("2")   # progress -> down


def test_timer_running_order_and_both_views_record(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_timer_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    tp = w.timer_panel
    clock = [1000.0]
    tp._clock = lambda: clock[0]
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    # a boat button exists in BOTH the grid and the ladder
    assert ("GT", "1", "1") in tp._buttons and ("GT", "1", "1") in tp._ladder_boats
    clock[0] = 1020.0
    tp._ladder_boats[("GT", "1", "1")].click()        # clicking the LADDER records a lap
    assert len(w.eventdata["record"]["GT"]["1"][1]["1"]) == 1
    clock[0] = 1041.0
    tp._buttons[("GT", "1", "2")].click()             # clicking the GRID records a lap
    assert len(w.eventdata["record"]["GT"]["1"][1]["2"]) == 1


def test_grid_buttons_autofit():
    _app()
    from cozer.app.timer import GridButtons

    class _P:
        def __init__(self):
            self._buttons = {}

        def record_lap(self, *a):
            pass

        def _boat_color(self, *a):
            return "#ffffff"

    g = GridButtons(_P(), "GT", "1", [str(i) for i in range(1, 13)])   # 12 boats
    g.resize(300, 200)
    g.relayout()                                         # what resizeEvent calls
    small = g.sz
    for b, r, c in g.own.values():                       # every button fits inside the area
        assert b.geometry().right() <= 300 and b.geometry().bottom() <= 200
    g.resize(600, 400)
    g.relayout()
    assert g.sz > small                                  # bigger window -> bigger square buttons


def test_timer_resume_continues_without_reset(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_timer_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    tp = w.timer_panel
    tp._clock = lambda: 100.0
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    tp.record_lap("GT", "1", "1")
    tp.on_stop()
    assert not tp._started
    tp.on_resume()
    assert tp._started                        # a start time exists -> resumes
    assert len(w.eventdata["record"]["GT"]["1"][1]["1"]) == 1   # prior data kept


def test_timer_reopen_reconstructs_order():
    _app()
    w = MainWindow(_recorded_event())          # GT/1 already has recorded laps
    tp = w.timer_panel
    tp.race_combo.setCurrentIndex(0)
    # the ladder is reconstructed from the record (both boats present), not recording
    assert ("GT", "1", "1") in tp._ladder_boats and ("GT", "1", "2") in tp._ladder_boats
    assert not tp._started


def test_timer_shows_buttons_on_race_select():
    _app()
    w = MainWindow(_timer_event())
    tp = w.timer_panel
    tp.race_combo.setCurrentIndex(0)
    # boat-number grid appears BEFORE Start, built from the class participant ids
    assert ("GT", "1", "1") in tp._buttons and ("GT", "1", "2") in tp._buttons
    assert not tp._started
    assert tp._buttons[("GT", "1", "1")].text().startswith("1")   # shows the boat number


def test_timer_record_before_start_is_noop():
    _app()
    w = MainWindow(_timer_event())
    w.timer_panel.record_lap("GT", "1", "1")     # not started -> no-op, no crash


def test_timer_reload_stop_autosave(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_timer_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    tp = w.timer_panel
    assert tp.race_combo.count() == 1
    tp._clock = lambda: 100.0
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    assert tp._started
    tp.on_stop()
    assert not tp._started
    tp.autosave_cb.setChecked(True)
    tp.autosave_cb.setChecked(False)             # exercise autosave toggle both ways


def _recorded_event():
    return {
        "title": "T", "venue": "V", "date": "D", "officer": "O", "secretary": "S",
        "scoringsystem": [10, 5, 3],
        "classes": [["x", "GT", "1*(3*1000):1"]],
        "participants": [["x", "A", "One", "EST", "GT", "1"],
                         ["x", "B", "Two", "FIN", "GT", "2"]],
        "races": [[["x", "GT", "1"]]],
        "rules": [["", "DQ", "313.4", "Disqualification"]],
        "record": {"GT": {"1": [
            {"course": [1000, 1000, 1000], "racetime": 100.0, "sheats": 1, "duration": None},
            {"1": [[1, 20.0], [1, 21.0], [1, 22.0]], "2": [[1, 25.0], [1, 26.0], [1, 27.0]]},
        ]}},
        "configure": {"language": "English"},
    }


def test_mark_positions():
    # laps at cumulative time, event marks at their absolute time
    from cozer.app.editor import mark_positions
    pos = mark_positions([[1, 20.0], [12, 5.0, "x"], [1, 21.0], [-1, 3.0]])
    assert [p[0] for p in pos] == ["lap", "event", "lap", "displap"]
    assert [round(p[1], 1) for p in pos] == [20.0, 5.0, 41.0, 44.0]
    # a disabled lap's time carries into the next lap's displayed time (dtime)
    assert pos[0][3] == "20.0"
    assert mark_positions([[1]])[0][1] == 0        # bare code, no time -> t=0


def test_insert_lap_split_unit():
    from cozer.app.editor import insert_lap_split
    marks = [[1, 20.0], [1, 20.0]]            # cumulative 20, 40
    insert_lap_split(marks, 30.0)
    assert marks == [[1, 20.0], [2, 10.0], [1, 10.0]]
    marks = [[1, 20.0]]                        # beyond the last lap -> append
    insert_lap_split(marks, 50.0)
    assert marks[-1] == [2, 30.0]


def test_toggle_and_delete_nearest_unit():
    from cozer.app.editor import delete_nearest, toggle_nearest
    coef = 10.0                                # px/s; tol 5px -> within 0.5s
    marks = [[1, 20.0], [12, 5.0, "x"], [1, 21.0]]
    assert toggle_nearest(marks, 20.0, coef) and marks[0][0] == -1        # lap by cumulative time
    assert toggle_nearest(marks, 5.0, coef) and marks[1][0] == -12        # event by absolute time
    assert delete_nearest(marks, 5.0, coef) is None
    assert not any(abs(m[0]) == 12 for m in marks)
    assert toggle_nearest([[1, 20.0]], 999.0, coef) is False              # nothing near -> no-op
    msg = delete_nearest([[1, 20.0]], 20.0, coef)                         # timed laps protected
    assert msg and "lap" in msg.lower()
    # deleting an inserted lap (code 2) merges its time into the following lap
    ins = [[1, 20.0], [2, 10.0], [1, 11.0]]                               # cumulative 20, 30, 41
    assert delete_nearest(ins, 30.0, coef) is None
    assert [m[0] for m in ins] == [1, 1] and ins[1][1] == 21.0


def test_editor_panel_buffers_edits_until_save(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    assert ep.heat_combo.count() == 1
    assert ep.timeline._rows and ep.timeline._rows[0][1]        # result shown in the row header
    rec = w.eventdata["record"]["GT"]["1"]                     # the stored (committed) record
    jpath = str(tmp_path / "e.cozj.journal")
    before = os.path.getsize(jpath) if os.path.exists(jpath) else 0

    ep.insert_rule_mark("GT", "1", "1", 12, 5.0, "foul")        # 12 = DQ, at t=5
    ep.insert_lap("GT", "1", "1", 30.0)                         # split a lap
    ep.toggle_at("GT", "1", "1", 20.0)                          # disable the lap at cumulative 20
    ep.delete_at("GT", "1", "1", 5.0)                           # delete the DQ event mark
    ep.commit_racetime(88.0)

    # edits are buffered in the draft, NOT written to the store yet
    assert ep._dirty is True
    d = ep._draft
    assert any(m[0] == 2 for m in d[1]["1"])                    # inserted lap split
    assert any(m[0] == -1 for m in d[1]["1"])                   # disabled lap
    assert not any(abs(m[0]) == 12 for m in d[1]["1"])          # DQ inserted then deleted
    assert d[0]["racetime"] == 88.0
    assert rec[0]["racetime"] == 100.0                          # store untouched
    assert not any(m[0] == 2 for m in rec[1]["1"])
    assert (os.path.getsize(jpath) if os.path.exists(jpath) else 0) == before

    assert ep.save_draft() is True                             # persist + snapshot
    assert ep._dirty is False
    assert rec[0]["racetime"] == 88.0                          # now committed
    assert any(m[0] == 2 for m in rec[1]["1"])
    import json as _json
    saved = _json.load(open(str(tmp_path / "e.cozj")))
    assert saved["record"]["GT"]["1"][0]["racetime"] == 88.0    # durably snapshotted


def test_timeline_widget_coords():
    _app()
    from cozer.app.editor import PAD, ROW_H, TOP
    w = MainWindow(_recorded_event())
    tl = w.editor_panel.timeline
    tl.set_data([("1", "hdr", [[1, 20.0]])], 100.0, 50.0, 8.0)
    assert tl.x_of(0) == PAD
    assert abs(tl.x_of(10) - (PAD + 80)) < 1e-6
    assert abs(tl.t_of(tl.x_of(10)) - 10.0) < 1e-6
    assert tl.row_at(5) == -1                                   # above the first row
    assert tl.row_at(TOP + 5) == 0
    assert tl.row_at(TOP + ROW_H * 5) == -1


def test_frozen_header_tracks_timeline_scroll():
    _app()
    w = MainWindow(_recorded_event())
    ep = w.editor_panel
    ep.reload()
    assert len(ep.header_col._rows) == len(ep.timeline._rows)   # same rows both panes
    ep._sync_header_scroll(37)                                   # exact offset, no skew
    assert ep.header_col.pos().y() == -37
    ep._sync_header_scroll(0)
    assert ep.header_col.pos().y() == 0


def test_editor_zoom_changes_scale():
    _app()
    w = MainWindow(_recorded_event())
    ep = w.editor_panel
    ep.reload()
    c0 = ep._coef
    ep._zoomed(1)
    assert ep._coef > c0                                        # zooming in widens the axis
    ep._zoomed(-1)
    assert abs(ep._coef - c0) < 1e-9


def test_timeline_paints_all_mark_kinds():
    _app()
    from PySide6.QtGui import QPixmap
    from cozer.app.editor import TimelineWidget
    tl = TimelineWidget(panel=None)
    marks = [[1, 20.0], [2, 10.0], [-1, 5.0], [12, 8.0, "foul"], [-12, 9.0, "x"], [99, 7.0]]
    tl.set_data([("1", "1.  pts 10", marks)], 100.0, 50.0, 8.0)
    tl.resize(tl.minimumWidth(), tl.minimumHeight())
    pm = QPixmap(tl.size())
    tl.render(pm)                                              # exercises paintEvent headless
    assert not pm.isNull()


def test_result_str_unit():
    from cozer.app.editor import result_str
    dq = {"place": 0, "points": 0, "avgspeed": 0.0, "maxlapspeed": 0.0,
          "lapinfo": (0, 0, 0), "notes": {"DQ": 1}}
    assert "–" in result_str(dq) and "DQ" in result_str(dq)
    ok = {"place": 1, "points": 10, "avgspeed": 50.0, "maxlapspeed": 60.0,
          "lapinfo": (3, 1, 2), "notes": {}}
    s = result_str(ok)
    assert s.startswith("1st/10")
    assert "A/M=50.0/60.0 km/h" in s
    assert "Laps/Pen/Left=3/1/2" in s


def test_result_header_wraps_to_two_lines():
    from cozer.app.editor import result_header
    ok = {"place": 1, "points": 10, "avgspeed": 50.0, "maxlapspeed": 60.0,
          "lapinfo": (3, 1, 2), "notes": {"IR": 1}}
    top, bottom = result_header(ok).split("\n")
    assert top == "1st/10  A/M=50.0/60.0 km/h"
    assert bottom == "Laps/Pen/Left=3/1/2 IR"


def test_editor_empty_state():
    _app()
    w = MainWindow()                                            # no record
    assert w.editor_panel.timeline._rows == []


def test_build_mark_menu_and_actions(tmp_path, monkeypatch):
    _app()
    from cozer.records import reccodemap
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    menu = ep.build_mark_menu("1", 10.0)
    assert any("Insert lap" in a.text() for a in menu.actions())
    assert any(a.menu() for a in menu.actions())                # rules submenu present
    d = ep._draft                                               # edits land in the draft buffer
    for a in menu.actions():
        if "Insert lap" in a.text():
            a.trigger()
            break
    assert any(m[0] == 2 for m in d[1]["1"])
    for a in menu.actions():                                    # trigger a rule (DQ) from a submenu
        if a.menu():
            a.menu().actions()[0].trigger()
            break
    assert any(m[0] == reccodemap["DQ"] for m in d[1]["1"])
    assert ep._dirty is True


def test_timeline_mouse_drag_and_rightclick(tmp_path, monkeypatch):
    _app()
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from cozer.app.editor import TOP
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    tl = ep.timeline

    def press(x, y, button):
        return QMouseEvent(QEvent.MouseButtonPress, QPointF(x, y), QPointF(x, y),
                           button, button, Qt.NoModifier)

    rx = tl.x_of(tl._racetime)
    tl.mousePressEvent(press(rx, 5, Qt.LeftButton))
    assert tl._drag
    newx = tl.x_of(30.0)
    tl.mouseMoveEvent(QMouseEvent(QEvent.MouseMove, QPointF(newx, 5), QPointF(newx, 5),
                                  Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    tl.mouseReleaseEvent(QMouseEvent(QEvent.MouseButtonRelease, QPointF(newx, 5), QPointF(newx, 5),
                                     Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert not tl._drag
    assert abs(ep._draft[0]["racetime"] - 30.0) < 0.5          # buffered until Save
    assert ep._dirty is True

    calls = []
    ep.open_mark_menu = lambda pid, ct, pos: calls.append((pid, round(ct)))
    tl.mousePressEvent(press(tl.x_of(10.0), TOP + 5, Qt.RightButton))
    assert calls and calls[0][0] == "1" and abs(calls[0][1] - 10) < 1


def test_edit_records_flush_discard_reverts(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    orig = w.eventdata["record"]["GT"]["1"][0]["racetime"]
    ep.commit_racetime(555.0)
    assert ep._dirty is True
    ep._ask_unsaved = lambda: "discard"                        # user chooses Discard
    assert ep.maybe_flush() is True
    assert ep._dirty is False
    ep.refresh()                                               # reloads a fresh draft
    assert ep._draft[0]["racetime"] == orig                    # edit reverted
    assert w.eventdata["record"]["GT"]["1"][0]["racetime"] == orig


def test_edit_records_flush_cancel_keeps_draft(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    ep.commit_racetime(555.0)
    ep._ask_unsaved = lambda: "cancel"                         # user chooses Cancel
    assert ep.maybe_flush() is False
    assert ep._dirty is True and ep._draft[0]["racetime"] == 555.0


def test_edit_records_flush_save_persists(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    ep.commit_racetime(777.0)
    ep._ask_unsaved = lambda: "save"                           # user chooses Save
    assert ep.maybe_flush() is True
    assert ep._dirty is False
    assert w.eventdata["record"]["GT"]["1"][0]["racetime"] == 777.0


def test_tab_switch_bounces_back_on_cancel(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    editor_idx = w.tabs.indexOf(ep)
    w.tabs.setCurrentIndex(editor_idx)
    w._prev_tab = editor_idx
    ep.commit_racetime(999.0)
    ep._ask_unsaved = lambda: "cancel"
    other = (editor_idx + 1) % w.tabs.count()
    w.tabs.setCurrentIndex(other)                              # try to leave with unsaved edits
    assert w.tabs.currentIndex() == editor_idx                 # bounced back, edits intact
    assert ep._dirty is True and ep._draft[0]["racetime"] == 999.0


def test_report_exception_captures_and_queues(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    import cozer.app.crashreport as cr
    w = MainWindow(_timer_event())
    try:
        raise RuntimeError("boom in a slot")
    except RuntimeError:
        et, ev, tb = sys.exc_info()
        report, url = appmain.report_exception(w, et, ev, tb)
    assert report["exc_type"] == "RuntimeError" and report["action"]     # tab name as context
    assert url is None                                    # not logged in -> queued for later
    assert len(cr.list_pending()) == 1


def test_report_exception_ignores_keyboardinterrupt(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    import cozer.app.crashreport as cr
    w = MainWindow(_timer_event())
    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        et, ev, tb = sys.exc_info()
        report, url = appmain.report_exception(w, et, ev, tb)
    assert report is None and url is None       # Ctrl+C / quit is not a crash
    assert cr.list_pending() == []


def test_help_menu_reflects_signin_state(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    import cozer.app.crashreport as cr
    w = MainWindow(_timer_event())
    w._refresh_help_menu()
    texts = [a.text() for a in w._help_menu.actions()]
    assert any("Sign in to GitHub" in t for t in texts)      # signed out -> offer sign-in
    cr.save_config({"token": "gho_x", "login": "pearu"})
    w._refresh_help_menu()
    texts = [a.text() for a in w._help_menu.actions()]
    assert any("Signed in to GitHub as pearu" in t for t in texts)
    assert any("out of GitHub" in t for t in texts)         # "Sign &out of GitHub" (mnemonic &)
    w._on_signout()
    assert cr.load_config().get("token") is None            # sign-out clears the token


def test_report_bug_queues_when_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    import cozer.app.crashreport as cr
    w = MainWindow(_timer_event())
    url = appmain.report_bug(w, "the timer button did nothing")
    assert url is None and len(cr.list_pending()) == 1     # queued until signed in


def test_startup_file_selects_event_arg():
    from cozer.app.main import _startup_file
    assert _startup_file([]) is None
    assert _startup_file(["--debug"]) is None
    assert _startup_file(["notes.txt"]) is None
    assert _startup_file(["event.coz"]) == "event.coz"
    assert _startup_file(["-x", "a.cozj", "b.coz"]) == "a.cozj"   # first event arg wins


def test_startup_file_loads_into_window(tmp_path, monkeypatch):
    import shutil
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    _app()
    coz = str(tmp_path / "ev.coz")
    shutil.copy(EVENT, coz)
    w = MainWindow()
    path = appmain._startup_file([coz])                          # what run() resolves
    assert path == coz
    w.load(path)
    assert w._fields["title"].text() and w.store is not None     # opened + auto-persisted


def test_log_pane_records_messages():
    _app()
    w = MainWindow(_recorded_event())
    w.log("hello world")
    assert "hello world" in w.log_view.toPlainText()
