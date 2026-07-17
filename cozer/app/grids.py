"""Editable data-entry grids for the General Information tab.

``ListTableModel`` edits an eventdata list-of-lists in place (each row keeps a
leading internal sort field at index 0, mirroring legacy). ``GridTab`` wraps a
table view with Add/Delete buttons; ``RacesTab`` handles the nested race list
(a list of races, each a list of class/heat rows).
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QTableView, QVBoxLayout, QWidget,
)


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


class ListTableModel(QAbstractTableModel):
    def __init__(self, data, columns, row_width):
        super().__init__()
        self._data = data                # list of rows, edited in place
        self._columns = columns          # [(row_index, header), ...]
        self._row_width = row_width       # total row length incl. index-0 sort field

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
    def __init__(self, columns, row_width):
        super().__init__()
        self.model = ListTableModel([], columns, row_width)
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
    def __init__(self):
        super().__init__()
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
        self.grid = GridTab([(1, "Class"), (2, "Heat")], 3)
        h.addWidget(self.grid, 2)
        # Keep the selected race's list label ("Race N: CLASS HEAT, ...") in sync
        # as its class/heat cells are edited or rows added/removed.
        self.grid.model.dataChanged.connect(self._update_current_label)
        self.grid.model.rowsInserted.connect(self._update_current_label)
        self.grid.model.rowsRemoved.connect(self._update_current_label)

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
