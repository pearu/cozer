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
import re

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
    QStyledItemDelegate, QTableView, QTabWidget, QVBoxLayout, QWidget,
)

from cozer.app import ruleset as rulesetmod
from cozer.app.grids import confirm_delete
from cozer.classes import getclass
from cozer.countries import IOC, is_ioc_code
from cozer.qualification import qualification_counts
from cozer.racepattern import (
    class_pattern, crack_race_pattern, describe_pattern, format_circuit_pattern,
    parse_simple_pattern, race_kind,
)

# The ``!qualification[N,N,M]`` hint token on a qualification phase's pattern.
_QUAL_TOKEN = re.compile(r"\s*!qualification\[[\d,\s]*\]", re.I)


def _strip_qual(pattern):
    """A pattern with any ``!qualification[...]`` token removed."""
    return _QUAL_TOKEN.sub("", pattern or "").strip()


def _with_qual(pattern, counts_str):
    """Append ``!qualification[<counts>]`` (from a ``'4,4,4'`` string) to a stripped
    pattern; returns the bare pattern when no counts are given."""
    base = _strip_qual(pattern)
    nums = [s.strip() for s in (counts_str or "").split(",") if s.strip()]
    return "%s!qualification[%s]" % (base, ",".join(nums)) if nums else base


# A qualification's default number of qheats when seeding: qheat1 + qheat2 + repechage
# (the classic 305.04.03 split). The operator's qualifiers tuple then drives the real count.
_DEFAULT_QHEATS = 3


def _course_prefill(finals_pattern, heats=1):
    """A starting pattern for a time-trial or qualification phase, derived from the finals:
    keep the lap structure (all phases run the same **course**) and reset the scoring (a time
    trial / qheat is ranked by lap, not scored). ``heats`` is the phase's heat count — a time
    trial is a single solo run (1); a qualification seeds ``_DEFAULT_QHEATS`` qheats (the
    Timer runs one heat per pattern heat, so it must match the qualifiers tuple length).
    ``""`` for a non-circuit finals (e.g. endurance) — nothing sensible to seed."""
    parsed = parse_simple_pattern(_strip_qual(finals_pattern))
    if not parsed:
        return ""
    return format_circuit_pattern(parsed["first"], parsed["other"], parsed["laps"], heats, 1)


def _set_heats(pattern, n):
    """``pattern`` with its leading heat count set to ``n`` (keeps the course + scoring); the
    original if it can't be reparsed."""
    parsed = parse_simple_pattern(_strip_qual(pattern))
    if not parsed:
        return pattern
    return format_circuit_pattern(parsed["first"], parsed["other"], parsed["laps"], n,
                                  max(1, min(parsed["scored"], n)))


_FINALS_KINDS = ("circuit", "endurance")


def _is_native(eventdata):
    return eventdata.get("schema", 1) >= 2


def _class_name(row):
    """The class/base name of a class-list row on either shape (native {name,…} or legacy list)."""
    return row.get("name") if isinstance(row, dict) else (row[1] if len(row) > 1 else "")


def base_classes(eventdata):
    """Distinct BASE class names in class-list order — a phase event's phases collapse onto
    their base, so each base is one tab. Both shapes (native entries / legacy suffixed rows)."""
    out, seen = [], set()
    for row in eventdata.get("classes", []) or []:
        b = getclass(_class_name(row))
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


def _phase_kinds(eventdata, base):
    """The set of phase kinds present for ``base`` (both shapes)."""
    if _is_native(eventdata):
        for e in eventdata.get("classes", []) or []:
            if e.get("name") == base:
                return {ph["kind"] for ph in e.get("phases", []) or []}
        return set()
    return {race_kind(eventdata, row[1]) for row in eventdata.get("classes", []) or []
            if len(row) > 1 and row[1] and getclass(row[1]) == base}


def _finals_kind(eventdata, base):
    """The base's finals phase kind (circuit / endurance) if present, else 'circuit'."""
    for k in _phase_kinds(eventdata, base):
        if k in _FINALS_KINDS:
            return k
    return "circuit"


def phase_pattern(eventdata, base, kind):
    """The full pattern (incl. the ``!qualification[…]`` token) for ``base``'s ``kind`` phase,
    or ``None``. Both shapes."""
    if _is_native(eventdata):
        for e in eventdata.get("classes", []) or []:
            if e.get("name") == base:
                for ph in e.get("phases", []) or []:
                    if ph["kind"] == kind:
                        pat = ph.get("pattern", "") or ""
                        if ph.get("qualifiers"):
                            pat = "%s!qualification[%s]" % (pat, ",".join(str(c) for c in ph["qualifiers"]))
                        return pat or None
        return None
    suffix = "/T" if kind == "timetrial" else "/Q" if kind == "qualification" else ""
    return class_pattern(eventdata, base + suffix)


def _native_entry(eventdata, base, create=False):
    for e in eventdata.get("classes", []) or []:
        if e.get("name") == base:
            return e
    if create:
        e = {"name": base, "phases": []}
        eventdata.setdefault("classes", []).append(e)
        return e
    return None


def _legacy_name(base, kind):
    return base + "/T" if kind == "timetrial" else base + "/Q" if kind == "qualification" else base


def set_phase(eventdata, base, kind, pattern):
    """Create or update ``base``'s ``kind`` phase to ``pattern`` (native: qualifiers split off
    the pattern into a list; legacy: a suffixed class row)."""
    if _is_native(eventdata):
        entry = _native_entry(eventdata, base, create=True)
        bare, quals = _strip_qual(pattern), qualification_counts(pattern)
        ph = next((p for p in entry["phases"] if p["kind"] == kind), None)
        if ph is None:
            ph = {"kind": kind}
            entry["phases"].append(ph)
        ph["pattern"] = bare
        if quals:
            ph["qualifiers"] = list(quals)
        else:
            ph.pop("qualifiers", None)
        return
    name = _legacy_name(base, kind)
    for row in eventdata.setdefault("classes", []):
        if len(row) > 1 and row[1] == name:
            while len(row) <= 2:
                row.append("")
            row[2] = pattern
            return
    eventdata.setdefault("classes", []).append(["", name, pattern])


def remove_phase(eventdata, base, kind):
    """Remove ``base``'s ``kind`` phase (both shapes)."""
    if _is_native(eventdata):
        e = _native_entry(eventdata, base)
        if e is not None:
            e["phases"] = [ph for ph in e.get("phases", []) if ph["kind"] != kind]
        return
    name = _legacy_name(base, kind)
    eventdata["classes"] = [r for r in eventdata.get("classes", [])
                            if not (len(r) > 1 and r[1] == name)]


def add_base(eventdata, name):
    """Add a new base class (with an empty finals phase)."""
    if _is_native(eventdata):
        eventdata.setdefault("classes", []).append(
            {"name": name, "phases": [{"kind": "circuit", "pattern": ""}]})
    else:
        eventdata.setdefault("classes", []).append(["", name, ""])


def remove_base(eventdata, base):
    """Remove a base class and all its phases (both shapes)."""
    if _is_native(eventdata):
        eventdata["classes"] = [e for e in eventdata.get("classes", []) if e.get("name") != base]
    else:
        eventdata["classes"] = [r for r in eventdata.get("classes", [])
                                if not (len(r) > 1 and r[1] and getclass(r[1]) == base)]


# Shown as the qheat1 column's header tooltip — tells the operator when it applies.
_QHEAT1_TOOLTIP = (
    "Qualification only: tick the boats the organizer placed in the first qualifying "
    "heat (qheat1), per their group split. The rest of the class become qheat2, and the "
    "repechage (last) heat is filled from the non-qualifiers. Ignored for classes "
    "without qualification heats.")


def has_qualification(eventdata, cl):
    """True if class ``cl``'s base has a qualification-kind phase — the condition under which
    the qheat1 membership checkbox is shown (§5.1). Both shapes."""
    return "qualification" in _phase_kinds(eventdata, getclass(cl))


# --- per-class participant table --------------------------------------------

class ParticipantClassModel(QAbstractTableModel):
    """A view of the master participants list filtered to one class. Edits,
    inserts and deletes operate on the master list in place; boat numbers are
    kept unique within the class."""

    COLS = [(5, "Boat #"), (1, "Name"), (2, "Surname"), (3, "From"), (6, "Nationality")]

    def __init__(self, participants, classname, warn=None, qheat1=None, show_qheat1=False):
        super().__init__()
        self._all = participants          # master list, edited in place
        self._class = classname
        self._warn = warn
        self._qheat1 = qheat1 if qheat1 is not None else {}   # eventdata['qheat1'] (per-base sets)
        # The qheat1 membership checkbox (sentinel column ``None``) appears only for a
        # class that has a qualification phase.
        self._cols = list(self.COLS) + ([(None, "qheat1")] if show_qheat1 else [])
        self._reindex()

    def _reindex(self):
        self._idx = [i for i, p in enumerate(self._all)
                     if len(p) > 4 and p[4] == self._class]

    def _qheat1_list(self):
        """The mutable qheat1 boat-id list for this class's base (created on demand)."""
        return self._qheat1.setdefault(getclass(self._class), [])

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._idx)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._cols)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._cols[section][1]
            if role == Qt.ToolTipRole and self._cols[section][0] is None:
                return _QHEAT1_TOOLTIP
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._all[self._idx[index.row()]]
        ci = self._cols[index.column()][0]
        if ci is None:                    # the qheat1 checkbox column
            if role == Qt.CheckStateRole:
                bid = str(row[5]) if len(row) > 5 else ""
                return Qt.Checked if bid and bid in self._qheat1_list() else Qt.Unchecked
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            return "" if ci >= len(row) else str(row[ci])
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        master = self._idx[index.row()]
        row = self._all[master]
        ci = self._cols[index.column()][0]
        if ci is None:                    # toggle qheat1 membership (organizer's split)
            if role != Qt.CheckStateRole:
                return False
            bid = str(row[5]) if len(row) > 5 else ""
            if not bid:
                return False
            lst = self._qheat1_list()
            if Qt.CheckState(value) == Qt.Checked:      # coerces both the enum and a raw int
                if bid not in lst:
                    lst.append(bid)
            elif bid in lst:
                lst.remove(bid)
            self.dataChanged.emit(index, index)
            return True
        if role != Qt.EditRole:
            return False
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
        if ci == 6 and value and not is_ioc_code(value):   # Nationality: soft-validate the IOC code
            if self._warn:                                 # accepted anyway (soft) — catches e.g. LIT->LTU
                self._warn("%r is not an IOC nationality code — pick one from the list" % value)
        while len(row) <= ci:
            row.append("")
        row[ci] = value
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        f = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self._cols[index.column()][0] is None:
            return f | Qt.ItemIsUserCheckable
        return f | Qt.ItemIsEditable

    def add_row(self):
        n = len(self._idx)
        self.beginInsertRows(QModelIndex(), n, n)
        self._all.append(["", "", "", "", self._class, "", ""])   # index 6 = nationality
        self._reindex()
        self.endInsertRows()

    def delete_row(self, r):
        if 0 <= r < len(self._idx):
            self.beginRemoveRows(QModelIndex(), r, r)
            del self._all[self._idx[r]]
            self._reindex()
            self.endRemoveRows()


class NationalityDelegate(QStyledItemDelegate):
    """Combo-box editor for the Nationality column: a dropdown of the IOC 3-letter codes shown
    as ``"EST — Estonia"`` (UIM §209 allows the code or the English name), storing the bare code
    ``"EST"``. Editable + type-ahead so the operator can type a code; the cell also shows the
    ``"EST — Estonia"`` form (see displayText) so the country is readable."""

    _items = sorted(IOC.items())            # (code, name) sorted by code — built once

    def displayText(self, value, locale):
        """Render the stored code as ``"EST — Estonia"`` so the country is readable in the cell
        (the model still stores the bare code). An unknown code (e.g. a legacy typo) shows as-is."""
        s = "" if value is None else str(value)
        name = IOC.get(s.strip().upper())
        return "%s — %s" % (s.strip().upper(), name) if name else s

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.addItem("", "")               # blank = clear the field
        for code, name in self._items:
            combo.addItem("%s — %s" % (code, name), code)
        combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        return combo

    def setEditorData(self, editor, index):
        code = (index.data() or "").strip().upper()
        i = editor.findData(code)
        editor.setCurrentIndex(i) if i >= 0 else editor.setEditText(code)

    def setModelData(self, editor, model, index):
        text = editor.currentText().strip()
        code = text.split()[0].upper() if text else ""   # "EST — Estonia" / "est" -> "EST"
        model.setData(index, code, Qt.EditRole)


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
    def __init__(self, participants, classname, warn=None, qheat1=None, show_qheat1=False):
        super().__init__()
        self._participants = participants
        self.model = ParticipantClassModel(participants, classname, warn, qheat1, show_qheat1)
        v = QVBoxLayout(self)
        self.view = QTableView()
        self.view.setModel(self.model)
        hdr = self.view.horizontalHeader()
        from_col = next(i for i, (f, _) in enumerate(self.model._cols) if f == 3)
        self.view.setItemDelegateForColumn(
            from_col, AutoCompleteDelegate(self._from_suggestions, self.view))
        nat_col = next((i for i, (f, _) in enumerate(self.model._cols) if f == 6), None)
        if nat_col is not None:                          # Nationality: IOC-code dropdown
            self.view.setItemDelegateForColumn(nat_col, NationalityDelegate(self.view))
        # 'From' (club) absorbs spare width; the Nationality and the qheat1 checkbox columns are
        # sized to content -- Nationality shows "CODE — Country", so this widens it enough to read
        # the country name without wasting space on a national (single-country) event.
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(from_col, QHeaderView.Stretch)
        for i, (field, _label) in enumerate(self.model._cols):
            if field == 6 or field is None:          # Nationality "CODE — Country" / checkbox column
                hdr.setSectionResizeMode(i, QHeaderView.ResizeToContents)
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
        if not idx.isValid():
            return
        r = idx.row()
        p = self.model._all[self.model._idx[r]] if r < len(self.model._idx) else []
        # real data = a name / surname / from / boat was entered (col 4 is the auto class name)
        if any(len(p) > i and str(p[i]).strip() for i in (1, 2, 3, 5)) \
                and not confirm_delete(self, "this participant"):
            return
        self.model.delete_row(r)


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


# --- phases dialog ----------------------------------------------------------

class PhasesDialog(QDialog):
    """Add / edit / remove a base class's **time-trial** and **qualification** phases. The
    finals (the plain class pattern) is edited separately; this manages the optional
    preceding phases so the operator never types a ``/T`` or ``/Q`` suffix — cozer writes
    those internal class rows. Qualifier counts are entered as a plain ``N,N,M`` list."""

    def __init__(self, parent, base, tt_pattern, qual_pattern, finals_pattern=""):
        super().__init__(parent)
        self.setWindowTitle("Phases — %s" % base)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Phases run <b>before</b> the final. Leave a box unchecked to omit "
                           "that phase; the final is the class's own race pattern."))

        self.tt_enable = QCheckBox("Time-trial phase")
        self.tt_enable.setChecked(bool(tt_pattern))
        # A new phase seeds its pattern from the finals course (heats / scoring reset);
        # an existing one keeps its own. Seeded even while unchecked, so ticking the box
        # reveals a ready pattern.
        self.tt_pat = QLineEdit(_strip_qual(tt_pattern) if tt_pattern
                                else _course_prefill(finals_pattern))
        self.tt_preview = QLabel("")
        self.tt_preview.setWordWrap(True)
        v.addWidget(self.tt_enable)
        ttf = QFormLayout()
        ttf.addRow("Pattern:", self.tt_pat)
        v.addLayout(ttf)
        v.addWidget(self.tt_preview)

        counts = qualification_counts(qual_pattern) if qual_pattern else None
        self.q_enable = QCheckBox("Qualification phase")
        self.q_enable.setChecked(bool(qual_pattern))
        self.q_pat = QLineEdit(_strip_qual(qual_pattern) if qual_pattern
                               else _course_prefill(finals_pattern, _DEFAULT_QHEATS))
        self.q_counts = QLineEdit(",".join(str(c) for c in counts) if counts else "")
        self.q_counts.setPlaceholderText("qualifiers per qheat, e.g. 4,4,4 (last = repechage)")
        self.q_preview = QLabel("")
        self.q_preview.setWordWrap(True)
        v.addWidget(self.q_enable)
        qf = QFormLayout()
        qf.addRow("Pattern:", self.q_pat)
        qf.addRow("Qualifiers per qheat:", self.q_counts)
        v.addLayout(qf)
        v.addWidget(self.q_preview)

        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self._accept)
        box.rejected.connect(self.reject)
        v.addWidget(box)
        self.tt_pat.textChanged.connect(self._update_previews)
        self.q_pat.textChanged.connect(self._update_previews)
        self.q_counts.textChanged.connect(self._counts_changed)
        self._update_previews()

    def _count_list(self):
        return [s for s in self.q_counts.text().replace(" ", "").split(",") if s]

    def _counts_changed(self, *_):
        # the Timer runs one qheat per pattern heat (get_heats), so keep the pattern's heat
        # count equal to the number of qualifiers entered (the tuple length).
        nums = self._count_list()
        if nums:
            newpat = _set_heats(self.q_pat.text().strip(), len(nums))
            if newpat and newpat != self.q_pat.text():
                self.q_pat.setText(newpat)          # fires _update_previews
        self._update_previews()

    def _update_previews(self, *_):
        self.tt_preview.setText(describe_pattern(self.tt_pat.text().strip()))
        self.q_preview.setText(describe_pattern(_with_qual(self.q_pat.text().strip(),
                                                           self.q_counts.text())))

    @staticmethod
    def _valid_pattern(pat):
        if not pat:
            return False
        try:
            crack_race_pattern(pat)
            return True
        except Exception:
            return False

    def _accept(self):
        for enabled, pat, label in ((self.tt_enable, self.tt_pat, "time-trial"),
                                    (self.q_enable, self.q_pat, "qualification")):
            if enabled.isChecked() and not self._valid_pattern(_strip_qual(pat.text().strip())):
                QMessageBox.information(
                    self, "Invalid pattern",
                    "The %s phase is enabled but its race pattern is empty or unparseable." % label)
                return
        self.accept()

    def timetrial_pattern(self):
        """The time-trial phase's pattern, or ``""`` when the phase is omitted."""
        return self.tt_pat.text().strip() if self.tt_enable.isChecked() else ""

    def qualification_pattern(self):
        """The qualification pattern incl. ``!qualification[...]``, or ``""``. The pattern's
        heat count is forced to the number of qualifiers — the Timer enumerates one qheat per
        pattern heat (get_heats), so they must agree."""
        if not self.q_enable.isChecked():
            return ""
        nums = self._count_list()
        pat = _strip_qual(self.q_pat.text().strip())
        if nums:
            pat = _set_heats(pat, len(nums))
        return _with_qual(pat, self.q_counts.text())


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
        for base in base_classes(self.window.eventdata):     # one tab per BASE class
            self.tabs.addTab(self._class_tab(base), base)
        self._update_counts()

    def _finals_pattern(self, base):
        return phase_pattern(self.window.eventdata, base, _finals_kind(self.window.eventdata, base))

    def _class_tab(self, base):
        w = QWidget()
        w._cozer_class = base                        # authoritative base name (label carries a count)
        lv = QVBoxLayout(w)
        prow = QHBoxLayout()
        summary = QLabel(self._pattern_summary(self._finals_pattern(base)))
        summary.setWordWrap(True)
        prow.addWidget(summary, 1)
        editp = QPushButton("Edit pattern…")
        editp.clicked.connect(lambda _=False, b=base, s=summary: self._edit_main_pattern(b, s))
        prow.addWidget(editp)
        phasesb = QPushButton("Phases…")
        phasesb.clicked.connect(lambda _=False, b=base: self._open_phases(b))
        prow.addWidget(phasesb)
        lv.addLayout(prow)
        phases = QLabel(self._phases_summary(base))
        phases.setWordWrap(True)
        phases.setStyleSheet("color:#333;")
        lv.addWidget(phases)
        grid = ClassParticipantsWidget(
            self._participants(), base, warn=self.window.log,
            qheat1=self.window.eventdata.setdefault("qheat1", {}),
            show_qheat1=has_qualification(self.window.eventdata, base))
        grid.model.rowsInserted.connect(self._update_counts)
        grid.model.rowsRemoved.connect(self._update_counts)
        lv.addWidget(grid, 1)
        return w

    def _phases_summary(self, base):
        bits = []
        for kind, label in (("timetrial", "Time trial"), ("qualification", "Qualification")):
            pat = phase_pattern(self.window.eventdata, base, kind)
            if pat is not None:
                bits.append("%s: %s" % (label, pat or "(no pattern)"))
        return ("Qualifying phases —  " + "      ·      ".join(bits) if bits else
                "Qualifying phases —  none (click Phases… to add a time trial or qualification)")

    def _tab_class(self, i):
        return getattr(self.tabs.widget(i), "_cozer_class", self.tabs.tabText(i))

    def _update_counts(self, *_):
        parts = self._participants()
        for i in range(self.tabs.count()):
            cl = self._tab_class(i)
            n = sum(1 for p in parts if len(p) > 4 and p[4] == cl)
            self.tabs.setTabText(i, "%s (%d)" % (cl, n))

    def _pattern_summary(self, pat):
        pat = pat or ""
        return ("Race pattern (final):  %s     —     %s" % (pat, describe_pattern(pat))
                if pat else "Race pattern (final):  (not set — click Edit pattern…)")

    def _edit_main_pattern(self, base, summary_label):
        """Edit the base's finals (main-race) pattern."""
        kind = _finals_kind(self.window.eventdata, base)
        dlg = PatternDialog(self, base, self._finals_pattern(base) or "")
        if dlg.exec():
            set_phase(self.window.eventdata, base, kind, dlg.pattern())
            summary_label.setText(self._pattern_summary(dlg.pattern()))
            self.window._reload_classes()

    def _open_phases(self, base):
        """Add / edit / remove the base's time-trial and qualification phases — cozer writes
        the internal phase (a native phase entry, or a ``/T``/``/Q`` row); no suffix typed."""
        ed = self.window.eventdata
        dlg = PhasesDialog(self, base,
                           phase_pattern(ed, base, "timetrial"),
                           phase_pattern(ed, base, "qualification"),
                           finals_pattern=self._finals_pattern(base) or "")
        if not dlg.exec():
            return
        self._sync_phase(base, "timetrial", dlg.timetrial_pattern())
        self._sync_phase(base, "qualification", dlg.qualification_pattern())
        self.reload()
        self.window._reload_classes()

    def _sync_phase(self, base, kind, pattern):
        """Create / update / remove the base's ``kind`` phase to match ``pattern`` (empty
        removes it, unless a race still uses that phase)."""
        if pattern:
            set_phase(self.window.eventdata, base, kind, pattern)
        elif phase_pattern(self.window.eventdata, base, kind) is not None:
            if self._phase_in_use(base, kind):
                self.window.log("Kept the %s phase of %s — a race still uses it" % (kind, base))
            else:
                remove_phase(self.window.eventdata, base, kind)

    def _add_class(self):
        existing = set(base_classes(self.window.eventdata))
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
            add_base(self.window.eventdata, name)    # name is already in the catalog
            self.reload()
            self.tabs.setCurrentIndex(self.tabs.count() - 1)
            self.window._reload_classes()

    def _phase_in_use(self, base, kind):
        """True if a scheduled race references the base's ``kind`` phase (either race shape)."""
        for race in self.window.eventdata.get("races", []):
            for e in race:
                if isinstance(e, dict):
                    if e.get("name") == base and e.get("kind") == kind:
                        return True
                elif len(e) > 1 and e[1] and getclass(e[1]) == base \
                        and race_kind(self.window.eventdata, e[1]) == kind:
                    return True
        return False

    def _class_in_use(self, base):
        """Reason class ``base`` can't be removed — it has participants, or a race uses one of
        its phases — else None."""
        if any(len(p) > 4 and p[4] == base for p in self._participants()):
            return "it has participants"
        if any(self._phase_in_use(base, kind)
               for kind in _phase_kinds(self.window.eventdata, base)):
            return "a race uses it"
        return None

    def _delete_class(self):
        i = self.tabs.currentIndex()
        if i < 0:
            return
        base = self._tab_class(i)
        reason = self._class_in_use(base)
        if reason:
            QMessageBox.information(
                self, "Cannot delete",
                "Cannot delete class %r while %s." % (base, reason))
            return
        ed = self.window.eventdata
        has_data = bool((ed.get("record") or {}).get(base)) or \
            any(phase_pattern(ed, base, k) for k in _phase_kinds(ed, base))
        if has_data and not confirm_delete(self, "class %r and its setup" % base):
            return
        remove_base(self.window.eventdata, base)
        self.reload()
        self.window._reload_classes()
