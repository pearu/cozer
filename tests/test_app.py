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
from cozer.raceclock import RaceClock  # noqa: E402
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
    assert w.report_tree.topLevelItemCount() == len(get_classes(ed))  # class/heat tree populated
    assert w.report_combo.count() == 11                    # all reports offered (incl. 2 legacy Final)


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


def test_export_report_writes_and_opens(tmp_path, monkeypatch):
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    # check one class so _report_selection() is exercised (whole class -> all heats)
    c0 = w.report_tree.topLevelItem(0)
    c0.setCheckState(0, Qt.Checked)
    classes, _heat_map = w._report_selection()
    assert classes == [c0.text(0)]
    out = str(tmp_path / "full_final.pdf")
    opened = []
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (out, "")))
    monkeypatch.setattr(appmain, "open_in_viewer", opened.append)
    monkeypatch.setattr(appmain.QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    w.report_combo.setCurrentIndex(2)                      # Full Final
    w.on_export()
    assert os.path.exists(out) and opened == [out]


def test_view_report_uses_event_reports_dir(tmp_path, monkeypatch):
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "ev.cozj"), "")))
    w.on_save_as()                                         # establish the event path
    opened = []
    monkeypatch.setattr(appmain, "open_in_viewer", opened.append)
    monkeypatch.setattr(appmain.QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    w.report_combo.setCurrentIndex(2)                      # Full Final
    w.on_view()                                            # no Save dialog
    rdir = tmp_path / "ev.reports"
    latest = rdir / "full_final.pdf"
    assert latest.exists() and opened == [str(latest)]     # written to <event>.reports/, opened
    assert len(list((rdir / "postings").glob("full_final_*.pdf"))) == 1  # archived posting


# The three tests below exercise the *surfacing* (indicator + dialog), so they
# monkeypatch validate.check_results with fixed findings and stay independent of
# what the validate layer actually flags (that is covered by test_validate.py).
def test_validation_indicator_reflects_findings(monkeypatch):
    _app()
    from cozer.validate import Finding
    fakes = [Finding("warning", "T-400", "2", "place-gap", "placings are not contiguous"),
             Finding("warning", "O-500", "3", "incomplete-heat", "stopped early")]
    monkeypatch.setattr(appmain.validate, "check_results", lambda ed: fakes)
    w = MainWindow(read_legacy_coz(EVENT))
    assert len(w._findings) == 2
    assert not w._warn_btn.isHidden() and "2 data warning" in w._warn_btn.text()
    shown = {}
    monkeypatch.setattr(appmain.QMessageBox, "warning",
                        staticmethod(lambda parent, title, text, *a, **k:
                                     shown.update(title=title, text=text)))
    w._show_warnings()                                     # clicking the indicator lists them
    assert "2" in shown["title"] and "T-400" in shown["text"] and "O-500" in shown["text"]


def test_validation_indicator_hidden_when_clean(monkeypatch):
    _app()
    monkeypatch.setattr(appmain.validate, "check_results", lambda ed: [])
    w = MainWindow(read_legacy_coz(EVENT))
    assert w._findings == [] and w._warn_btn.isHidden()


def test_report_generation_warns_on_findings(tmp_path, monkeypatch):
    _app()
    from cozer.validate import Finding
    monkeypatch.setattr(appmain.validate, "check_results",
                        lambda ed: [Finding("warning", "T-400", "2", "place-gap", "x")])
    w = MainWindow(read_legacy_coz(EVENT))
    warned = []
    monkeypatch.setattr(appmain.QMessageBox, "warning",
                        staticmethod(lambda parent, title, *a, **k: warned.append(title)))
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "r.pdf"), "")))
    monkeypatch.setattr(appmain, "open_in_viewer", lambda *a, **k: None)
    w.report_combo.setCurrentIndex(2)                     # Full Final
    w.on_export()
    assert any("Data warnings" in t for t in warned)      # loud warning before generating
    assert (tmp_path / "r.pdf").exists()                  # ...and it still generated


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
    monkeypatch.setattr(appmain.subprocess, "Popen", lambda args, env=None: calls.append(args))
    appmain.open_in_viewer("/tmp/x.pdf")
    assert calls == [["xdg-open", "/tmp/x.pdf"]]


def test_export_cancelled_dialog_is_noop(monkeypatch):
    _app()
    w = MainWindow(read_legacy_coz(EVENT))
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: ("", "")))
    w.on_export()                                          # cancelled -> returns, no error


def test_system_child_env_drops_conda_fontconfig(monkeypatch):
    # cozer exports FONTCONFIG_FILE (a private conf) + a conda LD_LIBRARY_PATH; a
    # system viewer must inherit NEITHER, else it parses cozer's env confs with the
    # system libfontconfig (xsi:nil warnings) or loads incompatible conda libs.
    # Paths built with os.sep/os.pathsep so the assertion holds on POSIX and Windows.
    prefix = os.sep + os.path.join("opt", "conda", "envs", "cozer")
    conda_lib = os.path.join(prefix, "lib")
    other = os.sep + os.path.join("usr", "local", "lib")
    monkeypatch.setattr(appmain.sys, "prefix", prefix)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("FONTCONFIG_FILE", os.path.join(prefix, "etc", "cozer-fonts.conf"))
    monkeypatch.setenv("FONTCONFIG_PATH", os.path.join(prefix, "etc", "fonts"))
    monkeypatch.setenv("LD_LIBRARY_PATH", os.pathsep.join([conda_lib, other]))
    env = appmain._system_child_env()
    assert "FONTCONFIG_FILE" not in env and "FONTCONFIG_PATH" not in env
    assert env["LD_LIBRARY_PATH"] == other                # conda entry stripped, rest kept


def test_open_in_viewer_uses_clean_env(monkeypatch):
    monkeypatch.setattr(appmain.sys, "platform", "linux")  # force the xdg-open branch
    monkeypatch.setattr(appmain.sys, "prefix", "/opt/conda/envs/cozer")
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("FONTCONFIG_FILE", "/opt/conda/envs/cozer/etc/cozer-fonts.conf")
    captured = {}

    def fake_popen(argv, env=None, **kw):
        captured["argv"], captured["env"] = argv, env
        return object()
    monkeypatch.setattr(appmain.subprocess, "Popen", fake_popen)
    appmain.open_in_viewer("/tmp/x.pdf")
    assert captured["argv"][0] == "xdg-open"             # system opener spawned
    assert "FONTCONFIG_FILE" not in captured["env"]       # child env sanitized


def test_classes_participants_panel_populates():
    _app()
    ed = read_legacy_coz(EVENT)
    w = MainWindow(ed)
    cp = w.classpart_panel
    named = [c[1] for c in ed["classes"] if len(c) > 1 and c[1]]
    assert cp.tabs.count() == len(named)                       # one subtab per class
    assert {cp._tab_class(i) for i in range(cp.tabs.count())} == set(named)
    assert w.rules_grid.model.rowCount() == len(ed["rules"])


def test_participant_class_model_filter_add_delete_unique():
    _app()
    from cozer.app.classpart import ParticipantClassModel
    parts = [["", "A", "One", "EST", "GT", "1"],
             ["", "B", "Two", "FIN", "GT", "2"],
             ["", "C", "Cee", "LAT", "OT", "1"]]
    m = ParticipantClassModel(parts, "GT")
    assert m.rowCount() == 2 and m.columnCount() == 4          # filtered to class GT
    assert m.data(m.index(0, 0)) == "1" and m.data(m.index(1, 1)) == "B"
    warned = []
    m2 = ParticipantClassModel(parts, "GT", warn=warned.append)
    assert m2.setData(m2.index(0, 0), "2") is False and warned  # boat # taken -> rejected
    assert m2.setData(m2.index(0, 0), "9") is True and parts[0][5] == "9"
    before = len(parts)
    m2.add_row()
    assert m2.rowCount() == 3 and len(parts) == before + 1 and parts[-1][4] == "GT"
    m2.delete_row(2)
    assert len(parts) == before


def test_from_autocomplete_suggestions_and_delegate():
    _app()
    from cozer.app.classpart import (ClassParticipantsWidget, AutoCompleteDelegate,
                                      ParticipantClassModel)
    parts = [["", "A", "One", "EST", "GT", "1"],
             ["", "B", "Two", "FIN", "GT", "2"],
             ["", "C", "Cee", "EST", "OT", "1"],      # EST recurs (other class)
             ["", "D", "Dee", "", "GT", "3"]]         # blank From ignored
    cw = ClassParticipantsWidget(parts, "GT")
    assert cw._from_suggestions() == ["EST", "FIN"]   # distinct, non-empty, all classes
    from_col = next(i for i, (f, _) in enumerate(ParticipantClassModel.COLS) if f == 3)
    deleg = cw.view.itemDelegateForColumn(from_col)
    assert isinstance(deleg, AutoCompleteDelegate)
    editor = deleg.createEditor(cw.view.viewport(), None, cw.model.index(0, from_col))
    comp = editor.completer()
    vals = [comp.model().data(comp.model().index(i, 0)) for i in range(comp.model().rowCount())]
    assert "EST" in vals and "FIN" in vals


def test_pattern_dialog_fields_and_raw():
    _app()
    from cozer.app.classpart import PatternDialog
    dlg = PatternDialog(None, "O-500", "4*(1430+7*1390):3")
    assert (dlg.first.value(), dlg.other.value(), dlg.laps.value(),
            dlg.heats.value(), dlg.scored.value()) == (1430, 1390, 8, 4, 3)
    assert dlg.raw.text() == "4*(1430+7*1390):3"
    dlg.heats.setValue(3)                                       # a field edit rebuilds raw
    assert dlg.raw.text() == "3*(1430+7*1390):3"
    dlg._accept()
    assert dlg.pattern() == "3*(1430+7*1390):3"
    assert PatternDialog(None, "END", "5000/6").raw.text() == "5000/6"   # endurance via raw


def test_pattern_dialog_validation(monkeypatch):
    _app()
    import cozer.app.classpart as classpart
    from cozer.app.classpart import PatternDialog
    dlg = PatternDialog(None, "O-500", "4*(1430+7*1390):3")
    dlg.heats.setValue(2)
    assert dlg.scored.maximum() == 2                            # scored can't exceed heats
    msgs = []
    monkeypatch.setattr(classpart, "QMessageBox",
                        type("M", (), {"information": staticmethod(lambda *a, **k: msgs.append(a))}))
    accepted = []
    dlg.accept = lambda: accepted.append(True)
    dlg.raw.setText("abc")                                      # unparseable
    dlg._accept()
    assert not accepted and msgs                                # rejected with a message
    dlg.raw.setText("3*(1000):1")                              # valid
    dlg._accept()
    assert accepted and dlg.pattern() == "3*(1000):1"


def test_class_subtab_shows_participant_count():
    _app()
    from cozer.app.classpart import ClassParticipantsWidget
    w = MainWindow(_recorded_event())                          # class GT has 2 participants
    cp = w.classpart_panel
    i = next(i for i in range(cp.tabs.count()) if cp._tab_class(i) == "GT")
    assert cp.tabs.tabText(i) == "GT (2)"
    cw = cp.tabs.widget(i).findChild(ClassParticipantsWidget)
    cw.model.add_row()
    assert cp.tabs.tabText(i) == "GT (3)"                       # count updates live
    cw.model.delete_row(0)
    assert cp.tabs.tabText(i) == "GT (2)"


def test_add_class_dialog_is_catalog_only():
    _app()
    from cozer.app.classpart import AddClassDialog
    dlg = AddClassDialog(None, ["O-500", "O-125"])
    assert dlg.name.isEditable() is False                       # no free text
    assert [dlg.name.itemText(i) for i in range(dlg.name.count())] == ["O-500", "O-125"]


def test_add_class_strict_refuses_when_catalog_exhausted(monkeypatch):
    _app()
    import cozer.app.classpart as classpart
    w = MainWindow(_recorded_event())          # class GT; catalog seeded to {GT}
    cp = w.classpart_panel
    opened = {"dlg": False}

    class Boom:
        def __init__(self, *a, **k):
            opened["dlg"] = True

    monkeypatch.setattr(classpart, "AddClassDialog", Boom)
    monkeypatch.setattr(classpart, "QMessageBox",
                        type("M", (), {"information": staticmethod(lambda *a, **k: None)}))
    cp._add_class()                            # GT already a class -> nothing to add
    assert opened["dlg"] is False and len(w.eventdata["classes"]) == 1


def test_classpart_add_and_delete_class(monkeypatch):
    _app()
    import cozer.app.classpart as classpart
    w = MainWindow(_recorded_event())                          # class GT with participants
    w.eventdata["classnames"] = ["GT", "OSY-400"]             # catalog offers OSY-400
    cp = w.classpart_panel
    assert {cp._tab_class(i) for i in range(cp.tabs.count())} == {"GT"}

    class FakeDlg:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return True

        def class_name(self):
            return "OSY-400"

    monkeypatch.setattr(classpart, "AddClassDialog", FakeDlg)
    cp._add_class()
    assert any(c[1] == "OSY-400" for c in w.eventdata["classes"])
    assert "OSY-400" in {cp._tab_class(i) for i in range(cp.tabs.count())}

    monkeypatch.setattr(classpart, "QMessageBox",
                        type("M", (), {"information": staticmethod(lambda *a, **k: None)}))
    gt = next(i for i in range(cp.tabs.count()) if cp._tab_class(i) == "GT")
    cp.tabs.setCurrentIndex(gt)
    cp._delete_class()
    assert any(c[1] == "GT" for c in w.eventdata["classes"])    # refused: has participants
    # OSY-400 has no participants, but put it in a race -> still refused
    w.eventdata["races"] = [[["", "OSY-400", "1"]]]
    osy = next(i for i in range(cp.tabs.count()) if cp._tab_class(i) == "OSY-400")
    cp.tabs.setCurrentIndex(osy)
    assert cp._class_in_use("OSY-400") == "a race uses it"
    cp._delete_class()
    assert any(c[1] == "OSY-400" for c in w.eventdata["classes"])   # refused: race uses it
    w.eventdata["races"] = []                                    # free it -> deletable
    cp._delete_class()
    assert not any(c[1] == "OSY-400" for c in w.eventdata["classes"])


def test_delete_classname_blocked_when_instantiated(monkeypatch):
    _app()
    w = MainWindow(_recorded_event())          # class GT is set up (in eventdata['classes'])
    assert w._classname_in_use("GT")           # blocked: instantiated as an event class
    # remove the GT event class and its participants -> name becomes deletable
    w.eventdata["classes"] = []
    w.eventdata["participants"] = []
    w.eventdata["races"] = []
    assert w._classname_in_use("GT") is None


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
        "scoringsystem": [10],
        "classes": [["", "GT", ""], ["", "OSY-400", ""], ["", "S-250", ""]],  # defined
        "participants": [],
        "races": [[["x", "GT", "1"], ["x", "OSY-400", "2"]]],
        "rules": [], "record": {}, "configure": {},
    }
    w = MainWindow(ed)
    rt = w.races_tab
    assert rt.race_list.item(0).text() == "Race 1: GT 1, OSY-400 2"
    # editing a class cell to another defined class updates the list label live
    rt.race_list.setCurrentRow(0)
    rt.grid.model.setData(rt.grid.model.index(0, 0), "S-250")
    assert rt.race_list.item(0).text() == "Race 1: S-250 1, OSY-400 2"


def test_validate_rule_cell_pure():
    from cozer.app.grids import validate_rule_cell
    rows = [["", "DQ", "314", "Foul"], ["", "DQ", "999", "Other"]]
    msg, blocking = validate_rule_cell(1, 2, "314", rows)       # paragraph -> duplicates DQ/314
    assert "already defined" in msg and blocking is False       # advisory
    assert validate_rule_cell(1, 2, "888", rows) is None        # unique
    assert validate_rule_cell(1, 1, "", rows) is None           # empty action is allowed


def test_race_cell_validator_pure():
    from cozer.app.grids import race_cell_validator
    v = race_cell_validator(lambda: ["O-500", "S-250"], lambda cl: ["2", "1r", "1R"])
    rows = [["", "O-500", "1"], ["", "", ""]]
    msg, blocking = v(1, 1, "XYZ", rows)
    assert "not a defined class" in msg and blocking is True    # undefined class -> hard reject
    assert v(1, 1, "S-250", rows) is None                       # defined class ok
    msg, blocking = v(1, 1, "O-500", rows)
    assert "already in this race" in msg and blocking is True   # duplicate class -> hard reject
    msg, blocking = v(0, 2, "9", rows)
    assert "expected next heat" in msg and blocking is False    # advisory
    assert v(0, 2, "2", rows) is None                           # a valid next heat


def test_rules_grid_advisory_on_duplicate():
    _app()
    from cozer.app.grids import GridTab, validate_rule_cell
    logs = []
    g = GridTab([(1, "Action"), (2, "Paragraph"), (3, "Description")], 4,
                validate=validate_rule_cell, warn=logs.append)
    rows = [["", "DQ", "314", "Foul"], ["", "DQ", "999", "Other"]]
    g.set_data(rows)
    m = g.model
    # advisory: the duplicate is ACCEPTED (organizer decides) but a warning is logged
    assert m.setData(m.index(1, 1), "314") is True and rows[1][2] == "314"
    assert logs and "already defined" in logs[-1]


def test_races_grid_advisory_and_dropdowns():
    _app()
    from cozer.app.grids import RacesTab, SuggestingDelegate

    class FakeWin:
        def __init__(self, ed):
            self.eventdata = ed
            self.logs = []

        def log(self, m):
            self.logs.append(m)

    ed = {"classes": [["", "GT", "1*(3*1000):1"], ["", "OT", "1*(3*1000):1"]],
          "races": [[["", "GT", "1"], ["", "", ""]]]}
    win = FakeWin(ed)
    rt = RacesTab(win)
    rt.set_data(ed["races"])
    rt.race_list.setCurrentRow(0)
    m = rt.grid.model
    # class not defined -> HARD REJECT (racepattern/heat logic depend on it), and warned
    assert m.setData(m.index(1, 0), "XYZ") is False and ed["races"][0][1][1] == ""
    assert any("not a defined class" in s for s in win.logs)
    assert m.setData(m.index(1, 0), "OT") is True and ed["races"][0][1][1] == "OT"   # defined ok
    # class column offers the defined classes and is editable (override allowed)
    cd = rt.grid.view.itemDelegateForColumn(0)
    assert isinstance(cd, SuggestingDelegate)
    ce = cd.createEditor(rt.grid.view.viewport(), None, m.index(0, 0))
    assert {ce.itemText(i) for i in range(ce.count())} == {"GT", "OT"} and ce.isEditable()
    # heat column offers the valid next heats for the row's class (via get_heats)
    hd = rt.grid.view.itemDelegateForColumn(1)
    he = hd.createEditor(rt.grid.view.viewport(), None, m.index(0, 1))
    assert "1" in [he.itemText(i) for i in range(he.count())]


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


def test_ruleset_import_pure():
    from cozer.app.ruleset import import_ruleset, is_ruleset, new_ruleset
    assert is_ruleset(new_ruleset("UIM circuit"))
    ev = {"kind": "event", "classes": [], "rules": [], "scoringsystem": []}
    src = {"scoringsystem": [10, 5], "classnames": ["A", "B"], "rules": [["", "DQ", "1", "x"]]}
    changed = import_ruleset(ev, src)
    assert set(changed) == {"classnames", "rules", "scoringsystem"}
    assert ev["classnames"] == ["A", "B"] and ev["scoringsystem"] == [10, 5]
    # additive union + dedup on a second import
    import_ruleset(ev, {"classnames": ["B", "C"],
                        "rules": [["", "DQ", "1", "x"], ["", "LL", "2", "y"]]})
    assert ev["classnames"] == ["A", "B", "C"] and len(ev["rules"]) == 2
    # idempotent, and an empty scoring system never clears an existing one
    assert import_ruleset(ev, src) == []
    import_ruleset(ev, {"scoringsystem": []})
    assert ev["scoringsystem"] == [10, 5]


def test_classnames_editor_rejects_empty_and_duplicate():
    _app()
    from cozer.app.grids import StringListEditor
    ed = StringListEditor(prompt="Class name:")
    data = []
    ed.set_data(data)
    assert ed.add_value("O-500") is True and data == ["O-500"]
    assert ed.add_value("  ") is False and data == ["O-500"]      # blank rejected
    assert ed.add_value("") is False and data == ["O-500"]
    assert ed.add_value("O-500") is False and data == ["O-500"]   # duplicate rejected
    assert ed.add_value(" T-400 ") is True and data == ["O-500", "T-400"]  # trimmed
    # renaming an item to blank is reverted, not stored
    ed.list.item(0).setText("")
    assert data[0] == "O-500"


def test_classname_delete_blocked_when_in_use(monkeypatch):
    _app()
    w = MainWindow(_recorded_event())          # class GT used by participants + a race
    w.eventdata["classnames"] = ["GT", "UNUSED"]
    w._reload_forms()
    ed = w.classnames_editor
    assert w._classname_in_use("GT") and w._classname_in_use("UNUSED") is None
    monkeypatch.setattr(appmain.QMessageBox, "information", staticmethod(lambda *a, **k: None))
    ed.list.setCurrentRow(w.eventdata["classnames"].index("GT"))
    ed._delete()
    assert "GT" in w.eventdata["classnames"]    # refused: still in use
    ed.list.setCurrentRow(w.eventdata["classnames"].index("UNUSED"))
    ed._delete()
    assert "UNUSED" not in w.eventdata["classnames"]   # unused: removed


def test_classnames_editor_drag_reorder_syncs_backing_list():
    _app()
    from cozer.app.grids import StringListEditor
    ed = StringListEditor()
    data = ["A", "B", "C"]
    ed.set_data(data)
    # simulate a drag that moves the first row to the bottom
    ed.list.blockSignals(True)
    ed.list.addItem(ed.list.takeItem(0))
    ed.list.blockSignals(False)
    ed._resync()
    assert data == ["B", "C", "A"]      # backing list follows the visual order, in place


def test_classnames_of_includes_event_classes():
    from cozer.app.ruleset import classnames_of
    ev = {"classnames": ["A"], "classes": [["", "B", "p"], ["", "A", "p"], ["", "", ""]]}
    assert classnames_of(ev) == ["A", "B"]      # union, order-preserving, blanks skipped


def test_ruleset_mode_hides_race_tabs():
    _app()
    w = MainWindow()
    w.on_new_ruleset()
    vis = [w.tabs.tabText(i) for i in range(w.tabs.count()) if w.tabs.isTabVisible(i)]
    assert "Timer" not in vis and "Edit Records" not in vis and "Reports" not in vis
    assert "General Information" in vis
    sub = w._geninfo_sub
    assert [sub.tabText(i) for i in range(sub.count()) if sub.isTabVisible(i)] == ["Rules"]
    w.on_new()                                   # back to a full event restores the tabs
    vis2 = [w.tabs.tabText(i) for i in range(w.tabs.count()) if w.tabs.isTabVisible(i)]
    assert {"Timer", "Edit Records", "Reports"} <= set(vis2)


def test_open_legacy_coz_seeds_classnames(tmp_path):
    import shutil
    _app()
    coz = str(tmp_path / "ev.coz")
    shutil.copy(EVENT, coz)                       # wc2000 legacy .coz
    w = MainWindow()
    w.load(coz)
    names = w.eventdata["classnames"]
    assert "O-500" in names and "S-250" in names
    assert set(names) == {c[1] for c in w.eventdata["classes"] if len(c) > 1 and c[1]}
    assert w.classnames_editor.list.count() == len(names)   # shown in the editor


def test_import_bundled_rulesets_via_window(monkeypatch):
    _app()
    import os
    from cozer.app.ruleset import bundled_dir
    w = MainWindow()                             # blank event
    for fname in ("uim_general_2013.cozj", "uim_circuit_2013.cozj"):
        p = os.path.join(bundled_dir(), fname)
        monkeypatch.setattr(appmain.QFileDialog, "getOpenFileName",
                            staticmethod(lambda *a, _p=p, **k: (_p, "")))
        w.on_import_ruleset()
    assert w.eventdata["scoringsystem"] and len(w.eventdata["rules"]) >= 20
    assert "O-500" in w.eventdata["classnames"]
    assert w.classnames_editor.list.count() == len(w.eventdata["classnames"])


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
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))   # fake race clock, seconds->ns
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
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))   # fake race clock, seconds->ns
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
    clock = [100.0]
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    clock[0] = 130.0                          # 30 s lap (above the bounce floor)
    tp.record_lap("GT", "1", "1")
    tp.on_stop()
    assert not tp._started
    tp.on_resume()
    assert tp._started                        # a start time exists -> resumes
    assert len(w.eventdata["record"]["GT"]["1"][1]["1"]) == 1   # prior data kept


def _record_then_reboot(tmp_path, monkeypatch, path):
    """Record two laps (cumulative 41 s from wall start 1000), then simulate a reboot:
    close the store and open the saved event in a fresh window (journal replay)."""
    w = MainWindow(_timer_event())
    _save_as(w, path, monkeypatch)
    tp = w.timer_panel
    clock = [1000.0]
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    for t in (1020.0, 1041.0):
        clock[0] = t
        tp.record_lap("GT", "1", "1")
    w.store.close()
    w2 = MainWindow()
    w2.load(path)
    tp2 = w2.timer_panel
    tp2.reload()
    tp2.race_combo.setCurrentIndex(0)
    return w2, tp2


def test_timer_survives_reboot_and_resume(tmp_path, monkeypatch):
    """A reboot loses the monotonic origin but not the journal: resume bridges the
    downtime via the persistent wall clock, so a post-reboot lap includes the time
    the machine was down."""
    _app()
    w2, tp2 = _record_then_reboot(tmp_path, monkeypatch, str(tmp_path / "e.cozj"))
    rec = w2.eventdata["record"]["GT"]["1"]
    assert rec[1]["1"] == [[1, 20.0], [1, 21.0]] and rec[0]["starttime"] == 1000.0  # replayed
    clock = [1200.0]                          # correct clock: 200 s after start (incl. downtime)
    tp2._wall = lambda: clock[0]
    tp2._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp2.on_resume()
    clock[0] = 1205.0
    tp2.record_lap("GT", "1", "1")
    laps = w2.eventdata["record"]["GT"]["1"][1]["1"]
    assert laps == [[1, 20.0], [1, 21.0], [1, 164.0]]   # 1205-1041: downtime included
    assert sum(m[1] for m in laps) == 205.0             # = wall 1205 - start 1000


def test_timer_reboot_resume_floors_at_recorded_when_wall_clock_is_wrong(tmp_path, monkeypatch):
    """If the machine boots with a wrong/backward clock reading earlier than the last
    recorded lap (dead RTC, NTP not synced), resume must NOT rewind the race and drop
    new crossings: it floors the elapsed at the furthest recorded lap."""
    _app()
    w2, tp2 = _record_then_reboot(tmp_path, monkeypatch, str(tmp_path / "e.cozj"))
    clock = [1005.0]                          # WRONG: reads 5 s in, below the 41 s recorded
    tp2._wall = lambda: clock[0]
    tp2._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp2.on_resume()                           # floors at 41 s, not the bogus 5 s
    clock[0] = 1010.0                          # a crossing 5 s after resume
    tp2.record_lap("GT", "1", "1")
    laps = w2.eventdata["record"]["GT"]["1"][1]["1"]
    assert len(laps) == 3                     # new lap kept, not dropped as negative
    assert laps[2] == [1, 5.0]                # 5 s since resume, off the floored point


def test_estimate_next_lap():
    from cozer.app.timer import estimate_next_lap
    assert estimate_next_lap([1000, 1000, 1000], [], 150) == 19.0         # first lap via @speed (24-5)
    assert round(estimate_next_lap([1000, 1000, 1000], [30.0], 150)) == 25  # 2nd lap via last-lap speed
    assert estimate_next_lap([100, 100], [3.0], 150) == 10.0              # never sooner than 10s
    assert estimate_next_lap([1000, 1000], [30.0, 31.0], 150) is None     # finished -> no hint
    assert estimate_next_lap([1000], [], 0) is None                       # first lap, no speed -> none


def test_heat_course_handles_suffixed_and_restart_heats():
    # The timer decodes the heat-id suffix via phases.heat_number now; a restart
    # (1r/1R) and a time-trial heat (1t) must resolve to the right heat's lap lengths.
    # (No timer test exercised a suffixed heat before this.)
    from cozer.app.timer import heat_course
    ed = {"classes": [["", "C", "3*(1000+2*1500):2"], ["", "C/T", "1*(1000):1"]]}
    assert heat_course(ed, "C", "1") == heat_course(ed, "C", "1r") == heat_course(ed, "C", "1R")
    assert heat_course(ed, "C", "1")[0] == [1000, 1500, 1500]     # heat 1 lap lengths
    assert heat_course(ed, "C", "2")[0] == [1000, 1500, 1500]     # heat 2
    assert heat_course(ed, "C/T", "1t")[0] == [1000]             # /T time-trial heat -> heat 1


def _memb_ev(classes, record=None, qheat1=None, boats=(10, 20, 30, 40)):
    ed = {"classes": classes, "record": record or {}, "scoringsystem": [400, 300, 225],
          "participants": [["", "A", "One", "X", "C", str(b)] for b in boats], "rules": []}
    if qheat1 is not None:
        ed["qheat1"] = {"C": qheat1}
    return ed


def test_heat_membership_nonqualification_is_full_field():
    # a circuit heat materializes every class participant, at any heat number
    from cozer.app.timer import heat_membership
    ed = _memb_ev([["", "C", "3*(1000):1"]], boats=(10, 20, 30))
    assert heat_membership(ed, "C", "1") == ["10", "20", "30"]
    assert heat_membership(ed, "C", "2") == ["10", "20", "30"]


def test_heat_membership_qualification_splits_by_qheat():
    # a qualification qheat materializes only its OWN group (no phantom-DNS for the others)
    from cozer.app.timer import heat_membership
    ed = _memb_ev([["", "C/Q", "3*(1000):1!qualification[1,1,1]"]],
                  record={"C/Q": {}}, qheat1=["10", "30"])
    assert heat_membership(ed, "C/Q", "1q") == ["10", "30"]     # qheat1 = the organizer's flag
    assert heat_membership(ed, "C/Q", "2q") == ["20", "40"]     # qheat2 = the complement


def test_heat_membership_repechage_is_selection_non_qualifiers():
    from cozer.app.timer import heat_membership
    info = {"course": [1000, 1000, 1000], "sheats": 1, "duration": None}

    def qh(fast, slow):
        return [dict(info), {fast: [(1, 20.0)] * 3, slow: [(1, 25.0)] * 3}]
    ed = _memb_ev([["", "C/Q", "3*(1000):1!qualification[1,1,1]"]],
                  record={"C/Q": {"1q": qh("10", "20"), "2q": qh("30", "40")}},
                  qheat1=["10", "20"])
    # 1q: 10 Q -> 20 down; 2q: 30 Q -> 40 down. Repechage field = {20, 40}.
    assert sorted(heat_membership(ed, "C/Q", "3q"), key=int) == ["20", "40"]


def test_heat_membership_repechage_falls_back_before_selections_recorded():
    # repechage field is empty until the selection qheats are recorded -> full field fallback
    from cozer.app.timer import heat_membership
    ed = _memb_ev([["", "C/Q", "3*(1000):1!qualification[1,1,1]"]],
                  record={"C/Q": {}}, qheat1=["10", "30"])
    assert heat_membership(ed, "C/Q", "3q") == ["10", "20", "30", "40"]


# --- Timer mis-pick guard: heat identity + the always-on identity display (§5.2) ----

def test_heat_identity_decodes_class_phase_heat_and_restart():
    from cozer.app.timer import heat_identity
    ed = {"classes": [["", "F 500", "4*(1000):3"],
                      ["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"],
                      ["", "F 500/T", "1*(1000):1"]]}
    assert heat_identity(ed, "F 500", "1") == "F 500 · heat 1"              # circuit -> no kind word
    assert heat_identity(ed, "F 500", "2r") == "F 500 · heat 2 (restart)"   # restart marked
    assert heat_identity(ed, "F 500/Q", "1q") == "F 500 · qualification · heat 1"
    assert heat_identity(ed, "F 500/T", "1t") == "F 500 · time trial · heat 1"


def test_timer_identity_label_shows_selected_race():
    _app()
    tp = MainWindow(_timer_event()).timer_panel
    tp.reload()
    assert "GT · heat 1" in tp.identity_label.text()    # surfaces what the race will record


def test_timer_identity_label_flags_qualification_phase():
    _app()
    ed = {"title": "T", "venue": "V", "date": "D", "officer": "O", "secretary": "S",
          "scoringsystem": [10, 5, 3], "configure": {"language": "English"}, "record": {},
          "classes": [["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"], ["", "F 500", "4*(1000):3"]],
          "participants": [["", "A", "One", "EST", "F 500", "10"]],
          "races": [[["", "F 500/Q", "1q"], ["", "F 500", "1"]]]}
    tp = MainWindow(ed).timer_panel
    tp.reload()
    txt = tp.identity_label.text()
    assert "F 500 · qualification · heat 1" in txt       # the qheat flagged as qualification
    assert "F 500 · heat 1" in txt                        # the final entry, unannotated


def test_closing_hint_arms_and_colors_button(tmp_path, monkeypatch):
    from cozer.app.timer import C_COMING, C_LATE
    _app()
    w = MainWindow(_timer_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    tp = w.timer_panel
    clock = [1000.0]
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    key = ("GT", "1", "1")
    assert key in tp._predict                        # first-lap closing hint armed at Start
    # simulate the arming timer firing (no Qt event loop in the test)
    tp._on_coming(key, 20.0)
    assert tp._phase[key] == "coming" and tp._boat_color(*key) == C_COMING
    tp._on_late(key)
    assert tp._boat_color(*key) == C_LATE
    tp.on_stop()
    assert not tp._predict and key not in tp._phase   # cancelled on Stop


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
    tp._wall = lambda: 100.0                  # no laps recorded here; default race clock is fine
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
    from cozer.app.main import _startup_file, _startup_paths
    assert _startup_file([]) is None
    assert _startup_file(["--debug"]) is None
    assert _startup_file(["notes.txt"]) is None
    assert _startup_file(["event.coz"]) == "event.coz"
    assert _startup_file(["-x", "a.cozj", "b.coz"]) == "a.cozj"   # first event arg wins
    assert _startup_paths(["-x", "a.cozj", "notes.txt", "b.coz"]) == ["a.cozj", "b.coz"]


def test_accumulate_ruleset_pure():
    from cozer.app.ruleset import accumulate_ruleset
    acc = {"classnames": [], "rules": [], "scoringsystem": []}
    r = accumulate_ruleset(acc, {"scoringsystem": [10, 5], "classnames": ["A", "B"],
                                 "rules": [["", "DQ", "314", "Foul"]]}, "gen: ")
    assert r == []
    assert acc["classnames"] == ["A", "B"] and acc["scoringsystem"] == [10, 5]
    # non-destructive: class names union; new rule added; same key with different
    # description is KEPT (not overwritten) and reported; scoring kept (source differs)
    r = accumulate_ruleset(acc, {"scoringsystem": [9, 9], "classnames": ["B", "C"],
                                 "rules": [["", "DQ", "314", "Fouling boats"],
                                           ["", "LL", "310", "Lost lap"]]}, "cir: ")
    assert acc["classnames"] == ["A", "B", "C"]
    assert [x[1:] for x in acc["rules"]] == [["DQ", "314", "Foul"], ["LL", "310", "Lost lap"]]
    assert acc["scoringsystem"] == [10, 5]                     # kept, not overwritten
    assert any("DQ/314" in m for m in r) and any("scoring" in m for m in r)


def test_accumulate_ruleset_fills_empty_scoring():
    from cozer.app.ruleset import accumulate_ruleset
    acc = {"classnames": [], "rules": [], "scoringsystem": []}
    accumulate_ruleset(acc, {"scoringsystem": [20, 17, 15]}, "gen: ")
    assert acc["scoringsystem"] == [20, 17, 15]                # filled because empty


def _write_cozj(path, data):
    from cozer.store import dumps
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(data))
    return path


def test_open_accumulated_rulesets_only_builds_initial_event(tmp_path):
    _app()
    from cozer.app.ruleset import new_ruleset
    gen = new_ruleset("gen")
    gen["scoringsystem"] = [20, 17]
    gen["classnames"] = ["O-500"]
    gen["rules"] = [["", "DQ", "314", "Foul"]]
    cir = new_ruleset("cir")
    cir["classnames"] = ["O-125"]
    cir["rules"] = [["", "LL", "310", "Lost lap"]]
    gp = _write_cozj(str(tmp_path / "gen.cozj"), gen)
    cp = _write_cozj(str(tmp_path / "cir.cozj"), cir)
    w = MainWindow()
    w.open_accumulated([gp, cp])                                 # use case 1: rulesets only
    assert w.eventdata["kind"] == "event"                       # a fresh initial event
    assert w.eventdata["scoringsystem"] == [20, 17]             # filled from the first ruleset
    assert w.eventdata["classnames"] == ["O-500", "O-125"]
    assert [r[1:3] for r in w.eventdata["rules"]] == [["DQ", "314"], ["LL", "310"]]


def test_open_accumulated_event_base_not_overwritten(tmp_path):
    _app()
    from cozer.app.ruleset import new_ruleset
    gen = new_ruleset("gen")
    gen["classnames"] = ["O-500"]
    gen["rules"] = [["", "DQ", "314", "Foul"], ["", "LL", "310", "Lost lap"]]
    cir = new_ruleset("cir")
    cir["classnames"] = ["O-125", "O-500"]
    ev = {"kind": "event", "title": "MyEvent", "scoringsystem": [10, 5],
          "classes": [["", "T-400", "3*(1000):1"]],            # classnames seeded from this
          "participants": [], "races": [], "rules": [["", "DQ", "314", "Fouling others"]],
          "record": {}, "configure": {}}
    gp = _write_cozj(str(tmp_path / "gen.cozj"), gen)
    cp = _write_cozj(str(tmp_path / "cir.cozj"), cir)
    ep = _write_cozj(str(tmp_path / "myevent.cozj"), ev)

    w = MainWindow()
    logged = []
    w.log = lambda m: logged.append(m)
    w.open_accumulated([gp, cp, ep])                            # use case 2: event is the base

    assert w.eventdata["kind"] == "event" and w.eventdata["title"] == "MyEvent"
    dq = next(r for r in w.eventdata["rules"] if r[1:3] == ["DQ", "314"])
    assert dq[3] == "Fouling others"                            # event kept, NOT overwritten
    assert any(r[1:3] == ["LL", "310"] for r in w.eventdata["rules"])   # new rule added
    assert w.eventdata["classnames"] == ["T-400", "O-500", "O-125"]     # union (event first)
    assert w.eventdata["scoringsystem"] == [10, 5]              # event's scoring kept
    assert sum("DQ/314" in m for m in logged) == 1             # one conflict reported


def test_open_accumulated_rejects_multiple_event_files(tmp_path):
    _app()
    ev1 = {"kind": "event", "title": "E1", "classes": [], "rules": [], "scoringsystem": [1]}
    ev2 = {"kind": "event", "title": "E2", "classes": [], "rules": [], "scoringsystem": [2]}
    p1 = _write_cozj(str(tmp_path / "e1.cozj"), ev1)
    p2 = _write_cozj(str(tmp_path / "e2.cozj"), ev2)
    w = MainWindow()
    logged = []
    w.log = lambda m: logged.append(m)
    w.open_accumulated([p1, p2])
    assert w.eventdata["title"] == "E1"                          # first event used
    assert any("ignoring" in m and "e2.cozj" in m for m in logged)


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


def test_has_qualification_detects_qualification_phase():
    from cozer.app.classpart import has_qualification
    ed = {"classes": [["", "C", "3*(1000):1"],
                      ["", "C/Q", "3*(1000):1!qualification[1,1,1]"]]}
    assert has_qualification(ed, "C") is True          # base C has a /Q sibling
    assert has_qualification(ed, "C/Q") is True
    assert has_qualification({"classes": [["", "D", "3*(1000):1"]]}, "D") is False


def test_qheat1_checkbox_column_toggles_membership():
    from PySide6.QtCore import Qt
    from cozer.app.classpart import ParticipantClassModel
    _app()
    parts = [["", "A", "One", "EST", "C", "10"], ["", "B", "Two", "FIN", "C", "20"]]
    qh = {}
    m = ParticipantClassModel(parts, "C", qheat1=qh, show_qheat1=True)
    assert m.columnCount() == 5                         # 4 base columns + qheat1
    assert m.headerData(4, Qt.Horizontal, Qt.DisplayRole) == "qheat1"
    assert m.headerData(4, Qt.Horizontal, Qt.ToolTipRole)  # tooltip present
    idx = m.index(0, 4)
    assert m.data(idx, Qt.CheckStateRole) == Qt.Unchecked
    assert m.flags(idx) & Qt.ItemIsUserCheckable
    assert m.setData(idx, Qt.Checked, Qt.CheckStateRole) is True
    assert qh == {"C": ["10"]}                          # boat 10 added to eventdata['qheat1']['C']
    assert m.data(idx, Qt.CheckStateRole) == Qt.Checked
    assert m.setData(idx, Qt.Unchecked, Qt.CheckStateRole) is True
    assert qh == {"C": []}                              # and removed


def test_qheat1_column_absent_without_qualification():
    from cozer.app.classpart import ParticipantClassModel
    _app()
    m = ParticipantClassModel([["", "A", "One", "EST", "C", "10"]], "C")  # show_qheat1=False
    assert m.columnCount() == 4                         # no qheat1 column


def test_qheat1_checkbox_column_sized_to_content_not_stretched():
    from PySide6.QtWidgets import QHeaderView
    from cozer.app.classpart import ClassParticipantsWidget
    _app()
    w = ClassParticipantsWidget([["", "A", "One", "EST", "C", "10"]], "C",
                                qheat1={}, show_qheat1=True)
    hdr = w.view.horizontalHeader()
    assert not hdr.stretchLastSection()                 # the checkbox column must not stretch
    qcol = w.model.columnCount() - 1                    # the trailing qheat1 checkbox column
    assert hdr.sectionResizeMode(qcol) == QHeaderView.ResizeToContents


# --- GUI phase authoring: one tab per base, Phases dialog writes /T,/Q rows ---------

def _phase_event():
    return {"kind": "event", "title": "P", "scoringsystem": [400, 300, 225], "rules": [],
            "classes": [["", "F 500/T", "1*(1000):1"],
                        ["", "F 500/Q", "3*(1000):1!qualification[4,4,4]"],
                        ["", "F 500", "4*(1400):3"], ["", "GT15", "2*(3*1000):1"]],
            "participants": [["", "A", "One", "EST", "F 500", "10"]], "races": []}


def test_base_classes_collapses_phase_rows():
    from cozer.app.classpart import base_classes
    ed = {"classes": [["", "F 500/T", "x"], ["", "F 500/Q", "y"], ["", "F 500", "z"],
                      ["", "GT15", "w"]]}
    assert base_classes(ed) == ["F 500", "GT15"]        # /T,/Q collapse onto the base, order kept


def test_classes_panel_one_tab_per_base():
    _app()
    cp = MainWindow(_phase_event()).classpart_panel
    assert [cp._tab_class(i) for i in range(cp.tabs.count())] == ["F 500", "GT15"]   # 2 tabs, not 4


def test_qualification_base_tab_shows_qheat1_column():
    _app()
    from cozer.app.classpart import ClassParticipantsWidget
    cp = MainWindow(_phase_event()).classpart_panel
    i = next(i for i in range(cp.tabs.count()) if cp._tab_class(i) == "F 500")
    cw = cp.tabs.widget(i).findChild(ClassParticipantsWidget)
    assert cw.model.columnCount() == 5                  # 4 base cols + qheat1 (F 500 has a /Q phase)


def test_sync_phase_writes_and_removes_suffixed_rows():
    _app()
    ed = {"kind": "event", "title": "P", "scoringsystem": [400, 300, 225], "rules": [],
          "classes": [["", "F 500", "4*(1400):3"]], "participants": [], "races": []}
    cp = MainWindow(ed).classpart_panel
    cp._sync_phase("F 500", "/T", "1*(1000):1")
    cp._sync_phase("F 500", "/Q", "3*(1000):1!qualification[4,4,4]")
    names = [r[1] for r in ed["classes"]]
    assert "F 500/T" in names and "F 500/Q" in names    # internal phase rows written by cozer
    cp._sync_phase("F 500", "/T", "")                   # disabling removes it (no race uses it)
    assert "F 500/T" not in [r[1] for r in ed["classes"]]


def test_phases_dialog_round_trips_patterns_and_counts():
    _app()
    from cozer.app.classpart import PhasesDialog
    dlg = PhasesDialog(None, "F 500", "1*(1000):1", "3*(1000):1!qualification[4,4,4]")
    assert dlg.tt_enable.isChecked() and dlg.q_enable.isChecked()
    assert dlg.q_pat.text() == "3*(1000):1" and dlg.q_counts.text() == "4,4,4"   # counts split out
    assert dlg.timetrial_pattern() == "1*(1000):1"
    assert dlg.qualification_pattern() == "3*(1000):1!qualification[4,4,4]"       # recombined


def test_phases_dialog_omitted_phase_returns_empty():
    _app()
    from cozer.app.classpart import PhasesDialog
    dlg = PhasesDialog(None, "F 500", None, None)
    assert not dlg.tt_enable.isChecked() and not dlg.q_enable.isChecked()
    assert dlg.timetrial_pattern() == "" and dlg.qualification_pattern() == ""


def test_phases_dialog_prefills_both_phases_from_finals_course():
    _app()
    from cozer.app.classpart import PhasesDialog
    dlg = PhasesDialog(None, "F 500", None, None, finals_pattern="4*(1000+4*1500):3")
    assert not dlg.tt_enable.isChecked() and not dlg.q_enable.isChecked()   # both off by default...
    assert dlg.tt_pat.text() == "1*(1000+4*1500):1"     # time trial = a single solo run
    assert dlg.q_pat.text() == "3*(1000+4*1500):1"      # qualification seeds 3 qheats (the default)
    assert dlg.q_counts.text() == ""                    # counts left for the operator
    # existing phases keep their own patterns (no reseed from finals)
    keep = PhasesDialog(None, "F 500", "1*(900):1", "3*(1000):1!qualification[4,4,4]",
                        finals_pattern="4*(1000+4*1500):3")
    assert keep.tt_pat.text() == "1*(900):1"
    assert keep.q_pat.text() == "3*(1000):1" and keep.q_counts.text() == "4,4,4"


def test_phases_dialog_syncs_pattern_heats_to_qualifier_count():
    # the Timer runs one qheat per pattern heat, so the pattern's heat count must follow the
    # number of qualifiers entered -- otherwise not all qheats could be run.
    _app()
    from cozer.app.classpart import PhasesDialog
    dlg = PhasesDialog(None, "F 500", None, None, finals_pattern="4*(1000+4*1500):3")
    dlg.q_enable.setChecked(True)
    dlg.q_counts.setText("5,5")                         # 2 qheats
    assert dlg.q_pat.text() == "2*(1000+4*1500):1"      # pattern heat count live-synced to 2
    assert dlg.qualification_pattern() == "2*(1000+4*1500):1!qualification[5,5]"
    dlg.q_counts.setText("6,6,6,6")                     # 4 qheats
    assert dlg.q_pat.text().startswith("4*")
    assert dlg.qualification_pattern() == "4*(1000+4*1500):1!qualification[6,6,6,6]"


def test_course_prefill_empty_for_endurance_finals():
    from cozer.app.classpart import _course_prefill
    assert _course_prefill("5000/6") == ""              # endurance -> nothing sensible to seed
    assert _course_prefill("") == ""
