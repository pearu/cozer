"""cozer main window (PySide6).

Phase 5a: file handling backed by the crash-safe store (open legacy .coz /
new-format .cozj, atomic save), the event-information form, and a Reports tab
that renders any of the 9 reports to PDF and opens it in the OS viewer.

Data-entry grids (classes/participants/races/rules), the live Timer, and the
graphical record editor land in subsequent Phase-5 passes.
"""
import copy
import os
import signal
import subprocess
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

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
    # menus: define selected-item colors explicitly, else the broad QWidget
    # background above leaves highlighted menu text invisible.
    " QMenu { background: #f4f3ee; color: #1a1a1a; }"
    " QMenu::item:selected { background: #2b3a67; color: #ffffff; }"
    " QMenuBar::item:selected { background: #2b3a67; color: #ffffff; }"
)

DEFAULT_EVENT = {
    "title": "", "venue": "", "date": "", "officer": "", "secretary": "",
    "scoringsystem": [], "classes": [], "participants": [], "races": [],
    "rules": [], "record": {}, "configure": {"language": "English"},
}

_EVENT_FIELDS = [("title", "Title"), ("venue", "Venue"), ("date", "Date"),
                 ("officer", "Officer of the Day"), ("secretary", "Secretary General")]

# (label, cozer.reports function name, accepts a class selection). Resolved lazily in
# on_generate so importing this module doesn't pull in weasyprint (a slow import).
_REPORTS = [
    ("Participants", "render_participants", True),
    ("Intermediate", "render_intermediate", True),
    ("Full Final", "render_full_final", True),
    ("Short Final", "render_short_final", True),
    ("Endurance Full Final", "render_endurance_final", True),
    ("Check List", "render_checklist", True),
    ("Laps Protocol", "render_laps_protocol", True),
    ("Info Letter", "render_info_letter", False),
    ("Registration Letter", "render_registration_letter", False),
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
    if exc_type is not None and issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        return None, None      # normal termination (Ctrl+C / quit), not a crash
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


def report_bug(window, description):
    """File a user-initiated bug report (submits if signed in, else queues). Returns
    the issue URL if filed, else None."""
    store = getattr(window, "store", None)
    path = store.path if store is not None else None
    report = crashreport.build_user_report(description, event_path=path,
                                            eventdata=getattr(window, "eventdata", None))
    return crashreport.Reporter().handle(report, event_path=path)


class SignInDialog(QDialog):     # pragma: no cover - modal dialog + network polling
    """GitHub device-flow login: shows the user code and polls until authorized."""

    def __init__(self, parent, cid, transport=None):
        super().__init__(parent)
        self.setWindowTitle("Sign in to GitHub")
        self._cid = cid
        self._transport = transport
        self.token = None
        start = crashreport.device_start(cid, transport=transport)
        self._device_code = start["device_code"]
        self._uri = start.get("verification_uri", "https://github.com/login/device")
        v = QVBoxLayout(self)
        v.addWidget(QLabel("1.  Open  %s" % self._uri))
        v.addWidget(QLabel("2.  Enter this one-time code:"))
        self._code = start.get("user_code", "")
        self._wlog("GitHub sign-in: approve code %s at %s" % (self._code, self._uri))
        code_edit = QLineEdit(self._code)
        code_edit.setReadOnly(True)                 # selectable + copyable, not editable
        code_edit.setAlignment(Qt.AlignCenter)
        code_edit.setStyleSheet("font-size: 22px; font-weight: bold; letter-spacing: 4px;")
        v.addWidget(code_edit)
        row = QHBoxLayout()
        openb = QPushButton("Open GitHub in browser")
        openb.clicked.connect(lambda: __import__("webbrowser").open(self._uri))
        copyb = QPushButton("Copy code")
        copyb.clicked.connect(lambda: QApplication.clipboard().setText(self._code))
        check = QPushButton("Check now")
        check.clicked.connect(self._poll)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        for b in (openb, copyb, check, cancel):
            row.addWidget(b)
        v.addLayout(row)
        self._status = QLabel("After you approve in the browser this continues automatically "
                              "— or click ‘Check now’.")
        v.addWidget(self._status)
        self._interval = max(1, int(start.get("interval", 5)))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(self._interval * 1000)

    def _wlog(self, msg):
        p = self.parent()
        if p is not None and hasattr(p, "log"):
            p.log(msg)

    def _poll(self):
        try:
            js = crashreport.device_poll_once(self._cid, self._device_code, transport=self._transport)
        except Exception as e:
            self._status.setText("Network error (will retry): %s" % e)
            self._wlog("sign-in poll network error: %s" % e)
            return
        err = js.get("error")
        if js.get("access_token"):
            self.token = js["access_token"]
            self._timer.stop()
            self._wlog("sign-in: token received")
            self.accept()
        elif err == "slow_down":
            self._interval += int(js.get("interval", 5))
            self._timer.start(self._interval * 1000)
            self._wlog("sign-in: slow_down -> backing off to %ds" % self._interval)
            self._status.setText("Waiting… (GitHub asked to slow down)")
        elif err in ("authorization_pending", None):
            self._status.setText("Waiting for you to approve in the browser…")
        else:
            self._timer.stop()
            self._wlog("sign-in failed: %s" % err)
            self._status.setText("Sign-in failed: %s" % err)


def _install_excepthook(window):     # pragma: no cover - process-global; needs the GUI loop
    prev = sys.excepthook

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return prev(exc_type, exc, tb)      # normal termination, not a crash
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
        self._help_menu = self.menuBar().addMenu("&Help")
        self._help_menu.aboutToShow.connect(self._refresh_help_menu)
        self._refresh_help_menu()

    def _refresh_help_menu(self):
        """Reflect GitHub sign-in state: show who is signed in + offer sign-out,
        otherwise offer sign-in."""
        self._help_menu.clear()
        cfg = crashreport.load_config()
        if cfg.get("token"):
            who = cfg.get("login") or "GitHub"
            act = self._help_menu.addAction("Signed in to GitHub as %s" % who)
            act.setEnabled(False)
            self._help_menu.addAction("Sign &out of GitHub", self._on_signout)
        else:
            self._help_menu.addAction("&Sign in to GitHub…", self._on_signin)
        self._help_menu.addAction("&Report a bug…", self._on_report_bug)

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

    # ---- Help: GitHub sign-in & bug reports ----
    def _on_signin(self):     # pragma: no cover - modal dialog + network
        try:
            dlg = SignInDialog(self, crashreport.client_id())
        except Exception as e:
            QMessageBox.warning(self, "Sign in", "Could not reach GitHub:\n%s" % e)
            return
        if dlg.exec() and dlg.token:
            cfg = crashreport.load_config()
            cfg["token"] = dlg.token
            try:
                cfg["login"] = crashreport.github_login(dlg.token)
            except Exception:
                cfg["login"] = None
            crashreport.save_config(cfg)
            n = len(crashreport.Reporter(config=cfg).submit_pending())
            self.log("Signed in to GitHub%s — submitted %d queued report(s)."
                     % (" as %s" % cfg["login"] if cfg.get("login") else "", n))
        else:
            self.log("GitHub sign-in cancelled")

    def _on_signout(self):
        cfg = crashreport.load_config()
        cfg["token"] = None
        cfg["login"] = None
        crashreport.save_config(cfg)
        self.log("Signed out of GitHub")

    def _on_report_bug(self):     # pragma: no cover - modal input dialog
        text, ok = QInputDialog.getMultiLineText(
            self, "Report a bug",
            "Describe what happened. The current event is attached so it can be reproduced:")
        if ok and text.strip():
            url = report_bug(self, text)
            self.log("Bug report %s" % ("filed: %s" % url if url
                                        else "saved locally — will submit when you sign in"))

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
        label, funcname, takes = _REPORTS[self.report_combo.currentIndex()]
        default = label.lower().replace(" ", "_") + ".pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Save report PDF", default, "PDF (*.pdf)")
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        try:
            import cozer.reports as R
            func = getattr(R, funcname)
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


def run(argv=None, app=None):     # pragma: no cover - launches the Qt event loop
    argv = list(argv) if argv is not None else sys.argv[1:]
    if app is None:
        app = QApplication.instance() or QApplication([sys.argv[0]] + argv)
    win = MainWindow()
    _install_excepthook(win)
    files = [a for a in argv if not a.startswith("-") and os.path.exists(a)]
    if files:
        win.load(files[0])
    win.show()
    # Ctrl+C on the terminal should behave like File -> Quit (a clean close).
    # A signal handler alone won't fire while Qt's C++ event loop is blocked, so a
    # small heartbeat timer periodically returns control to the Python interpreter.
    signal.signal(signal.SIGINT, lambda *_: win.close())
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start(200)
    win._heartbeat = heartbeat
    return app.exec()
