"""Live Timer — the safety-critical lap-recording panel.

Clicking a boat's button records a lap. Every recorded lap goes through
``store.record`` (append to eventdata + fsync to the journal immediately), so a
power loss at any instant loses at most nothing that was clicked. The recording
core (``setup_heat`` / ``record_lap``) takes an injectable clock so it can be
driven headlessly in tests.

Button colors follow the legacy palette and carry state: white = not started,
green = laps in progress, magenta = finished (all course laps done).
"""
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from cozer._py2compat import round2
from cozer.classes import getclass
from cozer.racepattern import crack_race_pattern
from cozer.records import gettimes

# Legacy prefs palette (RGB) — see legacy/cozer/prefs.py mycolors.
C_WAITING = "#ffffff"       # not started
C_PROGRESS = "#c8f0c8"      # laps in progress
C_FINISH = "#ff00ff"        # finished (all course laps)


def _idkey(pid):
    try:
        return (0, int(pid))
    except (ValueError, TypeError):
        return (1, str(pid))


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
        self._buttons = {}
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
        self.autosave_cb = QCheckBox("Auto-save")
        self.autosave_cb.toggled.connect(self._toggle_autosave)
        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)
        top.addWidget(self.autosave_cb)
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

    @property
    def eventdata(self):
        return self.window.eventdata

    def reload(self):
        self.race_combo.clear()
        for i in range(len(self.eventdata.get("races", []))):
            self.race_combo.addItem("Race %d" % (i + 1))
        self.on_stop()
        self._clear_buttons()

    def _selected_race(self):
        i = self.race_combo.currentIndex()
        races = self.eventdata.get("races", [])
        return races[i] if 0 <= i < len(races) else None

    def _ensure_store(self):
        if self.window.store is None:
            self.window.on_save_as()
        return self.window.store is not None

    def on_start(self):
        race = self._selected_race()
        if not race:
            return
        if not self._ensure_store():
            QMessageBox.warning(self, "Save required",     # pragma: no cover - dialog
                                "Save the event first so recording is journaled.")
            return
        now = self._clock()
        self._heats = []
        for entry in race:
            cl = entry[1] if len(entry) > 1 else ""
            h = entry[2] if len(entry) > 2 else ""
            if cl and h:
                self.setup_heat(cl, h, now)
                self._heats.append((cl, h))
        self._started = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._build_buttons()
        self.status.setText("Recording…")

    def setup_heat(self, cl, h, now):
        course, sheats, duration = heat_course(self.eventdata, cl, h)
        info = {"course": course, "sheats": sheats, "duration": duration, "starttime": now}
        self.window.store.record({"op": "heat", "cl": cl, "h": h, "info": info,
                                  "ids": class_ids(self.eventdata, cl)})

    def record_lap(self, cl, h, pid):
        if not self._started:
            return
        rec = self.eventdata["record"][cl][h]
        prev = sum(gettimes(rec[1].get(pid, [])))
        laptime = round2(self._clock() - rec[0]["starttime"] - prev)
        self.window.store.record({"op": "lap", "cl": cl, "h": h, "id": pid,
                                  "mark": [1, laptime]})
        self._recolor(cl, h, pid)

    def on_stop(self):
        self._started = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status.setText("Stopped")

    def _clear_buttons(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons = {}

    def _build_buttons(self):
        self._clear_buttons()
        for cl, h in self._heats:
            box = QGroupBox("%s  heat %s" % (cl, h))
            g = QGridLayout(box)
            ids = sorted(self.eventdata["record"][cl][h][1].keys(), key=_idkey)
            for i, pid in enumerate(ids):
                b = QPushButton()
                b.setMinimumSize(52, 42)
                b.clicked.connect(lambda _=False, c=cl, hh=h, p=pid: self.record_lap(c, hh, p))
                self._buttons[(cl, h, pid)] = b
                g.addWidget(b, i // 8, i % 8)
                self._recolor(cl, h, pid)
            self._grid.addWidget(box)
        self._grid.addStretch()

    def _recolor(self, cl, h, pid):
        b = self._buttons.get((cl, h, pid))
        if b is None:
            return
        rec = self.eventdata["record"][cl][h]
        laps = len([m for m in rec[1].get(pid, []) if m and m[0] in (1, 2)])
        need = len(rec[0].get("course", []))
        color = C_WAITING if laps == 0 else (C_FINISH if need and laps >= need else C_PROGRESS)
        b.setStyleSheet("background-color: %s;" % color)
        b.setText("%s\n%d" % (pid, laps))

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
