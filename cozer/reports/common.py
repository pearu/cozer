"""Shared helpers for building and rendering cozer reports."""
from datetime import datetime

from cozer.phases import heat_label      # single source (reports + the live feed share it); re-exported
from cozer.racepattern import crack_race_pattern
from cozer.reports.latexish import latex_to_html
from cozer.reports.render import TABLE_CSS, page_css

_ = heat_label     # re-exported: report modules import heat_label from here (keep the name bound)


def collect_penalty_notes(eventdata, classes=None, heat_map=None, labels=None):
    """The free-text notes on non-disabled operator-inserted marks in the included heats (issue #33), as
    display lines: ``"#<boat> in heat <h> at L<k> - <Label> (<article>): <reason>"`` — the mark's human
    label (``Lost a lap``) not its code, the ``at L<k>`` dropped when the mark is past the race stop line.
    A mark appears only when its note is non-empty. Returns ``[(class_display, heat_id, line), ...]`` in
    class → heat → boat → mark order (empty when nothing is annotated)."""
    from cozer.phases import class_phase_map, phase_heat_map
    from cozer.racepattern import get_classes
    from cozer.records import invreccodemap, marknote, UIM209_CODES
    from cozer.classes import getclass
    from cozer.reports.labels import RECCODE_LABEL
    labels = labels or {}
    phase_of = class_phase_map(eventdata)
    if classes is None:
        classes = get_classes(eventdata)

    def _label(code_name):                            # human label ("Lost a lap"), else the raw code
        return labels.get(RECCODE_LABEL.get(code_name, ""), code_name)

    def _bk(p):
        s = str(p)
        return (0, int(s)) if s.isdigit() else (1, s)

    out = []
    for cl in classes:
        ph = phase_of.get(cl)
        if ph is None:
            continue
        heat_recs = phase_heat_map(ph)
        if not heat_recs:
            continue
        heats = list(heat_map[cl]) if (heat_map and cl in heat_map) else sorted(heat_recs)
        heats = [h for h in heats if h in heat_recs]
        for h in heats:
            info, boats = heat_recs[h]
            racetime = info.get("racetime")
            for pid in sorted(boats, key=_bk):
                laps = 0
                for m in boats[pid]:
                    code = m[0]
                    if abs(code) in (1, 2):
                        if code > 0:                     # a completed (enabled) lap crossing
                            laps += 1
                        continue
                    note = marknote(m).strip()
                    cn = invreccodemap.get(abs(code), str(abs(code)))
                    if code < 0:                          # disabled mark -> ignore
                        continue
                    if cn in UIM209_CODES and not note:   # §209 outcome without a reason -> table only
                        continue                          # (a rule/penalty/LL mark is listed regardless)
                    art = (m[2] if len(m) > 2 else "").strip()
                    mt = m[1] if len(m) > 1 else 0
                    where = "#%s in Heat %s" % (pid, heat_label(h))   # "Heat" as the report's label
                    if racetime is None or mt <= racetime:   # not past the race stop line
                        where += " at L%d" % (laps + 1)
                    rule = "%s (%s)" % (_label(cn), art) if art else _label(cn)
                    line = "%s - %s" % (where, rule)
                    if note:                              # a reason follows a colon; none -> no trailing ':'
                        line += ": %s" % note
                    out.append((getclass(cl), h, line))
    return out


def penalty_notes_html(notes, labels, tiebreak=None):
    """The 'Notes' section (issue #33) placed after a report's results tables — grouped by class, one line
    per note. ``notes`` is ``collect_penalty_notes`` output (per-mark reasons); ``tiebreak`` is optional
    ``[(class_display, line), ...]`` for the §318.03 fastest-lap decisions (issue #34 point 5). Both merge
    into one per-class list, penalty notes first. '' when there is nothing to show."""
    from collections import OrderedDict
    byclass = OrderedDict()
    for cl, _h, line in (notes or []):
        byclass.setdefault(cl, []).append(line)
    for cl, line in (tiebreak or []):
        byclass.setdefault(cl, []).append(line)
    if not byclass:
        return ""
    blocks = ['<h3 class="class-heading">%s</h3>' % esc(labels["PenaltyNotes"])]
    for cl, lines in byclass.items():
        blocks.append('<div class="event-meta">%s %s</div>' % (esc(labels["Class"]), esc(cl)))
        blocks.append("<ul class=\"notes\">%s</ul>" % "".join("<li>%s</li>" % esc(line) for line in lines))
    return '<div class="penalty-notes">%s</div>' % "".join(blocks)


def fastest_lap_time(heat_recs, heats, pid):
    """The measured DURATION of a boat's fastest (max-speed) lap across ``heats`` -- the time counterpart
    of the analyzer's ``maxlapspeed``, so the §318.03 note's time value names the SAME lap the decision
    used (exact even on an unequal-length course; == the min lap duration when all laps are equal). ``None``
    if the boat has no completed lap. Derived from the record so the analyzer/golden are untouched."""
    from cozer.records import gettimes
    best_speed, best_dur = -1.0, None
    for h in heats:
        info, boats = heat_recs[h]
        course = info.get("course") or []
        for i, dt in enumerate(gettimes(boats.get(str(pid), boats.get(pid, [])))):
            if dt > 0 and course:
                sp = course[min(i, len(course) - 1)] / dt          # same lap-speed basis as the analyzer
                if sp > best_speed:
                    best_speed, best_dur = sp, dt
    return best_dur


def tiebreak_notes(ranked, metric, labels):
    """§318.03 auto-notes: where the placing between adjacent classified boats is decided by best lap
    speed -- equal points AND equal (stored, round2) average speed, then broken by best lap speed -- the
    deciding number is otherwise invisible, so emit one note per tie-group. ``ranked`` is the classified
    boats in placing order as ``(place, boat, points, avgspeed, maxlapspeed, best_lap_time)``. ``metric``
    follows the result-column switch: ``"speed"`` shows each boat's best lap speed (km/h), ``"total_time"``
    shows its best lap TIME (s). A group whose boats all share the same best lap speed is a true dead heat
    (not decided by §318.03) -> no note. Returns display lines (``[]`` when nothing was so decided)."""
    over = " %s " % labels["FastestLapOver"]
    out, i, n = [], 0, len(ranked)
    while i < n:
        j = i + 1
        while j < n and ranked[j][2] == ranked[i][2] and ranked[j][3] == ranked[i][3]:
            j += 1                                       # same points AND same avg speed -> one group
        group = ranked[i:j]
        if len(group) >= 2 and len({g[4] for g in group}) > 1:   # order decided by best lap speed
            places = [g[0] for g in group]
            rng = "%d-%d" % (min(places), max(places))
            boats = over.join(
                "#%s (%s)" % (boat, ("%.1f km/h" % maxsp) if metric != "total_time"
                              else ("%.2f s" % bt if bt else "-"))
                for (_pl, boat, _pts, _avg, maxsp, bt) in group)
            out.append(labels["FastestLapNote"] % (rng, boats))
        i = j
    return out


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


def _posted_at(labels):
    """The top-right "Posted at ____:____" line: the time is left blank (large, for hand-writing in
    pen) — the §209 *actual time of posting*, which starts the protest clock (§403). No date: the
    posting day is the generation day, already shown by the "Printed on <date>" footer stamp."""
    return ('<div style="text-align:right;font-size:10pt;margin-bottom:.15em">%s &nbsp;'
            '<span style="font-size:16pt">____:____</span></div>' % esc(labels["PostedAt"]))


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
    the §209 posting metadata (a render-time "Printed on" footer stamp + the top-right "Posted at"
    line + the signature block);
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
    if posting:      # top-right: "Posted at ____:____" — the time is hand-written at posting (owner)
        parts.append(_posted_at(labels))
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
