"""cozer main window (PySide6).

Phase 5a: file handling backed by the crash-safe store (open legacy .coz /
new-format .cozj, atomic save), the event-information form, and a Reports tab
that renders any of the 9 reports to PDF and opens it in the OS viewer.

Data-entry grids (classes/participants/races/rules), the live Timer, and the
graphical record editor land in subsequent Phase-5 passes.
"""
import copy
import os
import shutil
import signal
import subprocess
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from cozer.app import crashreport
from cozer.app import ruleset as rulesetmod
from cozer.app.classpart import ClassesParticipantsPanel
from cozer.app.editor import EditRecordsPanel
from cozer.app.grids import (
    GridTab, RacesTab, StringListEditor, parse_scoring, validate_rule_cell,
)
from cozer.app.timer import TimerPanel
from cozer.phases import class_phase_map, phase_heat_ids
from cozer.racepattern import get_classes
from cozer.native import to_native
from cozer.store import EventStore, load_event, read_legacy_coz
from cozer import validate

# App-wide light color scheme; editable inputs get the legacy tan tint (edit_bg).
APP_QSS = (
    "QMainWindow, QWidget { background: #f4f3ee; }"
    " QLineEdit, QTableView, QListWidget { background: #fbf7e6; }"
    " QHeaderView::section { background: #e6e2d3; padding: 3px; border: 0; }"
    " QPushButton { padding: 4px 10px; }"
    " QGroupBox { font-weight: bold; margin-top: 6px; }"
    " QTabBar::tab { padding: 5px 12px; }"
    # menus & combo-box dropdowns: define selected/highlighted colors explicitly, else the broad
    # QWidget background above leaves highlighted text invisible (a hovered item became unreadable).
    " QMenu { background: #f4f3ee; color: #1a1a1a; }"
    " QMenu::item:selected { background: #2b3a67; color: #ffffff; }"
    " QMenuBar::item:selected { background: #2b3a67; color: #ffffff; }"
    " QComboBox QAbstractItemView { background: #fbf7e6; color: #1a1a1a;"
    " selection-background-color: #2b3a67; selection-color: #ffffff; }"
)

DEFAULT_EVENT = {
    "title": "", "venue": "", "date": "", "officer": "", "secretary": "",
    "kind": "event", "scoringsystem": [], "classnames": [], "classes": [],
    "participants": [], "races": [], "rules": [], "record": {},
    "configure": {"language": "English"}, "schema": 2,   # new events are suffix-free native
}

_EVENT_FIELDS = [("title", "Title"), ("venue", "Venue"), ("date", "Date"),
                 ("officer", "Officer of the Day"), ("secretary", "Secretary General")]

# (label, render function, takes classes=, takes heat_map=). Resolved lazily in
# the report handlers so importing this module doesn't pull in weasyprint (slow).
_REPORTS = [
    ("Participants", "render_participants", True, False),
    ("Intermediate", "render_intermediate", True, True),
    ("Full Final", "render_full_final", True, True),
    ("Short Final", "render_short_final", True, True),
    ("Full Final (legacy)", "render_full_final_legacy", True, True),
    ("Short Final (legacy)", "render_short_final_legacy", True, True),
    ("Endurance Full Final", "render_endurance_final", True, True),
    ("Check List", "render_checklist", True, False),
    ("Laps Protocol", "render_laps_protocol", True, True),
    ("Info Letter", "render_info_letter", False, False),
    ("Registration Letter", "render_registration_letter", False, False),
]


def _system_child_env():
    """Environment for launching a *system* helper program (the PDF viewer, via
    xdg-open/open).

    cozer's launcher (``__main__._ensure_fontconfig``) exports ``FONTCONFIG_FILE``
    pointing at a private, env-specific fontconfig config to dodge a conda
    libfontconfig cache segfault; a conda launcher may likewise put
    ``$CONDA_PREFIX/lib`` on ``LD_LIBRARY_PATH``. Child processes inherit both, so
    a *system* viewer -- which links the system libfontconfig and system GLib --
    would parse cozer's env config (spurious ``invalid attribute 'xsi:nil'``
    warnings) or load incompatible conda libraries (crash). Hand system helpers a
    clean environment: drop cozer's fontconfig override and any conda entries from
    the loader path so they use their own system libraries.
    """
    env = dict(os.environ)
    for var in ("FONTCONFIG_FILE", "FONTCONFIG_PATH"):
        env.pop(var, None)
    prefixes = tuple(p for p in (sys.prefix, os.environ.get("CONDA_PREFIX")) if p)
    for var in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
        val = env.get(var)
        if not val:
            continue
        kept = [e for e in val.split(os.pathsep)
                if e and not any(e == p or e.startswith(p + os.sep) for p in prefixes)]
        if kept:
            env[var] = os.pathsep.join(kept)
        else:
            env.pop(var, None)
    return env


def open_in_viewer(path):
    """Open a file with the OS default application, with a system-clean
    environment so the viewer never inherits cozer's private fontconfig config or
    conda library paths (see _system_child_env)."""
    if sys.platform.startswith("win"):        # pragma: no cover - platform-specific
        os.startfile(path)
    elif sys.platform == "darwin":            # pragma: no cover - platform-specific
        subprocess.Popen(["open", path], env=_system_child_env())
    else:
        subprocess.Popen(["xdg-open", path], env=_system_child_env())


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
        try:                                    # also surface it in the Log tab -- a Windows
            if _report:                         # operator has no console to see the traceback on
                window.log(_report["traceback"].rstrip())
            window.log("GitHub issue filed: %s" % url if url else
                       "Crash recorded locally; no GitHub issue filed (sign in to file one).")
        except Exception:
            pass
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
        # Persistent "data warnings" indicator in the status bar (see validate.py).
        self._findings = []
        self._warn_btn = QPushButton()
        self._warn_btn.setFlat(True)
        self._warn_btn.setStyleSheet(
            "QPushButton { color: #b36b00; font-weight: bold; border: none; padding: 0 8px; }")
        self._warn_btn.setCursor(Qt.PointingHandCursor)
        self._warn_btn.setToolTip("Click to list the data warnings")
        self._warn_btn.clicked.connect(self._show_warnings)
        self._warn_btn.hide()
        self.statusBar().addPermanentWidget(self._warn_btn)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_geninfo_tab(), "General Information")
        self.timer_panel = TimerPanel(self)
        self.tabs.addTab(self.timer_panel, "Timer")
        self.editor_panel = EditRecordsPanel(self)
        self.tabs.addTab(self.editor_panel, "Edit Records")
        self._reports_tab = self._build_reports_tab()
        self.tabs.addTab(self._reports_tab, "Reports")
        self.tabs.addTab(self._build_log_tab(), "Log")
        self._prev_tab = self.tabs.currentIndex()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._reload_forms()
        self._refresh_title()
        self.log("Ready")

    def _on_tab_changed(self, idx):
        # Prompt to save/discard unsaved Edit Records edits before leaving the tab.
        prev = self._prev_tab
        if self.tabs.widget(prev) is self.editor_panel and idx != prev:
            if not self.editor_panel.maybe_flush():
                self.tabs.blockSignals(True)
                self.tabs.setCurrentIndex(prev)
                self.tabs.blockSignals(False)
                return
        self._prev_tab = idx
        self._refresh_warnings()   # data may have changed on the tab we just left
        # Entering the Timer / Edit Records: pick up data created on another tab (their combos
        # are otherwise only built at event-load) — races added on the Races tab, heats recorded
        # in the Timer. Timer refresh is a no-op mid-timing; the editor draft is already flushed.
        if self.tabs.widget(idx) is self.timer_panel:
            self.timer_panel.refresh_races()
        elif self.tabs.widget(idx) is self.editor_panel:
            self.editor_panel.refresh_heats()
        elif self.tabs.widget(idx) is self._reports_tab:
            self._reload_classes()          # pick up classes/heats recorded on other tabs

    def closeEvent(self, event):
        # Don't let unsaved race edits vanish on quit.
        if not self.editor_panel.maybe_flush():
            event.ignore()
            return
        if self.store is not None:
            self.store.close()   # flush pending journal fsyncs + stop the background syncer
        event.accept()

    # ---- menu / file operations ----
    def _build_menu(self):
        m = self.menuBar().addMenu("&File")
        for text, slot in [("&New", self.on_new), ("New &ruleset…", self.on_new_ruleset),
                           ("&Open…", self.on_open),
                           ("&Import legacy .coz…", self.on_import),
                           ("Import &ruleset…", self.on_import_ruleset), (None, None),
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
        if not self.editor_panel.maybe_flush():
            return
        self.eventdata = copy.deepcopy(DEFAULT_EVENT)
        self.store = None
        self._reload_forms()
        self._refresh_title()
        self.log("New event")

    def on_new_ruleset(self):
        if not self.editor_panel.maybe_flush():
            return
        self.eventdata = rulesetmod.new_ruleset()
        self.store = None
        self._reload_forms()
        self._refresh_title()
        self.log("New ruleset — define scoring, class names and rules, then Save As")

    def on_import_ruleset(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import ruleset", rulesetmod.bundled_dir(),
            "Cozer rulesets/events (*.cozj *.coz)")
        if not path:
            return
        try:
            if path.endswith(".coz"):
                source = read_legacy_coz(path)
            else:
                with open(path, encoding="utf-8") as f:
                    source = load_event(f.read())
        except Exception as e:      # pragma: no cover - surfaced, never crashes
            QMessageBox.critical(self, "Import error", "%s: %s" % (type(e).__name__, e))
            return
        changed = rulesetmod.import_ruleset(self.eventdata, source)
        self._reload_forms()      # persists with the event on the next File > Save
        name = source.get("title") or os.path.basename(path)
        self.log("Imported ruleset '%s' (%s)"
                 % (name, ", ".join(changed) if changed else "no new items"))

    def on_open(self):
        if not self.editor_panel.maybe_flush():
            return
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
                legacy = read_legacy_coz(path)
                # seed the class-name vocabulary, then convert to the fully suffix-free native
                # shape (record, classes, and the race schedule)
                legacy["classnames"] = rulesetmod.classnames_of(legacy)
                self.eventdata = to_native(legacy)
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

    def open_accumulated(self, paths, save_as=None):
        """``python -m cozer f1.cozj f2.cozj …`` — open/create one event that
        accumulates rulesets. With only rulesets, the result is an initial new
        event (use case 1). With one non-ruleset event file present, that event
        is the base and the rulesets are applied **non-destructively** — adding
        new class names/rules and filling empty scoring only, never overwriting
        the event's data (use case 2). Conflicts are reported to terminal + Log.

        ``save_as`` (the CLI's trailing *non-existing* ``.cozj`` argument) writes the merged
        event to that new file — a copy of the base event with the ruleset files accumulated in
        (use case 3). The input files are only read, never modified."""
        loaded = []
        for p in paths:
            try:
                data = (read_legacy_coz(p) if p.lower().endswith(".coz")
                        else load_event(open(p, encoding="utf-8").read()))
            except Exception as e:      # pragma: no cover - reported, never crashes
                self._report_accum("cannot read %s: %s" % (p, e))
                continue
            loaded.append((p, data))
        events = [(p, d) for p, d in loaded if not rulesetmod.is_ruleset(d)]
        rulesets = [(p, d) for p, d in loaded if rulesetmod.is_ruleset(d)]
        if len(events) > 1:
            self._report_accum(
                "multiple event files given; using %s and ignoring %s"
                % (os.path.basename(events[0][0]),
                   ", ".join(os.path.basename(p) for p, _ in events[1:])))
            events = events[:1]

        if save_as:                                 # write a NEW file; inputs stay read-only
            self.eventdata = (copy.deepcopy(events[0][1]) if events
                              else copy.deepcopy(DEFAULT_EVENT))
            self.eventdata["classnames"] = rulesetmod.classnames_of(self.eventdata)
        elif events:
            self.load(events[0][0])                 # store-backed base (never overwritten)
        else:
            self.on_new()                           # a fresh event to build from rulesets

        reports = []
        for p, d in rulesets:                       # non-destructive: add new / fill empty
            reports += rulesetmod.accumulate_ruleset(
                self.eventdata, d, "%s: " % os.path.basename(p))

        if save_as:                                 # persist the merge to the new file
            self.store = EventStore(save_as, self.eventdata)
            self.store.snapshot()
            self._refresh_title()
        self._reload_forms()
        for msg in reports:
            self._report_accum(msg)
        if rulesets:
            self._report_accum(
                "accumulated %d ruleset(s) -> %d class names, %d rules%s"
                % (len(rulesets), len(self.eventdata["classnames"]),
                   len(self.eventdata["rules"]),
                   " (%d conflict(s) kept existing)" % len(reports) if reports else ""))
        if save_as:
            self._report_accum(
                "created %s — %s%s" % (
                    os.path.basename(save_as),
                    ("copy of %s" % os.path.basename(events[0][0])) if events else "new event",
                    " + %d ruleset(s)" % len(rulesets) if rulesets else ""))

    def _report_accum(self, msg):
        print("cozer: %s" % msg, file=sys.stderr)
        self.log(msg)

    def on_import(self):
        if not self.editor_panel.maybe_flush():
            return
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
        self.classpart_panel = ClassesParticipantsPanel(self)
        self.races_tab = RacesTab(self)

        # The Rules sub-tab is also the editor for ruleset files: scoring system,
        # class-name vocabulary, penalty rules, and Import ruleset (additive).
        rules_w = QWidget()
        rv = QVBoxLayout(rules_w)
        srow = QHBoxLayout()
        srow.addWidget(QLabel("Scoring system:"))
        self.scoring_edit = QLineEdit()
        self.scoring_edit.textChanged.connect(
            lambda text: self.eventdata.__setitem__("scoringsystem", parse_scoring(text)))
        srow.addWidget(self.scoring_edit)
        imp = QPushButton("Import ruleset…")
        imp.clicked.connect(self.on_import_ruleset)
        srow.addWidget(imp)
        rv.addLayout(srow)
        cols = QHBoxLayout()
        cn_col = QVBoxLayout()
        cn_col.addWidget(QLabel("Class names:"))
        self.classnames_editor = StringListEditor(
            add_label="Add class name", prompt="Class name:",
            can_delete=self._classname_in_use)
        cn_col.addWidget(self.classnames_editor)
        cols.addLayout(cn_col, 1)
        rules_col = QVBoxLayout()
        rules_col.addWidget(QLabel("Rules:"))
        self.rules_grid = GridTab([(1, "Action"), (2, "Paragraph"), (3, "Description")], 4,
                                  validate=validate_rule_cell, warn=self.log)
        rules_col.addWidget(self.rules_grid)
        cols.addLayout(rules_col, 2)
        rv.addLayout(cols)

        sub.addTab(self.classpart_panel, "Classes && Participants")
        sub.addTab(self.races_tab, "Races")
        sub.addTab(rules_w, "Rules")
        self._geninfo_sub = sub
        v.addWidget(sub)
        return w

    def _ensure_keys(self):
        for key in ("classes", "participants", "races", "rules", "scoringsystem"):
            self.eventdata.setdefault(key, [])
        if "classnames" not in self.eventdata:
            # seed the class-name vocabulary from any classes already defined
            # (e.g. a legacy .coz / older working copy with no explicit list)
            self.eventdata["classnames"] = rulesetmod.classnames_of(self.eventdata)
        self.eventdata.setdefault("kind", "event")

    def _reload_forms(self):
        self._ensure_keys()
        for key, _ in _EVENT_FIELDS:
            self._fields[key].setText(str(self.eventdata.get(key, "")))
        self.classpart_panel.reload()
        self.races_tab.set_data(self.eventdata["races"])
        self.rules_grid.set_data(self.eventdata["rules"])
        self.classnames_editor.set_data(self.eventdata["classnames"])
        self.scoring_edit.setText(" ".join(str(x) for x in self.eventdata["scoringsystem"]))
        self._reload_classes()
        self.timer_panel.reload()
        self.editor_panel.reload()
        self._apply_kind()
        self._refresh_warnings()

    def _classname_in_use(self, name):
        """Reason a class name can't be removed from the catalog — it is set up as
        an event class, or a participant or race uses it — else None. Reads both the
        native ({name, phases}) and legacy (suffixed rows) shapes."""
        from cozer.classes import getclass
        for c in self.eventdata.get("classes", []):
            cn = c.get("name") if isinstance(c, dict) else (c[1] if len(c) > 1 else "")
            if getclass(cn) == name:
                return "it is set up as a class in this event (remove it under " \
                       "Classes & Participants first)"
        for p in self.eventdata.get("participants", []):
            if len(p) > 4 and p[4] == name:
                return "a participant is entered in class %r" % name
        for race in self.eventdata.get("races", []):
            for row in race:
                rn = row.get("name") if isinstance(row, dict) else (row[1] if len(row) > 1 else "")
                if getclass(rn) == name:
                    return "a race uses class %r" % name
        return None

    def _apply_kind(self):
        """A ruleset file (kind == 'ruleset') only defines scoring / class names /
        rules, so hide the race-specific tabs and show the Rules editor."""
        ruleset = rulesetmod.is_ruleset(self.eventdata)
        for w in (self.timer_panel, self.editor_panel, self._reports_tab):
            i = self.tabs.indexOf(w)
            if i >= 0:
                self.tabs.setTabVisible(i, not ruleset)
        for w in (self.classpart_panel, self.races_tab):
            i = self._geninfo_sub.indexOf(w)
            if i >= 0:
                self._geninfo_sub.setTabVisible(i, not ruleset)
        if ruleset:
            self.tabs.setCurrentIndex(0)
            self._geninfo_sub.setCurrentIndex(self._geninfo_sub.count() - 1)   # Rules

    # ---- data-validation warnings (see cozer/validate.py) ----
    def _refresh_warnings(self):
        """Recompute non-fatal data warnings and update the status-bar indicator."""
        self._findings = validate.check_results(self.eventdata)
        n = len(self._findings)
        if n:
            self._warn_btn.setText("⚠ %d data warning%s" % (n, "" if n == 1 else "s"))
            self._warn_btn.show()
        else:
            self._warn_btn.hide()

    def _show_warnings(self):
        """List the current data warnings (the status-bar indicator was clicked)."""
        findings = validate.check_results(self.eventdata)
        if not findings:
            QMessageBox.information(self, "Data warnings", "No data warnings.")
            return
        QMessageBox.warning(self, "Data warnings (%d)" % len(findings),
                            "\n".join(validate.format_findings(findings)))

    def _warn_before_report(self):
        """Loudly flag suspicious data before generating a report (non-blocking)."""
        findings = validate.check_results(self.eventdata)
        if findings:
            QMessageBox.warning(
                self, "Data warnings (%d)" % len(findings),
                "This report is generated from data with warnings:\n\n"
                + "\n".join(validate.format_findings(findings)))

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
            "Describe what happened — the first line becomes the issue title.\n"
            "The current event is attached so it can be reproduced:")
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
        for r in _REPORTS:
            self.report_combo.addItem(r[0])
        row.addWidget(self.report_combo)
        view = QPushButton("View")
        view.clicked.connect(self.on_view)
        row.addWidget(view)
        export = QPushButton("Export…")
        export.clicked.connect(self.on_export)
        row.addWidget(export)
        row.addStretch()
        v.addLayout(row)
        v.addWidget(QLabel("Classes / heats to include (none checked = all):"))
        self.report_tree = QTreeWidget()
        self.report_tree.setHeaderHidden(True)
        v.addWidget(self.report_tree)
        return w

    def _reload_classes(self):
        """Populate the Reports tab's class/heat tree, preserving the operator's checks.
        (Name kept: the Classes/Participants panel calls this when classes change; it is also
        refreshed on entering the Reports tab, so heats recorded on other tabs show up.) Heats
        are enumerated via the phase view, so the native record shape is transparent."""
        prev = {}                                   # class name -> (class check, {heat: check})
        for i in range(self.report_tree.topLevelItemCount()):
            c = self.report_tree.topLevelItem(i)
            prev[c.text(0)] = (c.checkState(0),
                               {c.child(j).text(0): c.child(j).checkState(0)
                                for j in range(c.childCount())})
        self.report_tree.clear()
        phase_map = class_phase_map(self.eventdata)  # synthesized class name -> its Phase (recorded)
        for cl in get_classes(self.eventdata):
            pstate, pheats = prev.get(cl, (Qt.Unchecked, {}))
            c = QTreeWidgetItem(self.report_tree, [cl])
            c.setFlags(c.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            ph = phase_map.get(cl)
            heat_ids = phase_heat_ids(ph) if ph is not None else []
            for h in heat_ids:
                hi = QTreeWidgetItem(c, [str(h)])
                hi.setFlags(hi.flags() | Qt.ItemIsUserCheckable)
                hi.setCheckState(0, pheats.get(str(h), Qt.Unchecked))
            if not heat_ids:                         # childless class: no auto-tristate to derive from
                c.setCheckState(0, Qt.Checked if pstate == Qt.Checked else Qt.Unchecked)

    def _report_selection(self):
        """(classes, heat_map) from the report tree; (None, None) means 'all'.
        A fully-checked class -> all its heats; a partially-checked class ->
        only the checked heats (heat_map[cl])."""
        classes, heat_map, any_checked = [], {}, False
        for i in range(self.report_tree.topLevelItemCount()):
            c = self.report_tree.topLevelItem(i)
            st = c.checkState(0)
            if st == Qt.Unchecked:
                continue
            any_checked = True
            classes.append(c.text(0))
            if st == Qt.PartiallyChecked:
                heat_map[c.text(0)] = [c.child(j).text(0) for j in range(c.childCount())
                                       if c.child(j).checkState(0) == Qt.Checked]
        if not any_checked:
            return None, None
        return classes, (heat_map or None)

    def _render_report(self, label, funcname, takes_classes, takes_heats, path):
        """Render report ``label`` to ``path``; return True on success. A failure
        is a cozer defect, not user error, so it is routed through the crash
        reporter (files if signed in, else queues) instead of dying silently."""
        try:
            import cozer.reports as R
            func = getattr(R, funcname)
            kwargs = {}
            if takes_classes or takes_heats:
                classes, heat_map = self._report_selection()
                if takes_classes:
                    kwargs["classes"] = classes
                if takes_heats:
                    kwargs["heat_map"] = heat_map
            func(self.eventdata, path, **kwargs)
            return True
        except Exception as e:
            _report, url = report_exception(self, type(e), e, e.__traceback__,
                                            action="Generate report: %s" % label)
            QMessageBox.critical(
                self, "Report error",
                "Could not generate the report; the error was recorded locally%s.\n\n%s: %s"
                % (" and reported" if url else "", type(e).__name__, e))
            return False

    def on_view(self):
        """Render the selected report to the event's ``<event>.reports/`` folder
        (a temp dir if the event is unsaved) and open it -- no Save dialog. Also
        archives a timestamped copy under ``postings/``."""
        from cozer.reports.output import report_output_paths
        label, funcname, tc, th = _REPORTS[self.report_combo.currentIndex()]
        stamp = datetime.now().strftime("%m%d-%H%M")
        event_path = self.store.path if self.store else None
        latest, posting = report_output_paths(event_path, label, stamp)
        os.makedirs(os.path.dirname(posting), exist_ok=True)   # makes <dir> and <dir>/postings
        self._warn_before_report()
        if not self._render_report(label, funcname, tc, th, latest):
            return
        try:
            shutil.copyfile(latest, posting)
            archived = " (archived postings/%s)" % os.path.basename(posting)
        except OSError:                        # pragma: no cover - archive is best-effort
            archived = ""
        self.log("Viewed %s%s" % (latest, archived))
        open_in_viewer(latest)

    def on_export(self):
        """Export the selected report to a location the user chooses (Save dialog)."""
        from cozer.reports.output import report_stem
        label, funcname, tc, th = _REPORTS[self.report_combo.currentIndex()]
        path, _ = QFileDialog.getSaveFileName(
            self, "Export report PDF", report_stem(label) + ".pdf", "PDF (*.pdf)")
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        self._warn_before_report()
        if self._render_report(label, funcname, tc, th, path):
            self.log("Exported %s" % path)
            open_in_viewer(path)

    def _refresh_title(self):
        kind = " [ruleset]" if rulesetmod.is_ruleset(self.eventdata) else ""
        self.setWindowTitle("COZER%s — %s"
                            % (kind, self.store.path if self.store else "(unsaved)"))


def _startup_paths(argv):
    """All .coz/.cozj file arguments, in order (existence checked by the caller)."""
    return [a for a in argv
            if not a.startswith("-") and a.lower().endswith((".coz", ".cozj"))]


def _startup_file(argv):
    """The first .coz/.cozj argument, or None."""
    paths = _startup_paths(argv)
    return paths[0] if paths else None


def _accumulate_target(argv):
    """Split the startup file arguments into ``(inputs, output, missing)``. ``output`` is a
    *trailing non-existing* ``.cozj`` argument — the CLI's create-and-merge target (write the
    merged event there) — else None. ``inputs`` are the earlier files that exist; ``missing``
    are other non-existing arguments (genuine typos, reported to the terminal)."""
    paths = _startup_paths(argv)
    output = None
    if paths and paths[-1].lower().endswith(".cozj") and not os.path.exists(paths[-1]):
        output, paths = paths[-1], paths[:-1]
    inputs = [p for p in paths if os.path.exists(p)]
    missing = [p for p in paths if not os.path.exists(p)]
    return inputs, output, missing


def run(argv=None, app=None):     # pragma: no cover - launches the Qt event loop
    argv = list(argv) if argv is not None else sys.argv[1:]
    if app is None:
        app = QApplication.instance() or QApplication([sys.argv[0]] + argv)
    win = MainWindow()
    _install_excepthook(win)
    inputs, save_as, missing = _accumulate_target(argv)   # python -m cozer f1.cozj f2.cozj [out.cozj]
    for p in missing:
        print("cozer: file not found: %s" % p, file=sys.stderr)
    if inputs or save_as:
        win.open_accumulated(inputs, save_as=save_as)
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
