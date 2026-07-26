"""Championship Points export (issue #62).

A cross-class **spreadsheet** of each driver's FINAL event ranking + points, for feeding a multi-event
championship / series where this event is one round. Unlike the other reports this is a CSV (stdlib, opens
in any spreadsheet program — no new dependency), not a PDF.

**Model A** (the shipped scope): the RANK is the authoritative, series-independent export; the event's own
points ride along only as a *reference* column, because the series may use a **different scoring system**
than the race event and applies its own table downstream. So cozer never presents the event points AS
championship points.

Reuses the Full-Final standings assembly (``build_full_final`` → ``sumanalyze``/``getsumresorder``) — no
core-scoring change; the ranking is exactly what the Full Final report shows.
"""
import csv
import io

from cozer.racepattern import get_classes
from cozer.reports.common import participants_index, nationalities_index
from cozer.reports.final import build_full_final

# The spreadsheet columns, in order. Event/Date identify the round so a championship tally can concatenate
# several rounds' exports; Place is the authoritative input, Points the event's own (reference) score.
COLUMNS = ["Event", "Date", "Class", "Place", "Boat", "First name", "Last name",
           "Club", "Nationality", "Points"]


def _event_name(eventdata):
    return (eventdata.get("broadcast", {}) or {}).get("eventname") or eventdata.get("title", "") or ""


def _race_classes(eventdata):
    """The RACE/final classes — the base class names, without the ``/T`` (time-trial) or ``/Q``
    (qualification) phase variants. Championship points come from the final race result, never the
    time trial (which scores 0), so those variants are excluded."""
    return [cl for cl in get_classes(eventdata) if "/" not in cl]


def build_championship_points(eventdata, classes=None):
    """Rows (list of dicts keyed by ``COLUMNS``) for the selected classes' final RACE standings.

    ``classes`` is the Reports-tab class selection (``None`` = all classes); any phase variant is
    normalized to its base race class, so the export always reflects the final race result (not the time
    trial). A driver who started but never classified appears with a blank Place and Points. Ordering:
    classes as selected/declared, drivers by final rank (unclassified last)."""
    race = _race_classes(eventdata)
    if classes is None:
        targets = race
    else:                                                   # normalize F 500/T -> F 500, keep order, dedupe
        seen, targets = set(), []
        for cl in classes:
            base = cl.split("/")[0]
            if base in race and base not in seen:
                seen.add(base)
                targets.append(base)
    model = build_full_final(eventdata, classes=targets)
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    event, date = _event_name(eventdata), eventdata.get("date", "") or ""
    rows = []
    for tbl in model["tables"]:
        cl = tbl["class"]                                   # display name == participant-index base key
        for r in tbl["rows"]:
            pid = str(r["id"])
            first, last, club = parts.get((cl, pid), ("", "", ""))
            points = r["sumpoints"]
            rows.append({
                "Event": event, "Date": date, "Class": cl,
                "Place": r["place"],                        # "" when unclassified/DNQ
                "Boat": pid, "First name": first, "Last name": last,
                "Club": club, "Nationality": nats.get((cl, pid), "") or r.get("nat", ""),
                "Points": "" if points in ("-", None) else points,   # reference only (see module doc)
            })
    return rows


def championship_points_csv(rows):
    """``rows`` as CSV text: the ``COLUMNS`` header then one line per driver."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def render_championship_points(eventdata, path, classes=None):
    """Write the Championship Points CSV to ``path``; returns the rows."""
    rows = build_championship_points(eventdata, classes=classes)
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(championship_points_csv(rows))
    return rows
