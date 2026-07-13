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
    _app()
    w = MainWindow()
    monkeypatch.setattr(appmain.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (EVENT, "")))
    w.on_import()
    assert w.eventdata["record"] and w.store is None
    w.on_open()                                            # .coz path -> import branch
    assert w.eventdata["record"]


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
        "record": {"GT": {"1": [
            {"course": [1000, 1000, 1000], "racetime": 100.0, "sheats": 1, "duration": None},
            {"1": [[1, 20.0], [1, 21.0], [1, 22.0]], "2": [[1, 25.0], [1, 26.0], [1, 27.0]]},
        ]}},
        "configure": {"language": "English"},
    }


def test_editor_reload_and_edits(tmp_path, monkeypatch):
    _app()
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    assert ep.heat_combo.count() == 1
    assert [ep.boat_combo.itemText(i) for i in range(ep.boat_combo.count())] == ["1", "2"]
    assert ep.marks.rowCount() == 3
    rec = w.eventdata["record"]["GT"]["1"]
    jpath = str(tmp_path / "e.cozj.journal")
    ep.insert_mark("GT", "1", "1", 12, 5.0, "foul")     # 12 = DQ
    assert any(m[0] == 12 for m in rec[1]["1"])
    ep.toggle_mark("GT", "1", "1", 0)
    assert rec[1]["1"][0][0] < 0                          # disabled
    n = len(rec[1]["1"])
    ep.delete_mark("GT", "1", "1", 0)
    assert len(rec[1]["1"]) == n - 1
    ep.set_racetime("GT", "1", 90.0)
    assert rec[0]["racetime"] == 90.0
    assert os.path.getsize(jpath) > 0                     # every edit journaled + fsync'd
    assert ep.results.toPlainText()                       # live results preview


def test_code_label():
    from cozer.app.editor import code_label
    assert code_label(1) == "lap" and code_label(-1) == "(off) lap"
    assert code_label(2) == "ins. lap"
    assert code_label(12) == "DQ" and code_label(-12) == "(off) DQ"


def test_insert_mark_dialog_values():
    _app()
    from cozer.app.editor import InsertMarkDialog
    from cozer.records import reccodemap
    dlg = InsertMarkDialog()
    dlg.code.setCurrentText("DQ")
    dlg.time.setValue(12.5)
    dlg.note.setText("x")
    code, ct, note = dlg.values()
    assert code == reccodemap["DQ"] and ct == 12.5 and note == "x"


def test_log_pane_records_messages():
    _app()
    w = MainWindow(_recorded_event())
    w.log("hello world")
    assert "hello world" in w.log_view.toPlainText()
