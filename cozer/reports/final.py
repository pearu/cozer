"""Full Final (landscape, per-heat + summary) and Short Final (portrait,
summary only) results reports, built from the proven scoring core."""
from cozer.analyzer import analyze, sumanalyze, getsumresorder, rule_action_codes
from cozer.classes import getclass
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_index, sheats_for as _sheats,
    meta_of, document_html,
)
from cozer.reports.labels import get_labels, LABELS, RECCODE_LABEL
from cozer.reports.render import render_pdf


def _legend_index(legend, code, rules):
    key = (code, "; ".join(str(x) for x in rules))
    if key not in legend:
        legend[key] = len(legend) + 1
    return legend[key]


def _result_text(r, legend):
    """Per-heat result cell (adapted from legacy res2latex): speeds + note codes
    with footnote references. Numbers break only at the slash."""
    laps, penlapsleft, lapsleft = r["lapinfo"]
    text = ""
    if r["points"] >= 0:
        if lapsleft:
            text = "%.1f/%.1f/%sL" % (r["avgspeed"], r["maxlapspeed"], laps)
        else:
            text = "%.1f/%.1f" % (r["avgspeed"], r["maxlapspeed"])
    text = text.replace("/", "/&#8203;")   # &#8203; = zero-width space: a wrap point after the slash
    notes = r["notes"]
    if not notes:
        return text or "-"
    parts = [text] if text else []
    for code in notes:
        rules = notes[code]
        if not rules:
            parts.append(esc(code))
        else:
            parts.append("%s<sup>%s</sup>" % (esc(code), _legend_index(legend, code, rules)))
    return " ".join(parts).strip() or "-"


def _legend_html(legend, labels):
    """Footnotes (¹ rule-text) + code glossary (DQ = Disqualif.) + result note."""
    foot, codes = [], []
    for (code, rules), idx in sorted(legend.items(), key=lambda kv: kv[1]):
        foot.append("<sup>%s</sup> %s" % (idx, display(rules)))
        if code not in codes:
            codes.append(code)
    bits = [esc(labels["ResNote"])] + foot
    for code in codes:
        lab = labels.get(RECCODE_LABEL.get(code, ""))
        if lab:
            bits.append("%s = %s" % (esc(code), esc(lab)))
    return "; ".join(bits)


def _build(eventdata, classes, heat_map, orientation, full):
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
        legend = {}
        rows = []
        for pid in order:
            first, last, club = parts.get((cl, str(pid)), ("", "", ""))
            names = get_fullname(first, last).split(";")
            sr = sumres[pid]
            scored = sr["place"] > 0
            heatcells = []
            for h in heats:
                rh = res[h].get(pid)                # a boat need not have raced every heat
                heatcells.append(
                    {"result": "-", "points": "-"} if rh is None else
                    {"result": _result_text(rh, legend),
                     "points": str(rh["points"]) if rh["place"] > 0 else "-"})
            rows.append({
                "place": str(sr["place"]) if scored else "",
                "name": names[0].strip(),
                "extra": [n.strip() for n in names[1:]],
                "from": club,
                "id": str(pid),
                "heats": heatcells,
                "best": ("%.1f/%.1f" % (sr["avgspeed"], sr["maxlapspeed"])) if scored else "-",
                "sumpoints": str(sr["points"]) if scored else "-",
            })
        tables.append({"class": getclass(cl), "heats": heats, "rows": rows,
                       "legend": _legend_html(legend, labels)})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": orientation,
            "full": full, "heading": labels["FinalResults"], "tables": tables}


def build_full_final(eventdata, classes=None, heat_map=None):
    return _build(eventdata, classes, heat_map, "landscape", True)


def build_short_final(eventdata, classes=None, heat_map=None):
    return _build(eventdata, classes, heat_map, "portrait", False)


def _table_html(t, labels, full):
    L = labels
    heats = t["heats"]
    if full:
        # Heats and the Summary hold the same kind of data (result + points), so give
        # them equal-width result+points column pairs (issue #14).
        pair = 69.0 / (len(heats) + 1)
        cols = ['<col style="width:4%">', '<col style="width:15%">',
                '<col style="width:8%">', '<col style="width:4.5%">']
        for _ in range(len(heats) + 1):        # one pair per heat, plus one for the Summary
            cols.append('<col style="width:%.2f%%">' % (pair * 0.58))
            cols.append('<col style="width:%.2f%%">' % (pair * 0.42))
        head1 = ('<tr><th colspan="4"></th>'
                 + "".join('<th class="num" colspan="2">%s %s</th>' % (esc(L["Heat"]), esc(h)) for h in heats)
                 + '<th class="num" colspan="2">%s</th></tr>' % esc(L["Summary"]))
        head2 = ('<tr><th class="num">%s</th><th>%s</th><th>%s</th><th class="num">%s</th>'
                 % (esc(L["Place"]), esc(L["Name"]), esc(L["From"]), esc(L["No"]))
                 + ('<th class="num">%s</th><th class="num">%s</th>' % (esc(L["Res"]), esc(L["Pts"]))) * len(heats)
                 + '<th class="num">%s</th><th class="num">%s</th></tr>' % (esc(L["Res"]), esc(L["Pts"])))
        fs = max(6.5, 9.0 - 0.45 * max(0, len(heats) - 3))
    else:
        # Place, Name, From, No, Results, Points — Results needs room for "45.6/48.2".
        cols = ['<col style="width:7%">', '<col style="width:38%">',
                '<col style="width:15%">', '<col style="width:8%">',
                '<col style="width:20%">', '<col style="width:12%">']
        head1 = ""
        head2 = ('<tr><th class="num">%s</th><th>%s</th><th>%s</th><th class="num">%s</th>'
                 '<th class="num">%s</th><th class="num">%s</th></tr>'
                 % (esc(L["Place"]), esc(L["Name"]), esc(L["From"]), esc(L["No"]),
                    esc(L["Results"]), esc(L["Points"])))
        fs = 9.0
    ncols = (4 + 2 * len(heats) + 2) if full else 6
    body = []
    for row in t["rows"]:
        cells = ('<td class="num">%s</td><td class="name">%s</td><td>%s</td><td class="num">%s</td>'
                 % (esc(row["place"]), display(row["name"]), display(row["from"]), esc(row["id"])))
        if full:
            for hc in row["heats"]:
                cells += '<td class="num">%s</td><td class="num">%s</td>' % (hc["result"], esc(hc["points"]))
        cells += ('<td class="num summary">%s</td><td class="num summary">%s</td>'
                  % (esc(row["best"]), esc(row["sumpoints"])))
        body.append("<tr>%s</tr>" % cells)
        for extra in row["extra"]:
            body.append('<tr class="sub"><td></td><td class="name">%s</td><td colspan="%d"></td></tr>'
                        % (display(extra), ncols - 2))
    colgroup = "<colgroup>%s</colgroup>" % "".join(cols)
    html = '<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"]))
    html += ('<table class="results" style="font-size:%.1fpt">%s<thead>%s%s</thead>'
             '<tbody>%s</tbody></table>' % (fs, colgroup, head1, head2, "".join(body)))
    if t["legend"]:
        html += '<div class="legend">%s</div>' % t["legend"]
    return html


def _results_html(model):
    body = [_table_html(t, model["labels"], model["full"]) for t in model["tables"]]
    return document_html(model["orientation"], model["labels"], model["meta"], model["heading"], body)


def full_final_html(model):
    return _results_html(model)


def short_final_html(model):
    return _results_html(model)


def render_full_final(eventdata, out_path, classes=None, heat_map=None):
    model = build_full_final(eventdata, classes, heat_map)
    html = full_final_html(model)
    render_pdf(html, out_path)
    return model, html


def render_short_final(eventdata, out_path, classes=None, heat_map=None):
    model = build_short_final(eventdata, classes, heat_map)
    html = short_final_html(model)
    render_pdf(html, out_path)
    return model, html
