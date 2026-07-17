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

from cozer.racepattern import get_heats


def race_label(index, race):
    """Human label for a race: ``"Race N: CLASS1 HEAT1, CLASS2 HEAT2, ..."``.

    ``race`` is a list of ``[_, class, heat]`` rows (index-0 is the sort field);
    rows with a blank class or heat are skipped. A race with no filled rows keeps
    the bare ``"Race N"``. ``index`` is 0-based; the label shows ``N = index+1``.
    """
    parts = ["%s %s" % (e[1], e[2]) for e in (race or [])
             if len(e) > 2 and e[1] and e[2]]
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


def race_cell_validator(defined_classes, next_heats):
    """Build a race-grid validator. ``defined_classes()`` returns the event's
    defined class names; ``next_heats(cl)`` returns the valid *next* heats for a
    class at this race (from get_heats — encodes ordering N before N+1 and the
    N -> Nr -> NR restart progression).

    A class that is not defined, or that already appears in the race, is
    **hard-rejected** (a class runs one heat per race, and the pattern/heat logic
    depend on a defined class); an out-of-order heat is **advisory** (logged, but
    accepted — the organizer may overrule for restarts/weather)."""
    def validate(row, field, value, rows):
        if field == 1 and value:                      # class column
            if value not in defined_classes():
                return ("Class %s is not a defined class" % value, True)   # hard reject
            for i, other in enumerate(rows):
                if i != row and len(other) > 1 and other[1] == value:
                    return ("Class %s is already in this race (row %d)" % (value, i + 1), True)
        elif field == 2 and value:                    # heat column
            cl = rows[row][1] if len(rows[row]) > 1 else ""
            if cl and cl in defined_classes():
                nh = next_heats(cl)
                if nh and value not in nh:
                    return ("Heat %s is not the expected next heat for class %s (expected %s)"
                            % (value, cl, "/".join(nh)), False)
        return None
    return validate


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
        validate = warn = None
        if window is not None:
            validate = race_cell_validator(self._defined_classes, self._next_heats)
            warn = window.log
        self.grid = GridTab([(1, "Class"), (2, "Heat")], 3, validate=validate, warn=warn)
        h.addWidget(self.grid, 2)
        if window is not None:      # editable dropdowns suggest classes / valid next heats
            self.grid.view.setItemDelegateForColumn(
                0, SuggestingDelegate(lambda idx: self._defined_classes(), self.grid.view))
            self.grid.view.setItemDelegateForColumn(
                1, SuggestingDelegate(self._heat_items, self.grid.view))
        # Keep the selected race's list label ("Race N: CLASS HEAT, ...") in sync
        # as its class/heat cells are edited or rows added/removed.
        self.grid.model.dataChanged.connect(self._update_current_label)
        self.grid.model.rowsInserted.connect(self._update_current_label)
        self.grid.model.rowsRemoved.connect(self._update_current_label)

    def _defined_classes(self):
        return [c[1] for c in self.window.eventdata.get("classes", [])
                if len(c) > 1 and c[1]]

    def _next_heats(self, cl):
        """Valid next heats for class ``cl`` at the selected race (from get_heats;
        encodes the heat/restart ordering). Empty if unknown."""
        try:
            return get_heats(self.window.eventdata, self.race_list.currentRow()).get(cl, [])
        except Exception:
            return []

    def _heat_items(self, index):
        cl = self.grid.model.data(self.grid.model.index(index.row(), 0)) or ""
        return self._next_heats(cl) if cl else []

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
            self.grid.set_data([])

    def _update_current_label(self, *args):
        row = self.race_list.currentRow()
        item = self.race_list.item(row) if 0 <= row < len(self._races) else None
        if item is not None:
            item.setText(race_label(row, self._races[row]))

    def _select(self, row):
        if 0 <= row < len(self._races):
            self.grid.set_data(self._races[row])

    def _add_race(self):
        self._races.append([["", "", ""]])
        self._refill()
        self.race_list.setCurrentRow(len(self._races) - 1)

    def _delete_race(self):
        row = self.race_list.currentRow()
        if 0 <= row < len(self._races):
            del self._races[row]
            self._refill()
