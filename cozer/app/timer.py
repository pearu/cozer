"""Live Timer — the safety-critical lap-recording panel (legacy TimerWin1 look).

Per heat there are two synchronized views, and a lap is recorded by clicking a
boat in **either** of them:
  * a **click grid** of square boat-number buttons that **auto-fit the window** —
    all boats stay visible at any window size; the buttons grow/shrink to fill the
    space (make the window bigger for bigger targets). Laid out in tens-grouped
    rows so the operator's eye finds a number fast.
  * a **running-order ladder** — `Ready to Start` → boats grouped into the zone
    after each `Lap N` marker by laps completed → finished boats (magenta) →
    `Finish`. A boat's vertical position is its progress; this ordering is also
    what the Phase-7 live feed will publish.

Every click goes through `store.record` (append + fsync to the journal). Start
clears the heat and stamps a start time; Resume continues without resetting; the
display is always recomputed from the record, so reopening reconstructs it.

`standings()` / `ladder()` / `calclayout()` are pure and unit-tested.
"""
import math
import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QMdiArea, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from cozer._py2compat import round2
from cozer.app.grids import race_label
from cozer.classes import getclass
from cozer.native import native_races_to_legacy, record_heat
from cozer.phases import heat_number
from cozer.qualification import qheat_boats
from cozer.racepattern import crack_race_pattern, class_pattern, pattern_speed, race_kind
from cozer.raceclock import make_race_clock
from cozer.records import gettimes

# A click within this of a boat's last is a hardware/double-click bounce, not a lap
# -> dropped. Genuine near-simultaneous mis-clicks (>= this, within ~10 s) are kept
# for the editor/analyzer to resolve. Owner-set floor.
_MIN_LAP = 0.01     # seconds

# Legacy prefs palette (RGB) — see legacy/cozer/prefs.py mycolors.
C_READY = "#00ff7f"         # readymark
C_LAPMARK = "#ff7f00"       # lapmark
C_FINISH = "#ff00ff"        # finish
C_FINISHBAR = "#000000"     # finishmark_bg (fg white)
C_INPROGRESS = "#c8c8c8"    # waiting1 (a lap done, still racing)
C_WAITING = "#ffffff"       # not started
C_COMING = "#00ff00"        # legacy 'coming': boat likely closing on the lap line
C_LATE = "#9696f0"          # legacy 'late': boat overdue past its expected crossing

# Lap-line closing hint: warn ~_CLOSING_LEAD s before a boat's expected crossing so
# the operator is ready to click; never sooner than _CLOSING_MIN after the last one.
_CLOSING_LEAD = 5.0    # seconds (legacy '- 5')
_CLOSING_MIN = 10.0    # seconds (legacy 'max(..., 10)')


def estimate_next_lap(course, laptimes, speed_kmh):
    """Seconds until ~``_CLOSING_LEAD`` before a boat's next expected crossing, from
    its last lap's speed -- or, before it has any lap, the class ``speed_kmh`` (the
    pattern '@<speed>' hint). ``course`` is the lap-length list (m), ``laptimes`` the
    boat's completed lap durations (s). None if the boat has finished or is not
    estimable. Legacy predicted this only from the 2nd lap on; the class speed gives
    the same closing hint for the FIRST lap too."""
    ndone = len(laptimes)
    if not course or ndone >= len(course):
        return None
    nextlen = course[min(ndone, len(course) - 1)]
    if ndone >= 1 and laptimes[-1] > 0:
        speed = course[min(ndone - 1, len(course) - 1)] / laptimes[-1]   # m/s from last lap
    elif speed_kmh > 0:
        speed = speed_kmh / 3.6                                          # first lap: class speed
    else:
        return None
    return max(nextlen / speed - _CLOSING_LEAD, _CLOSING_MIN) if speed > 0 else None


def _btn_qss(color, fontpx):
    """Boat-button style: a thin border separates neighbours (avoid mis-taps); on
    hover it thickens so the button stands out."""
    return ("QPushButton { background-color: %s; font-size: %dpx; border: 1px solid #9a9a9a; }"
            "QPushButton:hover { border: 3px solid #202020; }" % (color, fontpx))


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
    """(lap-lengths, scored-heats, duration) for class ``cl`` heat ``h``. Reads the pattern via
    class_pattern, so it works on the native ({name, phases}) and legacy models alike."""
    pat = class_pattern(eventdata, cl)
    if pat:
        r = crack_race_pattern(pat, cl)
        rpat, sheats = r[0], r[1]
        duration = r[2] if len(r) == 3 else None
        li = heat_number(h) - 1                          # phase model decodes the heat-id suffix
        li = max(0, min(li, len(rpat) - 1))
        return list(rpat[li]), sheats, duration
    return [], 1, None


def class_ids(eventdata, cl):
    base = getclass(cl)
    return [str(p[5]) for p in eventdata.get("participants", [])
            if len(p) > 5 and p[4] == base and p[5] != ""]


_KIND_WORD = {"timetrial": "time trial", "qualification": "qualification",
              "endurance": "endurance"}   # circuit (the main/final race) needs no annotation


def heat_identity(eventdata, cl, h):
    """A human-readable identity of the (cl, h) heat for the mis-pick guard: the base class,
    the phase kind (time trial / qualification / endurance — a plain circuit heat is left
    unannotated), the heat number, and a ``(restart)`` marker. Lets the operator eyeball
    exactly what a race will record so a wrong pick (wrong class / phase / restart) stands out."""
    word = _KIND_WORD.get(race_kind(eventdata, cl))
    txt = "%s · %s · heat %d" % (getclass(cl), word, heat_number(h)) if word else \
          "%s · heat %d" % (getclass(cl), heat_number(h))
    if h and h[-1] in ("r", "R"):
        txt += " (restart)"
    return txt


def heat_membership(eventdata, cl, h):
    """The boat-ids that make up class ``cl``'s heat ``h`` — who the Timer materializes and
    shows. For a qualification qheat this is the qheat's OWN group
    (``qualification.qheat_boats`` — qheat1 = the organizer's flag, qheat2 = the complement,
    qheat3 = the repechage field), so a boat appears only in the qheat it actually races (no
    phantom DNS for boats that belong to another qheat). Everything else — a circuit /
    time-trial / endurance heat, an out-of-range heat number, a 3+-way split the single flag
    can't express, or a repechage whose selection qheats aren't recorded yet — falls back to
    the full class field (``class_ids``)."""
    boats = qheat_boats(eventdata, cl, heat_number(h))
    return boats if boats else class_ids(eventdata, cl)


class GridButtons(QWidget):
    """Square boat-number buttons that auto-fit the widget's area (all always
    visible), arranged in tens-grouped rows (calclayout)."""
    def __init__(self, panel, cl, h, ids):
        super().__init__()
        self.panel, self.cl, self.h = panel, cl, h
        # Compact near-square packing (short travel), sorted so decades stay
        # contiguous (easy to find); arrangement is fixed by the boat set, so only
        # the size scales on resize -> stable positions / muscle memory.
        ids = sorted(ids, key=_idkey)
        n = len(ids) or 1
        self.ncols = min(n, max(3, int(math.ceil(math.sqrt(n)))))
        self.nrows = int(math.ceil(n / float(self.ncols)))
        self.own = {}               # pid -> (button, r, c)
        self.sz = 40
        for i, pid in enumerate(ids):
            b = QPushButton(str(pid), self)
            b.clicked.connect(lambda _=False, p=pid: self.panel.record_lap(self.cl, self.h, p))
            self.own[pid] = (b, i // self.ncols, i % self.ncols)
            panel._buttons[(cl, h, pid)] = b
        self.setMinimumSize(self.ncols * 30, self.nrows * 30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, _evt):
        self.relayout()

    def relayout(self):
        self.sz = max(26, min(self.width() // self.ncols, self.height() // self.nrows))
        g = max(4, self.sz // 8)               # gap ~1/8 of the button size
        for pid, (b, r, c) in self.own.items():
            b.setGeometry(c * self.sz + g // 2, r * self.sz + g // 2, self.sz - g, self.sz - g)
            self.restyle(pid)

    def restyle(self, pid):
        b = self.own[pid][0]
        color = self.panel._boat_color(self.cl, self.h, pid)
        b.setStyleSheet(_btn_qss(color, max(10, int(self.sz * 0.34))))


class TimerPanel(QWidget):
    _broadcast_done = Signal(object)   # (gist_id | None | False-on-failure) from the publish thread

    def __init__(self, window, wall=time.time, clock=None):
        super().__init__()
        self.window = window
        self._wall = wall                          # wall clock: displayed start time + resume bridge
        self._clock = clock or make_race_clock()   # race elapsed: monotonic, NTP-immune, sleep-safe
        self._phase = {}            # (cl, h, pid) -> 'coming' | 'late' (lap-line closing hint)
        self._predict = {}          # (cl, h, pid) -> QTimer arming the closing hint
        self._started = False
        self._heats = []
        self._buttons = {}          # (cl, h, pid) -> grid QPushButton
        self._ladder_boats = {}     # (cl, h, pid) -> ladder QPushButton
        self._ladder_layouts = {}   # (cl, h) -> QVBoxLayout of the ladder
        self._grids = {}            # (cl, h) -> GridButtons
        # Live-order broadcast (Phase 7, LIVE.md): publish the unofficial running order to a shared
        # feed, debounced so a slow/failed publish never blocks timing.
        self._broadcast_target = None       # (cl, h) whose order to publish next
        self._publishing = False            # a publish is in flight (avoid overlap / double gist-create)
        self._live_via_server = False       # last publish went to the self-hosted server (vs gist)
        self._broadcast_timer = QTimer(self)
        self._broadcast_timer.setSingleShot(True)
        self._broadcast_timer.setInterval(2500)     # ~1 post / 2.5 s (LIVE.md §3)
        self._broadcast_timer.timeout.connect(self._do_broadcast)
        self._broadcast_done.connect(self._on_broadcast_done)

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
        for w in (self.start_btn, self.stop_btn, self.resume_btn):
            top.addWidget(w)
        top.addStretch()
        self.broadcast_cb = QCheckBox("Broadcast live order")
        self.broadcast_cb.setToolTip(
            "Publish the unofficial live running order to a shared feed for a broadcast / venue "
            "display. Needs GitHub sign-in (top-right corner). Never affects timing.")
        self.broadcast_cb.toggled.connect(self._on_broadcast_toggled)
        top.addWidget(self.broadcast_cb)
        v.addLayout(top)

        # Live-viewer link (Phase 7, LIVE.md §6): shown once a broadcast gist exists so the operator
        # points the venue screens at it. Clickable (opens in the browser) + a Copy button. The base
        # URL follows the repo's GitHub Pages site; the gist id is the persisted live_gist_id.
        self._viewer_url = ""
        self.viewer_row = QWidget()
        _vr = QHBoxLayout(self.viewer_row)
        _vr.setContentsMargins(0, 0, 0, 0)
        _vr.addWidget(QLabel("Live viewer:"))
        self.viewer_link = QLabel()
        self.viewer_link.setTextFormat(Qt.RichText)
        self.viewer_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.viewer_link.setOpenExternalLinks(False)          # route clicks through the clean-env opener
        self.viewer_link.linkActivated.connect(self._open_viewer)
        _vr.addWidget(self.viewer_link, 1)
        _copy = QPushButton("Copy URL")
        _copy.clicked.connect(self._copy_viewer_url)
        _vr.addWidget(_copy)
        self.viewer_row.hide()
        v.addWidget(self.viewer_row)
        self._update_viewer_url()                             # show now if a gist exists from before

        # Mis-pick guard (§5.2): always show exactly what the selected race will record —
        # class · phase · heat · restart — so a wrong pick (wrong class/phase/restart) is
        # obvious before Start commits it.
        self.identity_label = QLabel("")
        self.identity_label.setWordWrap(True)
        self.identity_label.setStyleSheet("color:#00337a; font-weight:bold; padding:2px 0;")
        v.addWidget(self.identity_label)

        # Each heat is a resizable internal sub-window: the grid auto-fits it, so
        # maximizing the app doesn't blow up the buttons — the operator drags a
        # sub-window's borders to set a comfortable grid size.
        self.area = QMdiArea()
        self._subs = []
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
        for i, race in enumerate(self.eventdata.get("races", [])):
            self.race_combo.addItem(race_label(i, race))
        self.race_combo.blockSignals(False)
        # Race labels are long (multi-class, e.g. "Race 1: F-125 3, F-250 3, F-500 3"); widen the
        # drop-down popup to fit the widest one (+ scrollbar/margin) so the operator can tell the
        # races apart -- otherwise Qt elides them ("Race...00 1") in the narrow popup (issue #22).
        if self.race_combo.count():
            fm = self.race_combo.view().fontMetrics()
            widest = max(fm.horizontalAdvance(self.race_combo.itemText(i))
                         for i in range(self.race_combo.count()))
            self.race_combo.view().setMinimumWidth(widest + 40)
        self.on_stop()
        self._show_race()

    def refresh_races(self):
        """Re-sync the race combo with ``eventdata['races']`` — e.g. after races were added on
        the Races tab — preserving the current selection. No-op while a race is being timed, so
        switching tabs never interrupts timing (``reload`` would stop it)."""
        if getattr(self, "_started", False):
            return
        i = self.race_combo.currentIndex()
        self.reload()
        if 0 <= i < self.race_combo.count():
            self.race_combo.setCurrentIndex(i)

    def _selected_race(self):
        i = self.race_combo.currentIndex()
        races = self.eventdata.get("races", [])
        return races[i] if 0 <= i < len(races) else None

    def _race_heats(self, race):
        # race entries are native {name, kind, number, occurrence}; the record is addressed by
        # the legacy (class, heat) key, so convert per-entry (record_heat re-resolves it).
        rows = native_races_to_legacy([race])[0] if race else []
        return [(r[1], r[2]) for r in rows if len(r) > 2 and r[1] and r[2]]

    def _show_race(self):
        self._heats = self._race_heats(self._selected_race())
        self.identity_label.setText(self._race_identity_text())
        self._build()

    def _race_identity_text(self):
        """What the selected race records, decoded per heat — the mis-pick guard's display."""
        if not self._heats:
            return ""
        return "Records:   " + "       |       ".join(
            heat_identity(self.eventdata, cl, h) for cl, h in self._heats)

    def _rec(self, cl, h):
        return record_heat(self.eventdata, cl, h)      # dual-shape (native or legacy record)

    def _heat_ids(self, cl, h):
        rec = self._rec(cl, h)
        if rec:
            return sorted(rec[1].keys(), key=_idkey)
        return sorted(heat_membership(self.eventdata, cl, h), key=_idkey)

    def _boat_color(self, cl, h, pid):
        rec = self._rec(cl, h)
        marks = rec[1].get(pid, []) if rec else []
        laps = len([m for m in marks if m and m[0] in (1, 2)])
        need = len(rec[0].get("course", [])) if rec else len(heat_course(self.eventdata, cl, h)[0])
        if need and laps >= need:
            return C_FINISH
        phase = self._phase.get((cl, h, pid))       # lap-line closing hint overrides while racing
        if phase == "coming":
            return C_COMING
        if phase == "late":
            return C_LATE
        return C_INPROGRESS if laps else C_WAITING

    # ---- lap-line closing hint (legacy ToggleButtonTimer) ----
    def _arm_prediction(self, cl, h, pid):
        """Estimate when this boat next closes on the line and colour its button
        'coming' then 'late' as that time passes -- so the operator is ready to click."""
        key = (cl, h, pid)
        self._cancel_prediction(key)
        rec = self._rec(cl, h)
        course = (rec[0].get("course") if rec else None) or heat_course(self.eventdata, cl, h)[0]
        laptimes = gettimes(rec[1].get(pid, [])) if rec else []
        speed = pattern_speed(class_pattern(self.eventdata, cl) or "")
        et = estimate_next_lap(course, laptimes, speed)
        if et is None or not self._started:
            return
        t = QTimer(self)
        t.setSingleShot(True)
        t.timeout.connect(lambda k=key, e=et: self._on_coming(k, e))
        self._predict[key] = t
        t.start(int(et * 1000))

    def _on_coming(self, key, et):
        self._phase[key] = "coming"
        self._restyle_boat(*key)
        QApplication.beep()
        t = self._predict.get(key)
        if t is not None:                           # then, after a further 0.4*et, 'late'
            t.timeout.disconnect()
            t.timeout.connect(lambda k=key: self._on_late(k))
            t.start(int(0.4 * et * 1000))

    def _on_late(self, key):
        self._phase[key] = "late"
        self._restyle_boat(*key)

    def _cancel_prediction(self, key):
        t = self._predict.pop(key, None)
        if t is not None:
            t.stop()
        self._phase.pop(key, None)

    def _cancel_all_predictions(self):
        for key in list(self._predict):
            self._cancel_prediction(key)

    def _restyle_boat(self, cl, h, pid):
        grid = self._grids.get((cl, h))
        if grid is not None and pid in grid.own:
            grid.restyle(pid)

    def _arm_all_predictions(self):
        for cl, h in self._heats:
            for pid in self._heat_ids(cl, h):
                self._arm_prediction(cl, h, pid)

    def _boat_style(self, s):       # ladder boat button (fixed font)
        color = C_FINISH if s["finished"] else (C_INPROGRESS if s["laps"] else C_WAITING)
        return _btn_qss(color, 12)

    # ---- widget building ----
    def _clear(self):
        self._cancel_all_predictions()
        for sub in self._subs:
            sub.close()
        self._subs = []
        self.area.closeAllSubWindows()
        self._buttons = {}
        self._ladder_boats = {}
        self._ladder_layouts = {}
        self._grids = {}

    def _build(self):
        self._clear()
        for cl, h in self._heats:
            heat_w = QWidget()
            row = QHBoxLayout(heat_w)

            ladder_scroll = QScrollArea()          # ladder can be tall -> its own scroll
            ladder_scroll.setWidgetResizable(True)
            ladder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            ladder_scroll.setMinimumWidth(190)     # wider ladder buttons
            ladder_scroll.setMaximumWidth(220)
            ladder_host = QWidget()
            lv = QVBoxLayout(ladder_host)
            lv.setSpacing(2)
            self._ladder_layouts[(cl, h)] = lv
            ladder_scroll.setWidget(ladder_host)
            row.addWidget(ladder_scroll, 0)
            row.addSpacing(28)                     # gap between ladder and grid

            grid = GridButtons(self, cl, h, self._heat_ids(cl, h))
            self._grids[(cl, h)] = grid
            row.addWidget(grid, 1)

            sub = self.area.addSubWindow(heat_w)
            sub.setWindowTitle("%s  heat %s" % (cl, h))
            sub.setWindowFlags(Qt.SubWindow | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
            sub.resize(820, 560)
            sub.show()
            self._subs.append(sub)
            self._build_ladder(cl, h)

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
                b.setMinimumHeight(26)
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

    def _recorded_heats(self):
        """(cl, h) pairs in the selected race that already hold crossings."""
        return [(cl, h) for cl, h in self._heats
                if (self._rec(cl, h) or [None, {}])[1] and any((self._rec(cl, h))[1].values())]

    def _has_data(self):
        return bool(self._recorded_heats())

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
        now = self._wall()              # wall start time, stored for display
        self._clock.start()             # race elapsed starts at 0
        self._heats = self._race_heats(race)
        for cl, h in self._heats:
            self.setup_heat(cl, h, now)
        self._started = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.race_combo.setEnabled(False)
        self._build()
        self._arm_all_predictions()        # first-lap closing hints from the class @speed
        self.status.setText("Recording…")

    def _confirm_overwrite(self):      # pragma: no cover - modal dialog
        detail = "\n".join("  • " + heat_identity(self.eventdata, cl, h)
                           for cl, h in self._recorded_heats())
        return QMessageBox.question(
            self, "Overwrite race record?",
            "This race already has recorded data — Start will OVERWRITE:\n\n%s\n\n"
            "Start over and lose it? (Use Resume to continue timing instead.)" % detail
            ) == QMessageBox.Yes

    def on_resume(self):
        if not self._ensure_store():
            return
        starts = [(self._rec(cl, h) or [{}])[0].get("starttime") for cl, h in self._heats]
        starts = [s for s in starts if s is not None]
        if not starts:
            self.status.setText("Nothing to resume — press Start.")
            return
        # The race clock reset when the process restarted, so bridge the downtime via
        # the wall clock: resume at (wall now - start) elapsed. Within the resumed
        # session the clock is monotonic/NTP-immune again.
        ref = min(starts)
        bridged = self._wall() - ref
        # But the race has provably run at least as long as its furthest recorded lap.
        # Floor the resume there, so a wrong/backward wall clock at reboot (dead RTC or
        # NTP not yet synced) can't rewind the race and silently drop new crossings.
        recorded = 0.0
        for cl, h in self._heats:
            rec = self._rec(cl, h)
            st = (rec or [{}])[0].get("starttime")
            if rec and st is not None:
                for marks in rec[1].values():
                    recorded = max(recorded, (st - ref) + sum(gettimes(marks)))
        self._clock.start(int(max(bridged, recorded) * 1e9))
        self._started = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.race_combo.setEnabled(False)
        self.status.setText("Recording (resumed)…")
        self._arm_all_predictions()

    def setup_heat(self, cl, h, now):
        course, sheats, duration = heat_course(self.eventdata, cl, h)
        info = {"course": course, "sheats": sheats, "duration": duration, "starttime": now}
        self.window.store.record({"op": "heat", "cl": cl, "h": h, "info": info,
                                  "ids": heat_membership(self.eventdata, cl, h)})

    def record_lap(self, cl, h, pid):
        if not self._started:
            self.status.setText("Press Start (or Resume) to begin timing")
            return
        rec = record_heat(self.eventdata, cl, h)
        prev = sum(gettimes(rec[1].get(pid, [])))
        laptime = round2(self._clock.read_ns() / 1e9 - prev)
        if laptime < _MIN_LAP:             # hardware/double-click bounce, not a lap -> drop
            self.status.setText("Ignored a %.3fs bounce for boat %s" % (laptime, pid))
            return
        self.window.store.record({"op": "lap", "cl": cl, "h": h, "id": pid,
                                  "mark": [1, laptime]})
        grid = self._grids.get((cl, h))
        if grid is not None:
            grid.restyle(pid)
        self._build_ladder(cl, h)          # re-slot the boat into its new zone
        self._arm_prediction(cl, h, pid)   # predict the next crossing -> closing hint
        if self.broadcast_cb.isChecked():  # the order changed -> (throttled) publish the live feed
            self._broadcast_target = (cl, h)
            if not self._broadcast_timer.isActive():   # throttle, NOT restart-debounce: fire ~2.5s
                self._broadcast_timer.start()          # after the FIRST crossing of a burst, so busy
                                                       # racing (crossings <2.5s apart) can't starve
                                                       # the publish into 20-30s stalls (LIVE.md §5)

    # ---- live-order broadcast (Phase 7, LIVE.md) ----
    def _on_broadcast_toggled(self, on):
        """Turn the unofficial live-order feed on/off (LIVE.md §5). Transport is the self-hosted live
        server if configured (live_server_url + live_publish_secret), else the GitHub gist -- which
        needs sign-in, so turning it on while signed out (and without a server) prompts and clears the
        checkbox. On -> publish the current field **immediately** (so the URL appears at once, no
        crossing needed); off -> publish a `stopped` snapshot so the viewer shows the stream disabled."""
        if on:
            from cozer.app import crashreport
            cfg = crashreport.load_config()
            use_server = bool(cfg.get("live_server_url") and cfg.get("live_publish_secret"))
            if not use_server and not cfg.get("token"):
                self.status.setText("Sign in to GitHub (top-right corner) first, then turn on "
                                    "Broadcast live order.")
                self.broadcast_cb.blockSignals(True)
                self.broadcast_cb.setChecked(False)
                self.broadcast_cb.blockSignals(False)
                return
            if self._heats:                 # publish the current field now (gist + URL appear at once)
                self._broadcast_target = self._heats[0]
                cl, h = self._broadcast_target
                self._publish_order(cl, h, self._broadcast_order(cl, h))
                self.status.setText("Broadcasting the live order — the viewer link will appear here "
                                    "in a moment.")
            else:
                self.status.setText("Broadcasting on — select a race to publish the live order.")
        else:
            self._broadcast_timer.stop()
            if self._heats:                 # let the viewer know the stream stopped
                cl, h = self._broadcast_target or self._heats[0]
                self._publish_stopped(cl, h)
            self.status.setText("Live broadcast off.")

    def _do_broadcast(self):
        """(debounce fired after a crossing) Publish the current order of the heat that last changed."""
        if self._broadcast_target is None:
            return
        cl, h = self._broadcast_target
        self._publish_order(cl, h, self._broadcast_order(cl, h))

    def _broadcast_order(self, cl, h):
        """The order to publish for ``(cl, h)``: the live standings once crossings exist, else the
        full field in boat-number order — so a viewer opened before the start already shows the grid.

        Once racing, return the ``standings()`` **dicts** (``{id, laps, time, finished}``) so the feed
        carries laps/time and the "started" flag (live.snapshot reads them); pre-start, bare boat ids
        (the viewer then shows just nat/boat/surname until the first lap)."""
        rec = self._rec(cl, h)
        if rec and rec[1]:
            st = standings(rec)
            if st:
                return st
        return [str(pid) for pid in self._heat_ids(cl, h)]

    def _publish_order(self, cl, h, order):
        self._publish("order", cl, h, order)

    def _publish_stopped(self, cl, h):
        self._publish("stopped", cl, h, None)

    def _publish(self, kind, cl, h, order):
        """Build + publish a snapshot for ``(cl, h)`` in a background thread. Crucially BOTH the build
        and the network post run off the GUI thread: the build's first ``import cozer.app.live`` pulls
        in the report helpers (weasyprint), which is slow the first time and slower still over a network
        filesystem (sshfs), so doing it on the GUI thread froze cozer for seconds when Broadcast was
        first ticked (issue #20). ``kind`` is ``"order"`` (publish ``order``) or ``"stopped"`` (untick).
        Skips only a concurrent gist-*create* (no id yet) so two publishes can't create two gists; once
        the id exists, overlapping PATCHes are harmless."""
        import threading
        from datetime import datetime, timezone
        from cozer.app import crashreport
        cfg = crashreport.load_config()
        server_url = cfg.get("live_server_url")
        secret = cfg.get("live_publish_secret")
        channel = cfg.get("live_channel") or "live"
        use_server = bool(server_url and secret)
        token = cfg.get("token")
        gid = cfg.get("live_gist_id")
        if not use_server and not token:    # no transport configured -> skip quietly
            return
        if self._publishing and not use_server and not gid:   # gist: don't create two gists at once
            return
        self._publishing = True
        self._live_via_server = use_server
        ed = self.eventdata
        updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        def worker():
            result = None
            try:
                from cozer.app import live  # heavy import (weasyprint) -> keep it OFF the GUI thread
                snap = (live.stopped(ed, cl, h, updated) if kind == "stopped"
                        else live.snapshot(ed, cl, h, order, updated, live.DEFAULT_VIEW))
                if use_server:              # self-hosted server: fresh, no token, no gist
                    live.publish_server(server_url, channel, secret, snap)
                    result = True           # success; nothing to persist (the channel is in config)
                else:
                    result = live.publish(token, gid, snap)   # returns the gist id
            except Exception as exc:        # surfaced to the operator; never breaks timing
                result = exc
            self._broadcast_done.emit(result)
        threading.Thread(target=worker, daemon=True).start()

    def _on_broadcast_done(self, result):
        """(GUI thread) Publish finished. ``result`` is the gist id (str) on success, else the
        Exception the worker hit. A permission failure (401/403/404) means the signed-in token
        predates the ``gist`` scope (issue #21) -> ask the operator to re-authorize; anything else is
        a transient note. Timing is never affected either way."""
        self._publishing = False
        if isinstance(result, Exception):
            if not self._live_via_server and getattr(result, "code", None) in (401, 403, 404):
                self.status.setText("Couldn't publish the live order — cozer needs permission to "
                                    "create the live link. Please sign out and sign in to GitHub "
                                    "again (top-right corner), then turn Broadcast on again.")
            else:
                self.status.setText("Couldn't publish the live order (%s) — will retry on the next "
                                    "crossing." % result)
            return
        if not self._live_via_server:       # gist: persist the created id
            gid = result
            if not gid:
                return
            from cozer.app import crashreport
            cfg = crashreport.load_config()
            if cfg.get("live_gist_id") != gid:
                cfg["live_gist_id"] = gid
                crashreport.save_config(cfg)
        self._update_viewer_url()
        self.status.setText("Live order published — the Live viewer link is shown above.")

    def _update_viewer_url(self):
        """Show/refresh the copyable + clickable live-viewer link (LIVE.md §6). Self-hosted server:
        the viewer is served from the live server itself, ``<live_server_url>/?channel=<channel>``.
        Gist: the GitHub Pages viewer with the persisted ``live_gist_id``. Hidden until there's a
        published feed to point at."""
        from cozer.app import crashreport
        cfg = crashreport.load_config()
        url = ""
        if cfg.get("live_server_url") and cfg.get("live_publish_secret"):
            channel = cfg.get("live_channel") or "live"
            url = "%s/?channel=%s" % (cfg["live_server_url"].rstrip("/"), channel)
        elif cfg.get("live_gist_id"):
            owner, _, repo = crashreport.REPO.partition("/")
            url = "https://%s.github.io/%s/live-viewer.html?gist=%s" % (owner, repo, cfg["live_gist_id"])
        self._viewer_url = url
        if url:
            self.viewer_link.setText('<a href="%s">%s</a>' % (url, url))
            self.viewer_row.show()
        else:
            self.viewer_row.hide()

    def _copy_viewer_url(self):
        if self._viewer_url:
            QApplication.clipboard().setText(self._viewer_url)
            self.status.setText("Live viewer URL copied — paste it into the display screens' browser.")

    def _open_viewer(self, url):
        from cozer.app.main import open_in_viewer   # clean-env opener (lazy: main imports timer)
        open_in_viewer(url)

    def on_stop(self):
        self._started = False
        self._cancel_all_predictions()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.race_combo.setEnabled(True)
        self.status.setText("Stopped")

