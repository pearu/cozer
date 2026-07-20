"""Laps Counter Protocol (portrait): the lap-by-lap crossing grid from
``countlaps`` — for each lap column, the boat numbers in crossing order (bold =
completed within race time). This is the tally sheet the lap counters use.
"""
from cozer.analyzer import countlaps
from cozer.classes import getclass
from cozer.phases import class_phase_map, phase_heat_map
from cozer.racepattern import get_classes
from cozer.reports.common import esc, display, meta_of, document_html
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf


def build_laps_protocol(eventdata, classes=None, heat_map=None):
    labels = get_labels(eventdata)
    phase_of = class_phase_map(eventdata)               # legacy class name -> its Phase
    if classes is None:
        classes = get_classes(eventdata)
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
            continue                                    # it rather than KeyError on heat_recs[curheat]
        curheat = heats[-1]
        grid = countlaps(curheat, heat_recs[curheat])
        ncols = max((len(row) for row in grid), default=1)
        cells = []
        for row in grid:
            padded = [(str(i) if i else "", bool(fl)) for (i, fl) in row]
            padded += [("", False)] * (ncols - len(padded))
            cells.append(padded)
        tables.append({"class": getclass(cl), "heat": curheat, "ncols": ncols, "cells": cells})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["LapsCounterProtocol"], "tables": tables}


def laps_protocol_html(model):
    L = model["labels"]
    body = []
    for t in model["tables"]:
        n = t["ncols"]
        heads = [esc(L["Start"])] + ["%s %d" % (esc(L["Lap"]), i) for i in range(1, n)]
        head = "<tr>%s</tr>" % "".join('<th class="num">%s</th>' % h for h in heads)
        colg = "<colgroup>%s</colgroup>" % ('<col style="width:%.3f%%">' % (100.0 / n)) * n
        rows = []
        for row in t["cells"]:
            tds = "".join('<td class="num">%s</td>'
                          % (("<b>%s</b>" % esc(i)) if (i and fl) else esc(i)) for (i, fl) in row)
            rows.append("<tr>%s</tr>" % tds)
        body.append('<h3 class="class-heading">%s %s &nbsp; %s %s</h3>'
                    % (esc(L["Class"]), display(t["class"]), esc(L["Heat"]), esc(t["heat"])))
        body.append('<table class="results">%s<thead>%s</thead><tbody>%s</tbody></table>'
                    % (colg, head, "".join(rows)))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body)


def render_laps_protocol(eventdata, out_path, classes=None, heat_map=None):
    model = build_laps_protocol(eventdata, classes, heat_map)
    html = laps_protocol_html(model)
    render_pdf(html, out_path)
    return model, html
