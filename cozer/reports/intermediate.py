"""Intermediate results report (portrait): the current heat's ordering, with a
summary (best result + points across heats) when more than one heat is shown."""
import time as _time

from cozer.analyzer import analyze, sumanalyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, phase_heat_map
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_index, sheats_for as _sheats,
    meta_of, document_html,
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
        multi = len(heats) > 1
        istt = ph.kind == "timetrial"                   # dispatch on the phase (was: curheat.endswith("t"))
        sumres = sumanalyze(heats, res, _sheats(eventdata, cl, len(heats))) if multi else {}
        legend = {}
        rows = []
        for pid in getresorder(res[curheat]):
            first, last, club = parts.get((cl, str(pid)), ("", "", ""))
            names = get_fullname(first, last).split(";")
            r = res[curheat][pid]
            scored = r["place"] > 0
            row = {"place": str(r["place"]) if scored else "", "name": names[0].strip(),
                   "extra": [n.strip() for n in names[1:]], "from": club, "id": str(pid)}
            if istt:
                lt = r.get("laptime", 0)
                row["result"] = ("%.3f" % lt) if lt else "-"
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
                       "starttime": starttime, "rows": rows, "legend": _legend_html(legend, labels)})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["IntermediateResults"], "tables": tables}


def _header_and_cols(L, multi, istt):
    if istt:
        cols = ['<col style="width:8%">', '<col style="width:44%">', '<col style="width:22%">',
                '<col style="width:10%">', '<col style="width:16%">']
        head = ('<tr><th class="num">%s</th><th>%s</th><th>%s</th><th class="num">%s</th>'
                '<th class="num">%s</th></tr>'
                % (esc(L["Place"]), esc(L["Name"]), esc(L["From"]), esc(L["No"]), esc(L["LapTime"])))
        return head, cols, 5
    if multi:
        # Place, Name, From, No, cur-Res, cur-Pts, total-Res, total-Pts — the summary
        # (total) Res/Pts need the same room as the current-heat ones to avoid wrapping.
        cols = ['<col style="width:6%">', '<col style="width:27%">', '<col style="width:12%">',
                '<col style="width:7%">', '<col style="width:16%">', '<col style="width:8%">',
                '<col style="width:16%">', '<col style="width:8%">']
        head = ('<tr><th class="num">%s</th><th>%s</th><th>%s</th><th class="num">%s</th>'
                '<th class="num">%s</th><th class="num">%s</th>'
                '<th class="num">%s</th><th class="num">%s</th></tr>'
                % (esc(L["Place"]), esc(L["Name"]), esc(L["From"]), esc(L["No"]),
                   esc(L["Res"]), esc(L["Pts"]), esc(L["Res"]), esc(L["Pts"])))
        return head, cols, 8
    cols = ['<col style="width:7%">', '<col style="width:38%">', '<col style="width:15%">',
            '<col style="width:8%">', '<col style="width:20%">', '<col style="width:12%">']
    head = ('<tr><th class="num">%s</th><th>%s</th><th>%s</th><th class="num">%s</th>'
            '<th class="num">%s</th><th class="num">%s</th></tr>'
            % (esc(L["Place"]), esc(L["Name"]), esc(L["From"]), esc(L["No"]),
               esc(L["Res"]), esc(L["Pts"])))
    return head, cols, 6


def intermediate_html(model):
    L = model["labels"]
    body = []
    for t in model["tables"]:
        multi, istt = t["multi"], t["istt"]
        head, cols, ncols = _header_and_cols(L, multi, istt)
        rows = []
        for r in t["rows"]:
            cells = ('<td class="num">%s</td><td class="name">%s</td><td>%s</td><td class="num">%s</td>'
                     % (esc(r["place"]), display(r["name"]), display(r["from"]), esc(r["id"])))
            if istt:
                cells += '<td class="num">%s</td>' % esc(r["result"])
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
                    % (esc(L["Class"]), display(t["class"]), esc(L["Heat"]), esc(t["heat"])))
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
