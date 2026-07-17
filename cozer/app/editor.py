"""Edit Records — a graphical timeline editor, faithful to legacy EditWin1 /
RecordEditor.

Each competitor is a row: the baseline is the race, lap marks sit at their
*cumulative* time and event marks at their *absolute* time; the row header shows
the competitor's analysed result. A draggable red line is the race-stop time.
Right-clicking a row at a point in time opens the rules menu (grouped by code)
to insert that mark *at that time*, plus Insert-lap / Enable-Disable / Delete on
the nearest mark. Zoom stretches the time axis.

Post-race edits are *buffered*: they modify an in-memory draft of the current
heat and are written to the store (journaled + fsync'd + snapshot) only when the
operator presses "Save changes". Leaving a modified record — switching heat/tab
or quitting — prompts save/discard/cancel, so an accidental drag of the finish
line can never silently overwrite a completed race. The geometry and edit
operations are module-level pure functions, exercised headlessly by the tests;
the widget paints them and turns mouse events into those operations.
"""
import copy
import time

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from cozer.analyzer import analyze, getresorder
from cozer.records import insertmark, invreccodemap, reccodemap

LAP = QColor(255, 127, 0)
INSLAP = QColor(90, 190, 60)
DISABLED = QColor(150, 150, 150)
RACETIME = QColor(220, 0, 0)
BASELINE = QColor(60, 60, 120)
CODE_COLORS = {
    "LL": QColor(230, 200, 0), "LL2": QColor(230, 200, 0), "PL": QColor(230, 210, 90),
    "PL5": QColor(230, 210, 90), "PL8": QColor(230, 210, 90), "PL10": QColor(230, 210, 90),
    "PL3": QColor(230, 210, 90), "PL4": QColor(230, 210, 90), "PL15": QColor(230, 210, 90),
    "DS": QColor(150, 150, 150), "IR": QColor(30, 30, 30), "DQ": QColor(220, 0, 0),
    "RC": QColor(220, 0, 0), "YC": QColor(235, 200, 40), "BC": QColor(40, 90, 220),
    "NC": QColor(150, 70, 70), "NT": QColor(140, 140, 90),
    "Q": QColor(0, 170, 0), "NQ": QColor(210, 0, 210),
}

HEADER_W = 236       # frozen left column (competitor + result), always visible
PAD = 10             # small left margin before the timeline baseline
ROW_H = 46
TOP = 34
TICK = 16


# --- geometry + edit operations (pure; unit-tested) ------------------------

def mark_positions(marks):
    """(kind, time, code, label) for each mark. Laps use cumulative time, event
    marks their absolute time. kind: lap / inslap / displap / event / disevent."""
    out = []
    etime = 0.0
    dtime = 0.0
    for m in marks:
        code = m[0]
        t = m[1] if len(m) > 1 else 0
        if abs(code) in (1, 2):
            etime += t
            if code == 1:
                out.append(("lap", etime, code, "%s" % (t + dtime)))
                dtime = 0
            elif code == 2:
                out.append(("inslap", etime, code, "%s" % (t + dtime)))
                dtime = 0
            else:
                out.append(("displap", etime, code, ""))
                dtime += t
        else:
            note = m[2] if len(m) > 2 else ""
            label = invreccodemap.get(abs(code), str(abs(code)))
            out.append(("event" if code > 0 else "disevent", t, code,
                        ("%s %s" % (label, note)).strip()))
    return out


def insert_lap_split(marks, ct):
    """Insert an inserted-lap (code 2) boundary at cumulative time ``ct``
    (legacy RecordEditorMenu.OnInsert)."""
    et = 0.0
    ii = -1
    for i, m in enumerate(marks):
        if abs(m[0]) in (1, 2):
            et += m[1]
            if et > ct:
                ii = i
                break
    if ii >= 0:
        ct_local = marks[ii][1] - (et - ct)
        marks[ii] = [marks[ii][0], marks[ii][1] - ct_local] + list(marks[ii][2:])
        marks.insert(ii, [2, ct_local])
    else:
        marks.append([2, ct - et])
    return marks


def toggle_nearest(marks, ct, coef, tol=5):
    """Toggle the sign (enable/disable) of the mark nearest ``ct``
    (legacy OnEnable). Returns True if one was toggled."""
    et = 0.0
    for i, m in enumerate(marks):
        if abs(m[0]) in (1, 2):
            et += m[1]
            near = abs(ct - et) * coef < tol
        else:
            near = abs(ct - m[1]) * coef < tol
        if near:
            marks[i] = [-m[0]] + list(m[1:])
            return True
    return False


def delete_nearest(marks, ct, coef, tol=5):
    """Delete the mark nearest ``ct`` (legacy OnDelete). Timed laps (code 1)
    cannot be deleted. Returns a message on refusal, else None."""
    et = 0.0
    ii = -1
    for i, m in enumerate(marks):
        if abs(m[0]) in (1, 2):
            et += m[1]
            if abs(ct - et) * coef < tol:
                if abs(m[0]) == 2:
                    ii = i
                    break
                return "Can't delete a timed lap — use Enable/Disable instead."
        elif abs(ct - m[1]) * coef < tol:
            del marks[i]
            return None
    if ii >= 0:
        ni = -1
        for i in range(ii + 1, len(marks)):
            if abs(marks[i][0]) in (1, 2):
                ni = i
                break
        if ni >= 0:      # give the removed lap's time to the following lap
            marks[ni] = [marks[ni][0], marks[ni][1] + marks[ii][1]] + list(marks[ni][2:])
        del marks[ii]
    return None


def _ordinal(n):
    if n <= 0:
        return "–"
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s" % (n, suf)


def result_str(r):
    """Legacy res2str-style header: Nth/points  A/M=avg/max km/h  Laps/Pen/Left."""
    laps, pen, left = (list(r.get("lapinfo", (0, 0, 0))) + [0, 0, 0])[:3]
    notes = " ".join(r["notes"].keys()) if r.get("notes") else ""
    return "%s/%s  A/M=%.1f/%.1f km/h  Laps/Pen/Left=%d/%d/%d %s" % (
        _ordinal(r["place"]), r["points"], r["avgspeed"], r["maxlapspeed"], laps, pen, left, notes)


def result_header(r):
    """Two-line row label for the frozen column, so it stays narrow: place/points
    and A/M speeds on top, Laps/Pen/Left (+ notes) wrapped to the second line."""
    laps, pen, left = (list(r.get("lapinfo", (0, 0, 0))) + [0, 0, 0])[:3]
    notes = " ".join(r["notes"].keys()) if r.get("notes") else ""
    top = "%s/%s  A/M=%.1f/%.1f km/h" % (
        _ordinal(r["place"]), r["points"], r["avgspeed"], r["maxlapspeed"])
    bottom = ("Laps/Pen/Left=%d/%d/%d %s" % (laps, pen, left, notes)).rstrip()
    return top + "\n" + bottom


# --- frozen header column ---------------------------------------------------

class FrozenHolder(QWidget):
    """Fixed-width viewport that clips its HeaderColumn child. The column is
    moved vertically by exactly the timeline's scroll offset (see
    EditRecordsPanel._sync_header_scroll), so row labels stay pixel-aligned with
    their baselines at every scroll position — no scrollbar-height skew — and
    the frozen column is always visible regardless of zoom or horizontal scroll."""

    def __init__(self):
        super().__init__()
        self.setFixedWidth(HEADER_W)

    def paintEvent(self, _evt):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#f3edd6"))
        p.setPen(QPen(QColor(208, 196, 160)))       # right-edge separator
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.end()


class HeaderColumn(QWidget):
    """The competitor number + analysed result for each row (two lines each),
    painted for the whole record; FrozenHolder clips and scrolls it."""

    def __init__(self):
        super().__init__()
        self._rows = []
        self.setFixedWidth(HEADER_W)

    def set_data(self, rows):
        self._rows = rows
        self.resize(HEADER_W, TOP + len(rows) * ROW_H + 20)
        self.update()

    def paintEvent(self, _evt):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#f3edd6"))
        p.setPen(QPen(QColor(208, 196, 160)))       # right-edge separator
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.setFont(QFont("DejaVu Sans", 8))
        for ri, (pid, header, _marks) in enumerate(self._rows):
            cy = TOP + ri * ROW_H + ROW_H // 2
            lines = header.split("\n")
            p.setPen(QPen(QColor(20, 20, 20)))
            p.drawText(6, cy - 17, HEADER_W - 12, 17, Qt.AlignVCenter,
                       "#%s  %s" % (pid, lines[0]))
            if len(lines) > 1 and lines[1]:
                p.setPen(QPen(QColor(95, 95, 95)))
                p.drawText(18, cy + 1, HEADER_W - 24, 17, Qt.AlignVCenter, lines[1])
        p.end()


# --- painted timeline widget -----------------------------------------------

class TimelineWidget(QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self._rows = []          # [(pid, header, marks)]
        self._coef = 1.0
        self._maxtime = 1.0
        self._racetime = 0.0
        self._drag = False
        self.setMouseTracking(True)

    def set_data(self, rows, maxtime, racetime, coef):
        self._rows, self._maxtime, self._racetime, self._coef = rows, maxtime, racetime, coef
        self.setMinimumSize(int(PAD + coef * maxtime + 40), TOP + len(rows) * ROW_H + 20)
        self.update()

    def x_of(self, t):
        return PAD + self._coef * t

    def t_of(self, x):
        return max(0.0, (x - PAD) / self._coef) if self._coef else 0.0

    def row_at(self, y):
        r = int((y - TOP) // ROW_H)
        return r if 0 <= r < len(self._rows) else -1

    def paintEvent(self, _evt):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#fbf7e6"))
        p.setFont(QFont("DejaVu Sans", 8))
        for ri, (pid, header, marks) in enumerate(self._rows):
            y = TOP + ri * ROW_H + ROW_H // 2
            positions = mark_positions(marks)
            end = positions[-1][1] if positions else 0
            p.setPen(QPen(BASELINE, 2))
            p.drawLine(int(self.x_of(0)), y, int(self.x_of(end if end else 0)), y)
            for kind, t, code, label in positions:
                x = int(self.x_of(t))
                color = {"lap": LAP, "inslap": INSLAP, "displap": DISABLED,
                         "disevent": DISABLED}.get(kind)
                if color is None:
                    color = CODE_COLORS.get(invreccodemap.get(abs(code), ""), QColor(80, 80, 80))
                p.fillRect(x - 2, y - TICK // 2, 4, TICK, QBrush(color))
                if label:
                    p.setPen(QPen(QColor(40, 40, 40)))
                    p.drawText(x + 3, y + 14, label)
        # race-stop line
        rx = int(self.x_of(self._racetime))
        p.setPen(QPen(RACETIME, 2))
        p.drawLine(rx, 0, rx, TOP + len(self._rows) * ROW_H)
        p.drawText(rx + 3, 14, "race stop")
        p.end()

    def mousePressEvent(self, evt):
        x, y = evt.position().x(), evt.position().y()
        if evt.button() == Qt.LeftButton and abs(x - self.x_of(self._racetime)) < 6:
            self._drag = True
        elif evt.button() == Qt.RightButton:
            ri = self.row_at(y)
            if ri >= 0:
                self.panel.open_mark_menu(self._rows[ri][0], self.t_of(x),
                                          evt.globalPosition().toPoint())

    def mouseMoveEvent(self, evt):
        if self._drag:
            self._racetime = round(self.t_of(evt.position().x()), 2)
            self.update()

    def mouseReleaseEvent(self, evt):
        if self._drag:
            self._drag = False
            self.panel.commit_racetime(self._racetime)


# --- panel ------------------------------------------------------------------

class EditRecordsPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._heatkeys = []
        self._zoom = 1
        # Post-race edits are buffered in an in-memory draft of the current heat
        # and only written to the store when the operator presses "Save changes",
        # so an accidental drag of the finish line never silently overwrites a
        # completed race. Leaving a modified record prompts save/discard/cancel.
        self._draft = None            # deepcopy of [info, {pid: marks}] or None
        self._draft_key = None        # (cl, h) the draft belongs to
        self._dirty = False
        self._loaded_index = None     # combo index of the loaded draft (for cancel)
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Class / Heat:"))
        self.heat_combo = QComboBox()
        self.heat_combo.currentIndexChanged.connect(self._on_heat_changed)
        top.addWidget(self.heat_combo)
        zin = QPushButton("Zoom +")
        zin.clicked.connect(lambda: self._zoomed(1))
        zout = QPushButton("Zoom −")
        zout.clicked.connect(lambda: self._zoomed(-1))
        top.addWidget(zin)
        top.addWidget(zout)
        self.zoom_label = QLabel("Zoom: 1")
        top.addWidget(self.zoom_label)
        top.addSpacing(16)
        self.info_label = QLabel("")
        top.addWidget(self.info_label)
        top.addStretch()
        self.dirty_label = QLabel("")
        self.dirty_label.setStyleSheet("color:#b00000; font-weight:bold;")
        top.addWidget(self.dirty_label)
        self.save_btn = QPushButton("Save changes")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_draft)
        top.addWidget(self.save_btn)
        v.addLayout(top)
        # Frozen header column (left) + horizontally-scrolling timeline (right).
        # The header lives in a fixed-width clipping holder and is moved by the
        # timeline's vertical scroll offset, so the row labels stay visible and
        # pixel-aligned at any zoom or horizontal scroll offset.
        self.header_holder = FrozenHolder()
        self.header_col = HeaderColumn()
        self.header_col.setParent(self.header_holder)
        self.header_col.move(0, 0)
        self.timeline = TimelineWidget(self)
        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self.area.setWidget(self.timeline)
        self.area.verticalScrollBar().valueChanged.connect(self._sync_header_scroll)
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self.header_holder)
        body.addWidget(self.area, 1)
        v.addLayout(body, 1)

    # ---- data ----
    def _record(self):
        return self.window.eventdata.get("record", {})

    def reload(self):
        # A new document: drop any draft (callers flush first via maybe_flush).
        self._draft = None
        self._draft_key = None
        self._dirty = False
        self.heat_combo.blockSignals(True)
        self.heat_combo.clear()
        self._heatkeys = []
        for cl in sorted(self._record()):
            for h in sorted(self._record()[cl]):
                self._heatkeys.append((cl, h))
                self.heat_combo.addItem("%s / %s" % (cl, h))
        self.heat_combo.blockSignals(False)
        self.refresh()

    def _cur(self):
        i = self.heat_combo.currentIndex()
        return self._heatkeys[i] if 0 <= i < len(self._heatkeys) else (None, None)

    def _maxtime(self, rec):
        mx = 0.0
        for marks in rec[1].values():
            t = 0.0
            for m in marks:
                if abs(m[0]) in (1, 2):
                    t += m[1]
                elif len(m) > 1:
                    mx = max(mx, m[1])
            mx = max(mx, t)
        return 1.0 + mx * 1.05

    def _sync_header_scroll(self, value):
        # Move the header column by exactly the timeline's scroll offset; the
        # holder clips it, so alignment is exact at every position.
        self.header_col.move(0, -value)

    # ---- draft buffer (post-race edits held until "Save changes") ----
    def _load_draft(self):
        """Take a fresh in-memory copy of the current heat's record."""
        cl, h = self._cur()
        if cl is None:
            self._draft, self._draft_key = None, None
        else:
            self._draft = copy.deepcopy(self._record()[cl][h])
            self._draft_key = (cl, h)
        self._dirty = False
        self._loaded_index = self.heat_combo.currentIndex()

    def _on_heat_changed(self, idx):
        if self._dirty and self._loaded_index is not None and idx != self._loaded_index:
            if not self.maybe_flush():                # cancelled: stay on the record
                self.heat_combo.blockSignals(True)
                self.heat_combo.setCurrentIndex(self._loaded_index)
                self.heat_combo.blockSignals(False)
                return
        self.refresh()

    def _update_save(self):
        self.save_btn.setEnabled(self._dirty)
        self.dirty_label.setText("● unsaved changes" if self._dirty else "")

    def refresh(self):
        cl, h = self._cur()
        if cl is None:
            self._draft, self._draft_key, self._dirty = None, None, False
            self.header_col.set_data([])
            self.timeline.set_data([], 1.0, 0.0, 1.0)
            self.info_label.setText("")
            self._update_save()
            return
        if self._draft_key != (cl, h):
            self._load_draft()
        rec = self._draft
        ss = self.window.eventdata.get("scoringsystem", [])
        try:
            res = analyze(h, copy.deepcopy(rec), ss)
            order = getresorder(res)
        except Exception:            # pragma: no cover - degenerate data
            res, order = {}, sorted(rec[1].keys(), key=str)
        rows = [(str(pid), result_header(res[pid]) if pid in res else "", rec[1][pid])
                for pid in order]
        maxtime = self._maxtime(rec)
        racetime = rec[0].get("racetime", maxtime)
        width = int((1.4 ** self._zoom) * 600)
        coef = width / maxtime
        self._coef = coef
        self.header_col.set_data(rows)
        self.timeline.set_data(rows, maxtime, racetime, coef)
        self._sync_header_scroll(self.area.verticalScrollBar().value())
        start = rec[0].get("starttime")
        starttxt = ("Start: %s      " % time.ctime(start)) if start else ""
        self.info_label.setText(
            "%sRace time: %d:%05.2f  (%.1f s)"
            % (starttxt, int(racetime // 60), racetime % 60, racetime))
        self.zoom_label.setText("Zoom: %d" % self._zoom)
        self._update_save()

    def _zoomed(self, delta):
        self._zoom = max(0, min(16, self._zoom + delta))
        self.refresh()

    # ---- edits (buffered into the draft; persisted only on Save) ----
    def _require_store(self):
        if self.window.store is None:
            self.window.on_save_as()
        return self.window.store is not None

    def _commit(self, cl, h, pid, marks):
        self._draft[1][pid] = marks
        self._dirty = True
        self.refresh()

    def commit_racetime(self, value):
        if self._draft is None:
            return
        self._draft[0]["racetime"] = value
        self._dirty = True
        self.refresh()

    def insert_rule_mark(self, cl, h, pid, code, ct, note=""):
        marks = [list(m) for m in self._draft[1][pid]]
        insertmark(marks, code, ct, note)
        self._commit(cl, h, pid, marks)

    def insert_lap(self, cl, h, pid, ct):
        marks = [list(m) for m in self._draft[1][pid]]
        insert_lap_split(marks, ct)
        self._commit(cl, h, pid, marks)

    def toggle_at(self, cl, h, pid, ct):
        marks = [list(m) for m in self._draft[1][pid]]
        if toggle_nearest(marks, ct, self._coef):
            self._commit(cl, h, pid, marks)

    def delete_at(self, cl, h, pid, ct):
        marks = [list(m) for m in self._draft[1][pid]]
        msg = delete_nearest(marks, ct, self._coef)
        if msg:
            self.window.log(msg)
        else:
            self._commit(cl, h, pid, marks)

    # ---- save / discard the draft ----
    def save_draft(self):
        """Persist the buffered edits: journal each changed mark set / info key
        through the store, then snapshot. Returns True on success (nothing to do
        counts as success), False if no store could be established."""
        if not self._dirty or self._draft is None or self._draft_key is None:
            return True
        if not self._require_store():
            return False
        cl, h = self._draft_key
        stored = self.window.eventdata["record"][cl][h]
        for key, val in self._draft[0].items():
            if stored[0].get(key) != val:
                self.window.store.record(
                    {"op": "info", "cl": cl, "h": h, "key": key, "value": val})
        for pid, marks in self._draft[1].items():
            if stored[1].get(pid) != marks:
                self.window.store.record(
                    {"op": "replace", "cl": cl, "h": h, "id": pid, "marks": marks})
        self.window.store.snapshot()
        self._dirty = False
        self._update_save()
        self.window.log("Saved changes to %s / %s" % (cl, h))
        return True

    def maybe_flush(self):
        """Called before leaving the current record (heat/tab switch, quit). If
        there are unsaved edits, ask save/discard/cancel. Returns True if it's OK
        to proceed (saved or discarded), False if the user cancelled."""
        if not self._dirty:
            return True
        choice = self._ask_unsaved()
        if choice == "cancel":
            return False
        if choice == "save":
            return self.save_draft()
        self._draft, self._draft_key, self._dirty = None, None, False   # discard
        self._update_save()
        return True

    def _ask_unsaved(self):      # pragma: no cover - modal dialog
        cl, h = self._draft_key or ("", "")
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved race changes")
        box.setText("Save changes to race %s / %s?" % (cl, h))
        box.setStandardButtons(
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Save)
        return {QMessageBox.Save: "save", QMessageBox.Discard: "discard",
                QMessageBox.Cancel: "cancel"}.get(box.exec(), "cancel")

    # ---- right-click menu on the timeline ----
    def build_mark_menu(self, pid, ct):
        """The context menu for a right-click at time ``ct`` on boat ``pid`` —
        the event's rules grouped by code, then Insert-lap / Enable-Disable /
        Delete. Built separately from exec() so tests can trigger its actions."""
        cl, h = self._cur()
        menu = QMenu(self)
        if cl is None:
            return menu
        by_code = {}
        for r in self.window.eventdata.get("rules", []):
            if len(r) > 3 and r[1] in reccodemap:
                by_code.setdefault(r[1], []).append(r)
        for code_name in by_code:
            sub = menu.addMenu("%s…" % code_name)
            for r in by_code[code_name]:
                act = sub.addAction(r[3] or r[2])
                act.triggered.connect(
                    lambda _=False, rr=r: self.insert_rule_mark(cl, h, pid, reccodemap[rr[1]], ct, rr[2]))
        if by_code:
            menu.addSeparator()
        menu.addAction("Insert lap here").triggered.connect(lambda: self.insert_lap(cl, h, pid, ct))
        menu.addAction("Enable/Disable nearest").triggered.connect(lambda: self.toggle_at(cl, h, pid, ct))
        menu.addAction("Delete nearest").triggered.connect(lambda: self.delete_at(cl, h, pid, ct))
        return menu

    def open_mark_menu(self, pid, ct, global_pos):      # pragma: no cover - shows a modal menu
        if self._cur()[0] is None or self._draft is None:
            return
        self.build_mark_menu(pid, ct).exec(
            global_pos if isinstance(global_pos, QPoint) else QPoint(0, 0))
