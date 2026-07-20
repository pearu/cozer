"""Shared helpers for building and rendering cozer reports."""
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
    """True if ``values`` hold more than one distinct non-empty entry — the general condition for
    showing an optional report column. An all-empty or uniform (single-valued) column is hidden:
    it distinguishes nothing and would only waste space (owner's rule for From/club + Nationality)."""
    return len({(v or "").strip() for v in values} - {""}) > 1


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
    return {k: eventdata.get(k, "") for k in ("title", "venue", "date", "officer", "secretary")}


def document_html(orientation, labels, meta, heading, body_parts, subtitle=""):
    """Wrap report body (a list of HTML fragments) in a full styled document. ``subtitle``
    (optional) is shown under the heading -- used for the phase-kind line (§10-E)."""
    css = page_css(
        orientation,
        footer_left="%s  /%s/" % (meta["officer"], labels["OfficeroftheDay"]),
        footer_center=labels["Page"],
        footer_right="%s  /%s/" % (meta["secretary"], labels["SecretaryoftheRace"]),
    )
    parts = ["<style>%s\n%s</style>" % (css, TABLE_CSS)]
    parts.append('<h1 class="event-title">%s</h1>' % display(meta["title"]))
    parts.append('<div class="event-meta">%s &nbsp;&middot;&nbsp; %s</div>'
                 % (display(meta["venue"]), display(meta["date"])))
    parts.append('<h2 class="report-heading">%s</h2>' % display(heading))
    if subtitle:
        parts.append('<div class="report-subtitle">%s</div>' % display(subtitle))
    parts.extend(body_parts)
    return "\n".join(parts)
