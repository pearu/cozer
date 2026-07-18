"""Endurance Full Final report (landscape): total laps time, total laps, points.

Endurance heats route through analyze_endurance (via analyze), which yields
per-competitor ``totallaps`` = (total time, lap count); standings come from
sumanalyze/getsumresorder.
"""
from cozer.analyzer import analyze, sumanalyze, getsumresorder, rule_action_codes
from cozer.classes import getclass
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_index, sheats_for as _sheats,
    meta_of, document_html,
)
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf


def sec2time(secs):
    """HH:MM:SS[.mmm] (faithful port of legacy reports.sec2time)."""
    if secs is None:
        return "-"
    if secs < 0:
        return "- " + sec2time(-secs)
    hours = int(secs / 3600)
    minutes = int((secs - hours * 3600) / 60)
    seconds = int(secs - hours * 3600 - minutes * 60)
    rest = int((secs - hours * 3600 - minutes * 60 - seconds) * 1000)
    if isinstance(secs, int):
        return "%02i:%02i:%02i" % (hours, minutes, seconds)
    return "%02i:%02i:%02i.%03d" % (hours, minutes, seconds, rest)


def build_endurance_final(eventdata, classes=None, heat_map=None):
    record = eventdata.get("record", {})
    ss = eventdata.get("scoringsystem", [])
    labels = get_labels(eventdata)
    if classes is None:
        classes = [c for c in get_classes(eventdata) if c in record]
    parts = participants_index(eventdata)
    tables = []
    for cl in classes:
        if cl not in record:
            continue
        heats = list(heat_map[cl]) if (heat_map and cl in heat_map) else sorted(record[cl].keys())
        if not heats:
            continue
        rulecodes = rule_action_codes(eventdata)
        res = {h: analyze(h, record[cl][h], ss, rulecodes) for h in heats}
        sumres = sumanalyze(heats, res, _sheats(eventdata, cl, len(heats)))
        order = getsumresorder(sumres)
        h0 = heats[0]
        rows = []
        for pid in order:
            first, last, club = parts.get((cl, str(pid)), ("", "", ""))
            names = get_fullname(first, last).split(";")
            sr = sumres[pid]
            r0 = res[h0].get(pid, {})
            tl = r0.get("totallaps", (None, 0))
            scored = sr["place"] > 0
            rows.append({
                "place": str(sr["place"]) if scored else "",
                "name": names[0].strip(), "extra": [n.strip() for n in names[1:]],
                "from": club, "id": str(pid),
                "totaltime": sec2time(tl[0]),
                "totallaps": str(tl[1] or "-"),
                "points": str(sr["points"]) if scored else "-",
            })
        tables.append({"class": getclass(cl), "rows": rows})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "landscape",
            "heading": labels["FinalResults"], "tables": tables}


def endurance_final_html(model):
    L = model["labels"]
    colg = ('<colgroup><col style="width:6%"><col style="width:34%"><col style="width:18%">'
            '<col style="width:8%"><col style="width:16%"><col style="width:9%">'
            '<col style="width:9%"></colgroup>')
    head = ('<tr><th class="num">%s</th><th>%s</th><th>%s</th><th class="num">%s</th>'
            '<th class="num">Total Laps Time</th><th class="num">Total Laps</th>'
            '<th class="num">%s</th></tr>'
            % (esc(L["Place"]), esc(L["Name"]), esc(L["From"]), esc(L["No"]), esc(L["Points"])))
    body = []
    for t in model["tables"]:
        rows = []
        for r in t["rows"]:
            rows.append('<tr><td class="num">%s</td><td class="name">%s</td><td>%s</td>'
                        '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                        '<td class="num summary">%s</td></tr>'
                        % (esc(r["place"]), display(r["name"]), display(r["from"]), esc(r["id"]),
                           esc(r["totaltime"]), esc(r["totallaps"]), esc(r["points"])))
            for x in r["extra"]:
                rows.append('<tr class="sub"><td></td><td class="name">%s</td>'
                            '<td colspan="5"></td></tr>' % display(x))
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results">%s<thead>%s</thead><tbody>%s</tbody></table>'
                    % (colg, head, "".join(rows)))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body)


def render_endurance_final(eventdata, out_path, classes=None, heat_map=None):
    model = build_endurance_final(eventdata, classes, heat_map)
    html = endurance_final_html(model)
    render_pdf(html, out_path)
    return model, html
