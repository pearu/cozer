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
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from cozer import reports as R
from cozer.racepattern import get_classes
from cozer.store import EventStore, read_legacy_coz

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


class MainWindow(QMainWindow):
    def __init__(self, eventdata=None):
        super().__init__()
        self.store = None
        self.eventdata = eventdata if eventdata is not None else copy.deepcopy(DEFAULT_EVENT)
        self.resize(900, 600)
        self._build_menu()
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_event_tab(), "Event")
        self.tabs.addTab(self._build_reports_tab(), "Reports")
        self.statusBar().showMessage("Ready")
        self._reload_forms()
        self._refresh_title()

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
        self.statusBar().showMessage("New event")

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open event", "", "Cozer events (*.cozj *.coz)")
        if path:
            self.load(path)

    def load(self, path):
        if path.endswith(".coz"):
            self.eventdata = read_legacy_coz(path)
            self.store = None
        else:
            self.store = EventStore.open(path, default=copy.deepcopy(DEFAULT_EVENT))
            self.eventdata = self.store.eventdata
        self._reload_forms()
        self._refresh_title()
        self.statusBar().showMessage("Opened %s" % path)

    def on_import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import legacy .coz", "", "Legacy events (*.coz)")
        if path:
            self.eventdata = read_legacy_coz(path)
            self.store = None
            self._reload_forms()
            self._refresh_title()
            self.statusBar().showMessage("Imported %s — Save As to persist as .cozj" % path)

    def on_save(self):
        if self.store is None:
            return self.on_save_as()
        self.store.eventdata = self.eventdata
        self.store.snapshot()
        self.statusBar().showMessage("Saved %s" % self.store.path)

    def on_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save event as", "", "Cozer events (*.cozj)")
        if not path:
            return
        if not path.endswith(".cozj"):
            path += ".cozj"
        self.store = EventStore(path, self.eventdata)
        self.store.snapshot()
        self._refresh_title()
        self.statusBar().showMessage("Saved %s" % path)

    # ---- event tab ----
    def _build_event_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        self._fields = {}
        for key, label in _EVENT_FIELDS:
            edit = QLineEdit()
            edit.textChanged.connect(lambda text, k=key: self.eventdata.__setitem__(k, text))
            self._fields[key] = edit
            form.addRow(label + ":", edit)
        return w

    def _reload_forms(self):
        for key, _ in _EVENT_FIELDS:
            self._fields[key].setText(str(self.eventdata.get(key, "")))
        self._reload_classes()

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
        self.statusBar().showMessage("Wrote %s" % path)
        open_in_viewer(path)

    def _refresh_title(self):
        self.setWindowTitle("COZER — %s" % (self.store.path if self.store else "(unsaved)"))


def run(argv=None):     # pragma: no cover - launches the Qt event loop
    argv = list(argv) if argv is not None else sys.argv[1:]
    app = QApplication.instance() or QApplication([sys.argv[0]] + argv)
    win = MainWindow()
    files = [a for a in argv if not a.startswith("-") and os.path.exists(a)]
    if files:
        win.load(files[0])
    win.show()
    return app.exec()
