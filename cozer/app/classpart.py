"""The Classes & Participants tab: one subtab per class, each with the class's
race pattern and its participant spreadsheet (Boat #, Name, Surname, From).

Built on the unchanged internal representation:
  classes       -> [_, name, pattern]
  participants  -> [_, name, surname, from, class, id]

The class of a participant is set by the subtab it is entered under, so the two
lists stay in sync on the CLASS key; boat numbers are unique within a class.
Adding a class offers the rule set's class-name vocabulary; a class can only be
removed once it has no participants. Race patterns are edited in a structured
dialog (common circuit fields + a live preview + an editable raw string).
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QStyledItemDelegate,
    QTableView, QTabWidget, QVBoxLayout, QWidget,
)

from cozer.app import ruleset as rulesetmod
from cozer.racepattern import (
    crack_race_pattern, describe_pattern, format_circuit_pattern, parse_simple_pattern,
)


# --- per-class participant table --------------------------------------------

class ParticipantClassModel(QAbstractTableModel):
    """A view of the master participants list filtered to one class. Edits,
    inserts and deletes operate on the master list in place; boat numbers are
    kept unique within the class."""

    COLS = [(5, "Boat #"), (1, "Name"), (2, "Surname"), (3, "From")]

    def __init__(self, participants, classname, warn=None):
        super().__init__()
        self._all = participants          # master list, edited in place
        self._class = classname
        self._warn = warn
        self._reindex()

    def _reindex(self):
        self._idx = [i for i, p in enumerate(self._all)
                     if len(p) > 4 and p[4] == self._class]

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._idx)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLS[section][1]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row = self._all[self._idx[index.row()]]
        ci = self.COLS[index.column()][0]
        return "" if ci >= len(row) else str(row[ci])

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        master = self._idx[index.row()]
        row = self._all[master]
        ci = self.COLS[index.column()][0]
        if isinstance(value, str):
            value = value.strip()
        if ci == 5 and value:             # boat number must be unique within the class
            for j in self._idx:
                if j != master and len(self._all[j]) > 5 \
                        and str(self._all[j][5]) == str(value):
                    if self._warn:
                        self._warn("Boat number %s is already used in class %s"
                                   % (value, self._class))
                    return False
        while len(row) <= ci:
            row.append("")
        row[ci] = value
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def add_row(self):
        n = len(self._idx)
        self.beginInsertRows(QModelIndex(), n, n)
        self._all.append(["", "", "", "", self._class, ""])
        self._reindex()
        self.endInsertRows()

    def delete_row(self, r):
        if 0 <= r < len(self._idx):
            self.beginRemoveRows(QModelIndex(), r, r)
            del self._all[self._idx[r]]
            self._reindex()
            self.endRemoveRows()


class AutoCompleteDelegate(QStyledItemDelegate):
    """Cell editor whose QLineEdit offers as-you-type suggestions from
    ``values_fn()`` (recomputed each time an editor opens)."""

    def __init__(self, values_fn, parent=None):
        super().__init__(parent)
        self._values_fn = values_fn

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        comp = QCompleter(self._values_fn(), editor)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        editor.setCompleter(comp)
        return editor


class ClassParticipantsWidget(QWidget):
    def __init__(self, participants, classname, warn=None):
        super().__init__()
        self._participants = participants
        self.model = ParticipantClassModel(participants, classname, warn)
        v = QVBoxLayout(self)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.horizontalHeader().setStretchLastSection(True)
        from_col = next(i for i, (f, _) in enumerate(ParticipantClassModel.COLS) if f == 3)
        self.view.setItemDelegateForColumn(
            from_col, AutoCompleteDelegate(self._from_suggestions, self.view))
        v.addWidget(self.view)
        row = QHBoxLayout()
        add = QPushButton("Add participant")
        add.clicked.connect(self.model.add_row)
        delete = QPushButton("Delete participant")
        delete.clicked.connect(self._delete)
        row.addWidget(add)
        row.addWidget(delete)
        row.addStretch()
        v.addLayout(row)

    def _from_suggestions(self):
        """Distinct non-empty 'From' values across all participants (any class),
        for the From-column autocomplete."""
        seen, out = set(), []
        for p in self._participants:
            if len(p) > 3 and p[3] and p[3] not in seen:
                seen.add(p[3])
                out.append(p[3])
        return out

    def _delete(self):
        idx = self.view.currentIndex()
        if idx.isValid():
            self.model.delete_row(idx.row())


# --- add-class dialog -------------------------------------------------------

class AddClassDialog(QDialog):
    """Pick a class to run in this event from the rule set's catalog (Rules tab).
    Strictly catalog-only — no free text — so class names stay the official,
    canonical ones (no misspelled variants). New names are minted under Rules."""

    def __init__(self, parent, available):
        super().__init__(parent)
        self.setWindowTitle("Add class")
        self._result = ""
        form = QFormLayout(self)
        self.name = QComboBox()             # non-editable: catalog names only
        self.name.addItems(available)
        form.addRow("Class name:", self.name)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self._accept)
        box.rejected.connect(self.reject)
        form.addRow(box)

    def _accept(self):
        self._result = self.name.currentText().strip()
        if self._result:
            self.accept()

    def class_name(self):
        return self._result


# --- race-pattern dialog ----------------------------------------------------

class PatternDialog(QDialog):
    """Structured entry for the common circuit pattern, with a live preview and
    an editable raw string for endurance / exotic patterns (round-trips)."""

    def __init__(self, parent, classname, pattern):
        super().__init__(parent)
        self.setWindowTitle("Race pattern — %s" % classname)
        self._result = pattern or ""
        v = QVBoxLayout(self)
        form = QFormLayout()
        self.first = self._spin(1, 100000, " m")
        self.other = self._spin(1, 100000, " m")
        self.laps = self._spin(1, 500)
        self.heats = self._spin(1, 50)
        self.scored = self._spin(1, 50)
        for w, label in [(self.first, "First lap length"), (self.other, "Other lap length"),
                         (self.laps, "Laps per heat"), (self.heats, "Number of heats"),
                         (self.scored, "Scored (best) heats")]:
            form.addRow(label + ":", w)
        v.addLayout(form)
        v.addWidget(QLabel("Pattern string (advanced — edit for endurance / exotic):"))
        self.raw = QLineEdit()
        v.addWidget(self.raw)
        self.preview = QLabel("")
        self.preview.setWordWrap(True)
        v.addWidget(self.preview)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self._accept)
        box.rejected.connect(self.reject)
        v.addWidget(box)

        parsed = parse_simple_pattern(pattern)
        vals = parsed or {"first": 1400, "other": 1500, "laps": 5, "heats": 3, "scored": 3}
        for w, key in [(self.first, "first"), (self.other, "other"), (self.laps, "laps"),
                       (self.heats, "heats"), (self.scored, "scored")]:
            w.setValue(int(vals[key]))
        self.raw.setText(pattern or self._from_fields())
        self._sync_scored_max()
        for w in (self.first, self.other, self.laps, self.heats, self.scored):
            w.valueChanged.connect(self._fields_changed)
        self.heats.valueChanged.connect(self._sync_scored_max)
        self.raw.textChanged.connect(self._update_preview)
        self._update_preview()

    def _sync_scored_max(self, *_):
        self.scored.setMaximum(max(1, self.heats.value()))   # can't score more heats than run

    @staticmethod
    def _spin(lo, hi, suffix=""):
        s = QSpinBox()
        s.setRange(lo, hi)
        if suffix:
            s.setSuffix(suffix)
        return s

    def _from_fields(self):
        return format_circuit_pattern(self.first.value(), self.other.value(),
                                      self.laps.value(), self.heats.value(),
                                      self.scored.value())

    def _fields_changed(self, *_):
        self.raw.setText(self._from_fields())          # fields drive the raw string

    def _update_preview(self, *_):
        self.preview.setText(describe_pattern(self.raw.text().strip()))

    def _accept(self):
        raw = self.raw.text().strip()
        if not raw:
            QMessageBox.information(self, "Invalid pattern", "The race pattern is empty.")
            return
        try:
            crack_race_pattern(raw)                 # reject unparseable patterns (eval'd later)
        except Exception:
            QMessageBox.information(
                self, "Invalid pattern",
                "Could not parse the pattern %r.\nExpected e.g. 4*(1430+7*1390):3 "
                "or 5000/6 (endurance)." % raw)
            return
        self._result = raw
        self.accept()

    def pattern(self):
        return self._result


# --- the tab ----------------------------------------------------------------

class ClassesParticipantsPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        v = QVBoxLayout(self)
        bar = QHBoxLayout()
        addc = QPushButton("Add class…")
        addc.clicked.connect(self._add_class)
        delc = QPushButton("Delete class")
        delc.clicked.connect(self._delete_class)
        bar.addWidget(addc)
        bar.addWidget(delc)
        bar.addStretch()
        v.addLayout(bar)
        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)

    def _classes(self):
        return self.window.eventdata.setdefault("classes", [])

    def _participants(self):
        return self.window.eventdata.setdefault("participants", [])

    def reload(self):
        self.tabs.clear()
        for classrow in self._classes():
            if len(classrow) > 1 and classrow[1]:
                self.tabs.addTab(self._class_tab(classrow), classrow[1])
        self._update_counts()

    def _class_tab(self, classrow):
        cl = classrow[1]
        w = QWidget()
        w._cozer_class = cl                          # authoritative name (label carries a count)
        lv = QVBoxLayout(w)
        prow = QHBoxLayout()
        summary = QLabel(self._pattern_summary(classrow))
        summary.setWordWrap(True)
        prow.addWidget(summary, 1)
        editp = QPushButton("Edit pattern…")
        editp.clicked.connect(lambda _=False, r=classrow, s=summary: self._edit_pattern(r, s))
        prow.addWidget(editp)
        lv.addLayout(prow)
        grid = ClassParticipantsWidget(self._participants(), cl, warn=self.window.log)
        grid.model.rowsInserted.connect(self._update_counts)
        grid.model.rowsRemoved.connect(self._update_counts)
        lv.addWidget(grid, 1)
        return w

    def _tab_class(self, i):
        return getattr(self.tabs.widget(i), "_cozer_class", self.tabs.tabText(i))

    def _update_counts(self, *_):
        parts = self._participants()
        for i in range(self.tabs.count()):
            cl = self._tab_class(i)
            n = sum(1 for p in parts if len(p) > 4 and p[4] == cl)
            self.tabs.setTabText(i, "%s (%d)" % (cl, n))

    def _pattern_summary(self, classrow):
        pat = classrow[2] if len(classrow) > 2 else ""
        return ("Race pattern:  %s     —     %s" % (pat, describe_pattern(pat))
                if pat else "Race pattern:  (not set — click Edit pattern…)")

    def _edit_pattern(self, classrow, summary_label):
        pat = classrow[2] if len(classrow) > 2 else ""
        dlg = PatternDialog(self, classrow[1], pat)
        if dlg.exec():
            while len(classrow) <= 2:
                classrow.append("")
            classrow[2] = dlg.pattern()
            summary_label.setText(self._pattern_summary(classrow))
            self.window._reload_classes()

    def _add_class(self):
        existing = {r[1] for r in self._classes() if len(r) > 1 and r[1]}
        available = [c for c in rulesetmod.classnames_of(self.window.eventdata)
                     if c not in existing]
        if not available:
            QMessageBox.information(
                self, "No class names available",
                "Every catalogued class is already added, or none are defined.\n"
                "Add class names under the Rules tab first.")
            return
        dlg = AddClassDialog(self, available)
        if dlg.exec():
            name = dlg.class_name()
            if not name:
                return
            self._classes().append(["", name, ""])   # name is already in the catalog
            self.reload()
            self.tabs.setCurrentIndex(self.tabs.count() - 1)
            self.window._reload_classes()

    def _class_in_use(self, name):
        """Reason class ``name`` can't be removed from the event — a participant
        or a race uses it — else None."""
        if any(len(p) > 4 and p[4] == name for p in self._participants()):
            return "it has participants"
        for race in self.window.eventdata.get("races", []):
            for row in race:
                if len(row) > 1 and row[1] == name:
                    return "a race uses it"
        return None

    def _delete_class(self):
        i = self.tabs.currentIndex()
        if i < 0:
            return
        name = self._tab_class(i)
        reason = self._class_in_use(name)
        if reason:
            QMessageBox.information(
                self, "Cannot delete",
                "Cannot delete class %r while %s." % (name, reason))
            return
        classes = self._classes()
        for j, r in enumerate(classes):
            if len(r) > 1 and r[1] == name:
                del classes[j]
                break
        self.reload()
        self.window._reload_classes()
