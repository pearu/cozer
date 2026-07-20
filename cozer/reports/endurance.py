"""Endurance Full Final report (landscape): total laps time, total laps, points.

Endurance heats route through analyze_endurance (via analyze), which yields
per-competitor ``totallaps`` = (total time, lap count); standings come from
sumanalyze/getsumresorder.
"""
from cozer.analyzer import analyze, sumanalyze, getsumresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, phase_heat_map
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_index, nationalities_index,
    show_from, show_nationality, sheats_for as _sheats, meta_of, document_html,
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
                "from": club, "nat": nats.get((cl, str(pid)), ""), "id": str(pid),
                "totaltime": sec2time(tl[0]),
                "totallaps": str(tl[1] or "-"),
                "points": str(sr["points"]) if scored else "-",
            })
        tables.append({"class": getclass(cl), "rows": rows})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "landscape",
            "heading": labels["FinalResults"], "tables": tables, "posting": True,
            "show_from": show_from(eventdata), "show_nat": show_nationality(eventdata)}


def endurance_final_html(model):
    L = model["labels"]
    # Leading columns Place, Name, [From], [Nationality], No -- From/Nationality shown only when
    # they vary across the event (D1); Name absorbs the width a dropped/added column frees or takes.
    show_f, show_n = model.get("show_from", True), model.get("show_nat", False)
    name_w = 34 + (0 if show_f else 18) - (8 if show_n else 0)
    cols = ['<col style="width:6%">', '<col style="width:%d%%">' % name_w]
    if show_f:
        cols.append('<col style="width:18%">')
    if show_n:
        cols.append('<col style="width:8%">')
    cols += ['<col style="width:8%">', '<col style="width:16%">',
             '<col style="width:9%">', '<col style="width:9%">']
    colg = "<colgroup>%s</colgroup>" % "".join(cols)
    lead_head = '<th class="num">%s</th><th>%s</th>' % (esc(L["Place"]), esc(L["Name"]))
    if show_f:
        lead_head += '<th>%s</th>' % esc(L["From"])
    if show_n:
        lead_head += '<th class="num">%s</th>' % esc(L["Nationality"])
    lead_head += '<th class="num">%s</th>' % esc(L["No"])
    head = ('<tr>' + lead_head
            + '<th class="num">%s</th><th class="num">%s</th><th class="num">%s</th></tr>'
            % (esc(L["TotalLapsTime"]), esc(L["TotalLaps"]), esc(L["Points"])))
    subcol = 4 + int(show_f) + int(show_n)         # co-driver sub-row: colspan over the trailing cells
    body = []
    for t in model["tables"]:
        rows = []
        for r in t["rows"]:
            cells = '<td class="num">%s</td><td class="name">%s</td>' % (esc(r["place"]), display(r["name"]))
            if show_f:
                cells += '<td>%s</td>' % display(r["from"])
            if show_n:
                cells += '<td class="num">%s</td>' % esc(r["nat"])
            cells += ('<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                      '<td class="num summary">%s</td>'
                      % (esc(r["id"]), esc(r["totaltime"]), esc(r["totallaps"]), esc(r["points"])))
            rows.append("<tr>%s</tr>" % cells)
            for x in r["extra"]:
                rows.append('<tr class="sub"><td></td><td class="name">%s</td>'
                            '<td colspan="%d"></td></tr>' % (display(x), subcol))
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results">%s<thead>%s</thead><tbody>%s</tbody></table>'
                    % (colg, head, "".join(rows)))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body,
                         posting=model.get("posting", False))


def render_endurance_final(eventdata, out_path, classes=None, heat_map=None):
    model = build_endurance_final(eventdata, classes, heat_map)
    html = endurance_final_html(model)
    render_pdf(html, out_path)
    return model, html
