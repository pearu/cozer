"""Shared helpers for building and rendering cozer reports."""
from datetime import datetime

from cozer.phases import _parse_heat_id
from cozer.racepattern import crack_race_pattern
from cozer.reports.latexish import latex_to_html
from cozer.reports.render import TABLE_CSS, page_css


def heat_label(heat_id):
    """A heat id as displayed in a report header. UIM 209 restart notation: ``1``→``1``,
    ``1r``→``1R`` (first restart), ``1R``→``1R2`` (second restart). Time-trial (``2t``) and
    qualification (``3q``) ids show a **bare number** (``2``/``3``) — the phase kind is already
    shown separately (report subtitle / column), so the ``t``/``q`` would be a redundant leak.
    Presentation-only; the ``R`` suffix already means "second restart", so no finals/last-heat
    context is needed. An unrecognized id raises (surfaced, not silently mangled)."""
    number, suffix = _parse_heat_id(heat_id)
    return "%d%s" % (number, {"r": "R", "R": "R2", "t": "", "q": ""}.get(suffix, suffix))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def display(s):
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


def participants_index(eventdata):
    """(class, str(id)) -> (first, last, club), incl. /Q and /T variants."""
    parts = {}
    for p in eventdata.get("participants", []):
        if len(p) < 6:
            continue
        first, last, club, cls, pid = p[1], p[2], p[3], p[4], p[5]
        for c in (cls, cls + "/Q", cls + "/T"):
            parts[(c, str(pid))] = (first, last, club)
    return parts


def nationalities_index(eventdata):
    """(class, str(id)) -> nationality (participant index 6), incl. /Q and /T variants; ``""``
    if unset. Kept separate from :func:`participants_index` so existing report callers are
    untouched — a report reads this only when it renders the Nationality column."""
    out = {}
    for p in eventdata.get("participants", []):
        if len(p) < 6:
            continue
        nat = (p[6] if len(p) > 6 else "") or ""
        for c in (p[4], p[4] + "/Q", p[4] + "/T"):
            out[(c, str(p[5]))] = nat
    return out


def _has_distinct(values):
    """True if ``values`` are not all the same — the condition for showing an optional report
    column. Empty counts as its own value, so an all-empty column and a uniform column (every row
    identical, e.g. a national event's all-``EST``) are both hidden — they distinguish nothing —
    but a column where some rows are filled and others blank IS shown (the filled rows carry
    information worth printing). (owner's rule for From/club + Nationality.)"""
    return len({(v or "").strip() for v in values}) > 1


def show_from(eventdata):
    """Whether reports show the From/club column — only when clubs vary across the event (an event
    with no club, or one shared club, hides it)."""
    return _has_distinct(p[3] for p in eventdata.get("participants", []) if len(p) > 3)


def show_nationality(eventdata):
    """Whether reports show the Nationality column — only when nationalities vary across the event
    (a single-nationality *national* event, or none set, hides it — no wasted all-``EST`` column)."""
    return _has_distinct((p[6] if len(p) > 6 else "") for p in eventdata.get("participants", []) if len(p) >= 6)


def participants_by_class(eventdata):
    """class -> list of (sortkey, first, last, club, id) sorted by race number."""
    by_cls = {}
    for p in eventdata.get("participants", []):
        if len(p) < 6:
            continue
        first, last, club, cls, pid = p[1], p[2], p[3], p[4], p[5]
        if not cls:
            continue
        try:
            key = int(pid)
        except (ValueError, TypeError):
            key = pid
        by_cls.setdefault(cls, []).append((key, first, last, club, str(pid)))
    for cls in by_cls:
        by_cls[cls].sort(key=lambda t: (isinstance(t[0], str), t[0]))
    return by_cls


def sheats_for(eventdata, cl, default):
    # scored-heats count (":B") from the class pattern; class_pattern reads either the native
    # base/phase model or the legacy suffixed rows, so this is shape-agnostic. No pattern ->
    # score all heats (default). A malformed pattern is a real data fault and is left to raise
    # (any class reaching a report was already analyzed, which cracks the same pattern).
    from cozer.racepattern import class_pattern
    pat = class_pattern(eventdata, cl)
    return crack_race_pattern(pat, cl)[1] if pat else default


def meta_of(eventdata):
    return {k: eventdata.get(k, "")
            for k in ("title", "venue", "date", "officer", "secretary", "uim_commissioner")}


def _posted_on(labels, posted_date):
    """The top-right "Posted on: <date> __:__" line: ``date`` is the day the document is generated;
    the time is left blank (larger, for hand-writing in pen) — the §209 *actual time of posting*,
    which starts the protest clock (§403)."""
    return ('<div style="text-align:right;font-size:10pt;margin-bottom:.15em">%s: %s &nbsp;'
            '<span style="font-size:16pt">____:____</span></div>'
            % (esc(labels["PostedOn"]), esc(posted_date)))


def _posting_block(labels, meta):
    """The §209 signature block for a results sheet: ruled lines for each *assigned* signer — the
    OOD/Race Director (or delegate, §209/p37) and the UIM Sports Commissioner (co-signs before
    posting, p30 item 14). A signer with no name is omitted; if neither is set the block is empty.
    Inline-styled so it never touches the shared TABLE_CSS (byte-identical for the frozen legacy)."""
    cells = []
    for role, name in ((labels["OfficeroftheDay"], meta.get("officer", "")),
                       (labels["UIMCommissioner"], meta.get("uim_commissioner", ""))):
        if not (name or "").strip():
            continue                                       # only show a signer that has a name
        cells.append('<td style="width:44%%;border:0;padding:5.5em 0 0 0;text-align:center;'
                     'vertical-align:bottom">'
                     '<div style="border-top:1px solid #000;padding-top:2px;font-size:9pt">%s</div>'
                     '<div style="font-size:8pt;color:#444">%s</div></td>'
                     % (display(name), esc(role)))
    if not cells:
        return ""
    filler = ('<td style="width:12%;border:0"></td>' if len(cells) == 2
              else '<td style="width:56%;border:0"></td>')
    inner = cells[0] + filler + (cells[1] if len(cells) == 2 else "")
    return ('<table style="width:100%%;border:0;border-collapse:collapse;break-inside:avoid">'
            '<tr>%s</tr></table>' % inner)


def document_html(orientation, labels, meta, heading, body_parts, subtitle="", posting=False):
    """Wrap report body (a list of HTML fragments) in a full styled document. ``subtitle``
    (optional) is shown under the heading -- used for the phase-kind line (§10-E). ``posting`` adds
    the §209 posting metadata (a render-time "Printed on" stamp + the "Posted on"/signature block);
    it is passed only by the native results builders, so the frozen legacy reports (posting off) are
    byte-identical."""
    now = datetime.now()
    if posting:
        # The OOD is a signer in the posting block, so it is redundant in the footer — put the
        # informational render-time "Printed on" stamp in its place (footer-left); keep the
        # Secretary only when named. (posting reports only, so the legacy footer is untouched.)
        footer_left = "%s %s" % (labels["PrintedOn"], now.strftime("%Y-%m-%d %H:%M"))
        footer_right = (("%s  /%s/" % (meta["secretary"], labels["SecretaryoftheRace"]))
                        if (meta.get("secretary") or "").strip() else "")
    else:
        footer_left = "%s  /%s/" % (meta["officer"], labels["OfficeroftheDay"])
        footer_right = "%s  /%s/" % (meta["secretary"], labels["SecretaryoftheRace"])
    css = page_css(orientation, footer_left=footer_left, footer_center=labels["Page"],
                   footer_right=footer_right)
    parts = ["<style>%s\n%s</style>" % (css, TABLE_CSS)]
    if posting:      # top-right: "Posted on: <generation date> __:__" to hand-complete (owner)
        parts.append(_posted_on(labels, now.strftime("%Y-%m-%d")))
    parts.append('<h1 class="event-title">%s</h1>' % display(meta["title"]))
    parts.append('<div class="event-meta">%s &nbsp;&middot;&nbsp; %s</div>'
                 % (display(meta["venue"]), display(meta["date"])))
    parts.append('<h2 class="report-heading">%s</h2>' % display(heading))
    if subtitle:
        parts.append('<div class="report-subtitle">%s</div>' % display(subtitle))
    parts.extend(body_parts)
    if posting:      # signature block at the foot (only for signers that have a name)
        block = _posting_block(labels, meta)
        if block:
            parts.append(block)
    return "\n".join(parts)
