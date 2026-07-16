"""cozer main window (PySide6).

Phase 5a: file handling backed by the crash-safe store (open legacy .coz /
new-format .cozj, atomic save), the event-information form, and a Reports tab
that renders any of the 9 reports to PDF and opens it in the OS viewer.

Data-entry grids (classes/participants/races/rules), the live Timer, and the
graphical record editor land in subsequent Phase-5 passes.
"""
import copy
import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from cozer import reports as R
from cozer.app import crashreport
from cozer.app.editor import EditRecordsPanel
from cozer.app.grids import GridTab, RacesTab, parse_scoring
from cozer.app.timer import TimerPanel
from cozer.racepattern import get_classes
from cozer.store import EventStore, read_legacy_coz

# App-wide light color scheme; editable inputs get the legacy tan tint (edit_bg).
APP_QSS = (
    "QMainWindow, QWidget { background: #f4f3ee; }"
    " QLineEdit, QTableView, QListWidget { background: #fbf7e6; }"
    " QHeaderView::section { background: #e6e2d3; padding: 3px; border: 0; }"
    " QPushButton { padding: 4px 10px; }"
    " QGroupBox { font-weight: bold; margin-top: 6px; }"
    " QTabBar::tab { padding: 5px 12px; }"
)

DEFAULT_EVENT = {
    "title": "", "venue": "", "date": "", "officer": "", "secretary": "",
    "scoringsystem": [], "classes": [], "participants": [], "races": [],
    "rules": [], "record": {}, "configure": {"language": "English"},
}

_EVENT_FIELDS = [("title", "Title"), ("venue", "Venue"), ("date", "Date"),
                 ("officer", "Officer of the Day"), ("secretary", "Secretary General")]

# (label, render function, accepts a class selection)
_REPORTS = [
    ("Participants", R.render_participants, True),
    ("Intermediate", R.render_intermediate, True),
    ("Full Final", R.render_full_final, True),
    ("Short Final", R.render_short_final, True),
    ("Endurance Full Final", R.render_endurance_final, True),
    ("Check List", R.render_checklist, True),
    ("Laps Protocol", R.render_laps_protocol, True),
    ("Info Letter", R.render_info_letter, False),
    ("Registration Letter", R.render_registration_letter, False),
]


def open_in_viewer(path):
    """Open a file with the OS default application."""
    if sys.platform.startswith("win"):        # pragma: no cover - platform-specific
        os.startfile(path)
    elif sys.platform == "darwin":            # pragma: no cover - platform-specific
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def report_exception(window, exc_type, exc, tb, action=None):
    """Capture an unhandled error: write a local crash report and auto-submit if
    logged in (else queue). Returns (report, issue_url). Never raises."""
    try:
        store = getattr(window, "store", None)
        path = store.path if store is not None else None
        if action is None and getattr(window, "tabs", None) is not None:
            action = window.tabs.tabText(window.tabs.currentIndex())
        report = crashreport.build_report(exc_type, exc, tb, action=action, event_path=path,
                                          eventdata=getattr(window, "eventdata", None))
        reporter = crashreport.Reporter()
        url = reporter.handle(report, event_path=path)
        reporter.submit_pending()          # opportunistically drain earlier offline reports
        return report, url
    except Exception:      # pragma: no cover - reporting must never itself crash the app
        return None, None


def _install_excepthook(window):     # pragma: no cover - process-global; needs the GUI loop
    prev = sys.excepthook

    def hook(exc_type, exc, tb):
        _report, url = report_exception(window, exc_type, exc, tb)
        try:
            QMessageBox.critical(window, "cozer error",
                                 "An error occurred and was recorded locally%s.\n\n%s: %s"
                                 % (" and reported" if url else "",
                                    getattr(exc_type, "__name__", "Error"), exc))
        except Exception:
            pass
        prev(exc_type, exc, tb)

    sys.excepthook = hook


class MainWindow(QMainWindow):
    def __init__(self, eventdata=None):
        super().__init__()
        self.store = None
        self.eventdata = eventdata if eventdata is not None else copy.deepcopy(DEFAULT_EVENT)
        self.resize(980, 640)
        self.setStyleSheet(APP_QSS)
        self._build_menu()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_geninfo_tab(), "General Information")
        self.timer_panel = TimerPanel(self)
        self.tabs.addTab(self.timer_panel, "Timer")
        self.editor_panel = EditRecordsPanel(self)
        self.tabs.addTab(self.editor_panel, "Edit Records")
        self.tabs.addTab(self._build_reports_tab(), "Reports")
        self.tabs.addTab(self._build_log_tab(), "Log")
        self._reload_forms()
        self._refresh_title()
        self.log("Ready")

    # ---- menu / file operations ----
    def _build_menu(self):
        m = self.menuBar().addMenu("&File")
        for text, slot in [("&New", self.on_new), ("&Open…", self.on_open),
                           ("&Import legacy .coz…", self.on_import), (None, None),
                           ("&Save", self.on_save), ("Save &As…", self.on_save_as),
                           (None, None), ("&Quit", self.close)]:
            if text is None:
                m.addSeparator()
            else:
                m.addAction(text, slot)

    def on_new(self):
        self.eventdata = copy.deepcopy(DEFAULT_EVENT)
        self.store = None
        self._reload_forms()
        self._refresh_title()
        self.log("New event")

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open event", "", "Cozer events (*.cozj *.coz)")
        if path:
            self.load(path)

    def load(self, path):
        if path.endswith(".coz"):
            # Open a legacy file as an editable new-format working copy beside it, so
            # edits journal immediately (no Save-As prompt). The original .coz is left
            # untouched; an existing .cozj working copy is continued, never clobbered.
            cozj = os.path.splitext(path)[0] + ".cozj"
            if os.path.exists(cozj):
                self.store = EventStore.open(cozj, default=copy.deepcopy(DEFAULT_EVENT))
                self.eventdata = self.store.eventdata
                msg = "Opened %s — continuing working copy %s" % (path, cozj)
            else:
                self.eventdata = read_legacy_coz(path)
                self.store = EventStore(cozj, self.eventdata)
                self.store.snapshot()
                msg = "Opened %s — auto-saving to %s" % (path, cozj)
        else:
            self.store = EventStore.open(path, default=copy.deepcopy(DEFAULT_EVENT))
            self.eventdata = self.store.eventdata
            msg = "Opened %s" % path
        self._reload_forms()
        self._refresh_title()
        self.log(msg)

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import legacy .coz", "", "Legacy events (*.coz)")
        if path:
            self.eventdata = read_legacy_coz(path)
            self.store = None
            self._reload_forms()
            self._refresh_title()
            self.log("Imported %s — Save As to persist as .cozj" % path)

    def on_save(self):
        if self.store is None:
            return self.on_save_as()
        self.store.eventdata = self.eventdata
        self.store.snapshot()
        self.log("Saved %s" % self.store.path)

    def on_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save event as", "", "Cozer events (*.cozj)")
        if not path:
            return
        if not path.endswith(".cozj"):
            path += ".cozj"
        self.store = EventStore(path, self.eventdata)
        self.store.snapshot()
        self._refresh_title()
        self.log("Saved %s" % path)

    # ---- general information tab (event fields + data grids) ----
    def _build_geninfo_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)

        form_w = QWidget()
        form = QFormLayout(form_w)
        self._fields = {}
        for key, label in _EVENT_FIELDS:
            edit = QLineEdit()
            edit.textChanged.connect(lambda text, k=key: self.eventdata.__setitem__(k, text))
            self._fields[key] = edit
            form.addRow(label + ":", edit)
        v.addWidget(form_w)

        sub = QTabWidget()
        self.classes_grid = GridTab([(1, "Class"), (2, "Race pattern")], 3)
        self.participants_grid = GridTab(
            [(1, "Name"), (2, "Surname"), (3, "From"), (4, "Class"), (5, "Id")], 6)
        self.races_tab = RacesTab()

        rules_w = QWidget()
        rv = QVBoxLayout(rules_w)
        srow = QHBoxLayout()
        srow.addWidget(QLabel("Scoring system:"))
        self.scoring_edit = QLineEdit()
        self.scoring_edit.textChanged.connect(
            lambda text: self.eventdata.__setitem__("scoringsystem", parse_scoring(text)))
        srow.addWidget(self.scoring_edit)
        rv.addLayout(srow)
        self.rules_grid = GridTab([(1, "Action"), (2, "Paragraph"), (3, "Description")], 4)
        rv.addWidget(self.rules_grid)

        sub.addTab(self.classes_grid, "Classes")
        sub.addTab(self.participants_grid, "Participants")
        sub.addTab(self.races_tab, "Races")
        sub.addTab(rules_w, "Rules")
        v.addWidget(sub)
        return w

    def _ensure_keys(self):
        for key in ("classes", "participants", "races", "rules", "scoringsystem"):
            self.eventdata.setdefault(key, [])

    def _reload_forms(self):
        self._ensure_keys()
        for key, _ in _EVENT_FIELDS:
            self._fields[key].setText(str(self.eventdata.get(key, "")))
        self.classes_grid.set_data(self.eventdata["classes"])
        self.participants_grid.set_data(self.eventdata["participants"])
        self.races_tab.set_data(self.eventdata["races"])
        self.rules_grid.set_data(self.eventdata["rules"])
        self.scoring_edit.setText(" ".join(str(x) for x in self.eventdata["scoringsystem"]))
        self._reload_classes()
        self.timer_panel.reload()
        self.editor_panel.reload()

    # ---- log tab ----
    def _build_log_tab(self):
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        return self.log_view

    def log(self, msg):
        self.log_view.appendPlainText(msg)
        self.statusBar().showMessage(msg)

    # ---- reports tab ----
    def _build_reports_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("Report:"))
        self.report_combo = QComboBox()
        for label, _f, _t in _REPORTS:
            self.report_combo.addItem(label)
        row.addWidget(self.report_combo)
        gen = QPushButton("Generate PDF…")
        gen.clicked.connect(self.on_generate)
        row.addWidget(gen)
        row.addStretch()
        v.addLayout(row)
        v.addWidget(QLabel("Classes (none checked = all):"))
        self.class_list = QListWidget()
        v.addWidget(self.class_list)
        return w

    def _reload_classes(self):
        self.class_list.clear()
        for cl in get_classes(self.eventdata):
            item = QListWidgetItem(cl)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.class_list.addItem(item)

    def selected_classes(self):
        sel = [self.class_list.item(i).text() for i in range(self.class_list.count())
               if self.class_list.item(i).checkState() == Qt.Checked]
        return sel or None

    def on_generate(self):
        label, func, takes = _REPORTS[self.report_combo.currentIndex()]
        default = label.lower().replace(" ", "_") + ".pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save report PDF", default, "PDF (*.pdf)")
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        try:
            if takes:
                func(self.eventdata, path, classes=self.selected_classes())
            else:
                func(self.eventdata, path)
        except Exception as e:      # pragma: no cover - surfaced to the user, never crashes
            QMessageBox.critical(self, "Report error", "%s: %s" % (type(e).__name__, e))
            return
        self.log("Wrote %s" % path)
        open_in_viewer(path)

    def _refresh_title(self):
        self.setWindowTitle("COZER — %s" % (self.store.path if self.store else "(unsaved)"))


def run(argv=None):     # pragma: no cover - launches the Qt event loop
    argv = list(argv) if argv is not None else sys.argv[1:]
    app = QApplication.instance() or QApplication([sys.argv[0]] + argv)
    win = MainWindow()
    _install_excepthook(win)
    files = [a for a in argv if not a.startswith("-") and os.path.exists(a)]
    if files:
        win.load(files[0])
    win.show()
    return app.exec()
