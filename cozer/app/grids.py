"""Editable data-entry grids for the General Information tab.

``ListTableModel`` edits an eventdata list-of-lists in place (each row keeps a
leading internal sort field at index 0, mirroring legacy). ``GridTab`` wraps a
table view with Add/Delete buttons; ``RacesTab`` handles the nested race list
(a list of races, each a list of class/heat rows).
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
)

from cozer.classes import getclass


def combo():
    """A QComboBox whose popup honours the app stylesheet's ``::item:selected`` colours. Qt's default
    combo delegate ignores stylesheet ``::item`` rules, so the highlighted item paints as invisible
    light-on-light (issue #37: "popup hard to see"); a QStyledItemDelegate forces the stylesheet to
    paint. Use this instead of ``QComboBox()`` everywhere so no dropdown regresses."""
    c = QComboBox()
    c.setItemDelegate(QStyledItemDelegate(c))
    return c
from cozer.racepattern import class_pattern, crack_race_pattern, get_classes, race_kind
from cozer.app import dialogs

# Suffix-free phase presentation. Circuit (the main/final race) needs no tag; the others get
# a short tag in compact labels and a full word in dropdowns — no `/T`,`/Q` or `t`/`q` anywhere.
_PHASE_ORDER = ["timetrial", "qualification", "circuit", "endurance"]
_PHASE_LABEL = {"timetrial": "Time trial", "qualification": "Qualification",
                "circuit": "Circuit", "endurance": "Endurance"}
_PHASE_TAG = {"timetrial": "TT", "qualification": "Q"}   # circuit/endurance: no tag


def confirm_delete(parent, what):
    """Yes/No 'are you sure?' guard before deleting REAL (operator-entered) data; returns True
    to proceed. The default button is No, so a stray Enter/click never deletes. Callers skip this
    (delete straight away) when the target is blank — there is nothing to lose."""
    return dialogs.question(
        parent, "Delete?", "Delete %s? This can't be undone." % what) == QMessageBox.Yes


def _entry_label(e):
    """Compact suffix-free label for one race entry, or None if unfilled. Native entry
    ``{name, kind, number, occurrence}`` → ``"GT15 1"`` / ``"GT15 TT1"`` / ``"GT15 1·R1"``;
    a legacy ``[_, class, heat]`` row falls back to ``"class heat"``."""
    if isinstance(e, dict):
        base, kind, num = e.get("name", ""), e.get("kind", ""), e.get("number")
        if not base or not num:
            return None
        tag = _PHASE_TAG.get(kind, "")
        occ = e.get("occurrence", 0)
        return "%s %s%d%s" % (base, tag, num, ("·R%d" % occ if occ else ""))
    return "%s %s" % (e[1], e[2]) if len(e) > 2 and e[1] and e[2] else None


def race_label(index, race):
    """Human label for a race: ``"Race N: GT15 1, F 500 TT1, ..."`` (suffix-free).

    ``race`` is a list of native heat-entry dicts (``{name, kind, number, occurrence}``);
    unfilled entries are skipped and a race with none keeps the bare ``"Race N"``. ``index``
    is 0-based; the label shows ``N = index+1``. Legacy ``[_, class, heat]`` rows still format
    (for unit use), so this reads either shape.
    """
    parts = [lbl for lbl in (_entry_label(e) for e in (race or [])) if lbl]
    base = "Race %d" % (index + 1)
    return "%s: %s" % (base, ", ".join(parts)) if parts else base


def parse_scoring(text):
    """Parse a space-separated scoring system into a list of numbers."""
    out = []
    for tok in text.split():
        try:
            out.append(int(tok))
        except ValueError:
            try:
                out.append(float(tok))
            except ValueError:
                pass
    return out


# A validator returns None, or (message, blocking): blocking=True hard-rejects the
# edit; blocking=False just logs the message (advisory — the organizer decides).

def validate_rule_cell(row, field, value, rows):
    """Note when a rule edit duplicates another rule's (action, paragraph).
    Advisory only. Empty actions are left alone (an in-progress row is fine)."""
    if field not in (1, 2):
        return None
    r = (list(rows[row]) + ["", "", "", ""])[:4]
    r[field] = value
    action, paragraph = r[1], r[2]
    if not action:
        return None
    for i, other in enumerate(rows):
        if i != row and len(other) > 2 and other[1] == action and other[2] == paragraph:
            return ("Rule %s/%s is already defined (row %d)" % (action, paragraph or "-", i + 1),
                    False)
    return None


class ListTableModel(QAbstractTableModel):
    def __init__(self, data, columns, row_width, validate=None, warn=None):
        super().__init__()
        self._data = data                # list of rows, edited in place
        self._columns = columns          # [(row_index, header), ...]
        self._row_width = row_width       # total row length incl. index-0 sort field
        self._validate = validate         # (row, field, value, rows) -> reason or None
        self._warn = warn                 # called with the reason string on rejection

    def set_data(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._columns[section][1]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        row = self._data[index.row()]
        ci = self._columns[index.column()][0]
        return "" if ci >= len(row) else str(row[ci])

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        row = self._data[index.row()]
        ci = self._columns[index.column()][0]
        if self._validate is not None:
            result = self._validate(index.row(), ci, value, self._data)
            if result:                               # (message, blocking)
                message, blocking = result
                if self._warn:
                    self._warn(message)
                if blocking:                         # hard reject: do not accept the value
                    return False
        while len(row) <= ci:
            row.append("")
        row[ci] = value
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def add_row(self):
        n = len(self._data)
        self.beginInsertRows(QModelIndex(), n, n)
        self._data.append([""] * self._row_width)
        self.endInsertRows()

    def delete_row(self, row):
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._data[row]
            self.endRemoveRows()


class _DragReorderList(QListWidget):
    """Single-selection list whose rows can be reordered by dragging up/down;
    calls ``on_reordered`` after a drop so the owner can resync its backing list."""

    def __init__(self, on_reordered):
        super().__init__()
        self._on_reordered = on_reordered
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dropEvent(self, event):
        self.blockSignals(True)             # suppress spurious itemChanged mid-move
        super().dropEvent(event)
        self.blockSignals(False)
        self._on_reordered()


class StringListEditor(QWidget):
    """An editable list of non-empty, unique strings (e.g. the class-name
    vocabulary), backed by a Python list edited in place. Add prompts for a value
    and rejects blank or duplicate entries; items can be renamed inline (a rename
    to blank is reverted) and reordered by dragging up/down; Delete removes the
    selected one."""

    def __init__(self, add_label="Add", delete_label="Delete", prompt="Value:",
                 can_delete=None):
        super().__init__()
        self._data = []
        self._prompt = prompt
        self._can_delete = can_delete       # value -> reason string (blocked) or None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.list = _DragReorderList(self._resync)
        self.list.itemChanged.connect(self._changed)
        v.addWidget(self.list)
        buttons = QHBoxLayout()
        add = QPushButton(add_label)
        add.clicked.connect(self._add)
        delete = QPushButton(delete_label)
        delete.clicked.connect(self._delete)
        buttons.addWidget(add)
        buttons.addWidget(delete)
        buttons.addStretch()
        v.addLayout(buttons)

    def set_data(self, data):
        self._data = data                       # edited in place
        self.list.blockSignals(True)
        self.list.clear()
        for s in data:
            item = QListWidgetItem(str(s))
            # editable + draggable, but not a drop target, so drags reorder rows
            item.setFlags((item.flags() | Qt.ItemIsEditable | Qt.ItemIsDragEnabled)
                          & ~Qt.ItemIsDropEnabled)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _resync(self):
        """Rewrite the backing list in place to match the current row order
        (called after a drag reorder)."""
        self._data[:] = [self.list.item(i).text() for i in range(self.list.count())]

    def add_value(self, text):
        """Append ``text`` if it is non-empty and not already present. Returns
        True if it was added."""
        text = (text or "").strip()
        if not text or text in self._data:
            return False
        self._data.append(text)
        self.set_data(self._data)
        self.list.setCurrentRow(len(self._data) - 1)
        return True

    def _changed(self, item):
        row = self.list.row(item)
        if not (0 <= row < len(self._data)):
            return
        text = item.text().strip()
        if text and text != item.text():        # normalise surrounding whitespace
            self.list.blockSignals(True)
            item.setText(text)
            self.list.blockSignals(False)
        if text:
            self._data[row] = text
        else:                                    # reject a rename to blank: restore
            self.list.blockSignals(True)
            item.setText(str(self._data[row]))
            self.list.blockSignals(False)

    def _add(self):
        d = QInputDialog(self)
        d.setWindowTitle("Add")
        d.setLabelText(self._prompt)
        if dialogs.run_modal(d):
            self.add_value(d.textValue())

    def _delete(self):
        row = self.list.currentRow()
        if not (0 <= row < len(self._data)):
            return
        value = self._data[row]
        reason = self._can_delete(value) if self._can_delete else None
        if reason:
            dialogs.warn(self, "Cannot delete",
                         "Cannot delete %r: %s." % (value, reason))
            return
        if str(value).strip() and not confirm_delete(self, "%r" % value):
            return
        del self._data[row]
        self.set_data(self._data)


class GridTab(QWidget):
    def __init__(self, columns, row_width, validate=None, warn=None):
        super().__init__()
        self.model = ListTableModel([], columns, row_width, validate=validate, warn=warn)
        v = QVBoxLayout(self)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.view)
        buttons = QHBoxLayout()
        add = QPushButton("Add row")
        add.clicked.connect(self.model.add_row)
        delete = QPushButton("Delete row")
        delete.clicked.connect(self._delete_selected)
        buttons.addWidget(add)
        buttons.addWidget(delete)
        buttons.addStretch()
        v.addLayout(buttons)

    def set_data(self, data):
        self.model.set_data(data)

    def _delete_selected(self):
        idx = self.view.currentIndex()
        if not idx.isValid():
            return
        row = self.model._data[idx.row()] if idx.row() < len(self.model._data) else []
        if any(str(x).strip() for x in row[1:]) and not confirm_delete(self, "this row"):
            return                                       # row[0] is the internal sort field
        self.model.delete_row(idx.row())


# --- Races tab: native, suffix-free heat scheduling ------------------------

def _base_classes(eventdata):
    """Distinct base class names, in class-list order (each base is one schedulable class)."""
    out, seen = [], set()
    for c in get_classes(eventdata):
        b = getclass(c)
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


def _phases_of(eventdata, base):
    """Phase kinds defined for ``base``, in canonical order (time trial → qualification →
    circuit → endurance)."""
    kinds = {race_kind(eventdata, c) for c in get_classes(eventdata) if getclass(c) == base}
    return [k for k in _PHASE_ORDER if k in kinds]


def _synth_for(eventdata, base, kind):
    """The synthesized (legacy) class name for ``(base, kind)`` — the addressing key the
    pattern/heat helpers use — or None if the base has no such phase."""
    for c in get_classes(eventdata):
        if getclass(c) == base and race_kind(eventdata, c) == kind:
            return c
    return None


def _heat_numbers(eventdata, base, kind):
    """Valid heat numbers ``1..N`` for ``base``'s ``kind`` phase (N from its pattern)."""
    cl = _synth_for(eventdata, base, kind)
    pat = class_pattern(eventdata, cl) if cl else None
    if not pat:
        return []
    return list(range(1, len(crack_race_pattern(pat)[0]) + 1))


class RaceHeatsModel(QAbstractTableModel):
    """One race's scheduled heats as native, suffix-free entries
    (``{name, kind, number, occurrence}``), edited in place. Columns Class (base) / Phase
    (kind) / Heat (number) — the operator never sees or types a `/T`,`/Q`,`t`,`q` suffix.
    Setting the class resets its phase to the finals phase and heat to 1; setting the phase
    resets the heat to 1."""

    COLS = ["Class", "Phase", "Heat"]

    def __init__(self, window, warn=None):
        super().__init__()
        self.window = window
        self._race = []
        self._warn = warn

    @property
    def eventdata(self):
        return self.window.eventdata

    def set_race(self, race):
        self.beginResetModel()
        self._race = race
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._race)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        e = self._race[index.row()]
        col = index.column()
        if col == 0:
            return e.get("name", "")
        if col == 1:
            return _PHASE_LABEL.get(e.get("kind", ""), "")
        num = e.get("number") or 0
        if not num:
            return ""
        occ = e.get("occurrence", 0)
        return "%d (restart %d)" % (num, occ) if occ else str(num)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable   # display-only; heats are added via the form

    def add_entry(self, entry):
        n = len(self._race)
        self.beginInsertRows(QModelIndex(), n, n)
        self._race.append(entry)
        self.endInsertRows()

    def delete_row(self, row):
        if 0 <= row < len(self._race):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._race[row]
            self.endRemoveRows()


class RacesTab(QWidget):
    """Schedule which heat each class runs in each race. The left column lists the races; the
    right pane is an **add-a-heat form** — three always-visible cascading dropdowns (Class →
    Phase → Heat) + Add — over a read-only table of the selected race's heats. Suffix-free: the
    operator picks a base class, a phase, and a heat number; nothing shows or types a /T,/Q,t,q."""

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self._races = []
        h = QHBoxLayout(self)
        left = QVBoxLayout()
        self.race_list = QListWidget()
        self.race_list.currentRowChanged.connect(self._select)
        left.addWidget(self.race_list)
        lb = QHBoxLayout()
        add = QPushButton("Add race")
        add.clicked.connect(self._add_race)
        delete = QPushButton("Delete race")
        delete.clicked.connect(self._delete_race)
        lb.addWidget(add)
        lb.addWidget(delete)
        left.addLayout(lb)
        h.addLayout(left, 1)

        right = QVBoxLayout()
        form = QHBoxLayout()                            # visible dropdowns, so the feature is obvious
        form.addWidget(QLabel("Add heat:"))
        self.class_combo = combo()
        self.phase_combo = combo()
        self.heat_combo = combo()
        form.addWidget(self.class_combo, 2)
        form.addWidget(self.phase_combo, 2)
        form.addWidget(self.heat_combo, 1)
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_heat)
        form.addWidget(self.add_btn)
        right.addLayout(form)

        warn = window.log if window is not None else None
        self.model = RaceHeatsModel(window, warn=warn)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setEditTriggers(QTableView.NoEditTriggers)   # read-only; edit via the form
        self.view.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self.view)
        del_heat = QPushButton("Delete heat")
        del_heat.clicked.connect(self._delete_heat)
        rb = QHBoxLayout()
        rb.addWidget(del_heat)
        rb.addStretch()
        right.addLayout(rb)
        h.addLayout(right, 2)

        if window is not None:                          # cascade: class -> its phases -> heat numbers
            self.class_combo.currentTextChanged.connect(self._reload_phases)
            self.phase_combo.currentTextChanged.connect(self._reload_heats)
        self.model.rowsInserted.connect(self._update_current_label)
        self.model.rowsRemoved.connect(self._update_current_label)

    # ---- the add-a-heat form ----
    def _defined_classes(self):
        return _base_classes(self.window.eventdata)

    def _reload_class_combo(self):
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        if self.window is not None:
            self.class_combo.addItems(self._defined_classes())
        self.class_combo.blockSignals(False)
        self._reload_phases()

    def _reload_phases(self, *args):
        base = self.class_combo.currentText().strip()
        self.phase_combo.blockSignals(True)
        self.phase_combo.clear()
        if base and self.window is not None:
            self.phase_combo.addItems(
                [_PHASE_LABEL[k] for k in _phases_of(self.window.eventdata, base)])
        self.phase_combo.blockSignals(False)
        self._reload_heats()

    def _reload_heats(self, *args):
        base, kind = self.class_combo.currentText().strip(), self._form_kind()
        self.heat_combo.blockSignals(True)
        self.heat_combo.clear()
        if base and kind and self.window is not None:
            self.heat_combo.addItems(
                [str(n) for n in _heat_numbers(self.window.eventdata, base, kind)])
        self.heat_combo.blockSignals(False)

    def _form_kind(self):
        lbl = self.phase_combo.currentText()
        return next((k for k, l in _PHASE_LABEL.items() if l == lbl), "")

    def _add_heat(self):
        if self.window is None or self.race_list.currentRow() < 0:
            return
        base = self.class_combo.currentText().strip()
        if not base or base not in self._defined_classes():
            if base:
                self.window.log("Class %s is not a defined class" % base)
            return
        if any(isinstance(e, dict) and e.get("name") == base for e in self.model._race):
            self.window.log("Class %s is already in this race" % base)
            return
        try:
            number = int(self.heat_combo.currentText())
        except (ValueError, TypeError):
            number = 1
        self.model.add_entry({"name": base, "kind": self._form_kind(),
                              "number": number, "occurrence": 0})
        self._update_current_label()

    def _delete_heat(self):
        idx = self.view.currentIndex()
        if not idx.isValid():
            return
        e = self.model._race[idx.row()] if idx.row() < len(self.model._race) else {}
        if e.get("name") and not confirm_delete(self, "heat %s" % (_entry_label(e) or e.get("name"))):
            return
        self.model.delete_row(idx.row())
        self._update_current_label()

    # ---- races ----
    def set_data(self, races):
        self._races = races
        self._reload_class_combo()
        self._refill()

    def _refill(self):
        self.race_list.clear()
        for i in range(len(self._races)):
            self.race_list.addItem(race_label(i, self._races[i]))
        if self._races:
            self.race_list.setCurrentRow(0)
        else:
            self.model.set_race([])
        self._sync_enabled()

    def _sync_enabled(self):
        self.add_btn.setEnabled(self.race_list.currentRow() >= 0)

    def _update_current_label(self, *args):
        row = self.race_list.currentRow()
        item = self.race_list.item(row) if 0 <= row < len(self._races) else None
        if item is not None:
            item.setText(race_label(row, self._races[row]))

    def _select(self, row):
        if 0 <= row < len(self._races):
            self.model.set_race(self._races[row])
        self._sync_enabled()

    def _add_race(self):
        self._races.append([])                          # a new, empty race (fill it via the form)
        self._refill()
        self.race_list.setCurrentRow(len(self._races) - 1)

    def _delete_race(self):
        row = self.race_list.currentRow()
        if not (0 <= row < len(self._races)):
            return
        race = self._races[row]
        if any(isinstance(e, dict) and e.get("name") for e in race) \
                and not confirm_delete(self, "Race %d and its scheduled heats" % (row + 1)):
            return
        del self._races[row]
        self._refill()
