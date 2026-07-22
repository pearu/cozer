"""Practice / Time-trial results (portrait): each boat's best FULL lap across the time-trial heats,
fastest first.

A time-trial (a.k.a. practice / solo run -- the same thing for scoring) is judged on the best full lap,
not on points or per-heat finishing order, so this report is a plain best-lap ranking rather than the
circuit Final layout (issue #29). The Start->first-lap-line run-up is not a lap and never counts as the
best lap; a boat that completed no timed lap is listed last with a dash.
"""
from cozer.analyzer import analyze, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, phase_heat_map
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_index, nationalities_index,
    show_from, show_nationality, meta_of, document_html,
)
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf


def _numkey(bid):
    s = str(bid)
    return (0, int(s)) if s.isdigit() else (1, s)


def _row(cl, pid, parts, nats, place, laptime):
    first, last, club = parts.get((cl, pid), ("", "", ""))
    names = get_fullname(first, last).split(";")
    return {"place": place, "name": names[0].strip(), "extra": [n.strip() for n in names[1:]],
            "from": club, "nat": nats.get((cl, pid), ""), "id": pid, "laptime": laptime}


def build_timetrial(eventdata, classes=None, heat_map=None, options=None):
    ss = eventdata.get("scoringsystem", [])
    rc = rule_action_codes(eventdata)
    labels = get_labels(eventdata)
    phase_of = class_phase_map(eventdata)
    if classes is None:
        classes = get_classes(eventdata)
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    tables = []
    for cl in classes:
        ph = phase_of.get(cl)
        if ph is None or ph.kind != "timetrial":         # this report is time-trial ONLY
            continue
        heat_recs = phase_heat_map(ph)
        if not heat_recs:
            continue
        heats = list(heat_map[cl]) if (heat_map and cl in heat_map) else sorted(heat_recs)
        heats = [h for h in heats if h in heat_recs]
        if not heats:
            continue
        # Best lap per boat = the min lap time (equivalently the max lap speed) across ALL the class's
        # time-trial heats. `field` keeps every boat that ran, so one with no timed lap still appears.
        best, field = {}, set()
        for h in heats:
            info, boats = heat_recs[h]
            field.update(str(p) for p in boats)
            res = analyze(h, [dict(info), boats], ss, rc)
            for pid, r in res.items():
                lt = r.get("laptime", 0)
                if lt and lt > 0:
                    p = str(pid)
                    if p not in best or lt < best[p]:
                        best[p] = lt
        rows = [_row(cl, pid, parts, nats, str(place), "%.3f" % best[pid])
                for place, pid in enumerate(sorted(best, key=lambda p: (best[p], _numkey(p))), 1)]
        rows += [_row(cl, pid, parts, nats, "", "-")            # no timed lap -> last, dash
                 for pid in sorted(field - set(best), key=_numkey)]
        if rows:
            tables.append({"class": getclass(cl), "rows": rows})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["PracticeTimeTrial"], "tables": tables, "posting": True,
            "show_from": show_from(eventdata), "show_nat": show_nationality(eventdata)}


def timetrial_html(model):
    L = model["labels"]
    show_f, show_n = model.get("show_from", True), model.get("show_nat", False)
    body = []
    if not model["tables"]:                                     # no recorded time-trial heats -> a clear
        body.append('<p class="event-meta">%s</p>' % esc(L["NoTimeTrialData"]))   # note, not a blank page
    for t in model["tables"]:
        cols = ['<col style="width:7%">', '<col>']                       # Place, Name (absorbs width)
        head = ['<th class="num">%s</th>' % esc(L["Place"]), '<th>%s</th>' % esc(L["Name"])]
        if show_f:
            cols.append('<col style="width:16%">'); head.append('<th>%s</th>' % esc(L["From"]))
        if show_n:
            cols.append('<col style="width:8%">'); head.append('<th class="num">%s</th>' % esc(L["Nationality"]))
        cols.append('<col style="width:7%">'); head.append('<th class="num">%s</th>' % esc(L["No"]))
        cols.append('<col style="width:18%">'); head.append('<th class="num">%s</th>' % esc(L["LapTime"]))
        ncols = len(head)
        rows = []
        for r in t["rows"]:
            cells = '<td class="num">%s</td><td class="name">%s</td>' % (esc(r["place"]), display(r["name"]))
            if show_f:
                cells += '<td>%s</td>' % display(r["from"])
            if show_n:
                cells += '<td class="num">%s</td>' % esc(r["nat"])
            cells += '<td class="num">%s</td>' % esc(r["id"])
            cells += '<td class="num">%s</td>' % esc(r["laptime"])
            rows.append("<tr>%s</tr>" % cells)
            for x in r["extra"]:                                         # co-drivers on their own line
                rows.append('<tr class="sub"><td></td><td class="name">%s</td>'
                            '<td colspan="%d"></td></tr>' % (display(x), ncols - 2))
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results"><colgroup>%s</colgroup><thead><tr>%s</tr></thead>'
                    '<tbody>%s</tbody></table>' % ("".join(cols), "".join(head), "".join(rows)))
        body.append('<div class="legend">%s</div>' % esc(L["LapTimeNote"]))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body,
                         posting=model.get("posting", False))


def render_timetrial(eventdata, out_path, classes=None, heat_map=None, options=None):
    model = build_timetrial(eventdata, classes, heat_map, options)
    html = timetrial_html(model)
    render_pdf(html, out_path)
    return model, html
