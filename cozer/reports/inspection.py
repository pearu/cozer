"""Pre-Race Technical Inspection Form (issue #30).

Two variants of the UIM pre-race scrutineering check list, from the 2026 UIM Circuit Rulebook's own
recommended list (§503.02) + the reinforced-cockpit block (§509):

  * **Cockpit** classes (reinforced §509 safety capsule — F2/F4/F 500): general items + the full §509
    cockpit set.
  * **Non-cockpit** (open) classes (F 125/F 250/OSY 400/GT15/GT30): general items + the open-boat items.

Each checklist line is **mandatory unless marked**: a trailing italic note flags a *conditional* item
("if fitted", "titled events", "F4/S3 only", …) or a *recommended* one. Mandatory technical conditions
that a specialist already certified once (the cockpit was registered, the hull got its HIN, …) are NOT
physically re-inspected at the ramp — they sit in a separate **"Documents & certificates"** block where
the scrutineer confirms the paperwork exists.

The operator picks the variant (two entries in the Reports combo). Class(es) selected → a multi-page PDF,
one page per registered boat, with Class / Boat number / Driver pre-filled; nothing selected → one blank
page. English-only (UIM official-form language). Article numbers are universal.
"""
from cozer.reports.common import esc, display, meta_of, participants_by_class, get_fullname
from cozer.reports.labels import get_labels
from cozer.reports.render import render_pdf, page_css, TABLE_CSS

# Checklist items: (description, UIM 2026 article, condition). condition="" => mandatory; otherwise the
# note is printed in italic so an inspector sees the item only applies when the condition holds (or is
# merely recommended). Certificate-proven conditions are NOT here — they live in the documents block.
_GENERAL = [
    ("Life jacket / racing vest", "205.06", ""),
    ("Crash helmet (approved type, in date)", "205.07", ""),
    ("Prop guard", "205.10", ""),
    ("Lifting eyes and slings", "205.12", ""),
    ("National flag", "206.01", ""),
    ("Boat number on boat deck", "206.02", ""),
    ("Bow towing / mooring eye(s)", "504.01", ""),
    ("Flotation / buoyancy", "504.01", ""),
    ("Automatic throttle shut-off", "504.03", ""),
    ("Steering, fuel and electrical rigging", "504.05", ""),
    ("Electrical isolation switch", "504.11", ""),
    ("Fuel / oil (sample for testing)", "508.07", ""),
    ("Oil-absorbing carpet", "703", ""),
    ("U.I.M. sticker", "206.04", "titled events only"),
    ("Windscreen (removable, non-sharp)", "504.02", "if fitted"),
    ("Ballast — fixed, removable, ≤ 10% class min weight", "504.12", "if fitted"),
    ("Propeller exhaust-tube dimensions", "504.13", "if through-prop exhaust"),
]
_COCKPIT = [
    ("Frontal head restraint (FHR)", "205.07.01", ""),
    ("Protective clothing — one-piece overall", "205.11", ""),
    ("Pickle-forks present and attached", "509.02", ""),
    ("Seat belts / 6-point harness — wear and central release", "509.03", ""),
    ("Life jacket ballistic cover", "509.04", ""),
    ("Driver fully enclosed + helmet clearance", "509.05", ""),
    ("Energy-absorbing foam around helmet", "509.06", ""),
    ("Water deflector", "509.07", ""),
    ("Energy-absorbing padding and seat", "509.08", ""),
    ("Sharp edges in cockpit", "509.09", ""),
    ("Removable steering wheel", "509.10", ""),
    ("Rear-view mirrors (left + right)", "509.11", ""),
    ("Motor shut-off switch outside of cockpit", "509.12", ""),
    ("180° field of view", "509.13", ""),
    ("Air vents", "509.14", ""),
    ("Water inlet holes in back of boat", "509.15", ""),
    ("Canopy — shatterproof, external handle, rescue slot, quick-release hinge", "509.16", ""),
    ("Bottom of cockpit orange + number", "509.19", ""),
    ("Air supply — mounted, gauge readable, demonstrated", "509.20", ""),
    ("Overhead relief opening above helmet", "509.17", "recommended"),
    ("Crash boxes", "509.21", "F4 / S3 only"),
    ("Airbag system inspection", "509.24", "if an airbag is fitted"),
]
_OPEN = [
    ("Paddle", "504.01", ""),
    ("Lanyard ignition kill-cord", "504.03", ""),
    ("Sponson-fin fixed system", "522.03", ""),
]

# The live fit-check the reinforced-cockpit inspection guidelines require (printed under the §509 list).
_COCKPIT_FIT = ("With the driver: don all safety kit, get in, fasten the harness, fit the wheel, close "
                "the visor, then demonstrate self-release of the harness and use of the air supply.")

# Documents & certificates — the scrutineer confirms these EXIST (a specialist certified the underlying
# technical condition once); no physical re-inspection at the event. (name, reference, condition).
_DOCS_COMMON = [
    ("Valid licence", "", ""),
    ("Valid measurement certificate for the class", "", ""),
    ("Doctor's written approval for a driver with a physical handicap", "", "if applicable"),
]
_DOCS_COCKPIT = [
    ("U.I.M. Digital Log Book / Measurement Certificate", "501.11", ""),
    ("Cockpit U.I.M. registration № + Newton rating (plate + certificate)", "509.01", ""),
    ("Boat builder's U.I.M. registration (reinforced cockpit)", "509.01", ""),
    ("Immersion-training certificate (renewed ≤ 14 months)", "205.05", ""),
    ("Restraint-system manufacturer certificate", "509.03", ""),
    ("Hull Identification Number (HIN) present + recorded", "509.23", ""),
    ("Crash-box construction certificate", "509.21", "F4 / S3 only"),
    ("Cockpit / structure repair certification + log book", "509.22", "if repaired"),
]

_CSS_BODY = (
    ".ins-page + .ins-page{page-break-before:always}"
    "h2.report-heading{font-size:12pt;margin:.05cm 0 .18cm 0}"
    ".ins-field{font-size:9.5pt;margin:.08cm 0}"
    ".ins-fbox{display:inline-block;border-bottom:1px solid #333;min-width:3cm;height:.4cm;"
    "vertical-align:bottom}"
    ".ins-legend{font-size:7.5pt;color:#555;margin:.02cm 0 .12cm 0}"
    ".ins-grp{font-weight:bold;background:#dcdcdc;padding:2px 5px;font-size:8.5pt;margin:.12cm 0 .06cm 0;"
    "border:1px solid #bbb}"
    ".ins-cols{column-count:2;column-gap:12px}"
    ".ci{break-inside:avoid;display:flex;align-items:baseline;gap:5px;padding:1.5px 0;"
    "border-bottom:1px solid #e2e2e2;font-size:8.5pt}"
    ".ci .box{flex:0 0 auto;width:10px;height:10px;border:1px solid #333;transform:translateY(1px)}"
    ".ci .txt{flex:1 1 auto}"
    ".ci .art{flex:0 0 auto;color:#555;white-space:nowrap}"
    ".ci .cond{color:#777;font-style:italic}"
    ".ins-note{font-size:8pt;font-style:italic;color:#333;margin:.1cm 0 .05cm 0}"
    ".ins-docs{border:1px solid #333;padding:4px 6px;margin-top:.18cm}"
    ".ins-docs .dh{font-weight:bold;font-size:8.5pt;margin-bottom:.06cm}"
    ".ins-sig{margin-top:.35cm} .ins-sigline{border-bottom:1px solid #333;width:55%;height:.8cm}"
    ".ins-sig .role{font-weight:bold;margin-top:2px;font-size:9pt}"
)


def _boatkey(rec):
    pid = rec[4]
    try:
        return (0, int(pid))
    except (TypeError, ValueError):
        return (1, str(pid))


def _boats_for(eventdata, classes):
    """(class, boat_number, driver) per registered boat in the selected classes, boat-number order.
    Empty when ``classes`` is falsy (nothing selected) -> caller emits one blank template page."""
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
    docs = list(_DOCS_COMMON) + (list(_DOCS_COCKPIT) if cockpit else [])
    heading = "Pre-Race Technical Inspection — %s" % (
        "Cockpit Classes" if cockpit else "Non-cockpit Classes")
    return {"meta": meta_of(eventdata), "labels": get_labels(eventdata), "orientation": "portrait",
            "cockpit": cockpit, "sections": sections, "docs": docs, "heading": heading,
            "fit_note": _COCKPIT_FIT if cockpit else "", "boats": _boats_for(eventdata, classes)}


def _fields_html(cl, boat, driver):
    def val(x):
        return esc(x) if x else '<span class="ins-fbox"></span>'
    row = ('<div class="ins-field"><b>Class:</b> %s&nbsp;&nbsp;&nbsp;<b>Boat number:</b> %s'
           % (val(cl), val(boat)))
    if driver:
        row += '&nbsp;&nbsp;&nbsp;<b>Driver:</b> %s' % display(driver)
    return row + "</div>"


def _item_html(name, art, cond):
    cond_html = ' <span class="cond">— %s</span>' % esc(cond) if cond else ""
    art_html = '<span class="art">%s</span>' % esc(art) if art else ""
    return ('<div class="ci"><span class="box"></span>'
            '<span class="txt">%s%s</span>%s</div>' % (esc(name), cond_html, art_html))


def _section_html(title, items):
    body = "".join(_item_html(*it) for it in items)
    return '<div class="ins-grp">%s</div><div class="ins-cols">%s</div>' % (esc(title), body)


def _docs_html(docs):
    items = "".join(_item_html(name, ref, cond) for name, ref, cond in docs)
    return ('<div class="ins-docs"><div class="dh">Documents &amp; certificates — confirm each exists '
            '(no physical re-inspection):</div><div class="ins-cols">%s</div></div>' % items)


def _html(model):
    header = ('<h1 class="event-title">%s</h1>'
              '<div class="event-meta">%s &nbsp;&middot;&nbsp; %s</div>'
              '<h2 class="report-heading">%s</h2>'
              % (display(model["meta"]["title"]), display(model["meta"]["venue"]),
                 display(model["meta"]["date"]), esc(model["heading"])))
    legend = ('<div class="ins-legend">Every item is mandatory unless marked in italics '
              '(condition, or “recommended”). Tick each check.</div>')
    sections = "".join(_section_html(t, items) for t, items in model["sections"])
    fit = '<div class="ins-note">%s</div>' % esc(model["fit_note"]) if model["fit_note"] else ""
    docs = _docs_html(model["docs"])
    sig = ('<div class="ins-sig"><div class="ins-sigline"></div>'
           '<div class="role">Technical Officer</div></div>')

    pages = []
    for cl, boat, driver in (model["boats"] or [("", "", "")]):   # [] -> one blank template page
        pages.append('<section class="ins-page">%s%s%s%s%s%s%s</section>'
                     % (header, _fields_html(cl, boat, driver), legend, sections, fit, docs, sig))

    L, meta = model["labels"], model["meta"]
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
