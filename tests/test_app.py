"""Offscreen (headless) smoke tests for the PySide6 GUI."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

from cozer.store import read_legacy_coz  # noqa: E402
from cozer.native import record_heat  # noqa: E402
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
    # the class/heat selector is one tab per phase; each tab's tree top-level items are its classes
    n_classes = sum(w.report_tabs.widget(i).topLevelItemCount()
                    for i in range(w.report_tabs.count()))
    assert n_classes == len(get_classes(ed))               # every class appears under some phase tab
    assert w.report_combo.count() == 15                    # all reports (incl. 2 legacy Final + 2 Inspection + Time-trial)


def test_event_field_edits_update_eventdata():
    _app()
    w = MainWindow()
    w._fields["venue"].setText("Lake Harku")
    assert w.eventdata["venue"] == "Lake Harku"


def test_uim_commissioner_settings_field():
    # §10 posting metadata: the UIM Sports Commissioner is a stored event field, editable in the
    # settings form (loads on open, writes back on edit) and defaulted blank on a new event.
    from cozer.app.main import DEFAULT_EVENT
    from cozer.app.ruleset import new_ruleset
    assert DEFAULT_EVENT["uim_commissioner"] == "" and new_ruleset()["uim_commissioner"] == ""
    _app()
    ev = _timer_event()
    ev["uim_commissioner"] = "Carlo"
    w = MainWindow(ev)
    assert w._fields["uim_commissioner"].text() == "Carlo"     # loads the stored value
    w._fields["uim_commissioner"].setText("Dana")
    assert w.eventdata["uim_commissioner"] == "Dana"           # edits write back


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
    # check one class so _report_selection() is exercised (whole class -> all heats). The selector has
    # one tab per phase; a class is a top-level item of its phase tab's tree; real name on UserRole.
    c0 = w.report_tabs.widget(0).topLevelItem(0)
    c0.setCheckState(0, Qt.Checked)
    classes, _heat_map = w._report_selection()
    assert classes == [c0.data(0, Qt.UserRole)]
    out = str(tmp_path / "full_final.pdf")
    opened = []
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (out, "")))
    monkeypatch.setattr(appmain, "open_in_viewer", opened.append)
    monkeypatch.setattr(appmain.QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    w.report_combo.setCurrentIndex(3)                      # Full Final
    w.on_export()
    assert os.path.exists(out) and opened == [out]


def test_report_options_laps_toggle_reaches_render(tmp_path, monkeypatch):
    # D3: the Reports-tab "show lap count for all finishers" checkbox feeds an options dict to
    # the reports that honour it (Full Final), and NOT to those that don't (legacy / participants).
    import cozer.reports as R
    _app()
    w = MainWindow(read_legacy_coz(EVENT))
    assert hasattr(w, "opt_all_laps") and not w.opt_all_laps.isChecked()   # exists, default off
    assert w._report_options() == {"show_laps": False}
    w.opt_all_laps.setChecked(True)
    assert w._report_options() == {"show_laps": True}

    seen = {}
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "r.pdf"), "")))
    monkeypatch.setattr(appmain, "open_in_viewer", lambda *a, **k: None)
    monkeypatch.setattr(appmain.QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    for fn in ("render_full_final", "render_full_final_legacy"):
        monkeypatch.setattr(R, fn, (lambda name: (lambda *a, **k: seen.__setitem__(name, k)))(fn))

    w.report_combo.setCurrentIndex(w.report_combo.findText("Full Final"))         # native -> gets options
    w.on_export()
    assert seen["render_full_final"].get("options") == {"show_laps": True}
    w.report_combo.setCurrentIndex(w.report_combo.findText("Full Final (legacy)"))  # -> no options kwarg
    w.on_export()
    assert "options" not in seen["render_full_final_legacy"]


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
    w.report_combo.setCurrentIndex(3)                      # Full Final (after Participants/Intermediate/Qualification)
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
    w.report_combo.setCurrentIndex(3)                     # Full Final
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
    assert record_heat(w2.eventdata, cl, h)[0]["racetime"] == 123.0


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
    assert m.rowCount() == 2 and m.columnCount() == 5          # filtered to class GT (5 base cols)
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


def test_nationality_field_and_show_helper():
    # D1: nationality is a distinct participant field (index 6). The Participants GUI has a
    # Nationality column; reports show a Nationality column only for multi-nationality events.
    _app()
    from cozer.reports.common import show_from, show_nationality, nationalities_index
    from cozer.app.classpart import ParticipantClassModel
    ed = {"participants": [["", "A", "One", "Tallinn HC", "GT", "1", "EST"],
                           ["", "B", "Two", "Helsinki", "GT", "2", "FIN"]]}
    assert show_nationality(ed) and show_from(ed)             # both vary -> show both columns
    assert nationalities_index(ed)[("GT", "1")] == "EST"
    # a national event with one shared club -> both columns hidden (uniform, nothing to distinguish)
    national = {"participants": [["", "A", "One", "HC", "GT", "1", "EST"],
                                 ["", "B", "Two", "HC", "GT", "2", "EST"]]}
    assert not show_nationality(national) and not show_from(national)
    # no club specified at all -> From hidden; nationalities still vary -> Nationality shown
    noclub = {"participants": [["", "A", "One", "", "GT", "1", "EST"],
                               ["", "B", "Two", "", "GT", "2", "FIN"]]}
    assert not show_from(noclub) and show_nationality(noclub)
    # only one participant's nationality/club filled, the rest blank -> still shown (the filled
    # row is distinguished from the blanks; empty counts as its own value)
    partial = {"participants": [["", "A", "One", "Tallinn", "GT", "1", "EST"],
                                ["", "B", "Two", "", "GT", "2", ""]]}
    assert show_nationality(partial) and show_from(partial)
    # all blank -> hidden
    allblank = {"participants": [["", "A", "One", "", "GT", "1", ""],
                                 ["", "B", "Two", "", "GT", "2", ""]]}
    assert not show_nationality(allblank) and not show_from(allblank)
    # the Participants GUI model exposes an editable Nationality column at participant index 6
    m = ParticipantClassModel(ed["participants"], "GT")
    assert "Nationality" in [c[1] for c in m.COLS]
    natcol = next(i for i, (ci, _) in enumerate(m.COLS) if ci == 6)
    assert m.data(m.index(0, natcol)) == "EST"
    assert m.setData(m.index(1, natcol), "SWE") and ed["participants"][1][6] == "SWE"


def test_nationality_dropdown_delegate_and_soft_validate():
    # The Nationality column is a dropdown of IOC codes shown "CODE — Name", storing the bare
    # code; an invalid code (e.g. legacy LIT) is accepted but flagged (offering the list = LTU).
    _app()
    from cozer.app.classpart import NationalityDelegate, ParticipantClassModel
    d = NationalityDelegate()
    combo = d.createEditor(None, None, None)
    texts = [combo.itemText(i) for i in range(combo.count())]
    assert "EST — Estonia" in texts and "LTU — Lithuania" in texts   # code + English name (§209)
    assert not any(t.startswith("LIT ") for t in texts)              # the corpus typo isn't offered
    assert combo.itemData(combo.findText("EST — Estonia")) == "EST"  # stores the bare code
    assert combo.view().minimumWidth() >= 200        # popup widened so "CODE — Country" is readable
    # the cell renders the readable "CODE — Country" form (an unknown code shows as-is)
    assert d.displayText("EST", None) == "EST — Estonia"
    assert d.displayText("LIT", None) == "LIT" and d.displayText("", None) == ""

    warns = []
    m = ParticipantClassModel([["", "A", "", "", "GT", "1", ""]], "GT", warn=warns.append)
    natcol = next(i for i, (ci, _) in enumerate(m.COLS) if ci == 6)
    assert m.setData(m.index(0, natcol), "LIT") and "not an IOC" in warns[-1]   # accepted + warned
    assert m.setData(m.index(0, natcol), "EST") and len(warns) == 1            # valid -> no new warn


def test_classname_guard_and_races_dropdown_on_native_model():
    # Regression (3c-2): the native {name, phases} model must not crash the catalog-delete
    # guard or the Races-tab class dropdown -- both used to read classes as legacy `c[1]` rows.
    _app()
    from cozer.native import to_native
    ed = to_native({"scoringsystem": [10], "rules": [], "record": {}, "participants": [],
                    "classes": [["", "GT15/T", "1*(1000):1"], ["", "GT15", "4*(1400):3"],
                                ["", "OSY-400", "4*(1400):3"]], "races": []})
    ed["races"] = [[{"name": "OSY-400", "kind": "circuit", "number": 1, "occurrence": 0}]]
    w = MainWindow(ed)
    assert w._classname_in_use("GT15")                  # set up as an event class (native shape)
    assert w._classname_in_use("OSY-400")               # and a race uses it
    assert w._classname_in_use("NOPE") is None
    got = w.races_tab._defined_classes()                # dropdown enumerates base classes (suffix-free)
    assert set(got) == {"GT15", "OSY-400"} and "GT15/T" not in got


def test_legacy_decoders_are_import_only():
    # Close-out guard for the suffix refactor: the in-memory model is fully native (through 3d),
    # so the legacy-shape decoders (class_pattern / get_classes / to_phases legacy branches) must
    # run ONLY while importing a legacy `.coz` (via to_native) -- never in native operation. If
    # this fails, some code routes native operation through the legacy path (or a newly-added
    # legacy branch needs a classes.note_legacy_read tag). See cozer/classes.py.
    _app()
    import cozer.classes as classesmod
    import cozer.reports as R
    from cozer.store import dump_event, load_event
    from cozer.racepattern import get_classes, class_pattern, get_heats, race_kind
    from cozer.phases import to_phases
    from cozer.validate import check_results

    ed = load_event(dump_event(read_legacy_coz(EVENT)))     # wc2000 -> fully native in-memory
    from cozer.native import is_native
    assert is_native(ed)

    classesmod.legacy_reads.clear()                         # ignore the import that built `ed`
    w = MainWindow(ed)                                      # builds every panel on the native model
    w._reload_forms()
    w.timer_panel.reload()
    w.editor_panel.refresh_heats()
    for c in get_classes(ed):                              # core suffix-decoders, native shape
        class_pattern(ed, c)
        race_kind(ed, c)
    for i in range(len(ed.get("races", [])) + 1):
        get_heats(ed, i)
    to_phases(ed)
    for build in (R.build_full_final, R.build_short_final, R.build_participants, R.build_checklist,
                  R.build_intermediate, R.build_laps_protocol, R.build_endurance_final,
                  R.build_info_letter, R.build_registration_letter):
        build(ed)
    check_results(ed)
    load_event(dump_event(ed))                             # native save round-trip
    assert classesmod.legacy_reads == [], classesmod.legacy_reads   # native op never decodes legacy

    classesmod.legacy_reads.clear()                        # positive control: import DOES decode
    dump_event(read_legacy_coz(EVENT))                     # to_native reads the legacy shape
    assert classesmod.legacy_reads                         # ... so the legacy path is exercised


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


def test_timer_picks_up_races_added_on_races_tab():
    # Regression: a race added on the Races tab must appear in the Timer combo when you switch
    # to it (the combo was only built at event-load, so newly-added races were invisible).
    _app()
    ed = {"title": "T", "scoringsystem": [10], "rules": [], "record": {}, "participants": [],
          "classes": [["", "GT", "1*(1000):1"]], "races": [], "configure": {}}
    w = MainWindow(ed)
    assert w.timer_panel.race_combo.count() == 0          # no races at load
    w.races_tab._add_race()                               # add one on the Races tab
    w.eventdata["races"][0] = [["", "GT", "1"]]
    # simulate switching to the Timer tab
    w.tabs.setCurrentWidget(w.timer_panel)
    assert w.timer_panel.race_combo.count() == 1          # now visible in the Timer
    assert "GT 1" in w.timer_panel.race_combo.itemText(0)


def test_editor_picks_up_heats_recorded_after_load():
    # Regression: a heat recorded in the Timer must appear in Edit Records when you switch to it
    # (the heat combo was only built at event-load, so freshly-recorded heats were invisible).
    _app()
    from cozer.native import to_native
    from cozer.store import apply_op
    ed = to_native({"title": "T", "scoringsystem": [10], "rules": [], "participants": [],
                    "classes": [["", "GT", "1*(1000):1"]], "record": {}, "races": []})
    w = MainWindow(ed)
    assert w.editor_panel.heat_combo.count() == 0         # no records at load
    apply_op(w.eventdata, {"op": "heat", "cl": "GT", "h": "1",
                           "info": {"course": [1000]}, "ids": ["1"]})
    apply_op(w.eventdata, {"op": "lap", "cl": "GT", "h": "1", "id": "1", "mark": [1, 20.0]})
    w.tabs.setCurrentWidget(w.editor_panel)               # simulate switching to Edit Records
    assert w.editor_panel.heat_combo.count() == 1
    assert "GT / 1" in w.editor_panel.heat_combo.itemText(0)


def test_editor_delete_race_data(tmp_path, monkeypatch):
    # owner: a "Delete race data" button in Edit Records warns (default No) when there IS measured data
    # and, on Yes, RESTORES the heat to a pre-Start state — it removes the record slot (delheat op), so
    # the heat drops out of the record-based combo (no emptied residual left behind).
    import cozer.app.editor as editor_mod
    from cozer.native import to_native, record_heat
    from cozer.store import apply_op
    _app()
    ed = to_native({"title": "T", "scoringsystem": [10], "rules": [], "participants": [],
                    "classes": [["", "GT", "1*(1000):1"]], "record": {}, "races": []})
    apply_op(ed, {"op": "heat", "cl": "GT", "h": "1", "info": {"course": [1000]}, "ids": ["1", "2"]})
    apply_op(ed, {"op": "lap", "cl": "GT", "h": "1", "id": "1", "mark": [1, 20.0]})
    w = MainWindow(ed)
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",           # Delete goes through the store
                        staticmethod(lambda *a, **k: (str(tmp_path / "ev.cozj"), "")))
    w.on_save_as()
    assert w.store is not None
    w.tabs.setCurrentWidget(w.editor_panel)
    p = w.editor_panel
    p.heat_combo.setCurrentIndex(0)
    assert p._cur() == ("GT", "1")

    # declining (No) keeps the data + the heat
    monkeypatch.setattr(editor_mod, "confirm_delete", lambda *a, **k: False)
    p._delete_race_data()
    assert record_heat(w.eventdata, "GT", "1")[1].get("1")       # still there (declined)
    assert p.heat_combo.count() == 1

    # measured data -> a confirm is asked; on Yes the slot is REMOVED -> gone from the combo (pre-Start)
    asks = []
    monkeypatch.setattr(editor_mod, "confirm_delete", lambda *a, **k: asks.append(1) or True)
    p._delete_race_data()
    assert asks                                                  # measured -> prompted
    assert record_heat(w.eventdata, "GT", "1") is None           # slot removed -> pre-Start (no residual)
    assert p.heat_combo.count() == 0                             # heat dropped from the record-based combo

    # nothing selected now -> a further delete is a quiet no-op (no prompt)
    asks.clear()
    p._delete_race_data()
    assert not asks


def test_reports_tree_shows_native_heats_and_refreshes_on_entry():
    # Regression: the Reports class/heat tree read the record by synthesized class name, so on the
    # native model (record keyed by base->kind->number) heats were missing; and it wasn't refreshed
    # on entering the tab, so heats recorded elsewhere didn't show (the editor->reports update gap).
    _app()
    from cozer.native import to_native
    from cozer.store import apply_op
    ed = to_native({"title": "T", "scoringsystem": [10], "rules": [], "participants": [],
                    "classes": [["", "GT", "2*(1000):1"]], "record": {}, "races": []})
    apply_op(ed, {"op": "heat", "cl": "GT", "h": "1", "info": {"course": [1000]}, "ids": ["1"]})
    apply_op(ed, {"op": "lap", "cl": "GT", "h": "1", "id": "1", "mark": [1, 20.0]})
    w = MainWindow(ed)

    def heats_of(cl):
        for i in range(w.report_tabs.count()):            # phase tab -> class (real name on UserRole)
            tree = w.report_tabs.widget(i)
            for j in range(tree.topLevelItemCount()):
                c = tree.topLevelItem(j)
                if c.data(0, Qt.UserRole) == cl:
                    return [c.child(k).text(0) for k in range(c.childCount())]
        return None

    assert heats_of("GT") == ["1"]                        # native heat shows (was empty/wrong)
    apply_op(w.eventdata, {"op": "heat", "cl": "GT", "h": "2", "info": {"course": [1000]}, "ids": ["1"]})
    apply_op(w.eventdata, {"op": "lap", "cl": "GT", "h": "2", "id": "1", "mark": [1, 21.0]})
    w.tabs.setCurrentWidget(w._reports_tab)               # switch to Reports -> refreshed
    assert heats_of("GT") == ["1", "2"]


def test_delete_confirmation_guards_real_data(monkeypatch):
    # Deleting REAL data asks "are you sure?" (No keeps, Yes deletes); a blank target is deleted
    # straight away (nothing to lose).
    _app()
    from cozer.app.grids import RacesTab
    from cozer.native import to_native
    from PySide6.QtWidgets import QMessageBox

    calls = []
    ans = [QMessageBox.No]
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: (calls.append(1), ans[0])[1]))

    class FakeWin:
        def __init__(self, ed):
            self.eventdata = ed

        def log(self, m):
            pass

    ed = to_native({"classes": [["", "GT", "3*(1000):1"]], "record": {}, "races": []})
    ed["races"] = [[{"name": "GT", "kind": "circuit", "number": 1, "occurrence": 0}],   # real
                   [{"name": "", "kind": "", "number": 0, "occurrence": 0}]]            # blank
    rt = RacesTab(FakeWin(ed))
    rt.set_data(ed["races"])

    rt.race_list.setCurrentRow(0)                       # real race, answer No -> kept
    rt._delete_race()
    assert len(ed["races"]) == 2 and len(calls) == 1

    ans[0] = QMessageBox.Yes                            # real race, answer Yes -> deleted
    rt.race_list.setCurrentRow(0)
    rt._delete_race()
    assert len(ed["races"]) == 1 and len(calls) == 2

    calls.clear()                                       # remaining race is blank -> no prompt
    rt.race_list.setCurrentRow(0)
    rt._delete_race()
    assert ed["races"] == [] and calls == []


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
    from cozer.native import to_native
    ed = to_native({
        "title": "T", "venue": "V", "date": "D", "officer": "O", "secretary": "S",
        "scoringsystem": [10],
        "classes": [["", "GT", "3*(1000):1"], ["", "OSY-400", "3*(1000):1"],
                    ["", "S-250", "3*(1000):1"]],
        "participants": [], "races": [], "rules": [], "record": {}, "configure": {},
    })
    ed["races"] = [[{"name": "GT", "kind": "circuit", "number": 1, "occurrence": 0},
                    {"name": "OSY-400", "kind": "circuit", "number": 2, "occurrence": 0}]]
    w = MainWindow(ed)
    rt = w.races_tab
    assert rt.race_list.item(0).text() == "Race 1: GT 1, OSY-400 2"     # suffix-free label
    # adding a heat via the add-heat form updates the list label live
    rt.race_list.setCurrentRow(0)
    rt.class_combo.setCurrentText("S-250")             # cascade -> phase Circuit, heat 1
    rt._add_heat()
    assert rt.race_list.item(0).text() == "Race 1: GT 1, OSY-400 2, S-250 1"
    assert ed["races"][0][-1] == {"name": "S-250", "kind": "circuit", "number": 1, "occurrence": 0}


def test_validate_rule_cell_pure():
    from cozer.app.grids import validate_rule_cell
    rows = [["", "DQ", "314", "Foul"], ["", "DQ", "999", "Other"]]
    msg, blocking = validate_rule_cell(1, 2, "314", rows)       # paragraph -> duplicates DQ/314
    assert "already defined" in msg and blocking is False       # advisory
    assert validate_rule_cell(1, 2, "888", rows) is None        # unique
    assert validate_rule_cell(1, 1, "", rows) is None           # empty action is allowed


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


def test_races_add_heat_form_cascades_and_validates():
    _app()
    from cozer.app.grids import RacesTab
    from cozer.native import to_native

    class FakeWin:
        def __init__(self, ed):
            self.eventdata = ed
            self.logs = []

        def log(self, m):
            self.logs.append(m)

    ed = to_native({"classes": [["", "GT", "3*(1000):1"], ["", "GT/T", "1*(1000):1"],
                                ["", "OT", "3*(1000):1"]], "record": {}, "races": []})
    ed["races"] = [[]]                                  # one empty race
    win = FakeWin(ed)
    rt = RacesTab(win)
    rt.set_data(ed["races"])
    rt.race_list.setCurrentRow(0)

    # the add-heat form's three dropdowns are always visible + cascade:
    assert {rt.class_combo.itemText(i) for i in range(rt.class_combo.count())} == {"GT", "OT"}  # bases, no /T
    rt.class_combo.setCurrentText("GT")                # -> phases of GT (circuit + time trial)
    assert {rt.phase_combo.itemText(i) for i in range(rt.phase_combo.count())} == {"Circuit", "Time trial"}
    rt.phase_combo.setCurrentText("Circuit")           # -> heat numbers 1..3 (GT circuit = 3 heats)
    assert [rt.heat_combo.itemText(i) for i in range(rt.heat_combo.count())] == ["1", "2", "3"]

    rt.heat_combo.setCurrentText("2")                  # Add appends a native suffix-free entry
    rt._add_heat()
    assert ed["races"][0] == [{"name": "GT", "kind": "circuit", "number": 2, "occurrence": 0}]
    rt._add_heat()                                     # GT already in the race -> rejected + logged
    assert len(ed["races"][0]) == 1 and any("already in this race" in s for s in win.logs)

    rt.phase_combo.setCurrentText("Time trial")        # cascade updates the heat list (TT = 1 heat)
    assert [rt.heat_combo.itemText(i) for i in range(rt.heat_combo.count())] == ["1"]


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
    # loaded as the suffix-free native shape: class entries are base/phase dicts
    assert set(names) == {c["name"] for c in w.eventdata["classes"] if c.get("name")}
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


def test_accumulate_target_splits_trailing_new_cozj(tmp_path):
    from cozer.app.main import _accumulate_target
    a = str(tmp_path / "a.cozj"); b = str(tmp_path / "b.cozj"); out = str(tmp_path / "out.cozj")
    open(a, "w").write("{}"); open(b, "w").write("{}")
    # trailing non-existing .cozj -> the create-and-merge output target
    assert _accumulate_target([a, b, out]) == ([a, b], out, [])
    # all existing -> no output target (normal accumulate/open)
    assert _accumulate_target([a, b]) == ([a, b], None, [])
    # a non-existing input that is NOT last -> reported as missing, not an output
    assert _accumulate_target([out, a]) == ([a], None, [out])


def test_cli_create_and_merge_to_new_cozj(tmp_path):
    # `cozer base.cozj ruleset.cozj out.cozj` (out non-existing) -> create out = a copy of the base
    # event with the ruleset accumulated in; the input files are read-only.
    _app()
    import os
    from cozer.app.ruleset import bundled_dir
    from cozer.store import dump_event, load_event

    base = str(tmp_path / "base.cozj")
    base_ed = {"title": "Base", "scoringsystem": [], "rules": [], "participants": [
        ["", "A", "One", "EST", "GT", "1"]], "record": {}, "races": [], "schema": 2,
        "classes": [{"name": "GT", "phases": [{"kind": "circuit", "pattern": "3*(1000):1"}]}]}
    open(base, "w").write(dump_event(base_ed))
    base_before = open(base).read()
    rulesets = [os.path.join(bundled_dir(), n) for n in         # general = scoring/rules, circuit = vocab
                ("uim_general_2013.cozj", "uim_circuit_2013.cozj")]
    out = str(tmp_path / "merged.cozj")

    w = MainWindow()
    w.open_accumulated([base] + rulesets, save_as=out)
    assert os.path.exists(out)                                         # the new file was created
    merged = load_event(open(out, encoding="utf-8").read())
    assert any(c["name"] == "GT" for c in merged["classes"])           # base event copied over
    assert any(len(p) > 4 and p[4] == "GT" for p in merged["participants"])  # base data preserved
    assert merged["scoringsystem"]                                     # ruleset scoring filled in
    assert "O-500" in merged["classnames"]                            # ruleset vocabulary accumulated
    assert open(base).read() == base_before                            # inputs untouched


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


def test_window_title_shows_build_version():
    # a screenshot must reveal the running build: the title carries the cozer version (+ the git hash
    # when run from a source checkout) so a reported screenshot's version is obvious.
    from cozer import __version__
    _app()
    w = MainWindow(_timer_event())
    title = w.windowTitle()
    assert title.startswith("COZER ") and __version__ in title


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
    marks = record_heat(w.eventdata, "GT", "1")[1]["1"]
    assert [m[0] for m in marks] == [1, 1, 1]
    assert [m[1] for m in marks] == [20.0, 21.0, 22.0]
    assert os.path.getsize(str(tmp_path / "e.cozj.journal")) > 0     # journaled + fsync'd
    import copy
    from cozer.analyzer import analyze
    res = analyze("1", copy.deepcopy(record_heat(w.eventdata, "GT", "1")), [10, 5, 3])
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
    # laptimes = cumulative crossing time at each lap (running sum of the per-lap durations)
    assert by["1"]["laptimes"] == [20.0, 41.0] and by["1"]["time"] == 41.0
    assert by["2"]["laptimes"] == [19.0, 39.0, 61.0]


def test_standings_same_laps_by_time():
    from cozer.app.timer import standings
    rec = [{"course": [1000, 1000]}, {"1": [[1, 30.0]], "2": [[1, 25.0]]}]
    assert [s["id"] for s in standings(rec)] == ["2", "1"]     # equal laps -> faster leads


def test_standings_freezes_finished_boat_at_course_length():
    # issue #26: a finished boat clicked again past the line must NOT out-rank the real winner. Boat 2
    # finished 3 laps first (61s); boat 1 finished 3 laps at 66s then got a spurious 4th click (a 0.3s
    # bounce). Without the freeze, boat 1 (4 "laps") sorts first as the "leader" and every gap goes to
    # 0.0. With it, both are capped at need=3 and ranked by their real finish time.
    from cozer.app.timer import standings
    rec = [{"course": [1000, 1000, 1000]},
           {"1": [[1, 20.0], [1, 21.0], [1, 25.0], [1, 0.3]],   # 3 laps @66s + spurious 4th click
            "2": [[1, 19.0], [1, 20.0], [1, 22.0]]}]            # 3 laps @61s (the real winner)
    order = standings(rec)
    assert [s["id"] for s in order] == ["2", "1"]               # real winner leads, not the extra-click boat
    by = {s["id"]: s for s in order}
    assert by["1"]["laps"] == 3 and by["1"]["time"] == 66.0     # frozen at the finish (4th click dropped)
    assert by["1"]["laptimes"] == [20.0, 41.0, 66.0]


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
    #   Finish -> finished boat 2 (below the Finish marker, legacy order)
    assert seq[0] == ("marker", "Ready to Start")
    assert ("boat", "3") in seq[:3]
    fin_i = seq.index(("marker", "Finish"))
    assert seq[fin_i + 1:] == [("boat", "2")]                       # finished boats sit below Finish
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
    assert len(record_heat(w.eventdata, "GT", "1")[1]["1"]) == 1
    clock[0] = 1041.0
    tp._buttons[("GT", "1", "2")].click()             # clicking the GRID records a lap
    assert len(record_heat(w.eventdata, "GT", "1")[1]["2"]) == 1


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
    # recording: Start + Resume disabled, only Stop enabled
    assert not tp.start_btn.isEnabled() and tp.stop_btn.isEnabled() and not tp.resume_btn.isEnabled()
    clock[0] = 130.0                          # 30 s lap (above the bounce floor)
    tp.record_lap("GT", "1", "1")
    tp.on_stop()
    assert not tp._started
    # stopped: Start + Resume enabled, Stop disabled
    assert tp.start_btn.isEnabled() and not tp.stop_btn.isEnabled() and tp.resume_btn.isEnabled()
    tp.on_resume()
    assert tp._started                        # a start time exists -> resumes
    # recording again: Resume disabled too (owner feedback)
    assert not tp.start_btn.isEnabled() and tp.stop_btn.isEnabled() and not tp.resume_btn.isEnabled()
    assert len(record_heat(w.eventdata, "GT", "1")[1]["1"]) == 1   # prior data kept


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
    rec = record_heat(w2.eventdata, "GT", "1")
    assert rec[1]["1"] == [[1, 20.0], [1, 21.0]] and rec[0]["starttime"] == 1000.0  # replayed
    clock = [1200.0]                          # correct clock: 200 s after start (incl. downtime)
    tp2._wall = lambda: clock[0]
    tp2._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp2.on_resume()
    clock[0] = 1205.0
    tp2.record_lap("GT", "1", "1")
    laps = record_heat(w2.eventdata, "GT", "1")[1]["1"]
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
    laps = record_heat(w2.eventdata, "GT", "1")[1]["1"]
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
    from cozer.native import to_native
    ed = {"classes": [["", "C", "3*(1000+2*1500):2"], ["", "C/T", "1*(1000):1"]]}
    assert heat_course(ed, "C", "1") == heat_course(ed, "C", "1r") == heat_course(ed, "C", "1R")
    assert heat_course(ed, "C", "1")[0] == [1000, 1500, 1500]     # heat 1 lap lengths
    assert heat_course(ed, "C", "2")[0] == [1000, 1500, 1500]     # heat 2
    assert heat_course(ed, "C/T", "1t")[0] == [1000]             # /T time-trial heat -> heat 1
    # same answers on the native model (heat_course reads the pattern via class_pattern) -- it
    # used to index classes as legacy rows and silently return an empty course on native
    nat = to_native(ed)
    assert heat_course(nat, "C", "2")[0] == [1000, 1500, 1500]
    assert heat_course(nat, "C/T", "1t")[0] == [1000]


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


def test_closing_hint_arms_after_first_lap_and_colors_button(tmp_path, monkeypatch):
    # The closing hint predicts the next crossing from the last lap's speed, so it only arms once a
    # boat has crossed the FIRST lap-line -- before that we can't tell it has actually started, so its
    # button must keep its colour (owner). Once armed it colours the button 'coming' -> 'late'.
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
    assert key not in tp._predict                    # no first-lap hint (may not have started yet)
    clock[0] = 1030.0                                # first crossing (30 s lap)
    tp.record_lap("GT", "1", "1")
    assert key in tp._predict                        # now armed off the boat's own lap time
    # simulate the arming timer firing (no Qt event loop in the test)
    tp._on_coming(key, 20.0)
    assert tp._phase[key] == "coming" and tp._boat_color(*key) == C_COMING
    tp._on_late(key)
    assert tp._boat_color(*key) == C_LATE
    tp.on_stop()
    assert not tp._predict and key not in tp._phase   # cancelled on Stop


def test_grid_button_shrinks_and_greys_on_click_restores_on_coming(tmp_path, monkeypatch):
    # owner: a just-clicked grid button shrinks (subtle mis-click guard) AND turns gray (in-progress) --
    # even if it was showing the green "coming" hint at the click; it restores to full size when the
    # boat is next "coming".
    from cozer.app.timer import C_COMING, C_INPROGRESS
    _app()
    w = MainWindow(_timer_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    tp = w.timer_panel
    clock = [1000.0]
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))
    tp.race_combo.setCurrentIndex(0)
    tp.on_start()
    grid = tp._grids[("GT", "1")]
    key = ("GT", "1", "1")
    assert "1" not in grid.pressed                        # full size before any click
    tp._phase[key] = "coming"                             # boat was showing the green closing hint
    assert tp._boat_color(*key) == C_COMING
    clock[0] = 1030.0
    tp.record_lap("GT", "1", "1")
    assert "1" in grid.pressed                            # shrunk right after the crossing
    assert tp._boat_color(*key) == C_INPROGRESS           # ...and gray, not the stale green
    tp._on_coming(key, 20.0)
    assert "1" not in grid.pressed                        # restored when the boat is closing again


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
    # the running-order ladder is also drawn on select (all boats "Ready to Start"), not only after Start
    assert ("GT", "1", "1") in tp._ladder_boats and ("GT", "1", "2") in tp._ladder_boats


def test_timer_ladder_and_grid_boat_colours_match():
    # the ladder + grid buttons for a boat must colour identically; a restyle (e.g. the closing-hint)
    # updates BOTH, not just the grid.
    from cozer.app.timer import C_COMING
    _app()
    tp = MainWindow(_timer_event()).timer_panel
    tp.race_combo.setCurrentIndex(0)                       # draws both the grid and the ladder
    grid_btn = tp._buttons[("GT", "1", "1")]
    ladder_btn = tp._ladder_boats[("GT", "1", "1")]
    tp._phase[("GT", "1", "1")] = "coming"                 # a closing-hint phase
    tp._restyle_boat("GT", "1", "1")
    assert C_COMING in grid_btn.styleSheet() and C_COMING in ladder_btn.styleSheet()


def test_timer_broadcast_builds_off_gui_thread(tmp_path, monkeypatch):
    # issue #20: building the snapshot does `import cozer.app.live`, which pulls in weasyprint --
    # slow the first time, and much slower over a network filesystem (sshfs). So both the build AND
    # the network post must run on a background thread; ticking Broadcast must never do them on the
    # GUI thread (it froze cozer for seconds). Guard: `live.snapshot` runs off the calling thread.
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    import threading
    import cozer.app.crashreport as cr
    import cozer.app.live as live
    _app()
    tp = MainWindow(_timer_event()).timer_panel
    cr.save_config({"live_server_url": "https://live.cozer.ee", "live_publish_secret": "sek"})
    built = {}
    done = threading.Event()

    def snap(*a, **k):
        built["ident"] = threading.get_ident()
        return {"n": 1}
    monkeypatch.setattr(live, "snapshot", snap)
    monkeypatch.setattr(live, "publish_server", lambda *a, **k: done.set() or "e/feed/c")

    tp._publish_order("GT", "1", ["1"])                 # real background thread (not mocked here)
    assert done.wait(5), "the publish worker never ran"
    assert built.get("ident") and built["ident"] != threading.get_ident()   # built off the GUI thread


def test_timer_broadcast_via_server(tmp_path, monkeypatch):
    # With a self-hosted live server configured (live_server_url + live_publish_secret), Broadcast
    # publishes to it -- no GitHub token needed -- and the viewer link points at the server channel.
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    import threading
    import cozer.app.crashreport as cr
    import cozer.app.live as live
    _app()
    tp = MainWindow(_timer_event()).timer_panel

    class _Sync:
        def __init__(self, target=None, daemon=None): self._t = target
        def start(self): self._t()
    monkeypatch.setattr(threading, "Thread", _Sync)
    posts = []
    monkeypatch.setattr(live, "snapshot", lambda *a, **k: {"n": 1})
    monkeypatch.setattr(live, "publish_server",                # (base_url, eventname, channel, secret, snap)
                        lambda url, en, ch, secret, snap: posts.append((url, en, ch, secret)) or "%s/feed/%s" % (en, ch))

    # event name + channel live in the event (.coz); server URL + secret in cozer config
    tp.eventdata["broadcast"] = {"eventname": "0726", "channel": "harku"}
    cr.save_config({"live_server_url": "https://live.cozer.ee", "live_publish_secret": "sek"})
    tp.race_combo.setCurrentIndex(0)
    tp._publishing = False
    tp.broadcast_btn.setChecked(True)                          # no token, but server config -> allowed
    assert tp.broadcast_btn.isChecked()
    assert posts and posts[-1] == ("https://live.cozer.ee", "0726", "harku", "sek")   # published to the server
    assert tp._viewer_url == "https://live.cozer.ee/0726/feed/harku/"           # viewer link -> the feed path
    assert not tp.copy_url_btn.isHidden()


def test_broadcast_settings_persist_and_viewer_url(tmp_path, monkeypatch):
    # The Reports-tab "Live broadcast" section stores the server URL + publish secret in cozer config
    # (persist across restarts) and the event name + channel in the event, slugified. The publish
    # secret must NEVER reach the event (its content is embedded verbatim in bug reports). Saving
    # refreshes the Timer viewer link to the feed path.
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    import json
    import cozer.app.crashreport as cr
    _app()
    w = MainWindow(_timer_event())
    w.live_url_edit.setText("https://live.cozer.ee/")
    w.live_secret_edit.setText("  sek  ")
    w.live_event_edit.setText("Harku 2026")                    # free text -> slugified into the event
    w.live_channel_edit.setText("A")
    w._save_broadcast_settings()
    cfg = cr.load_config()
    assert cfg["live_server_url"] == "https://live.cozer.ee/"                   # stored (rstrip at use)
    assert cfg["live_publish_secret"] == "sek"                                  # trimmed
    assert w.eventdata["broadcast"] == {"eventname": "harku-2026", "channel": "a"}   # slugified, in the event
    assert w.live_event_edit.text() == "harku-2026" and w.live_channel_edit.text() == "a"   # echoed back
    assert "sek" not in json.dumps(w.eventdata)                                 # the secret never in the event
    assert w.timer_panel._viewer_url == "https://live.cozer.ee/harku-2026/feed/a/"   # viewer -> the feed path
    assert not w.timer_panel.copy_url_btn.isHidden()


def test_broadcast_refresh_republishes_on_view_change(tmp_path, monkeypatch):
    # Owner: selecting a race (and start/stop/resume) must re-publish the feed, not only lap crossings.
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    _app()
    w = MainWindow(_timer_event())
    tp = w.timer_panel
    tp.race_combo.setCurrentIndex(0)          # heats populated (fires _show_race)
    tp._broadcast_timer.stop()
    tp.broadcast_btn.setChecked(False)        # broadcasting OFF -> _broadcast_refresh is a no-op
    tp._broadcast_refresh()
    assert not tp._broadcast_timer.isActive()
    # broadcasting ON (set without firing the publish thread) -> a view change re-arms the throttle
    tp.broadcast_btn.blockSignals(True)
    tp.broadcast_btn.setChecked(True)
    tp.broadcast_btn.blockSignals(False)
    tp._broadcast_target = None
    tp._broadcast_refresh()
    assert tp._broadcast_timer.isActive() and tp._broadcast_target == tp._heats[0]


def test_timer_race_combo_popup_fits_labels():
    # issue #22: the Race dropdown must be wide enough to show the full (long, multi-class) race
    # labels rather than eliding them ("Race...00 1"), so the operator can tell races apart.
    _app()
    tp = MainWindow(_timer_event()).timer_panel
    assert tp.race_combo.count() >= 1
    view = tp.race_combo.view()
    fm = view.fontMetrics()
    widest = max(fm.horizontalAdvance(tp.race_combo.itemText(i))
                 for i in range(tp.race_combo.count()))
    assert view.minimumWidth() >= widest        # popup fits the longest label (no elision)


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
    w._autosave_action.setChecked(True)          # auto-save now lives on the File menu (window-wide)
    assert w._autosave is not None
    w._autosave_action.setChecked(False)         # exercise autosave toggle both ways
    assert w._autosave is None


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


def test_nearest_event_mark_and_notes():
    from cozer.app.editor import nearest_event_mark
    from cozer.records import marknote, setmarknote
    # a lap at t=20, a DQ (12) event at t=25, a lap (cum 41), a DQ event at t=50
    marks = [[1, 20.0], [12, 25.0, "313.4"], [1, 21.0], [12, 50.0, "205.1"]]
    assert nearest_event_mark(marks, 26.0) == 1          # nearest event mark is the DQ, not a lap
    assert nearest_event_mark(marks, 49.0) == 3
    assert nearest_event_mark([[1, 20.0], [1, 21.0]], 20.0) is None    # no event marks
    # a note lives in the 4th slot; setmarknote grows a 3-slot mark, clearing empties it
    assert marknote(marks[1]) == ""
    marks[1] = setmarknote(marks[1], "cut the buoy")
    assert marknote(marks[1]) == "cut the buoy" and marks[1] == [12, 25.0, "313.4", "cut the buoy"]
    marks[1] = setmarknote(marks[1], "")
    assert marknote(marks[1]) == ""


def test_suspect_marks_flags_outliers_and_out_of_order():
    # suspect_marks lives in validate (shared detector); editor re-exports it. Returns {idx: (cat, hint)}.
    from cozer.app.editor import suspect_marks
    # clean 6-lap boat: short start leg (3.5s) then ~11s laps -> nothing flagged, incl. the start lap
    clean = [[1, 3.5], [1, 11.0], [1, 10.8], [1, 11.2], [1, 10.9], [1, 11.1]]
    assert suspect_marks(clean, 6) == {}
    # a mid-race double-click (a 0.3s lap among ~11s laps) is flagged as far-shorter (index 3)
    dbl = [[1, 3.5], [1, 11.0], [1, 10.8], [1, 0.3], [1, 11.2], [1, 10.9]]
    s = suspect_marks(dbl, 6)
    assert set(s) == {3} and s[3][0] == "short" and "shorter" in s[3][1]
    # a missed crossing (two laps merged ~24s) is flagged as far-longer (index 2)
    miss = [[1, 3.5], [1, 11.0], [1, 24.0], [1, 11.2], [1, 10.9], [1, 11.1]]
    s = suspect_marks(miss, 6)
    assert set(s) == {2} and s[2][0] == "long" and "longer" in s[2][1]
    # a non-advancing crossing (duration 0) is flagged as an impossible ordering (index 2)
    ooo = [[1, 3.5], [1, 11.0], [1, 0.0], [1, 11.2], [1, 10.9], [1, 11.1]]
    s = suspect_marks(ooo, 6)
    assert set(s) == {2} and s[2][0] == "order" and "advance" in s[2][1]


def test_suspect_marks_ignores_past_finish_disabled_and_short_fields():
    from cozer.app.editor import suspect_marks
    # a spurious extra click past the 5-lap finish (a 0.3s "6th lap") is NOT flagged (issue #26 case)
    extra = [[1, 3.5], [1, 11.0], [1, 10.8], [1, 11.2], [1, 10.9], [1, 0.3]]
    assert suspect_marks(extra, 5) == {}
    # a disabled lap is never flagged; its time rolls into the next enabled lap
    dis = [[1, 3.5], [1, 11.0], [-1, 0.3], [1, 10.8], [1, 11.2], [1, 10.9]]
    assert suspect_marks(dis, 6) == {}
    # too few laps for a reliable median -> no outlier flag (avoids false positives on tiny fields)
    short = [[1, 3.5], [1, 0.3], [1, 11.0]]
    assert suspect_marks(short, 3) == {}


def test_timeline_widget_stores_suspects_and_blinks():
    _app()
    from cozer.app.editor import TimelineWidget
    tw = TimelineWidget(None)
    rows = [("1", "", [[1, 3.5], [1, 11.0], [1, 0.3], [1, 11.2], [1, 10.9], [1, 11.1]])]
    tw.set_data(rows, 40.0, 40.0, 5.0, [{2: ("short", "double-click")}])
    assert tw._suspects == [{2: ("short", "double-click")}]
    assert tw._blink_timer.isActive()              # blinking because a mark is flagged
    tw.set_data(rows, 40.0, 40.0, 5.0, [{}])       # nothing flagged -> stop wasting repaints
    assert not tw._blink_timer.isActive()


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
    rec = record_heat(w.eventdata, "GT", "1")                     # the stored (committed) record
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
    from cozer import store as _store                          # load via the real path (native on disk)
    saved = _store.load_event(open(str(tmp_path / "e.cozj"), encoding="utf-8").read())
    assert record_heat(saved, "GT", "1")[0]["racetime"] == 88.0    # durably snapshotted


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
    # rule items carry the UIM article in the label (issue #33): "313.4 — Disqualification"
    rule_labels = [aa.text() for a in menu.actions() if a.menu() for aa in a.menu().actions()]
    assert any("313.4" in t and "Disqualification" in t for t in rule_labels)
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


def test_edit_note_sets_and_reads_on_nearest_event_mark(tmp_path, monkeypatch):
    _app()
    from cozer.records import marknote
    w = MainWindow(_recorded_event())
    _save_as(w, str(tmp_path / "e.cozj"), monkeypatch)
    ep = w.editor_panel
    ep.reload()
    ep.insert_rule_mark("GT", "1", "1", 12, 25.0, "313.4")     # DQ mark, article 313.4
    # context reflects the nearest event mark + its rule text + the participant (issue #33)
    info = ep.note_context("GT", "1", "1", 26.0)
    assert info is not None
    _idx, code_name, article, note, ruletext, phase, name, nat = info
    assert code_name == "DQ" and article == "313.4" and note == ""
    assert ruletext == "Disqualification" and "One" in name and nat == "EST"
    # set a note on the nearest event mark, read it back from the draft
    assert ep.set_note_at("GT", "1", "1", 26.0, "cut the buoy") is True
    dq = next(m for m in ep._draft[1]["1"] if abs(m[0]) == 12)
    assert marknote(dq) == "cut the buoy" and ep._dirty is True
    # boat 2 has no event mark -> no context, nothing to set
    assert ep.note_context("GT", "1", "2", 10.0) is None
    assert ep.set_note_at("GT", "1", "2", 10.0, "x") is False


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
    orig = record_heat(w.eventdata, "GT", "1")[0]["racetime"]
    ep.commit_racetime(555.0)
    assert ep._dirty is True
    ep._ask_unsaved = lambda: "discard"                        # user chooses Discard
    assert ep.maybe_flush() is True
    assert ep._dirty is False
    ep.refresh()                                               # reloads a fresh draft
    assert ep._draft[0]["racetime"] == orig                    # edit reverted
    assert record_heat(w.eventdata, "GT", "1")[0]["racetime"] == orig


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
    assert record_heat(w.eventdata, "GT", "1")[0]["racetime"] == 777.0


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


def test_render_report_permission_error_is_friendly(tmp_path, monkeypatch):
    # a locked/read-only report file (the PDF still open in a viewer, or a OneDrive folder) gets a
    # clear "close it and retry" message and is NOT filed as a crash (it's the environment, not a bug).
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    import cozer.reports as R
    _app()
    w = MainWindow(_timer_event())
    monkeypatch.setattr(R, "render_participants",
                        lambda *a, **k: (_ for _ in ()).throw(PermissionError(13, "denied")))
    warned = {}
    monkeypatch.setattr(appmain.QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warned.update(text=a[2]) or appmain.QMessageBox.Ok))
    reported = {"n": 0}
    monkeypatch.setattr(appmain, "report_exception",
                        lambda *a, **k: reported.update(n=reported["n"] + 1) or (None, None))
    ok = w._render_report("Participants", "render_participants", False, False, False,
                          str(tmp_path / "participants.pdf"))
    assert ok is False
    assert "open in another program" in warned.get("text", "")   # friendly guidance shown
    assert reported["n"] == 0                                     # NOT crash-reported


def test_menu_corner_reflects_signin_state(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    import cozer.app.crashreport as cr
    w = MainWindow(_timer_event())
    w._refresh_auth_corner()
    assert "Sign in to GitHub" in w._auth_btn.text()         # signed out -> offer sign-in
    cr.save_config({"token": "gho_x", "login": "pearu"})
    w._refresh_auth_corner()
    assert "Signed in as pearu" in w._auth_btn.text()        # signed in -> show who
    w._on_auth_toggle()                                      # the one button toggles -> sign out
    assert cr.load_config().get("token") is None             # sign-out clears the token
    w._refresh_auth_corner()
    assert "Sign in to GitHub" in w._auth_btn.text()         # back to signed-out label
    # the Help menu now carries genuine help actions (rulebook + About), not the account controls
    htexts = [a.text() for a in w._help_menu.actions() if a.text()]
    assert any("Circuit Rules" in t for t in htexts) and any("About" in t for t in htexts)
    assert not any("Sign in" in t or "Signed in" in t for t in htexts)


def test_check_for_updates_menu_and_handler(monkeypatch):
    # Help ▸ Check for updates: the action exists and the handler reports each state without error.
    _app()
    w = MainWindow()
    htexts = [a.text() for a in w._help_menu.actions() if a.text()]
    assert any("Check for" in t and "update" in t.lower() for t in htexts)
    import cozer.app.update as upd
    seen = {}
    monkeypatch.setattr(appmain.QMessageBox, "information",
                        staticmethod(lambda parent, title, text, *a, **k: seen.__setitem__("text", text)))
    monkeypatch.setattr(upd, "check", lambda *a, **k: {
        "current": "3.0.0", "kind": "wheel", "latest": {"tag": "v3.0.0"}, "available": False})
    w._on_check_updates()
    assert "up to date" in seen["text"]                                    # up-to-date path
    monkeypatch.setattr(upd, "check", lambda *a, **k: {
        "current": "3.0.0", "kind": "wheel", "latest": None, "available": False})
    w._on_check_updates()
    assert "offline" in seen["text"]                                       # couldn't-check / offline path
    monkeypatch.setattr(appmain.QMessageBox, "exec", lambda self: 0)       # available path -> must not raise
    monkeypatch.setattr(upd, "check", lambda *a, **k: {
        "current": "3.0.0rc1", "kind": "windows-installer", "available": True,
        "latest": {"tag": "v3.0.0", "name": "cozer v3.0.0", "notes": "notes", "url": "https://x", "assets": []}})
    w._on_check_updates()


def test_apply_update_dispatches_by_install_kind(monkeypatch):
    # Phase 2: _apply_update routes to the right action -- installer opens the .exe download, pip
    # runs the wheel update, a source checkout is informational only.
    _app()
    w = MainWindow()
    import cozer.app.update as upd
    opened, ran = {}, {}
    monkeypatch.setattr(appmain, "open_in_viewer", lambda u: opened.__setitem__("url", u))
    monkeypatch.setattr(appmain.QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(appmain.QMessageBox, "question", staticmethod(lambda *a, **k: appmain.QMessageBox.Yes))
    monkeypatch.setattr(w, "_run_pip_update", lambda url, release_url=None: ran.__setitem__("url", url))
    res = {"current": "3.0.0", "kind": "x", "latest": {"url": "https://rel"}, "available": True}
    monkeypatch.setattr(upd, "recommend", lambda r: {"action": "installer", "url": "https://dl/x.exe", "hint": "x.exe"})
    w._apply_update(res)
    assert opened.get("url") == "https://dl/x.exe"                  # installer -> browser download
    monkeypatch.setattr(upd, "recommend", lambda r: {"action": "pip", "url": "https://dl/x.whl", "hint": "x.whl"})
    w._apply_update(res)
    assert ran.get("url") == "https://dl/x.whl"                     # pip -> wheel update
    opened.clear(); ran.clear()
    monkeypatch.setattr(upd, "recommend", lambda r: {"action": "source", "url": None, "hint": ""})
    w._apply_update(res)
    assert not opened and not ran                                  # source -> informational only


def test_startup_update_check(monkeypatch):
    # Phase 3: the startup check runs once, in the background (no blocking), and notes an available
    # update unobtrusively via the Log; it is silent when up to date / offline, and it never runs
    # under tests (COZER_NO_UPDATE_CHECK, set by conftest).
    _app()
    w = MainWindow()
    logs = []
    monkeypatch.setattr(w, "log", logs.append)
    w._on_update_check_result({"available": True, "latest": {"name": "cozer v9.9.9", "tag": "v9.9.9"}})
    assert logs and "available" in logs[-1] and "v9.9.9" in logs[-1]     # noted in the Log
    logs.clear()
    w._on_update_check_result({"available": False, "latest": {"tag": "v1"}})
    w._on_update_check_result(None)                                     # offline -> None
    assert not logs                                                    # silent when up-to-date/offline
    # the env guard skips the network check entirely under the suite
    import cozer.app.update as upd
    called = []
    monkeypatch.setattr(upd, "check", lambda *a, **k: called.append(1))
    w._start_update_check()
    assert not called
    # with the guard cleared, the background worker does call update.check (run the thread inline)
    monkeypatch.delenv("COZER_NO_UPDATE_CHECK", raising=False)
    import threading

    class _Sync:
        def __init__(self, target=None, daemon=None):
            self._t = target

        def start(self):
            self._t()
    monkeypatch.setattr(threading, "Thread", _Sync)
    monkeypatch.setattr(upd, "check", lambda *a, **k: called.append("ran") or {"available": False, "latest": None})
    w._start_update_check()
    assert called == ["ran"]


def test_report_bug_queues_when_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    import cozer.app.crashreport as cr
    w = MainWindow(_timer_event())
    url = appmain.report_bug(w, "the timer button did nothing")
    assert url is None and len(cr.list_pending()) == 1     # queued until signed in


def test_bug_report_screenshot_saved_and_referenced(tmp_path, monkeypatch):
    # A GUI snapshot is saved next to the local report and referenced (by basename only — no
    # local path leaked into the public issue body).
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    import cozer.app.crashreport as cr
    png = b"\x89PNG\r\n\x1a\n\x00fake-image-bytes"
    rep = cr.build_user_report("GUI glitch", eventdata={})
    cr.write_local(rep, screenshot=png)
    shot = rep["screenshot"]
    assert shot.endswith(".png") and open(shot, "rb").read() == png     # PNG written to disk
    body = cr.report_body(rep)
    assert os.path.basename(shot) in body and shot not in body         # referenced, path not leaked


def test_report_bug_screenshot_checkbox_gates_attachment(tmp_path, monkeypatch):
    # The dialog's opt-in checkbox decides whether a screenshot is captured (default off): only
    # when checked does _on_report_bug grab the window and forward the PNG to report_bug.
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    _app()
    w = MainWindow(_timer_event())
    assert w._grab_png()[:8] == b"\x89PNG\r\n\x1a\n"        # grabs a real PNG of the window
    sent = {}
    monkeypatch.setattr(appmain, "report_bug",
                        lambda win, text, screenshot=None: sent.update(t=text, s=screenshot))
    monkeypatch.setattr(w, "_bug_dialog", lambda: ("no screenshot please", False))
    w._on_report_bug()
    assert sent["s"] is None                               # unchecked -> no screenshot
    monkeypatch.setattr(w, "_bug_dialog", lambda: ("attach one", True))
    w._on_report_bug()
    assert sent["s"][:8] == b"\x89PNG\r\n\x1a\n"            # checked -> PNG forwarded


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
    assert m.columnCount() == 6                         # 5 base columns + qheat1
    qcol = m.columnCount() - 1                           # qheat1 is the trailing column
    assert m.headerData(qcol, Qt.Horizontal, Qt.DisplayRole) == "qheat1"
    assert m.headerData(qcol, Qt.Horizontal, Qt.ToolTipRole)  # tooltip present
    idx = m.index(0, m.columnCount() - 1)               # the trailing qheat1 checkbox column
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
    assert m.columnCount() == 5                         # no qheat1 column (5 base cols)


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
    assert cw.model.columnCount() == 6                  # 5 base cols + qheat1 (F 500 has a /Q phase)


def test_sync_phase_writes_and_removes_phases():
    _app()
    from cozer.native import to_native
    from cozer.app.classpart import phase_pattern
    ed = to_native({"kind": "event", "title": "P", "scoringsystem": [400, 300, 225], "rules": [],
                    "classes": [["", "F 500", "4*(1400):3"]], "participants": [], "races": []})
    cp = MainWindow(ed).classpart_panel
    cp._sync_phase("F 500", "timetrial", "1*(1000):1")
    cp._sync_phase("F 500", "qualification", "3*(1000):1!qualification[4,4,4]")
    assert phase_pattern(ed, "F 500", "timetrial") == "1*(1000):1"        # phases authored natively
    assert phase_pattern(ed, "F 500", "qualification") == "3*(1000):1!qualification[4,4,4]"
    assert all(c["name"] == "F 500" for c in ed["classes"])              # no /T,/Q suffixes stored
    cp._sync_phase("F 500", "timetrial", "")                             # disabling removes it (no race uses it)
    assert phase_pattern(ed, "F 500", "timetrial") is None


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
