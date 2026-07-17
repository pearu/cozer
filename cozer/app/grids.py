"""Editable data-entry grids for the General Information tab.

``ListTableModel`` edits an eventdata list-of-lists in place (each row keeps a
leading internal sort field at index 0, mirroring legacy). ``GridTab`` wraps a
table view with Add/Delete buttons; ``RacesTab`` handles the nested race list
(a list of races, each a list of class/heat rows).
"""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QPushButton, QTableView, QVBoxLayout, QWidget,
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
