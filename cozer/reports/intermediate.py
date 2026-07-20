"""Intermediate results report (portrait): the current heat's ordering, with a
summary (best result + points across heats) when more than one heat is shown."""
import time as _time

from cozer.analyzer import analyze, sumanalyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, heat_number, phase_heat_map
from cozer.qualification import classify_qheat, qheat_qualify_count
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, heat_label, participants_index, nationalities_index,
    show_from, show_nationality, sheats_for as _sheats, meta_of, document_html,
)
from cozer.reports.final import _result_text, _legend_html
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf


def build_intermediate(eventdata, classes=None, heat_map=None):
    ss = eventdata.get("scoringsystem", [])
    labels = get_labels(eventdata)
    phase_of = class_phase_map(eventdata)               # legacy class name -> its Phase
    if classes is None:
        classes = get_classes(eventdata)
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    tables = []
    for cl in classes:
        ph = phase_of.get(cl)
        if ph is None:                                  # no such phase
            continue
        heat_recs = phase_heat_map(ph)                  # {heat_id: [info, boats]} for this phase
        if not heat_recs:                               # phase has no recorded heats -> skip
            continue
        heats = list(heat_map[cl]) if (heat_map and cl in heat_map) else sorted(heat_recs)
        heats = [h for h in heats if h in heat_recs]    # a selected heat may be unrecorded (stale
        if not heats:                                   # selection / programmatic heat_map) -> skip
            continue                                    # it rather than KeyError on heat_recs[h]
        rulecodes = rule_action_codes(eventdata)
        res = {h: analyze(h, heat_recs[h], ss, rulecodes) for h in heats}
        curheat = heats[-1]
        istt = ph.kind == "timetrial"                   # dispatch on the phase (was: curheat.endswith("t"))
        isqual = ph.kind == "qualification"
        multi = len(heats) > 1 and not isqual           # qual qheats are separate: no cross-heat summary
        sumres = sumanalyze(heats, res, _sheats(eventdata, cl, len(heats))) if multi else {}
        # per-qheat Q/DNQ (top-N of THIS qheat qualify) — the "printed after each qheat" view
        qmarks = classify_qheat(eventdata, cl, heat_number(curheat)) if isqual else {}
        qcount = qheat_qualify_count(eventdata, cl, heat_number(curheat)) if isqual else 0
        legend = {}
        rows = []
        for pid in getresorder(res[curheat]):
            first, last, club = parts.get((cl, str(pid)), ("", "", ""))
            names = get_fullname(first, last).split(";")
            r = res[curheat][pid]
            scored = r["place"] > 0
            row = {"place": str(r["place"]) if scored else "", "name": names[0].strip(),
                   "extra": [n.strip() for n in names[1:]], "from": club,
                   "nat": nats.get((cl, str(pid)), ""), "id": str(pid)}
            if istt:
                lt = r.get("laptime", 0)
                row["result"] = ("%.3f" % lt) if lt else "-"
            elif isqual:
                row["result"] = _result_text(r, legend)
                row["status"] = qmarks.get(str(pid), "")           # "Q" / "DNQ"
            else:
                row["result"] = _result_text(r, legend)
                row["points"] = str(r["points"]) if scored else "-"
            if multi:
                sr = sumres.get(pid, {})
                ok = sr.get("place", 0) > 0
                row["best"] = ("%.1f/&#8203;%.1f" % (sr["avgspeed"], sr["maxlapspeed"])) if ok else "-"
                row["sumpoints"] = str(sr["points"]) if ok else "-"
            rows.append(row)
        st = heat_recs[curheat][0].get("starttime")
        starttime = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(st)) if st else labels["None"]
        tables.append({"class": getclass(cl), "heat": curheat, "multi": multi, "istt": istt,
                       "isqual": isqual, "qcount": qcount, "starttime": starttime,
                       "rows": rows, "legend": _legend_html(legend, labels)})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["IntermediateResults"], "tables": tables,
            "show_from": show_from(eventdata), "show_nat": show_nationality(eventdata)}


def _header_and_cols(L, multi, istt, isqual=False, show_from=True, show_nat=False):
    # leading columns Place, Name, [From], [Nationality], No -- then a mode-specific tail. From
    # and Nationality are optional (shown only when they vary across the event); Name (width None)
    # absorbs the leftover width.
    lead = [(7, L["Place"], "num"), (None, L["Name"], "")]
    if show_from:
        lead.append((14, L["From"], ""))
    if show_nat:
        lead.append((8, L["Nationality"], "num"))
    lead.append((7, L["No"], "num"))
    if istt:
        tail = [(16, L["LapTime"], "num")]
    elif isqual:
        tail = [(20, L["Res"], "num"), (14, L["Qualify"], "num")]
    elif multi:                                         # cur-Res, cur-Pts, total-Res, total-Pts
        tail = [(16, L["Res"], "num"), (8, L["Pts"], "num"), (16, L["Res"], "num"), (8, L["Pts"], "num")]
    else:
        tail = [(20, L["Res"], "num"), (12, L["Pts"], "num")]
    allcols = lead + tail
    used = sum(w for w, _, _ in allcols if w is not None)
    cols = ['<col style="width:%d%%">' % (w if w is not None else max(18, 100 - used))
            for w, _, _ in allcols]
    head = "<tr>%s</tr>" % "".join(
        ('<th class="num">%s</th>' % esc(h)) if c == "num" else ('<th>%s</th>' % esc(h))
        for _, h, c in allcols)
    return head, cols, len(allcols)


def intermediate_html(model):
    L = model["labels"]
    body = []
    show_f, show_n = model.get("show_from", True), model.get("show_nat", False)
    for t in model["tables"]:
        multi, istt, isqual = t["multi"], t["istt"], t.get("isqual", False)
        head, cols, ncols = _header_and_cols(L, multi, istt, isqual, show_f, show_n)
        rows = []
        for r in t["rows"]:
            cells = '<td class="num">%s</td><td class="name">%s</td>' % (esc(r["place"]), display(r["name"]))
            if show_f:
                cells += '<td>%s</td>' % display(r["from"])
            if show_n:
                cells += '<td class="num">%s</td>' % esc(r["nat"])
            cells += '<td class="num">%s</td>' % esc(r["id"])
            if istt:
                cells += '<td class="num">%s</td>' % esc(r["result"])
            elif isqual:
                cells += '<td class="num">%s</td><td class="num">%s</td>' % (r["result"], esc(r["status"]))
            else:
                cells += '<td class="num">%s</td><td class="num">%s</td>' % (r["result"], esc(r["points"]))
                if multi:
                    cells += ('<td class="num summary">%s</td><td class="num summary">%s</td>'
                              % (r["best"], esc(r["sumpoints"])))
            rows.append("<tr>%s</tr>" % cells)
            for x in r["extra"]:
                rows.append('<tr class="sub"><td></td><td class="name">%s</td>'
                            '<td colspan="%d"></td></tr>' % (display(x), ncols - 2))
        body.append('<h3 class="class-heading">%s %s &nbsp; %s %s</h3>'
                    % (esc(L["Class"]), display(t["class"]), esc(L["Heat"]), esc(heat_label(t["heat"]))))
        body.append('<div class="event-meta">%s: %s</div>' % (esc(L["Starttime"]), esc(t["starttime"])))
        body.append('<table class="results"><colgroup>%s</colgroup><thead>%s</thead>'
                    '<tbody>%s</tbody></table>' % ("".join(cols), head, "".join(rows)))
        if t["legend"]:
            body.append('<div class="legend">%s</div>' % t["legend"])
    return document_html(model["orientation"], L, model["meta"], model["heading"], body)


def render_intermediate(eventdata, out_path, classes=None, heat_map=None):
    model = build_intermediate(eventdata, classes, heat_map)
    html = intermediate_html(model)
    render_pdf(html, out_path)
    return model, html
