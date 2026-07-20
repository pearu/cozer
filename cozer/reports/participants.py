"""Participants (registered competitors) and Drivers-Meeting Check List reports.
Both are participant listings — no scoring — grouped by class."""
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_by_class, nationalities_index,
    show_from, show_nationality, meta_of, document_html,
)
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf

CHECK_BLANK_ROWS = 4   # extra empty rows per class for late write-ins


def _class_tables(eventdata, classes):
    by_cls = participants_by_class(eventdata)
    nats = nationalities_index(eventdata)
    if classes is None:
        classes = [c for c in get_classes(eventdata) if c in by_cls]
    tables = []
    for cl in classes:
        if cl not in by_cls:
            continue
        rows = []
        for _key, first, last, club, pid in by_cls[cl]:
            names = get_fullname(first, last).split(";")
            rows.append({"name": names[0].strip(), "extra": [n.strip() for n in names[1:]],
                         "from": club, "nat": nats.get((cl, str(pid)), ""), "id": pid})
        tables.append({"class": cl, "rows": rows})
    return tables


def build_participants(eventdata, classes=None):
    labels = get_labels(eventdata)
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["Registeredcompetitors"], "tables": _class_tables(eventdata, classes),
            "show_from": show_from(eventdata), "show_nat": show_nationality(eventdata)}


def participants_html(model):
    L = model["labels"]
    # optional middle columns between Name and Race No.: From (club) and/or Nationality, each
    # shown only when it varies across the event (build_participants set the flags).
    mid = ([("from", L["From"])] if model.get("show_from") else []) + \
          ([("nat", L["Nationality"])] if model.get("show_nat") else [])
    id_w, mid_w = 14, 24
    cols = (['<col style="width:%d%%">' % (100 - id_w - mid_w * len(mid))]
            + ['<col style="width:%d%%">' % mid_w for _ in mid]
            + ['<col style="width:%d%%">' % id_w])
    head = "<tr>%s%s<th class=\"num\">%s</th></tr>" % (
        "<th>%s</th>" % esc(L["Name"]), "".join("<th>%s</th>" % esc(h) for _, h in mid),
        esc(L["RaceNo"]))
    body = []
    for t in model["tables"]:
        rows = []
        for r in t["rows"]:
            cells = ('<td class="name">%s</td>' % display(r["name"])
                     + "".join('<td>%s</td>' % display(r[k]) for k, _ in mid)
                     + '<td class="num">%s</td>' % esc(r["id"]))
            rows.append("<tr>%s</tr>" % cells)
            for x in r["extra"]:
                rows.append('<tr class="sub"><td class="name">%s</td>%s</tr>'
                            % (display(x), "<td></td>" * (len(mid) + 1)))
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results"><colgroup>%s</colgroup><thead>%s</thead>'
                    '<tbody>%s</tbody></table>' % ("".join(cols), head, "".join(rows)))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body)


def build_checklist(eventdata, classes=None):
    labels = get_labels(eventdata)
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "landscape",
            "heading": labels["DriversMeetingChecklist"], "tables": _class_tables(eventdata, classes)}


def checklist_html(model):
    L = model["labels"]
    colg = ('<colgroup><col style="width:26%"><col style="width:16%"><col style="width:6%">'
            '<col style="width:13%"><col style="width:13%"><col style="width:13%">'
            '<col style="width:13%"></colgroup>')
    head = ('<tr><th>%s</th><th>%s</th><th class="num">%s</th><th>%s</th>'
            '<th>%s 1</th><th>%s 2</th><th>%s 3</th></tr>'
            % (esc(L["Name"]), esc(L["From"]), esc(L["No"]), esc(L["Inspection"]),
               esc(L["Meeting"]), esc(L["Meeting"]), esc(L["Meeting"])))
    blanks = "<td></td><td></td><td></td><td></td>"     # inspection + 3 meetings
    body = []
    for t in model["tables"]:
        rows = []
        for r in t["rows"]:
            rows.append('<tr style="height:0.95cm"><td class="name">%s</td><td>%s</td>'
                        '<td class="num">%s</td>%s</tr>'
                        % (display(r["name"]), display(r["from"]), esc(r["id"]), blanks))
            for x in r["extra"]:
                rows.append('<tr class="sub"><td class="name">%s</td><td></td><td></td>%s</tr>'
                            % (display(x), blanks))
        for _ in range(CHECK_BLANK_ROWS):
            rows.append('<tr style="height:0.95cm"><td></td><td></td><td></td>%s</tr>' % blanks)
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results">%s<thead>%s</thead><tbody>%s</tbody></table>'
                    % (colg, head, "".join(rows)))
    return document_html(model["orientation"], L, model["meta"], model["heading"], body)


def render_participants(eventdata, out_path, classes=None):
    model = build_participants(eventdata, classes)
    html = participants_html(model)
    render_pdf(html, out_path)
    return model, html


def render_checklist(eventdata, out_path, classes=None):
    model = build_checklist(eventdata, classes)
    html = checklist_html(model)
    render_pdf(html, out_path)
    return model, html
