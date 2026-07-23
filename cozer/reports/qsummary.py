"""Qualification summary report (portrait) — the *final-like* view of a qualification phase:
one table per class listing every boat's overall **Q / DNQ** advancement across all qheats,
distinguishing a direct (primary) qualifier from a repechage (second-chance) one.

Companion to the Intermediate report's per-qheat ``isqual`` view (printed after each qheat):
this one summarises who reached the finals once every qheat has run (UIM 209 / §4.1)."""
from cozer.analyzer import analyze, getresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import canonical_record, class_phase_map
from cozer.qualification import classify, qualification_counts
from cozer.racepattern import class_pattern, get_classes
from cozer.reports.common import (
    display, esc, get_fullname, meta_of, participants_index, nationalities_index,
    show_from, show_nationality, document_html, collect_penalty_notes, penalty_notes_html,
)
from cozer.reports.final import _legend_html, _result_text
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf


def build_qualification(eventdata, classes=None, heat_map=None):
    ss = eventdata.get("scoringsystem", [])
    labels = get_labels(eventdata)
    phase_of = class_phase_map(eventdata)
    parts = participants_index(eventdata)
    if classes is None:
        classes = get_classes(eventdata)
    tables = []
    for cl in classes:
        ph = phase_of.get(cl)
        if ph is None or ph.kind != "qualification":
            continue
        counts = qualification_counts(class_pattern(eventdata, cl))
        final = classify(eventdata, cl)                 # boat -> "primary" | "repechage" | "dnq"
        if not counts or not final:
            continue
        nq = len(counts)
        rulecodes = rule_action_codes(eventdata)
        # per boat: the last qheat it raced (repechage overrides its earlier selection qheat) and
        # its result there — analyze each qheat once.
        info = {}                                       # boat -> (qheat_number, result, place, is_rep)
        legend = {}
        for number in range(1, nq + 1):
            canon = canonical_record(ph, number)
            if canon is None:
                continue
            hid, rec = canon
            res = analyze(hid, [dict(rec[0]), rec[1]], ss, rulecodes)
            is_rep = (nq >= 2 and number == nq)
            for pid in getresorder(res):
                info[str(pid)] = (number, _result_text(res[pid], legend, native=True), res[pid]["place"], is_rep)

        nats = nationalities_index(eventdata)
        rows = []
        for boat, st in final.items():
            number, result, place, is_rep = info.get(boat, (0, "-", 0, False))
            first, last, club = parts.get((cl, boat), ("", "", ""))
            names = get_fullname(first, last).split(";")
            rows.append({
                "id": boat, "name": names[0].strip(), "extra": [n.strip() for n in names[1:]],
                "from": club, "nat": nats.get((cl, boat), ""), "result": result,
                "qheat": (labels["Repechage"] if is_rep else str(number)) if number else "-",
                "status": "DNQ" if st == "dnq" else "Q",
                # order: qualified first (primaries by qheat/place, then repechage), then DNQ
                "_sort": (0 if st != "dnq" else 1, 1 if is_rep else 0, number, place),
            })
        rows.sort(key=lambda r: r["_sort"])
        for r in rows:
            del r["_sort"]
        tables.append({"class": getclass(cl), "rows": rows,
                       "legend": _legend_html(legend, labels, extra=labels["QualifyNote"], native=True)})
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "heading": labels["PhaseQualification"], "tables": tables, "posting": True,
            "penalty_notes": collect_penalty_notes(eventdata, classes, heat_map, labels),
            "show_from": show_from(eventdata), "show_nat": show_nationality(eventdata)}


def qualification_html(model):
    L = model["labels"]
    # optional person columns between Name and Qheat: From (club, 14%) and/or Nationality (8%),
    # each shown only when it varies across the event.
    person = (([("from", L["From"], 14)] if model.get("show_from") else [])
              + ([("nat", L["Nationality"], 8)] if model.get("show_nat") else []))
    name_w = 100 - (8 + 10 + 20 + 12) - sum(w for _, _, w in person)   # No, Qheat, Res, Qualify + person
    cols = ('<col style="width:8%">' + '<col style="width:%d%%">' % name_w
            + "".join('<col style="width:%d%%">' % w for _, _, w in person)
            + '<col style="width:10%"><col style="width:20%"><col style="width:12%">')
    head = ('<tr><th class="num">%s</th><th>%s</th>%s<th class="num">%s</th>'
            '<th class="num">%s</th><th class="num">%s</th></tr>'
            % (esc(L["No"]), esc(L["Name"]), "".join("<th>%s</th>" % esc(h) for _, h, _ in person),
               esc(L["Heat"]), esc(L["Res"]), esc(L["Qualify"])))
    body = []
    for t in model["tables"]:
        rows = []
        for r in t["rows"]:
            person_cells = "".join("<td>%s</td>" % display(r[k]) for k, _, _ in person)
            rows.append('<tr><td class="num">%s</td><td class="name">%s</td>%s'
                        '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                        % (esc(r["id"]), display(r["name"]), person_cells,
                           esc(r["qheat"]), r["result"], esc(r["status"])))
            for x in r["extra"]:
                rows.append('<tr class="sub"><td></td><td class="name">%s</td>'
                            '<td colspan="%d"></td></tr>' % (display(x), 3 + len(person)))
        body.append('<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"])))
        body.append('<table class="results"><colgroup>%s</colgroup><thead>%s</thead>'
                    '<tbody>%s</tbody></table>' % (cols, head, "".join(rows)))
        if t["legend"]:
            body.append('<div class="legend">%s</div>' % t["legend"])
    nh = penalty_notes_html(model.get("penalty_notes"), L)            # issue #33: notes after the tables
    if nh:
        body.append(nh)
    return document_html(model["orientation"], L, model["meta"], model["heading"], body,
                         posting=model.get("posting", False))


def render_qualification(eventdata, out_path, classes=None, heat_map=None):
    render_pdf(qualification_html(build_qualification(eventdata, classes, heat_map)), out_path)
