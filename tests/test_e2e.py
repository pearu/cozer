"""End-to-end integration test — the automated half of Phase 6's "full mock event".

Drives the *real* code through one realistic event in a single run:
  new event + store -> import rulesets -> classes/participants/patterns/races ->
  record laps through the Timer (journaled) -> power-loss journal-replay recovery ->
  edit records + save -> render all 9 reports.

It complements the per-part unit tests: this catches regressions in how the parts
fit together on one event. Runs headless (offscreen) in CI.
"""
import copy
import os
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

import cozer.app.main as appmain  # noqa: E402
from cozer.app.main import MainWindow, _REPORTS  # noqa: E402
from cozer.app.ruleset import bundled_dir, import_ruleset  # noqa: E402
from cozer.store import EventStore, loads, read_legacy_coz  # noqa: E402
from cozer.raceclock import RaceClock  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# wc2000's legacy circuit classes mapped to the 2026 circuit catalog:
# OSY/T map 1:1 (space form), the O-<disp> classes become the F-<disp> equivalents,
# and S-250 -> GT15. The map is a pure relabel, so analysis results are unchanged.
CLASS_MAP_2026 = {
    "OSY-400": "OSY 400", "T-400": "T 400",
    "O-500": "F 500", "O-250": "F 250", "O-125": "F 125", "S-250": "GT15",
}


def _ruleset(name):
    return loads(open(os.path.join(bundled_dir(), name), encoding="utf-8").read())


def build_wc2000_2026():
    """Synthesise a 2026-rules event from wc2000's real data (reusable fixture for
    2026-based e2e tests): keep the participants/races/records, reset scoring +
    rules to 2026 (import the 2026 rulesets), and rename classes to the 2026
    catalog via CLASS_MAP_2026 (everywhere they appear)."""
    ed = read_legacy_coz(os.path.join(REPO, "legacy", "events", "wc2000.coz"))
    ed["kind"] = "event"
    ed["scoringsystem"] = []
    ed["rules"] = []
    for rs in ("uim_general_2026.cozj", "uim_circuit_2026.cozj"):
        import_ruleset(ed, _ruleset(rs))
    m = CLASS_MAP_2026
    for c in ed.get("classes", []):
        if len(c) > 1 and c[1] in m:
            c[1] = m[c[1]]
    for p in ed.get("participants", []):
        if len(p) > 4 and p[4] in m:
            p[4] = m[p[4]]
    for race in ed.get("races", []):
        for row in race:
            if len(row) > 1 and row[1] in m:
                row[1] = m[row[1]]
    # remap the record's class keys, and normalise boat ids to str (new-cozer
    # convention; the legacy pickle stores them as ints)
    ed["record"] = {
        m.get(cl, cl): {h: [info, {str(b): mk for b, mk in bm.items()}]
                        for h, (info, bm) in heats.items()}
        for cl, heats in (ed.get("record") or {}).items()
    }
    return ed


def _app():
    return QApplication.instance() or QApplication([])


def _import_ruleset(w, monkeypatch, filename):
    p = os.path.join(bundled_dir(), filename)
    monkeypatch.setattr(appmain.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, _p=p, **k: (_p, "")))
    w.on_import_ruleset()


def test_end_to_end_mock_event(tmp_path, monkeypatch):
    _app()
    path = str(tmp_path / "mock.cozj")

    # 1. New event backed by the crash-safe store
    w = MainWindow()
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (path, "")))
    w.on_save_as()
    assert w.store is not None and os.path.exists(path)

    # 2. Import rule sets: scoring + rules (general) and class-name vocabulary (circuit)
    _import_ruleset(w, monkeypatch, "uim_general_2013.cozj")
    _import_ruleset(w, monkeypatch, "uim_circuit_2013.cozj")
    assert w.eventdata["scoringsystem"] and w.eventdata["rules"]
    assert "O-500" in w.eventdata["classnames"]

    # 3. A class (from the catalog) with a pattern, its participants, and a race
    w.eventdata["classes"] = [["", "O-500", "1*(3*1000):1"]]        # 1 heat, 3 laps
    w.eventdata["participants"] = [["", "Ann", "One", "EST", "O-500", "1"],
                                   ["", "Bo", "Two", "FIN", "O-500", "2"]]
    w.eventdata["races"] = [[["", "O-500", "1"]]]
    w._reload_forms()
    assert {w.classpart_panel._tab_class(i) for i in range(w.classpart_panel.tabs.count())} == {"O-500"}

    # 4. Record laps through the Timer (each click journaled + fsync'd)
    tp = w.timer_panel
    tp.reload()
    tp.race_combo.setCurrentIndex(0)
    clock = [1000.0]
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))   # fake race clock, seconds->ns
    tp.on_start()
    assert ("O-500", "1", "1") in tp._buttons
    for boat in ("1", "2"):
        clock[0] = 1000.0
        for dt in (20.0, 21.0, 22.0):
            clock[0] += dt
            tp.record_lap("O-500", "1", boat)
    laps = w.eventdata["record"]["O-500"]["1"][1]
    assert [m[0] for m in laps["1"]] == [1, 1, 1] and [m[0] for m in laps["2"]] == [1, 1, 1]
    assert os.path.getsize(path + ".journal") > 0                  # journaled, not yet snapshotted

    # 5. Power-loss recovery drill — reopen a COPY (snapshot + journal) and replay
    rec_dir = tmp_path / "recover"
    rec_dir.mkdir()
    rpath = str(rec_dir / "mock.cozj")
    shutil.copy(path, rpath)
    shutil.copy(path + ".journal", rpath + ".journal")
    recovered = EventStore.open(rpath)
    rlaps = recovered.eventdata["record"]["O-500"]["1"][1]
    assert len(rlaps["1"]) == 3 and len(rlaps["2"]) == 3          # journaled laps survived

    # 6. Edit Records: set the race-stop time and save the draft
    ep = w.editor_panel
    ep.reload()
    ep.heat_combo.setCurrentIndex(next(
        i for i, (cl, h) in enumerate(ep._heatkeys) if (cl, h) == ("O-500", "1")))
    ep.commit_racetime(70.0)
    assert ep.save_draft() is True
    assert w.eventdata["record"]["O-500"]["1"][0]["racetime"] == 70.0

    # 7. Render all 9 reports offline; each must produce a non-empty PDF
    import cozer.reports as R
    for _label, funcname, takes, *_ in _REPORTS:      # tolerate extra fields (e.g. heat_map)
        out = str(tmp_path / (funcname + ".pdf"))
        func = getattr(R, funcname)
        if takes:
            func(w.eventdata, out, classes=None)
        else:
            func(w.eventdata, out)
        assert os.path.exists(out) and os.path.getsize(out) > 0, funcname


def test_end_to_end_wc2000_2026(tmp_path, monkeypatch):
    from cozer.analyzer import analyze

    _app()
    ed = build_wc2000_2026()
    scoring = ed["scoringsystem"]
    assert scoring == _ruleset("uim_circuit_2026.cozj")["scoringsystem"]     # 2026 scoring
    classnames = {c[1] for c in ed["classes"] if len(c) > 1 and c[1]}
    assert classnames == {"OSY 400", "T 400", "F 500", "F 250", "F 125", "GT15"}
    assert all(cl in ed["classnames"] for cl in classnames)                  # all in the catalog

    # comparability: a class rename is a pure relabel — same places/points under 2026 scoring
    orig = read_legacy_coz(os.path.join(REPO, "legacy", "events", "wc2000.coz"))
    for legacy_cl, cl2026 in CLASS_MAP_2026.items():
        for h in orig["record"].get(legacy_cl, {}):
            a = analyze(h, copy.deepcopy(orig["record"][legacy_cl][h]), scoring)
            b = analyze(h, copy.deepcopy(ed["record"][cl2026][h]), scoring)
            assert {str(k): (a[k]["place"], a[k]["points"]) for k in a} == \
                   {str(k): (b[k]["place"], b[k]["points"]) for k in b}, (cl2026, h)

    # back it with a store, then drive the pipeline on the real 2026 data
    path = str(tmp_path / "wc2026.cozj")
    w = MainWindow(ed)
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (path, "")))
    w.on_save_as()

    # wc2000 is a *completed* event, so it is not re-timed here (re-timing finished
    # heats would destroy or corrupt the historical result); the fresh-recording +
    # journal-replay path is exercised by test_end_to_end_mock_event. Instead, check
    # the 2026-updated real event round-trips through a snapshot reopen.
    reopened = EventStore.open(path)
    assert reopened.eventdata["scoringsystem"] == scoring                     # 2026 scoring
    assert {c[1] for c in reopened.eventdata["classes"]} == classnames        # remapped classes
    assert reopened.eventdata["record"]["F 500"]["1"][1]                      # records intact

    # edit records: adjust a race-stop time on a real heat and save
    ep = w.editor_panel
    ep.reload()
    ep.heat_combo.setCurrentIndex(0)
    cur_cl, cur_h = ep._heatkeys[0]
    ep.commit_racetime(400.0)
    assert ep.save_draft() is True
    assert w.eventdata["record"][cur_cl][cur_h][0]["racetime"] == 400.0

    # render a few representative reports on the real, 2026-scored data (all 9 are
    # exercised on smaller data by test_end_to_end_mock_event)
    import cozer.reports as R
    for funcname in ("render_full_final", "render_participants", "render_endurance_final"):
        out = str(tmp_path / (funcname + ".pdf"))
        getattr(R, funcname)(w.eventdata, out, classes=None)
        assert os.path.exists(out) and os.path.getsize(out) > 0, funcname


def _reenact_heat(w, cl, h, source_heat):
    """Fill heat (cl, h) by re-enacting it through the real recording paths — the
    data structures get built the way a real race builds them, not initialised
    with results: plain laps via Timer button clicks (the clock is set to each
    boat's arrival instant, boats interleaved in time order), then the event marks
    (DS/IR/DQ/…) via Edit Records. The heat must start empty (no overwrite prompt)."""
    marks_by_boat = source_heat[1]
    tp = w.timer_panel
    tp.reload()
    ri = next(i for i, race in enumerate(w.eventdata["races"])
              if any(len(r) > 2 and r[1] == cl and r[2] == h for r in race))
    tp.race_combo.setCurrentIndex(ri)
    clock = [0.0]                                   # start-time is 0; arrivals are cumulative
    tp._wall = lambda: clock[0]
    tp._clock = RaceClock(lambda: int(round(clock[0] * 1e9)))   # fake race clock, seconds->ns
    tp.on_start()
    arrivals = []
    for boat, marks in marks_by_boat.items():
        t = 0.0
        for m in marks:
            if m[0] == 1:                          # a timed lap = a button press
                t += m[1]
                arrivals.append((t, boat))
    for t, boat in sorted(arrivals):               # click as each boat crosses, in time order
        clock[0] = t
        tp.record_lap(cl, h, boat)
    tp.on_stop()
    ep = w.editor_panel
    ep.reload()
    ep.heat_combo.setCurrentIndex(next(i for i, k in enumerate(ep._heatkeys) if k == (cl, h)))
    for boat, marks in marks_by_boat.items():
        for m in marks:
            if m[0] > 2:                           # event mark at its absolute time + note
                ep.insert_rule_mark(cl, h, boat, m[0], m[1], m[2] if len(m) > 2 else "")
    assert ep.save_draft() is True


def test_reenact_one_heat_matches_wc2000(tmp_path, monkeypatch):
    """First instance of the full re-enactment (option 2 on one heat): rebuild
    wc2000's O-250/2 (-> F 250/2: 14 laps + 4 IR marks) through button clicks +
    Edit Records and assert it matches the historical record exactly. The other
    heats stay available for an eventual all-heats slow test."""
    _app()
    src = build_wc2000_2026()
    cl, h = "F 250", "2"
    source_heat = copy.deepcopy(src["record"][cl][h])
    src["record"] = {}                             # start from empty — fill via the real paths
    w = MainWindow(src)
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "reenact.cozj"), "")))
    w.on_save_as()

    _reenact_heat(w, cl, h, source_heat)

    got = w.eventdata["record"][cl][h][1]
    for boat, ms in source_heat[1].items():
        assert [list(m) for m in got.get(boat, [])] == [list(m) for m in ms], boat
    assert not {b for b in got if b not in source_heat[1] and got[b]}      # no spurious boats


def test_report_generation_error_is_filed(tmp_path, monkeypatch):
    """A report-generation failure must reach the crash reporter, not die silently
    in a message box. Regression guard for the gap the owner hit: reproducing a
    report crash filed no bug report because the generate path swallowed it.

    Works against either report-generation entry point -- the original
    ``on_generate`` or the Reports-tab refactor's ``_render_report`` (called by
    on_view/on_export) -- so this test and that refactor can land independently."""
    _app()
    w = MainWindow(build_wc2000_2026())
    entry = _REPORTS[w.report_combo.currentIndex()]
    label, funcname = entry[0], entry[1]

    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(tmp_path / "r.pdf"), "")))
    monkeypatch.setattr(appmain.QMessageBox, "critical",
                        staticmethod(lambda *a, **k: None))          # no modal in the test
    import cozer.reports as R
    monkeypatch.setattr(R, funcname,
                        lambda *a, **k: (_ for _ in ()).throw(KeyError("83")))

    seen = {}

    def fake_report(window, et, ev, tb, action=None):
        seen["action"], seen["exc"] = action, ev
        return object(), "https://github.com/x/y/issues/1"
    monkeypatch.setattr(appmain, "report_exception", fake_report)

    if hasattr(w, "_render_report"):                                 # Reports-tab refactor
        takes_classes = entry[2] if len(entry) > 2 else False
        takes_heats = entry[3] if len(entry) > 3 else False
        w._render_report(label, funcname, takes_classes, takes_heats,
                         str(tmp_path / "r.pdf"))                    # must not raise
    else:                                                            # original entry point
        w.on_generate()                                             # must not raise

    assert isinstance(seen.get("exc"), KeyError)                     # the real defect was filed
    assert seen["action"] == "Generate report: %s" % label
