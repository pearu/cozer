"""Championship Points export (issue #62) — a cross-class CSV of each driver's final RACE ranking +
points.

The real-data tests are driven off the live event file events/tln26.cozj. That file is NOT committed (real
event data lives in the private cozer-events repo), so those tests **skip on CI** and run only where the
file is present (a developer's checkout). The CSV-writer test is file-independent so CI keeps coverage of
the output format.

The event file is LIVE (its results change during the event), so the real-data assertions are data-
independent invariants cross-checked against the proven Full Final, plus guards for the two bugs found
while building it: the time-trial (/T) phase leaking in (0-point duplicate rows) and duplicate boats."""
import csv
import io
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cozer.reports.champpoints import (                             # noqa: E402
    build_championship_points, championship_points_csv, COLUMNS, _race_classes,
)

EVENT = os.path.join(REPO, "events", "tln26.cozj")
needs_event = pytest.mark.skipif(
    not os.path.exists(EVENT), reason="live event file events/tln26.cozj not in repo (CI)")


def _ed():
    from cozer.store import load_event
    return load_event(open(EVENT).read())


def _row(cls, place, boat, first, last, club="", nat="", points=""):
    return {"Event": "e", "Date": "d", "Class": cls, "Place": place, "Boat": boat,
            "First name": first, "Last name": last, "Club": club, "Nationality": nat, "Points": points}


def test_csv_writer_header_and_round_trip():           # file-independent -> always runs (incl. CI)
    rows = [_row("AA", "1", "7", "Ann", "Bee", "RC", "EST", "10"),
            _row("AA", "", "9", "Cee", "Dee")]         # unclassified: blank Place + Points
    text = championship_points_csv(rows)
    assert text.splitlines()[0] == ",".join(COLUMNS)   # header row
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert len(parsed) == len(rows)                    # one line per driver
    assert all(parsed[i][c] == str(rows[i][c]) for i in range(len(rows)) for c in COLUMNS)


def _fullfinal_place_points(ed):
    """{(class, boat): (place_str, points_str)} from the Full Final, per RACE class only."""
    from cozer.reports.final import build_full_final
    out = {}
    for cl in _race_classes(ed):
        for tbl in build_full_final(ed, classes=[cl])["tables"]:
            for r in tbl["rows"]:
                pts = "" if r["sumpoints"] in ("-", None) else r["sumpoints"]
                out[(tbl["class"], str(r["id"]))] = (r["place"], pts)
    return out


@needs_event
def test_championship_points_match_the_full_final_race_standings():
    ed = _ed()
    rows = build_championship_points(ed)
    # 1. only RACE classes appear — never a /T (time-trial) or /Q (qualification) variant
    assert all("/" not in r["Class"] for r in rows)
    # 2. no boat appears twice in a class (the /T-leak bug produced a 0-point duplicate row)
    seen = [(r["Class"], r["Boat"]) for r in rows]
    assert len(seen) == len(set(seen)), "duplicate (class, boat) in the export"
    # 3. every driver's place + points equal the Full Final's for that (class, boat) — ties the export to
    #    the proven standings, so a wrong phase (e.g. the 0-point time trial) can't slip through
    ff = _fullfinal_place_points(ed)
    assert {(r["Class"], r["Boat"]): (r["Place"], r["Points"]) for r in rows} == ff
    assert len(rows) == len(ff) and rows                           # complete + non-empty


@needs_event
def test_selection_normalizes_phase_variants_to_the_race_class():
    ed = _ed()
    race = _race_classes(ed)
    some = race[0]
    # selecting the TIME-TRIAL variant still exports that class's RACE result (base class), not the TT
    picked = build_championship_points(ed, classes=[some + "/T"])
    assert {r["Class"] for r in picked} == {some}
    assert picked == [r for r in build_championship_points(ed, classes=[some]) if r["Class"] == some]
    # None == all race classes THAT HAVE RACED (a class with no race records yet is omitted, so it's a
    # subset of the race classes, never a /T variant); unknown class -> nothing
    exported = {r["Class"] for r in build_championship_points(ed)}
    assert exported and exported <= set(race)
    assert build_championship_points(ed, classes=["No Such Class"]) == []


@needs_event
def test_csv_and_reference_columns_over_real_data():
    ed = _ed()
    rows = build_championship_points(ed)
    parsed = list(csv.DictReader(io.StringIO(championship_points_csv(rows))))
    assert len(parsed) == len(rows)
    # Place is the authoritative input; an unclassified driver has both Place and Points (reference) blank
    for r in rows:
        if r["Place"] == "":
            assert r["Points"] == ""
    # every row carries the same event id + date, so a championship tally can concatenate rounds
    assert {r["Event"] for r in rows} == {"tln26"}
    assert {r["Date"] for r in rows} == {ed.get("date", "")}


@needs_event
def test_reports_tab_button_writes_the_csv(tmp_path, monkeypatch):
    # end-to-end: the Reports-tab "Export championship points…" button writes a CSV of all raced classes
    # (no selection == all). Patches the Save dialog to a temp path.
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    import cozer.app.main as appmain
    w = appmain.MainWindow(_ed())
    out = str(tmp_path / "points.csv")
    monkeypatch.setattr(appmain.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (out, "")))
    w.on_export_championship_points()
    parsed = list(csv.DictReader(open(out, encoding="utf-8")))
    assert list(parsed[0].keys()) == COLUMNS
    assert len(parsed) == len(build_championship_points(_ed()))    # matches the pure builder
