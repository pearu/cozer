"""Full Final results report.

Builds a structured report model from ``eventdata`` and the proven scoring core
(``analyze`` + ``sumanalyze``), then renders print-quality HTML/PDF. The model
values come entirely from equivalence-proven functions; only the assembly and
presentation are new (see MAINTENANCE_PLAN.md Phase 4).
"""
import copy

from cozer.analyzer import analyze, sumanalyze, getsumresorder
from cozer.classes import getclass
from cozer.racepattern import crack_race_pattern, get_classes
from cozer.reports.render import TABLE_CSS, page_css, render_pdf
from cozer.reports.latexish import latex_to_html


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _display(s):
    """Render a free-text field (may contain LaTeX) as a safe HTML fragment."""
    return latex_to_html(s)


def get_fullname(first, last):
    """Combine first/last, supporting ';'-separated multi-driver boats
    (faithful port of legacy reports.get_fullname)."""
    first, last = str(first), str(last)
    if ";" in first and first.count(";") > last.count(";"):
        last += ";" * (first.count(";") - last.count(";"))
    if ";" in last and first.count(";") < last.count(";"):
        first += ";" * (last.count(";") - first.count(";"))
    if ";" in first and first.count(";") == last.count(";"):
        return "; ".join("%s %s" % (f, l) for f, l in zip(first.split(";"), last.split(";")))
    return "%s %s" % (first, last)


def _participants_index(eventdata):
    parts = {}
    for p in eventdata.get("participants", []):
        if len(p) < 6:
            continue
        first, last, club, cls, pid = p[1], p[2], p[3], p[4], p[5]
        for c in (cls, cls + "/Q", cls + "/T"):
            parts[(c, str(pid))] = (first, last, club)
    return parts


def _sheats(eventdata, cl, default):
    for l in eventdata.get("classes", []):
        if len(l) > 2 and l[1] == cl and l[2]:
            try:
                return crack_race_pattern(l[2], cl)[1]
            except Exception:
                return default
    return default


def _legend_index(legend, code, rules):
    key = (code, "; ".join(str(x) for x in rules))
    if key not in legend:
        legend[key] = len(legend) + 1
    return legend[key]


def _result_text(r, legend):
    """Per-heat result cell (adapted from legacy res2latex): speeds and any
    note codes with footnote references. Same information, HTML presentation."""
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
            parts.append(_esc(code))
        else:
            parts.append("%s<sup>%s</sup>" % (_esc(code), _legend_index(legend, code, rules)))
    return " ".join(parts).strip() or "-"


def build_full_final(eventdata, classes=None, heat_map=None):
    """Return a report model: title/meta + one table per class with per-heat
    results and summary standings, ordered by ``getsumresorder``."""
    record = eventdata.get("record", {})
    ss = eventdata.get("scoringsystem", [])
    if classes is None:
        classes = [c for c in get_classes(eventdata) if c in record]
    parts = _participants_index(eventdata)
    tables = []
    for cl in classes:
        if cl not in record:
            continue
        heats = list(heat_map[cl]) if (heat_map and cl in heat_map) else sorted(record[cl].keys())
        if not heats:
            continue
        res = {h: analyze(h, copy.deepcopy(record[cl][h]), ss) for h in heats}
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
                r = res[h][pid]
                heatcells.append({
                    "result": _result_text(r, legend),
                    "points": str(r["points"]) if r["place"] > 0 else "-",
                })
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
        tables.append({
            "class": getclass(cl),
            "heats": heats,
            "rows": rows,
            "legend": [{"index": i, "code": k[0], "rules": k[1]}
                       for k, i in sorted(legend.items(), key=lambda kv: kv[1])],
        })
    return {
        "title": eventdata.get("title", ""),
        "venue": eventdata.get("venue", ""),
        "date": eventdata.get("date", ""),
        "officer": eventdata.get("officer", ""),
        "secretary": eventdata.get("secretary", ""),
        "heading": "Final Results",
        "orientation": "landscape",
        "tables": tables,
    }


def _table_html(t):
    heats = t["heats"]
    ncols = 4 + 2 * len(heats) + 2
    head1 = '<tr><th colspan="4"></th>'
    for h in heats:
        head1 += '<th class="num" colspan="2">Heat %s</th>' % _esc(h)
    head1 += '<th class="num" colspan="2">Summary</th></tr>'
    head2 = ('<tr><th class="num">Pl</th><th>Name</th><th>From</th><th class="num">No</th>'
             + '<th class="num">Res</th><th class="num">Pts</th>' * len(heats)
             + '<th class="num">Res</th><th class="num">Pts</th></tr>')
    body = []
    for row in t["rows"]:
        cells = ('<td class="num">%s</td><td class="name">%s</td><td>%s</td><td class="num">%s</td>'
                 % (_esc(row["place"]), _display(row["name"]), _display(row["from"]), _esc(row["id"])))
        for hc in row["heats"]:
            cells += '<td class="num">%s</td><td class="num">%s</td>' % (hc["result"], _esc(hc["points"]))
        cells += ('<td class="num summary">%s</td><td class="num summary">%s</td>'
                  % (_esc(row["best"]), _esc(row["sumpoints"])))
        body.append("<tr>%s</tr>" % cells)
        for extra in row["extra"]:
            body.append('<tr class="sub"><td></td><td class="name">%s</td><td colspan="%d"></td></tr>'
                        % (_display(extra), ncols - 2))
    # colgroup widths (sum ~100%) so table-layout:fixed always fits the page width
    pair = 57.0 / len(heats) if heats else 57.0
    cols = ['<col style="width:3.5%">', '<col style="width:15%">',
            '<col style="width:8%">', '<col style="width:4.5%">']
    for _h in heats:
        cols.append('<col style="width:%.2f%%">' % (pair * 0.58))
        cols.append('<col style="width:%.2f%%">' % (pair * 0.42))
    cols += ['<col style="width:7%">', '<col style="width:5%">']
    colgroup = "<colgroup>%s</colgroup>" % "".join(cols)
    fs = max(6.5, 9.0 - 0.45 * max(0, len(heats) - 3))   # shrink many-heat tables
    html = '<h3 class="class-heading">Class %s</h3>' % _display(t["class"])
    html += ('<table class="results" style="font-size:%.1fpt">%s<thead>%s%s</thead>'
             '<tbody>%s</tbody></table>' % (fs, colgroup, head1, head2, "".join(body)))
    if t["legend"]:
        leg = "; ".join('<sup>%d</sup> %s = %s' % (e["index"], _esc(e["code"]), _display(e["rules"]))
                        for e in t["legend"])
        html += '<div class="legend">%s</div>' % leg
    return html


def full_final_html(model):
    css = page_css(model["orientation"],
                   footer_left="%s  /Officer of the Day/" % model["officer"],
                   footer_center="Page",
                   footer_right="%s  /Secretary/" % model["secretary"])
    parts = ["<style>%s\n%s</style>" % (css, TABLE_CSS)]
    parts.append('<h1 class="event-title">%s</h1>' % _display(model["title"]))
    parts.append('<div class="event-meta">%s &nbsp;&middot;&nbsp; %s</div>'
                 % (_display(model["venue"]), _display(model["date"])))
    parts.append('<h2 class="report-heading">%s</h2>' % _display(model["heading"]))
    for t in model["tables"]:
        parts.append(_table_html(t))
    return "\n".join(parts)


def render_full_final(eventdata, out_path, classes=None, heat_map=None):
    model = build_full_final(eventdata, classes, heat_map)
    html = full_final_html(model)
    render_pdf(html, out_path)
    return model, html
