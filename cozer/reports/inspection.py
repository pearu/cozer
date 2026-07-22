"""Pre-Race Technical Inspection Form (issue #30).

Two variants of the UIM pre-race scrutineering check list, mirroring the 2026 UIM Circuit Rulebook's
own recommended list (§503.02) plus the reinforced-cockpit block (§509):

  * **Cockpit** classes (reinforced §509 safety capsule, e.g. F2/F4/F 500): general items + the §509
    cockpit block.
  * **Non-cockpit** (open) classes (e.g. F 125/F 250/OSY 400/GT15/GT30): general items + the open-boat
    items (paddle, lanyard kill-cord, sponson-fin system).

The operator chooses the variant (two entries in the Reports combo). Each form is a compact **single
page**. Behaviour by class selection in the Reports tab:

  * **class(es) selected** -> a multi-page PDF with **one page per registered boat**, the *Class* and
    *Boat number* (and driver) pre-filled from the registration data — every boat needs a form.
  * **nothing selected** (``classes`` is ``None``) -> a single blank page whose *Class* and *Boat
    number* are filled in by hand.

English-only (UIM official-form language); the article numbers are universal.
"""
from cozer.reports.common import esc, display, meta_of, participants_by_class, get_fullname
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf, page_css, TABLE_CSS

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

# Compact styling so the whole form (incl. the §509 cockpit block, the longest) fits ONE A4 page;
# one <section class="ins-page"> per boat, each starting on a fresh page. The 9.5pt table font is the
# largest that still keeps the cockpit form on one page even with a multi-line event title (the header
# repeats per boat page) — a bigger font spills to a 2nd page for such events, so don't raise it.
_CSS_BODY = (
    ".ins-page + .ins-page{page-break-before:always}"
    "h2.report-heading{font-size:12pt;margin:.05cm 0 .28cm 0}"
    ".ins-field{font-size:10pt;margin:.1cm 0}"
    ".ins-fbox{display:inline-block;border-bottom:1px solid #333;min-width:3.4cm;height:.42cm;"
    "vertical-align:bottom}"
    ".ins-ck{border-collapse:collapse;width:100%;table-layout:fixed;margin:.12cm 0}"
    ".ins-ck th,.ins-ck td{border:1px solid #555;padding:1.5px 5px;font-size:9.5pt;"
    "vertical-align:middle}"
    ".ins-ck th{background:#e8e8e8;text-align:left}"
    ".ins-ck td.art{text-align:center;white-space:nowrap}"
    ".ins-ck tr.grp td{background:#dcdcdc;font-weight:bold;padding:1px 5px}"
    ".ins-docs{border:1px solid #333;padding:4px 4px 4px 2px;font-size:8pt;margin-top:.18cm}"
    ".ins-docs b{font-size:8.5pt} .ins-docs ul{margin:.08cm 0 0 .4cm;padding-left:.5cm}"
    ".ins-docs li{margin:1px 0}"
    ".ins-sig{margin-top:.4cm} .ins-sigline{border-bottom:1px solid #333;width:60%;height:.85cm}"
    ".ins-sig .role{font-weight:bold;margin-top:2px;font-size:9pt}"
)


def _boatkey(rec):
    pid = rec[4]
    try:
        return (0, int(pid))
    except (TypeError, ValueError):
        return (1, str(pid))


def _boats_for(eventdata, classes):
    """One (class, boat_number, driver) tuple per registered boat in the selected classes, boat-number
    order. Empty list when ``classes`` is falsy (None / nothing selected) -> caller emits one blank
    template page."""
    if not classes:
        return []
    by = participants_by_class(eventdata)
    boats = []
    for cl in classes:
        for _key, first, last, _club, pid in sorted(by.get(cl, []), key=_boatkey):
            driver = get_fullname(first, last).split(";")[0].strip()
            boats.append((cl, str(pid), driver))
    return boats


def _build(eventdata, classes, cockpit):
    sections = [("General", _GENERAL)]
    sections.append(("Reinforced cockpit (§509)", _COCKPIT) if cockpit else ("Open boats", _OPEN))
    docs = _DOCS_HEAD + (_DOCS_COCKPIT if cockpit else []) + _DOCS_TAIL
    heading = "Pre-Race Technical Inspection — %s" % (
        "Cockpit Classes" if cockpit else "Non-cockpit Classes")
    return {"meta": meta_of(eventdata), "labels": get_labels(eventdata), "orientation": "portrait",
            "cockpit": cockpit, "sections": sections, "docs": docs, "heading": heading,
            "boats": _boats_for(eventdata, classes)}


def _fields_html(cl, boat, driver):
    def val(x):
        return esc(x) if x else '<span class="ins-fbox"></span>'
    row = ('<div class="ins-field"><b>Class:</b> %s&nbsp;&nbsp;&nbsp;<b>Boat number:</b> %s'
           % (val(cl), val(boat)))
    if driver:
        row += '&nbsp;&nbsp;&nbsp;<b>Driver:</b> %s' % display(driver)
    return row + "</div>"


def _checklist_html(sections):
    colg = ('<colgroup><col style="width:60%"><col style="width:15%">'
            '<col style="width:25%"></colgroup>')
    head = '<tr><th>Item</th><th class="art">U.I.M. art.</th><th>Check</th></tr>'
    rows = []
    for title, items in sections:
        rows.append('<tr class="grp"><td colspan="3">%s</td></tr>' % esc(title))
        for item, art in items:
            rows.append('<tr><td>%s</td><td class="art">%s</td><td></td></tr>' % (esc(item), esc(art)))
    return ('<table class="ins-ck">%s<thead>%s</thead><tbody>%s</tbody></table>'
            % (colg, head, "".join(rows)))


def _html(model):
    L, meta = model["labels"], model["meta"]
    header = ('<h1 class="event-title">%s</h1>'
              '<div class="event-meta">%s &nbsp;&middot;&nbsp; %s</div>'
              '<h2 class="report-heading">%s</h2>'
              % (display(meta["title"]), display(meta["venue"]), display(meta["date"]),
                 esc(model["heading"])))
    checklist = _checklist_html(model["sections"])
    docs = ('<div class="ins-docs"><b>The driver must be able to show:</b><ul>%s</ul></div>'
            % "".join("<li>%s</li>" % esc(d) for d in model["docs"]))
    sig = ('<div class="ins-sig"><div class="ins-sigline"></div>'
           '<div class="role">Technical Officer</div></div>')

    pages = []
    for cl, boat, driver in (model["boats"] or [("", "", "")]):   # [] -> one blank template page
        pages.append('<section class="ins-page">%s%s%s%s%s</section>'
                     % (header, _fields_html(cl, boat, driver), checklist, docs, sig))

    css = page_css(model["orientation"],
                   footer_left="%s  /%s/" % (meta["officer"], L["OfficeroftheDay"]),
                   footer_center=L["Page"],
                   footer_right="%s  /%s/" % (meta["secretary"], L["SecretaryoftheRace"]))
    return "<style>%s\n%s\n%s</style>%s" % (css, TABLE_CSS, _CSS_BODY, "".join(pages))


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
