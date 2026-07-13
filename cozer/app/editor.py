"""Edit Records — review and correct a heat's recorded marks, with a live
results preview.

Each competitor's marks (laps + event marks) are shown in a table; you can
insert a mark (penalty/lost-lap/DQ/… from the record codes), enable/disable a
mark (toggle its sign), or delete one, and adjust the heat's race time. Every
edit is committed through the store (journaled + fsync'd), so corrections are as
durable as the original recording. The results panel re-runs the proven
``analyze`` after each change.

The edit operations (set_racetime / insert_mark / toggle_mark / delete_mark)
are plain methods, driven directly by the headless tests.
"""
import copy

from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from cozer._py2compat import round2
from cozer.analyzer import analyze, getresorder
from cozer.records import insertmark, invreccodemap, reccodemap


def code_label(code):
    if code in (1, -1):
        base = "lap"
    elif code in (2, -2):
        base = "ins. lap"
    else:
        base = invreccodemap.get(abs(code), str(abs(code)))
    return base if code > 0 else "(off) " + base


class InsertMarkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Insert mark")
        form = QFormLayout(self)
        self.code = QComboBox()
        for name in reccodemap:
            self.code.addItem(name)
        self.time = QDoubleSpinBox()
        self.time.setRange(0.0, 1e6)
        self.time.setDecimals(2)
        self.note = QLineEdit()
        form.addRow("Code:", self.code)
        form.addRow("Time (s):", self.time)
        form.addRow("Note:", self.note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def values(self):
        return reccodemap[self.code.currentText()], round2(self.time.value()), self.note.text()


class EditRecordsPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._heatkeys = []

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Class / Heat:"))
        self.heat_combo = QComboBox()
        self.heat_combo.currentIndexChanged.connect(self._on_heat)
        top.addWidget(self.heat_combo)
        top.addWidget(QLabel("Race time (s):"))
        self.racetime_edit = QLineEdit()
        self.racetime_edit.setFixedWidth(90)
        self.racetime_edit.editingFinished.connect(self._on_racetime)
        top.addWidget(self.racetime_edit)
        top.addWidget(QLabel("Boat:"))
        self.boat_combo = QComboBox()
        self.boat_combo.currentIndexChanged.connect(self._refresh_marks)
        top.addWidget(self.boat_combo)
        top.addStretch()
        v.addLayout(top)

        mid = QHBoxLayout()
        self.marks = QTableWidget(0, 3)
        self.marks.setHorizontalHeaderLabels(["Code", "Time", "Note"])
        self.marks.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.marks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.marks.horizontalHeader().setStretchLastSection(True)
        mid.addWidget(self.marks, 2)
        self.results = QPlainTextEdit()
        self.results.setReadOnly(True)
        mid.addWidget(self.results, 3)
        v.addLayout(mid, 1)

        btns = QHBoxLayout()
        for text, slot in [("Insert mark…", self._on_insert), ("Enable/Disable", self._on_toggle),
                           ("Delete mark", self._on_delete)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch()
        v.addLayout(btns)

    # ---- data access ----
    def _record(self):
        return self.window.eventdata.get("record", {})

    def reload(self):
        self.heat_combo.blockSignals(True)
        self.heat_combo.clear()
        self._heatkeys = []
        for cl in sorted(self._record()):
            for h in sorted(self._record()[cl]):
                self._heatkeys.append((cl, h))
                self.heat_combo.addItem("%s / %s" % (cl, h))
        self.heat_combo.blockSignals(False)
        self._on_heat()

    def _cur(self):
        i = self.heat_combo.currentIndex()
        return self._heatkeys[i] if 0 <= i < len(self._heatkeys) else (None, None)

    def _cur_boat(self):
        return self.boat_combo.currentText()

    def _on_heat(self):
        cl, h = self._cur()
        if cl is None:
            self.racetime_edit.clear()
            self.boat_combo.clear()
            self.marks.setRowCount(0)
            self.results.clear()
            return
        info = self._record()[cl][h][0]
        self.racetime_edit.setText(str(info.get("racetime", "")))
        self.boat_combo.blockSignals(True)
        self.boat_combo.clear()
        for pid in sorted(self._record()[cl][h][1].keys(), key=str):
            self.boat_combo.addItem(str(pid))
        self.boat_combo.blockSignals(False)
        self._refresh_marks()

    def _refresh_marks(self):
        self.marks.setRowCount(0)
        cl, h = self._cur()
        pid = self._cur_boat()
        if cl is not None and pid != "":
            for m in self._record()[cl][h][1].get(pid, []):
                r = self.marks.rowCount()
                self.marks.insertRow(r)
                self.marks.setItem(r, 0, QTableWidgetItem(code_label(m[0])))
                self.marks.setItem(r, 1, QTableWidgetItem(str(m[1]) if len(m) > 1 else ""))
                self.marks.setItem(r, 2, QTableWidgetItem(str(m[2]) if len(m) > 2 else ""))
        self._refresh_results()

    def _refresh_results(self):
        cl, h = self._cur()
        if cl is None:
            return
        ss = self.window.eventdata.get("scoringsystem", [])
        try:
            res = analyze(h, copy.deepcopy(self._record()[cl][h]), ss)
        except Exception as e:      # pragma: no cover - surfaced, never crashes
            self.results.setPlainText("(analysis error: %s: %s)" % (type(e).__name__, e))
            return
        lines = []
        for pid in getresorder(res):
            r = res[pid]
            place = r["place"] if r["place"] > 0 else "-"
            notes = " ".join(r["notes"].keys()) if r["notes"] else ""
            lines.append("%3s  #%-4s  pts=%-4s  %.1f/%.1f  %s"
                         % (place, pid, r["points"], r["avgspeed"], r["maxlapspeed"], notes))
        self.results.setPlainText("\n".join(lines))

    # ---- edit operations (journaled via the store) ----
    def _commit(self, cl, h, pid, marks):
        self.window.store.record({"op": "replace", "cl": cl, "h": h, "id": pid, "marks": marks})
        self._refresh_marks()

    def set_racetime(self, cl, h, value):
        self.window.store.record({"op": "info", "cl": cl, "h": h, "key": "racetime", "value": value})
        self._refresh_results()

    def insert_mark(self, cl, h, pid, code, ct, note=""):
        marks = [list(m) for m in self._record()[cl][h][1][pid]]
        insertmark(marks, code, ct, note)
        self._commit(cl, h, pid, marks)

    def toggle_mark(self, cl, h, pid, index):
        marks = [list(m) for m in self._record()[cl][h][1][pid]]
        if 0 <= index < len(marks):
            marks[index][0] = -marks[index][0]
            self._commit(cl, h, pid, marks)

    def delete_mark(self, cl, h, pid, index):
        marks = [list(m) for m in self._record()[cl][h][1][pid]]
        if 0 <= index < len(marks):
            del marks[index]
            self._commit(cl, h, pid, marks)

    # ---- UI slots ----
    def _require_store(self):
        if self.window.store is None:
            self.window.on_save_as()
        return self.window.store is not None

    def _on_racetime(self):
        cl, h = self._cur()
        if cl is None or not self._require_store():
            return
        try:
            value = float(self.racetime_edit.text())
        except ValueError:
            return
        self.set_racetime(cl, h, value)

    def _on_insert(self):
        cl, h = self._cur()
        pid = self._cur_boat()
        if cl is None or pid == "" or not self._require_store():
            return
        dlg = InsertMarkDialog(self)
        if dlg.exec():                  # pragma: no cover - modal dialog
            code, ct, note = dlg.values()
            self.insert_mark(cl, h, pid, code, ct, note)

    def _on_toggle(self):
        cl, h = self._cur()
        pid = self._cur_boat()
        row = self.marks.currentRow()
        if cl is not None and pid != "" and row >= 0 and self._require_store():
            self.toggle_mark(cl, h, pid, row)

    def _on_delete(self):
        cl, h = self._cur()
        pid = self._cur_boat()
        row = self.marks.currentRow()
        if cl is not None and pid != "" and row >= 0 and self._require_store():
            self.delete_mark(cl, h, pid, row)
