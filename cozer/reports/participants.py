"""Participants (registered competitors) and Drivers-Meeting Check List reports.
Both are participant listings — no scoring — grouped by class."""
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, participants_by_class, meta_of, document_html,
)
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf

CHECK_BLANK_ROWS = 4   # extra empty rows per class for late write-ins


def _class_tables(eventdata, classes):
    by_cls = participants_by_class(eventdata)
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
                         "from": club, "id": pid})
        tables.append({"class": cl, "rows": rows})
    return tables


def build_participants(eventdata, classes=None):
    labels = get_labels(eventdata)
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["Registeredcompetitors"], "tables": _class_tables(eventdata, classes)}


def participants_html(model):
    L = model["labels"]
    colg = '<colgroup><col style="width:58%"><col style="width:28%"><col style="width:14%"></colgroup>'
    head = ('<tr><th>%s</th><th>%s</th><th class="num">%s</th></tr>'
            % (esc(L["Name"]), esc(L["Country"]), esc(L["RaceNo"])))
    body = []
    for t in model["tables"]:
        rows = []
        for r in t["rows"]:
            rows.append('<tr><td class="name">%s</td><td>%s</td><td class="num">%s</td></tr>'
                        % (display(r["name"]), display(r["from"]), esc(r["id"])))
            for x in r["extra"]:
                rows.append('<tr class="sub"><td class="name">%s</td><td></td><td></td></tr>' % display(x))
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results">%s<thead>%s</thead><tbody>%s</tbody></table>'
                    % (colg, head, "".join(rows)))
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
