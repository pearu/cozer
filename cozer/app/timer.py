"""Live Timer — the safety-critical lap-recording panel.

Per heat there are two halves (legacy ``TimerWin1``):
  * a **click grid** of boat-number buttons — each click records a lap, which
    goes straight through ``store.record`` (append + fsync to the journal), so a
    power loss loses at most nothing that was clicked;
  * a **running-order column** — the boats sorted into current standings
    (finished, then most laps, then least elapsed time), refreshed on every lap,
    so the timekeeper sees who leads and each boat's progress at a glance. This
    ordering is also what the Phase-7 live feed will publish.

Start clears the heat and stamps a start time; Resume continues an in-progress
heat without resetting (e.g. after a stop or reopening a part-timed event). The
running order is always recomputed from the record, so reopening reconstructs
the display automatically.

The recording/ordering logic (``setup_heat`` / ``record_lap`` / ``standings``)
takes an injectable clock and is driven headlessly by the tests.
"""
import math
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from cozer._py2compat import round2
from cozer.classes import getclass
from cozer.racepattern import crack_race_pattern
from cozer.records import gettimes

# Legacy prefs palette (RGB) — see legacy/cozer/prefs.py mycolors.
C_WAITING = "#ffffff"       # not started
C_PROGRESS = "#c8f0c8"      # laps in progress
C_FINISH = "#ff00ff"        # finished (all course laps)
_FIN_BG = QColor(255, 0, 255)
_LEAD_BG = QColor(230, 240, 255)


def _idkey(pid):
    try:
        return (0, int(pid))
    except (ValueError, TypeError):
        return (1, str(pid))


def calclayout(ids):
    """Arrange boat ids into rows for the click grid (legacy calclayout):
    grouped by tens, about sqrt(n) per row."""
    bydec = {}
    for i in ids:
        try:
            di = (int(i) // 10) * 10
        except (ValueError, TypeError):
            di = str(i)[:1]
        bydec.setdefault(di, []).append(i)
    n = max(3, int(math.ceil(math.sqrt(len(ids) or 1))))
    rows = [[]]
    for k in sorted(bydec, key=lambda x: (isinstance(x, str), x)):
        grp = bydec[k]
        if len(rows[-1]) + len(grp) < n:
            rows[-1] = rows[-1] + grp
        elif not rows[-1]:
            rows[-1] = grp[:n]
            if grp[n:]:
                rows.append(grp[n:])
        else:
            rows.append(grp[:n])
            if grp[n:]:
                rows.append(grp[n:])
    return rows


def standings(rec):
    """Running order for a heat record ``[info, {id: marks}]`` — a list of
    ``{id, laps, time, finished}`` sorted leader-first (finished first, then more
    laps, then less elapsed time). Disabled laps are excluded (via gettimes)."""
    info, boats = rec[0], rec[1]
    need = len(info.get("course", []))
    rows = []
    for pid, marks in boats.items():
        times = gettimes(marks)
        laps = len(times)
        rows.append({"id": pid, "laps": laps, "time": round2(sum(times)),
                     "finished": bool(need) and laps >= need})
    rows.sort(key=lambda r: (0 if r["finished"] else 1, -r["laps"], r["time"], _idkey(r["id"])))
    return rows


def heat_course(eventdata, cl, h):
    """(lap-lengths, scored-heats, duration) for class ``cl`` heat ``h``."""
    for l in eventdata.get("classes", []):
        if len(l) > 2 and l[1] == cl and l[2]:
            r = crack_race_pattern(l[2], cl)
            rpat, sheats = r[0], r[1]
            duration = r[2] if len(r) == 3 else None
            li = int(h[:-1]) - 1 if (h and h[-1] in "rqtR") else int(h) - 1
            li = max(0, min(li, len(rpat) - 1))
            return list(rpat[li]), sheats, duration
    return [], 1, None


def class_ids(eventdata, cl):
    base = getclass(cl)
    return [str(p[5]) for p in eventdata.get("participants", [])
            if len(p) > 5 and p[4] == base and p[5] != ""]


class TimerPanel(QWidget):
    def __init__(self, window, clock=time.time):
        super().__init__()
        self.window = window
        self._clock = clock
        self._started = False
        self._heats = []
        self._buttons = {}          # (cl, h, pid) -> QPushButton (click grid)
        self._orderlists = {}       # (cl, h) -> QListWidget (running order)
        self._autosave = None

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Race:"))
        self.race_combo = QComboBox()
        top.addWidget(self.race_combo)
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setEnabled(False)
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self.on_resume)
        self.autosave_cb = QCheckBox("Auto-save")
        self.autosave_cb.toggled.connect(self._toggle_autosave)
        for w in (self.start_btn, self.stop_btn, self.resume_btn, self.autosave_cb):
            top.addWidget(w)
        top.addStretch()
        v.addLayout(top)

        self.area = QScrollArea()
        self.area.setWidgetResizable(True)
        self._host = QWidget()
        self._grid = QVBoxLayout(self._host)
        self.area.setWidget(self._host)
        v.addWidget(self.area, 1)
        self.status = QLabel("")
        v.addWidget(self.status)
        self.race_combo.currentIndexChanged.connect(self._show_race)

    @property
    def eventdata(self):
        return self.window.eventdata

    # ---- race / heat selection ----
    def reload(self):
        self.race_combo.blockSignals(True)
        self.race_combo.clear()
        for i in range(len(self.eventdata.get("races", []))):
            self.race_combo.addItem("Race %d" % (i + 1))
        self.race_combo.blockSignals(False)
        self.on_stop()
        self._show_race()

    def _selected_race(self):
        i = self.race_combo.currentIndex()
        races = self.eventdata.get("races", [])
        return races[i] if 0 <= i < len(races) else None

    def _race_heats(self, race):
        return [(e[1], e[2]) for e in race if len(e) > 2 and e[1] and e[2]] if race else []

    def _show_race(self):
        """Show the click grid + running order for the selected race, seeded from
        any already-recorded data (so reopening reconstructs the display)."""
        self._heats = self._race_heats(self._selected_race())
        self._build()

    def _rec(self, cl, h):
        return self.eventdata.get("record", {}).get(cl, {}).get(h)

    def _heat_ids(self, cl, h):
        rec = self._rec(cl, h)
        if rec:
            return sorted(rec[1].keys(), key=_idkey)
        return sorted(class_ids(self.eventdata, cl), key=_idkey)

    # ---- widget building ----
    def _clear(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons = {}
        self._orderlists = {}

    def _build(self):
        self._clear()
        for cl, h in self._heats:
            box = QGroupBox("%s  heat %s" % (cl, h))
            row = QHBoxLayout(box)
            grid_host = QWidget()
            g = QGridLayout(grid_host)
            ids = self._heat_ids(cl, h)
            r = 0
            for line in calclayout(ids):
                for c, pid in enumerate(line):
                    b = QPushButton()
                    b.setMinimumSize(52, 42)
                    b.clicked.connect(lambda _=False, cc=cl, hh=h, p=pid: self.record_lap(cc, hh, p))
                    self._buttons[(cl, h, pid)] = b
                    g.addWidget(b, r, c)
                r += 1
            row.addWidget(grid_host, 2)
            order = QListWidget()
            order.setMinimumWidth(220)
            self._orderlists[(cl, h)] = order
            row.addWidget(order, 1)
            self._grid.addWidget(box)
            for pid in ids:
                self._recolor(cl, h, pid)
            self._refresh_order(cl, h)
        self._grid.addStretch()

    # ---- recording ----
    def _ensure_store(self):
        if self.window.store is None:
            self.window.on_save_as()
        return self.window.store is not None

    def _has_data(self):
        for cl, h in self._heats:
            rec = self._rec(cl, h)
            if rec and any(rec[1].get(pid) for pid in rec[1]):
                return True
        return False

    def on_start(self):
        race = self._selected_race()
        if not race:
            return
        if not self._ensure_store():
            QMessageBox.warning(self, "Save required",     # pragma: no cover - dialog
                                "Save the event first so recording is journaled.")
            return
        if self._has_data() and not self._confirm_overwrite():   # pragma: no cover - dialog
            return
        now = self._clock()
        self._heats = self._race_heats(race)
        for cl, h in self._heats:
            self.setup_heat(cl, h, now)          # records a fresh heat (clears + starttime)
        self._started = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.race_combo.setEnabled(False)
        self._build()
        self.status.setText("Recording…")

    def _confirm_overwrite(self):      # pragma: no cover - modal dialog
        return QMessageBox.question(
            self, "Overwrite race record?",
            "This race already has recorded data. Start over and lose it?\n"
            "(Use Resume to continue timing instead.)") == QMessageBox.Yes

    def on_resume(self):
        """Continue an in-progress heat without resetting — needs a prior start."""
        if not self._ensure_store():
            return
        if not any((self._rec(cl, h) or [{}])[0].get("starttime") for cl, h in self._heats):
            self.status.setText("Nothing to resume — press Start.")
            return
        self._started = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.race_combo.setEnabled(False)
        self.status.setText("Recording (resumed)…")

    def setup_heat(self, cl, h, now):
        course, sheats, duration = heat_course(self.eventdata, cl, h)
        info = {"course": course, "sheats": sheats, "duration": duration, "starttime": now}
        self.window.store.record({"op": "heat", "cl": cl, "h": h, "info": info,
                                  "ids": class_ids(self.eventdata, cl)})

    def record_lap(self, cl, h, pid):
        if not self._started:
            self.status.setText("Press Start (or Resume) to begin timing")
            return
        rec = self.eventdata["record"][cl][h]
        prev = sum(gettimes(rec[1].get(pid, [])))
        laptime = round2(self._clock() - rec[0]["starttime"] - prev)
        self.window.store.record({"op": "lap", "cl": cl, "h": h, "id": pid,
                                  "mark": [1, laptime]})
        self._recolor(cl, h, pid)
        self._refresh_order(cl, h)

    def on_stop(self):
        self._started = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.race_combo.setEnabled(True)
        self.status.setText("Stopped")

    # ---- display ----
    def _recolor(self, cl, h, pid):
        b = self._buttons.get((cl, h, pid))
        if b is None:
            return
        rec = self._rec(cl, h)
        marks = rec[1].get(pid, []) if rec else []
        laps = len([m for m in marks if m and m[0] in (1, 2)])
        need = len(rec[0].get("course", [])) if rec else len(heat_course(self.eventdata, cl, h)[0])
        color = C_WAITING if laps == 0 else (C_FINISH if need and laps >= need else C_PROGRESS)
        b.setStyleSheet("background-color: %s;" % color)
        b.setText("%s\n%d" % (pid, laps))

    def _refresh_order(self, cl, h):
        lst = self._orderlists.get((cl, h))
        rec = self._rec(cl, h)
        if lst is None or rec is None:
            return
        need = len(rec[0].get("course", []))
        lst.clear()
        for pos, s in enumerate(standings(rec), 1):
            tag = "FIN" if s["finished"] else "%d/%d" % (s["laps"], need)
            item = QListWidgetItem("%2d.  #%-4s  %-6s  %6.1fs" % (pos, s["id"], tag, s["time"]))
            if s["finished"]:
                item.setBackground(QBrush(_FIN_BG))
            elif pos == 1 and s["laps"] > 0:
                item.setBackground(QBrush(_LEAD_BG))
            lst.addItem(item)

    # ---- autosave ----
    def _toggle_autosave(self, on):
        if on:
            self._autosave = QTimer(self)
            self._autosave.timeout.connect(self._do_autosave)
            self._autosave.start(30000)
        elif self._autosave is not None:
            self._autosave.stop()
            self._autosave = None

    def _do_autosave(self):     # pragma: no cover - periodic timer callback
        if self.window.store is not None:
            self.window.on_save()
