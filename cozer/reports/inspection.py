"""Pre-Race Technical Inspection Form (issue #30).

Two variants of the UIM pre-race scrutineering check list, mirroring the 2026 UIM Circuit Rulebook's
own recommended list (§503.02) plus the reinforced-cockpit block (§509):

  * **Cockpit** classes (reinforced §509 safety capsule, e.g. F2/F4/F 500): general items + the §509
    cockpit block.
  * **Non-cockpit** (open) classes (e.g. F 125/F 250/OSY 400/GT15/GT30): general items + the open-boat
    items (paddle, lanyard kill-cord, sponson-fin system).

The operator chooses the variant (two entries in the Reports combo) and marks the specific classes in
the Reports tab; the form lists whatever was selected. English-only (UIM official-form language); the
article numbers are universal. A static form — no scoring — styled like ``letters.py``.
"""
from cozer.racepattern import get_classes
from cozer.reports.common import esc, meta_of, document_html
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf

# Checklist items as (description, UIM 2026 article). GENERAL applies to every boat; COCKPIT is the
# reinforced-cockpit-only §509 block; OPEN is the items that apply only to boats WITHOUT a reinforced
# cockpit. Article numbers are the current 2026 values (the old 503.xx equipment articles moved to
# 504.xx; the 509.xx cockpit numbers are unchanged). See docs / issue #30 for the full remap.
_GENERAL = [
    ("Life jacket / racing vest", "205.06"),
    ("Crash helmet", "205.07"),
    ("National flag", "206.01"),
    ("Boat number on boat deck", "206.02"),
    ("Bow towing / mooring eye", "504.01"),
    ("Flotation / buoyancy", "504.01"),
    ("Automatic throttle shut-off", "504.03"),
    ("Steering drum and steering cables", "504.05"),
    ("Rigging of fuel systems", "504.05"),
    ("Rigging of electrical systems", "504.05"),
    ("Electrical isolation switch", "504.11"),
    ("Lifting eyes and slings", "205.12"),
    ("Prop guard", "205.10"),
    ("Oil-absorbing carpet", "703"),
    ("U.I.M. sticker (all titled events)", "206.04"),
    ("Fuel / oil", "508.07"),
]
_COCKPIT = [
    ("ID plate on cockpit", "509.01"),
    ("Flotation and pickle-forks (cockpit)", "509.02"),
    ("Seat belts and belt buckle (check for wear)", "509.03"),
    ("Life jacket ballistic cover", "509.04"),
    ("Driver fitting in cockpit", "509.05"),
    ("Water deflector", "509.07"),
    ("Energy-absorbing padding and seat", "509.08"),
    ("Sharp edges in cockpit", "509.09"),
    ("Removable steering wheel", "509.10"),
    ("Rear-view mirrors", "509.11"),
    ("Motor shut-off switch outside of cockpit", "509.12"),
    ("Air vents", "509.14"),
    ("Water inlet holes in back of boat", "509.15"),
    ("Bottom of cockpit coloured orange / number under cockpit", "509.19"),
    ("Air supply (breathing-air bottle)", "509.20"),
]
_OPEN = [
    ("Paddle", "504.01"),
    ("Lanyard ignition kill-cord", "504.03"),
    ("Sponson-fin fixed system", "522.03"),
]

# Driver documents to show (2026 §503.02). HEAD + TAIL apply to all; the middle block is added on the
# cockpit form only. (The 2012 form's homologation sheet / U.I.M.-N.A. page stamps / "current rulebook"
# items are intentionally dropped — the 2026 §503.02 document list no longer includes them.)
_DOCS_HEAD = [
    "a valid licence",
    "a valid measurement certificate for the relevant class",
]
_DOCS_COCKPIT = [
    "a copy of the boat builder's U.I.M. registration (reinforced cockpits)",
    "a valid immersion-training certificate (§205.05) for boats with reinforced cockpits",
    "the manufacturer's certificate of the restraint system (§509.03)",
]
_DOCS_TAIL = [
    "for drivers with a physical handicap, a doctor's written approval that the driver may race "
    "(mentioning any special conditions)",
]

_CSS = (
    "<style>"
    ".ins-field{font-size:11pt;margin:.18cm 0} "
    ".ins-fbox{display:inline-block;border-bottom:1px solid #333;min-width:5cm;height:.55cm;"
    "vertical-align:bottom} "
    ".ins-ck{border-collapse:collapse;width:100%;table-layout:fixed;margin:.2cm 0} "
    ".ins-ck th,.ins-ck td{border:1px solid #333;padding:3px 6px;font-size:9.5pt;vertical-align:middle} "
    ".ins-ck th{background:#eee;text-align:left} "
    ".ins-ck td.art{text-align:center;white-space:nowrap} "
    ".ins-ck tr.grp td{background:#ddd;font-weight:bold} "
    ".ins-docs{border:1px solid #333;padding:6px 6px 6px 4px;font-size:9pt;margin-top:.25cm} "
    ".ins-docs ul{margin:.15cm 0 0 .5cm;padding-left:.6cm} .ins-docs li{margin:2px 0} "
    ".ins-sig{margin-top:.7cm} .ins-sigline{border-bottom:1px solid #333;width:60%;height:1cm} "
    ".ins-sig .role{font-weight:bold;margin-top:2px}"
    "</style>"
)


def _build(eventdata, classes, cockpit):
    labels = get_labels(eventdata)
    names = list(classes) if classes else list(get_classes(eventdata))
    sections = [("General", _GENERAL)]
    sections.append(("Reinforced cockpit (§509)", _COCKPIT) if cockpit
                    else ("Open boats", _OPEN))
    docs = _DOCS_HEAD + (_DOCS_COCKPIT if cockpit else []) + _DOCS_TAIL
    heading = "Pre-Race Technical Inspection — %s" % (
        "Cockpit Classes" if cockpit else "Non-cockpit Classes")
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": "portrait",
            "cockpit": cockpit, "classes": names, "sections": sections, "docs": docs,
            "heading": heading}


def _html(model):
    classes_txt = " / ".join(esc(c) for c in model["classes"]) or "&nbsp;"
    fields = ('<div class="ins-field"><b>Classes:</b> %s</div>'
              '<div class="ins-field"><b>Class:</b> <span class="ins-fbox"></span>'
              '&nbsp;&nbsp;&nbsp;<b>Boat number:</b> <span class="ins-fbox"></span></div>'
              % classes_txt)

    colg = ('<colgroup><col style="width:60%"><col style="width:16%">'
            '<col style="width:24%"></colgroup>')
    head = '<tr><th>Item</th><th class="art">U.I.M. art.</th><th>Check</th></tr>'
    rows = []
    for title, items in model["sections"]:
        rows.append('<tr class="grp"><td colspan="3">%s</td></tr>' % esc(title))
        for item, art in items:
            rows.append('<tr style="height:0.7cm"><td>%s</td><td class="art">%s</td><td></td></tr>'
                        % (esc(item), esc(art)))
    table = ('<table class="ins-ck">%s<thead>%s</thead><tbody>%s</tbody></table>'
             % (colg, head, "".join(rows)))

    docs = ('<div class="ins-docs"><b>The driver must be able to show:</b><ul>%s</ul></div>'
            % "".join("<li>%s</li>" % esc(d) for d in model["docs"]))
    sig = '<div class="ins-sig"><div class="ins-sigline"></div><div class="role">Technical Officer</div></div>'

    return _CSS + document_html(model["orientation"], model["labels"], model["meta"],
                                model["heading"], [fields, table, docs, sig])


def build_inspection_cockpit(eventdata, classes=None):
    return _build(eventdata, classes, cockpit=True)


def build_inspection_open(eventdata, classes=None):
    return _build(eventdata, classes, cockpit=False)


def inspection_cockpit_html(model):
    return _html(model)


def inspection_open_html(model):
    return _html(model)


def render_inspection_cockpit(eventdata, out_path, classes=None):
    model = build_inspection_cockpit(eventdata, classes)
    html = inspection_cockpit_html(model)
    render_pdf(html, out_path)
    return model, html


def render_inspection_open(eventdata, out_path, classes=None):
    model = build_inspection_open(eventdata, classes)
    html = inspection_open_html(model)
    render_pdf(html, out_path)
    return model, html
