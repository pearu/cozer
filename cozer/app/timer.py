"""Live Timer — the safety-critical lap-recording panel (legacy TimerWin1 look).

Per heat there are two synchronized views, and a lap is recorded by clicking a
boat in **either** of them:
  * a **click grid** of boat-number buttons (laid out by tens, `calclayout`);
  * a **running-order ladder** — `Ready to Start` → boats grouped into the zone
    after each `Lap N` marker by how many laps they have completed → finished
    boats (magenta) → `Finish`. A boat's vertical position is its progress; this
    ordering is also what the Phase-7 live feed will publish.

Every click goes straight through `store.record` (append + fsync to the
journal), so a power loss loses at most nothing that was clicked. Start clears
the heat and stamps a start time; Resume continues an in-progress heat without
resetting. The display is always recomputed from the record, so reopening a
part-timed event reconstructs it. Button size is operator-adjustable (A−/A+) for
comfortable high-pace tapping, and persisted in the event config.

`standings()` / `ladder()` / `calclayout()` are pure and unit-tested.
"""
import math
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from cozer._py2compat import round2
from cozer.classes import getclass
from cozer.racepattern import crack_race_pattern
from cozer.records import gettimes

# Legacy prefs palette (RGB) — see legacy/cozer/prefs.py mycolors.
C_READY = "#00ff7f"         # readymark
C_LAPMARK = "#ff7f00"       # lapmark
C_FINISH = "#ff00ff"        # finish
C_FINISHBAR = "#000000"     # finishmark_bg (fg white)
C_INPROGRESS = "#c8c8c8"    # waiting1 (a lap done, still racing)
C_WAITING = "#ffffff"       # not started
DEFAULT_BUTSIZE = 46


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


def ladder(rec):
    """Marker-zone ladder rows for the running-order column, top->bottom:
    ``('marker', label)`` and ``('boat', standing_dict)``. Each boat sits in the
    zone right after the ``Lap k`` marker for its completed-lap count; finished
    boats drop to the bottom (before ``Finish``). Returns ``(rows, need)``."""
    need = len(rec[0].get("course", []))
    zones = {}
    finished = []
    for b in standings(rec):
        if b["finished"]:
            finished.append(b)
        else:
            zones.setdefault(min(b["laps"], max(need - 1, 0)), []).append(b)
    rows = [("marker", "Ready to Start")]
    for k in range(need):
        if k > 0:
            rows.append(("marker", "Lap %d" % k))
        for b in zones.get(k, []):
            rows.append(("boat", b))
    for b in finished:
        rows.append(("boat", b))
    rows.append(("marker", "Finish"))
    return rows, need


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
        self._buttons = {}          # (cl, h, pid) -> grid QPushButton
        self._ladder_boats = {}     # (cl, h, pid) -> ladder QPushButton
        self._ladder_layouts = {}   # (cl, h) -> QVBoxLayout of the ladder
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
        top.addWidget(QLabel("Button size:"))
        smaller = QPushButton("A−")
        smaller.setFixedWidth(34)
        smaller.clicked.connect(lambda: self._bump_size(-6))
        bigger = QPushButton("A+")
        bigger.setFixedWidth(34)
        bigger.clicked.connect(lambda: self._bump_size(6))
        top.addWidget(smaller)
        top.addWidget(bigger)
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
        self._heats = self._race_heats(self._selected_race())
        self._build()

    def _rec(self, cl, h):
        return self.eventdata.get("record", {}).get(cl, {}).get(h)

    def _heat_ids(self, cl, h):
        rec = self._rec(cl, h)
        if rec:
            return sorted(rec[1].keys(), key=_idkey)
        return sorted(class_ids(self.eventdata, cl), key=_idkey)

    # ---- sizing ----
    def _butsize(self):
        try:
            return int(self.eventdata.get("configure", {}).get("id_but_size", DEFAULT_BUTSIZE))
        except (TypeError, ValueError):
            return DEFAULT_BUTSIZE

    def _bump_size(self, delta):
        self.eventdata.setdefault("configure", {})["id_but_size"] = \
            max(28, min(110, self._butsize() + delta))
        self._build()

    def _boat_style(self, s):
        color = C_FINISH if s["finished"] else (C_INPROGRESS if s["laps"] else C_WAITING)
        sz = self._butsize()
        return "background-color: %s; font-size: %dpx;" % (color, max(9, int(sz * 0.34)))

    # ---- widget building ----
    def _clear(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._buttons = {}
        self._ladder_boats = {}
        self._ladder_layouts = {}

    def _build(self):
        self._clear()
        sz = self._butsize()
        for cl, h in self._heats:
            box = QGroupBox("%s  heat %s" % (cl, h))
            row = QHBoxLayout(box)

            ladder_host = QWidget()
            lv = QVBoxLayout(ladder_host)
            lv.setSpacing(2)
            self._ladder_layouts[(cl, h)] = lv
            row.addWidget(ladder_host, 1)

            grid_host = QWidget()
            g = QGridLayout(grid_host)
            r = 0
            for line in calclayout(self._heat_ids(cl, h)):
                for c, pid in enumerate(line):
                    b = QPushButton(str(pid))
                    b.setMinimumSize(sz, sz)
                    b.clicked.connect(lambda _=False, cc=cl, hh=h, p=pid: self.record_lap(cc, hh, p))
                    self._buttons[(cl, h, pid)] = b
                    g.addWidget(b, r, c)
                r += 1
            row.addWidget(grid_host, 2)

            self._grid.addWidget(box)
            self._build_ladder(cl, h)
            for pid in self._heat_ids(cl, h):
                self._recolor(cl, h, pid)
        self._grid.addStretch()

    def _build_ladder(self, cl, h):
        lv = self._ladder_layouts.get((cl, h))
        if lv is None:
            return
        while lv.count():
            item = lv.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for k in list(self._ladder_boats):
            if k[0] == cl and k[1] == h:
                del self._ladder_boats[k]
        rec = self._rec(cl, h)
        if rec is None:
            return
        sz = self._butsize()
        rows, _ = ladder(rec)
        for r in rows:
            if r[0] == "marker":
                lbl = QLabel(r[1])
                lbl.setAlignment(Qt.AlignCenter)
                color = C_READY if r[1] == "Ready to Start" else \
                    (C_FINISHBAR if r[1] == "Finish" else C_LAPMARK)
                fg = "#ffffff" if r[1] == "Finish" else "#000000"
                lbl.setStyleSheet("background-color: %s; color: %s; padding: 3px; font-weight: bold;"
                                  % (color, fg))
                lv.addWidget(lbl)
            else:
                s = r[1]
                pid = s["id"]
                b = QPushButton(str(pid))
                b.setMinimumHeight(max(22, int(sz * 0.6)))
                b.setStyleSheet(self._boat_style(s))
                b.clicked.connect(lambda _=False, cc=cl, hh=h, p=pid: self.record_lap(cc, hh, p))
                self._ladder_boats[(cl, h, pid)] = b
                lv.addWidget(b)
        lv.addStretch()

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
            self.setup_heat(cl, h, now)
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
        self._build_ladder(cl, h)          # re-slot the boat into its new zone

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
        color = C_FINISH if (need and laps >= need) else (C_INPROGRESS if laps else C_WAITING)
        b.setStyleSheet("background-color: %s; font-size: %dpx;"
                        % (color, max(9, int(self._butsize() * 0.34))))
        b.setText(str(pid))

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
