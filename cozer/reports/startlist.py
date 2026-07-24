"""Start List / jetty positions (portrait) — each heat's DERIVED start order (PHASES.md §5).

Prints, per selected class and heat, the ordered boat list for the heat's **start / jetty positions**,
computed by :func:`cozer.seeding.start_order`: heat N by heat N-1's finishing order; a final by the
qualifying / time-trial order; the first heat by the participant-list order (307.01 dead-engine jetty
positions from the time trials). This is the paper grid the OOD posts before a heat — the *report*
consumer of the same start order the timer ladder shows. Derived, never stored, so a heat's grid can be
posted **before it is raced**. A boat with no prior-heat ranking (a mid-series joiner) seeds to the back.
"""
from cozer.classes import getclass
from cozer.phases import class_phase_map, heat_number
from cozer.racepattern import class_pattern, crack_race_pattern, get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_index, nationalities_index,
    show_from, show_nationality, meta_of, document_html,
)
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf
from cozer.seeding import start_order


def _heat_count(eventdata, cl):
    """Number of heats the class runs, from its pattern (0 if it has no parseable pattern)."""
    pat = class_pattern(eventdata, cl)
    if not pat:
        return 0
    return len(crack_race_pattern(pat)[0])


def build_startlist(eventdata, classes=None, heat_map=None):
    labels = get_labels(eventdata)
    phase_of = class_phase_map(eventdata)
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    if classes is None:
        classes = get_classes(eventdata)
    tables = []
    for cl in classes:
        if phase_of.get(cl) is None:
            continue
        nheats = _heat_count(eventdata, cl)
        if not nheats:
            continue
        # The operator's heat selection (heat_map) narrows to specific heat numbers; otherwise every
        # heat the class runs gets its own start list (each is posted before its own race).
        if heat_map and cl in heat_map:
            numbers = sorted({heat_number(h) for h in heat_map[cl]})
        else:
            numbers = list(range(1, nheats + 1))
        for number in numbers:
            if not 1 <= number <= nheats:
                continue
            order = start_order(eventdata, cl, str(number))
            if not order:                                   # a class with no boats -> nothing to post
                continue
            rows = []
            for pos, pid in enumerate(order, 1):
                first, last, club = parts.get((cl, pid), ("", "", ""))
                names = get_fullname(first, last).split(";")
                rows.append({"pos": pos, "id": pid, "name": names[0].strip(),
                             "extra": [n.strip() for n in names[1:]],
                             "from": club, "nat": nats.get((cl, pid), "")})
            tables.append({"class": getclass(cl), "heat": number, "rows": rows})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["StartList"], "tables": tables,
            "show_from": show_from(eventdata), "show_nat": show_nationality(eventdata)}


def startlist_html(model):
    L = model["labels"]
    show_f, show_n = model.get("show_from", True), model.get("show_nat", False)
    body = []
    if not model["tables"]:                                 # no seedable class -> a clear note, not blank
        body.append('<p class="event-meta">%s</p>' % esc(L["NoStartListData"]))
    for t in model["tables"]:
        cols = ['<col style="width:8%">', '<col style="width:8%">', '<col>']    # Pos, No, Name
        head = ['<th class="num">%s</th>' % esc(L["StartPos"]),
                '<th class="num">%s</th>' % esc(L["No"]),
                '<th>%s</th>' % esc(L["Name"])]
        if show_f:
            cols.append('<col style="width:16%">')
            head.append('<th>%s</th>' % esc(L["From"]))
        if show_n:
            cols.append('<col style="width:8%">')
            head.append('<th class="num">%s</th>' % esc(L["Nationality"]))
        ncols = len(head)
        rows = []
        for r in t["rows"]:
            cells = ('<td class="num">%s</td><td class="num">%s</td><td class="name">%s</td>'
                     % (esc(r["pos"]), esc(r["id"]), display(r["name"])))
            if show_f:
                cells += '<td>%s</td>' % display(r["from"])
            if show_n:
                cells += '<td class="num">%s</td>' % esc(r["nat"])
            rows.append('<tr>%s</tr>' % cells)
            for x in r["extra"]:                            # a co-driver (endurance) on its own sub-row
                trailing = ('<td colspan="%d"></td>' % (ncols - 3)) if ncols > 3 else ''
                rows.append('<tr class="sub"><td></td><td></td><td class="name">%s</td>%s</tr>'
                            % (display(x), trailing))
        body.append('<h3 class="class-heading">%s %s — %s %s</h3>'
                    % (esc(L["Class"]), display(t["class"]), esc(L["Heat"]), esc(t["heat"])))
        body.append('<table class="results"><colgroup>%s</colgroup><thead><tr>%s</tr></thead>'
                    '<tbody>%s</tbody></table>' % ("".join(cols), "".join(head), "".join(rows)))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body,
                         posting=False)


def render_startlist(eventdata, out_path, classes=None, heat_map=None):
    render_pdf(startlist_html(build_startlist(eventdata, classes, heat_map)), out_path)
