"""Editable data-entry grids for the General Information tab.

``ListTableModel`` edits an eventdata list-of-lists in place (each row keeps a
leading internal sort field at index 0, mirroring legacy). ``GridTab`` wraps a
table view with Add/Delete buttons; ``RacesTab`` handles the nested race list
(a list of races, each a list of class/heat rows).
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QStyledItemDelegate, QTableView, QVBoxLayout,
    QWidget,
)

from cozer.classes import getclass
from cozer.racepattern import class_pattern, crack_race_pattern, get_classes, race_kind

# Suffix-free phase presentation. Circuit (the main/final race) needs no tag; the others get
# a short tag in compact labels and a full word in dropdowns — no `/T`,`/Q` or `t`/`q` anywhere.
_PHASE_ORDER = ["timetrial", "qualification", "circuit", "endurance"]
_PHASE_LABEL = {"timetrial": "Time trial", "qualification": "Qualification",
                "circuit": "Circuit", "endurance": "Endurance"}
_PHASE_TAG = {"timetrial": "TT", "qualification": "Q"}   # circuit/endurance: no tag


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


class SuggestingDelegate(QStyledItemDelegate):
    """An editable combo-box cell editor: it offers the suggestions from
    ``items_fn(index)`` but lets the operator type an override (cozer suggests,
    the organizer decides)."""

    def __init__(self, items_fn, parent=None):
        super().__init__(parent)
        self._items_fn = items_fn

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.addItems([str(x) for x in self._items_fn(index)])
        return combo

    def setEditorData(self, editor, index):
        editor.setCurrentText(index.data() or "")

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)


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
        text, ok = QInputDialog.getText(self, "Add", self._prompt)
        if ok:
            self.add_value(text)

    def _delete(self):
        row = self.list.currentRow()
        if not (0 <= row < len(self._data)):
            return
        value = self._data[row]
        reason = self._can_delete(value) if self._can_delete else None
        if reason:
            QMessageBox.information(self, "Cannot delete",
                                    "Cannot delete %r: %s." % (value, reason))
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
        if idx.isValid():
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
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def _reject(self, msg):
        if self._warn:
            self._warn(msg)
        return False

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        e = self._race[index.row()]
        col = index.column()
        value = (value or "").strip()
        if col == 0:                                    # Class (base)
            if value and value not in _base_classes(self.eventdata):
                return self._reject("Class %s is not a defined class" % value)
            if value and any(o is not e and o.get("name") == value for o in self._race):
                return self._reject("Class %s is already in this race" % value)
            e["name"] = value
            phases = _phases_of(self.eventdata, value)
            e["kind"] = phases[-1] if phases else ""    # default to the finals phase
            e["number"] = 1 if e["kind"] else 0
            e["occurrence"] = 0
        elif col == 1:                                  # Phase (kind); value is a label
            kind = next((k for k, lbl in _PHASE_LABEL.items() if lbl == value), value)
            if kind and kind not in _phases_of(self.eventdata, e.get("name", "")):
                return self._reject("%s has no %s phase" % (e.get("name", ""), value or "?"))
            e["kind"] = kind
            e["number"] = 1 if kind else 0
            e["occurrence"] = 0
        else:                                           # Heat (number)
            try:
                num = int(str(value).split()[0])
            except (ValueError, IndexError):
                return False
            valid = _heat_numbers(self.eventdata, e.get("name", ""), e.get("kind", ""))
            if valid and num not in valid and self._warn:  # advisory, not blocked
                self._warn("Heat %d is out of range for %s %s (1..%d)"
                           % (num, e.get("name", ""),
                              _PHASE_LABEL.get(e.get("kind", ""), ""), valid[-1]))
            e["number"] = num
        self.dataChanged.emit(index, self.index(index.row(), len(self.COLS) - 1))
        return True

    def add_row(self):
        n = len(self._race)
        self.beginInsertRows(QModelIndex(), n, n)
        self._race.append({"name": "", "kind": "", "number": 0, "occurrence": 0})
        self.endInsertRows()

    def delete_row(self, row):
        if 0 <= row < len(self._race):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._race[row]
            self.endRemoveRows()


class RacesTab(QWidget):
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
        warn = window.log if window is not None else None
        self.model = RaceHeatsModel(window, warn=warn)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.horizontalHeader().setStretchLastSection(True)
        right.addWidget(self.view)
        if window is not None:      # cascading suffix-free dropdowns: class → phase → heat number
            self.view.setItemDelegateForColumn(
                0, SuggestingDelegate(lambda idx: self._defined_classes(), self.view))
            self.view.setItemDelegateForColumn(
                1, SuggestingDelegate(self._phase_items, self.view))
            self.view.setItemDelegateForColumn(
                2, SuggestingDelegate(self._heat_items, self.view))
        rb = QHBoxLayout()
        addr = QPushButton("Add row")
        addr.clicked.connect(self.model.add_row)
        delr = QPushButton("Delete row")
        delr.clicked.connect(self._delete_row)
        rb.addWidget(addr)
        rb.addWidget(delr)
        rb.addStretch()
        right.addLayout(rb)
        h.addLayout(right, 2)

        # Keep the selected race's list label ("Race N: GT15 1, …") in sync as cells/rows change.
        self.model.dataChanged.connect(self._update_current_label)
        self.model.rowsInserted.connect(self._update_current_label)
        self.model.rowsRemoved.connect(self._update_current_label)

    def _defined_classes(self):
        return _base_classes(self.window.eventdata)

    def _row_entry(self, index):
        r = index.row()
        return self.model._race[r] if 0 <= r < len(self.model._race) else {}

    def _phase_items(self, index):
        base = self._row_entry(index).get("name", "")
        return [_PHASE_LABEL[k] for k in _phases_of(self.window.eventdata, base)] if base else []

    def _heat_items(self, index):
        e = self._row_entry(index)
        return [str(n) for n in _heat_numbers(self.window.eventdata,
                                              e.get("name", ""), e.get("kind", ""))]

    def _delete_row(self):
        idx = self.view.currentIndex()
        if idx.isValid():
            self.model.delete_row(idx.row())

    def set_data(self, races):
        self._races = races
        self._refill()

    def _refill(self):
        self.race_list.clear()
        for i in range(len(self._races)):
            self.race_list.addItem(race_label(i, self._races[i]))
        if self._races:
            self.race_list.setCurrentRow(0)
        else:
            self.model.set_race([])

    def _update_current_label(self, *args):
        row = self.race_list.currentRow()
        item = self.race_list.item(row) if 0 <= row < len(self._races) else None
        if item is not None:
            item.setText(race_label(row, self._races[row]))

    def _select(self, row):
        if 0 <= row < len(self._races):
            self.model.set_race(self._races[row])

    def _add_race(self):
        self._races.append([{"name": "", "kind": "", "number": 0, "occurrence": 0}])
        self._refill()
        self.race_list.setCurrentRow(len(self._races) - 1)

    def _delete_race(self):
        row = self.race_list.currentRow()
        if 0 <= row < len(self._races):
            del self._races[row]
            self._refill()
