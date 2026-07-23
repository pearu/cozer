"""Full Final (landscape, per-heat + summary) and Short Final (portrait,
summary only) results reports, built from the proven scoring core."""
from cozer.analyzer import analyze, sumanalyze, getsumresorder, rule_action_codes
from cozer.classes import getclass
from cozer.phases import class_phase_map, phase_heat_map
from cozer.qualification import classify, participant_boats, qualification_class
from cozer.racepattern import get_classes
from cozer.reports.common import (
    esc, display, get_fullname, heat_label, participants_index, nationalities_index,
    show_from, show_nationality, sheats_for as _sheats, meta_of, document_html,
    collect_penalty_notes, penalty_notes_html,
)
from cozer.reports.labels import get_labels, phase_kinds_subtitle, RECCODE_LABEL
from cozer.reports.render import render_pdf
from cozer.records import UIM209_CODES


def _legend_index(legend, code, rules):
    key = (code, "; ".join(str(x) for x in rules))
    if key not in legend:
        legend[key] = len(legend) + 1
    return legend[key]


def _result_text(r, legend, native=False):
    """Per-heat result cell (adapted from legacy res2latex): speeds + note codes. Numbers break only at
    the slash. The completed-lap count ``/NL`` is shown ONLY for a boat short of the full distance (its
    classification then depends on laps, §317.01); a boat with no ``/NL`` completed all required laps -- a
    report footnote states that convention (issue #34, uniform across the result reports). In ``native``
    mode (issue #33) the note codes carry NO footnote superscript -- the rule article + any reason live in
    the Notes section -- the codes seen feed a plain footer key."""
    laps, penlapsleft, lapsleft = r["lapinfo"]
    text = ""
    if r["points"] >= 0:
        if lapsleft:                                    # short of the full distance -> show completed laps
            text = "%.1f/%.1f/%sL" % (r["avgspeed"], r["maxlapspeed"], laps)
        else:
            text = "%.1f/%.1f" % (r["avgspeed"], r["maxlapspeed"])
    text = text.replace("/", "/&#8203;")   # &#8203; = zero-width space: a wrap point after the slash
    notes = r["notes"]
    if not notes:
        return text or "-"
    parts = [text] if text else []
    for code in notes:
        rules = notes[code]
        if native:
            parts.append(esc(code))
            legend[code] = True                     # code-string key -> footer glossary (no footnote)
        elif rules:
            parts.append("%s<sup>%s</sup>" % (esc(code), _legend_index(legend, code, rules)))
        else:
            parts.append(esc(code))
    return " ".join(parts).strip() or "-"


def _legend_html(legend, labels, note=None, extra=None, native=False, laps_note=False):
    """The footer: the result-column note (ResNote) + a code key (DQ = Disqualif.). Legacy mode also
    lists the rule-article footnotes referenced by result-cell superscripts; ``native`` mode (issue #33)
    has no such footnotes — the article + reason are in the Notes section — just the code key. The note
    defaults to the speed ``ResNote``; a caller whose result column is not speed passes its own. ``extra``
    appends one more note at the end (e.g. the Q/DNQ key for a qualification report). ``laps_note`` appends
    the "blank = full distance" lap-count convention (issue #34), for a table where ``/NL`` can appear."""
    bits = [esc(note if note is not None else labels["ResNote"])]
    if native:
        codes = list(legend)                        # code-string keys, insertion order; no footnotes
    else:
        foot, codes = [], []
        for (code, rules), idx in sorted(legend.items(), key=lambda kv: kv[1]):
            foot.append("<sup>%s</sup> %s" % (idx, display(rules)))
            if code not in codes:
                codes.append(code)
        bits += foot
    for code in codes:
        if native and code in UIM209_CODES:         # §209 outcomes are standard UIM codes -> not keyed
            continue
        lab = labels.get(RECCODE_LABEL.get(code, ""))
        if lab:
            bits.append("%s = %s" % (esc(code), esc(lab)))
    if laps_note:
        bits.append(esc(labels["LapCountNote"]))
    if extra:
        bits.append(esc(extra))
    return "; ".join(bits)


def _finalist_set(eventdata, cl, ph):
    """The finalist boat-ids for a finals class ``cl`` fed by a qualification phase, or
    ``None`` when no such phase is recorded (then the report is unchanged). A finalist is a
    boat ``classify`` marks `primary`/`repechage`; ``classify`` respects a manual `DNQ`/`Q`
    edit, so a §10-F make-up promotion reads as a finalist here."""
    if ph.kind in ("timetrial", "qualification"):
        return None
    qual_cl = qualification_class(eventdata, cl)
    labels = classify(eventdata, qual_cl) if qual_cl else {}
    if not labels:                                       # qualification not recorded -> no tail
        return None
    return {b for b, s in labels.items() if s != "dnq"}


def _dnq_rows(eventdata, cl, finalist_set, parts, nats, nheats):
    """The UIM 209 DNQ tail: every entered-and-accepted boat that is not a finalist, in
    participant-list order, marked `DNQ` with no final points (§5.1 step 4)."""
    rows = []
    for b in participant_boats(eventdata, cl):
        if b in finalist_set:
            continue
        first, last, club = parts.get((cl, b), ("", "", ""))
        names = get_fullname(first, last).split(";")
        rows.append({
            "place": "", "name": names[0].strip(), "extra": [n.strip() for n in names[1:]],
            "from": club, "nat": nats.get((cl, b), ""), "id": b,
            "heats": [{"result": "-", "points": "-"}] * nheats,
            "best": "DNQ", "sumpoints": "-",
        })
    return rows


def _build(eventdata, classes, heat_map, orientation, full, phase_native=False, options=None):
    ss = eventdata.get("scoringsystem", [])
    labels = get_labels(eventdata)
    phase_of = class_phase_map(eventdata)               # legacy class name -> its Phase
    if classes is None:
        classes = get_classes(eventdata)
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    tables, kinds = [], []
    for cl in classes:
        ph = phase_of.get(cl)
        if ph is None:                                  # no such phase
            continue
        heat_recs = phase_heat_map(ph)                  # {heat_id: [info, boats]} for this phase
        if not heat_recs:                               # phase has no recorded heats -> skip (was
            continue                                    # the `c in record` filter, now phase-aware)
        heats = list(heat_map[cl]) if (heat_map and cl in heat_map) else sorted(heat_recs)
        heats = [h for h in heats if h in heat_recs]    # a selected heat may be unrecorded (stale
        if not heats:                                   # selection / programmatic heat_map) -> skip
            continue                                    # it rather than KeyError on heat_recs[h]
        rulecodes = rule_action_codes(eventdata)
        res = {h: analyze(h, heat_recs[h], ss, rulecodes) for h in heats}
        sumres = sumanalyze(heats, res, _sheats(eventdata, cl, len(heats)))
        order = getsumresorder(sumres)
        # UIM 209 DNQ tail: when a qualification phase feeds this finals phase, the report
        # lists every entered boat -- finalists in the classified body, non-qualifiers below.
        # A new-convention feature only: the legacy report stays byte-faithful.
        finalist_set = _finalist_set(eventdata, cl, ph) if phase_native else None
        legend = {}
        rows = []
        for pid in order:
            if finalist_set is not None and str(pid) not in finalist_set:
                continue                                # a non-qualifier -> shown in the DNQ tail
            first, last, club = parts.get((cl, str(pid)), ("", "", ""))
            names = get_fullname(first, last).split(";")
            sr = sumres[pid]
            scored = sr["place"] > 0
            heatcells = []
            for h in heats:
                rh = res[h].get(pid)                # a boat need not have raced every heat
                heatcells.append(
                    {"result": "-", "points": "-"} if rh is None else
                    {"result": _result_text(rh, legend, native=phase_native),
                     "points": str(rh["points"]) if rh["place"] > 0 else "-"})
            rows.append({
                "place": str(sr["place"]) if scored else "",
                "name": names[0].strip(),
                "extra": [n.strip() for n in names[1:]],
                "from": club,
                "nat": nats.get((cl, str(pid)), ""),
                "id": str(pid),
                "heats": heatcells,
                "best": ("%.1f/%.1f" % (sr["avgspeed"], sr["maxlapspeed"])) if scored else "-",
                "sumpoints": str(sr["points"]) if scored else "-",
            })
        if finalist_set is not None:
            rows.extend(_dnq_rows(eventdata, cl, finalist_set, parts, nats, len(heats)))
        tables.append({"class": getclass(cl), "heats": heats, "rows": rows,
                       "legend": _legend_html(legend, labels, native=phase_native,
                                              laps_note=phase_native)})   # native shows /NL-when-short
        kinds.append(ph.kind)
    subtitle = phase_kinds_subtitle(labels, kinds) if phase_native else ""
    return {"meta": meta_of(eventdata), "labels": labels, "orientation": orientation,
            "full": full, "heading": labels["FinalResults"], "tables": tables,
            "subtitle": subtitle,
            # From/Nationality columns + the §209 posting block + the issue-#33 notes are native-only
            # (legacy stays byte-faithful: From always, no Nationality, no posting block, no notes).
            "penalty_notes": collect_penalty_notes(eventdata, classes, heat_map, labels) if phase_native else None,
            "show_from": show_from(eventdata) if phase_native else True,
            "show_nat": show_nationality(eventdata) if phase_native else False,
            "posting": phase_native}


# New phase-native reports (PHASES §5.1 step 4 / §10-E): the DNQ tail + phase-kind subtitle.
def build_full_final(eventdata, classes=None, heat_map=None, options=None):
    return _build(eventdata, classes, heat_map, "landscape", True, phase_native=True, options=options)


def build_short_final(eventdata, classes=None, heat_map=None, options=None):
    return _build(eventdata, classes, heat_map, "portrait", False, phase_native=True, options=options)


# Legacy byte-faithful reports: kept as the reference for comparison against the legacy
# Python-2 core (no subtitle, no DNQ tail). Same implementation, phase_native off.
def build_full_final_legacy(eventdata, classes=None, heat_map=None):
    return _build(eventdata, classes, heat_map, "landscape", True, phase_native=False)


def build_short_final_legacy(eventdata, classes=None, heat_map=None):
    return _build(eventdata, classes, heat_map, "portrait", False, phase_native=False)


def _table_html(t, labels, full, show_f=True, show_n=False):
    # Leading columns Place, Name, [From], [Nationality], No. From/Nationality are optional
    # (native reports only, shown when they vary); with the defaults (From on, Nationality off)
    # this reproduces the frozen legacy layout byte-for-byte.
    L = labels
    heats = t["heats"]
    lead_head = '<th class="num">%s</th><th>%s</th>' % (esc(L["Place"]), esc(L["Name"]))
    if show_f:
        lead_head += '<th>%s</th>' % esc(L["From"])
    if show_n:
        lead_head += '<th class="num">%s</th>' % esc(L["Nationality"])
    lead_head += '<th class="num">%s</th>' % esc(L["No"])
    nlead = 3 + int(show_f) + int(show_n)
    if full:
        # Heats and the Summary hold the same kind of data (result + points), so give
        # them equal-width result+points column pairs (issue #14). The pool left for those
        # pairs shifts by any width the optional From/Nationality columns free up or take.
        pool = 69.0 + (0 if show_f else 8) - (5 if show_n else 0)
        pair = pool / (len(heats) + 1)
        cols = ['<col style="width:4%">', '<col style="width:15%">']
        if show_f:
            cols.append('<col style="width:8%">')
        if show_n:
            cols.append('<col style="width:5%">')
        cols.append('<col style="width:4.5%">')
        for _ in range(len(heats) + 1):        # one pair per heat, plus one for the Summary
            cols.append('<col style="width:%.2f%%">' % (pair * 0.58))
            cols.append('<col style="width:%.2f%%">' % (pair * 0.42))
        head1 = ('<tr><th colspan="%d"></th>' % nlead
                 + "".join('<th class="num" colspan="2">%s %s</th>' % (esc(L["Heat"]), esc(heat_label(h))) for h in heats)
                 + '<th class="num" colspan="2">%s</th></tr>' % esc(L["Summary"]))
        head2 = ('<tr>' + lead_head
                 + ('<th class="num">%s</th><th class="num">%s</th>' % (esc(L["Res"]), esc(L["Pts"]))) * len(heats)
                 + '<th class="num">%s</th><th class="num">%s</th></tr>' % (esc(L["Res"]), esc(L["Pts"])))
        fs = max(6.5, 9.0 - 0.45 * max(0, len(heats) - 3))
    else:
        # Place, Name, [From], [Nationality], No, Results, Points — Results needs room for
        # "45.6/48.2"; Name absorbs the width any optional column frees up or takes.
        name_w = 38 + (0 if show_f else 15) - (8 if show_n else 0)
        cols = ['<col style="width:7%">', '<col style="width:%d%%">' % name_w]
        if show_f:
            cols.append('<col style="width:15%">')
        if show_n:
            cols.append('<col style="width:8%">')
        cols += ['<col style="width:8%">', '<col style="width:20%">', '<col style="width:12%">']
        head1 = ""
        head2 = ('<tr>' + lead_head
                 + '<th class="num">%s</th><th class="num">%s</th></tr>'
                 % (esc(L["Results"]), esc(L["Points"])))
        fs = 9.0
    ncols = (nlead + 2 * len(heats) + 2) if full else (nlead + 2)
    body = []
    for row in t["rows"]:
        cells = '<td class="num">%s</td><td class="name">%s</td>' % (esc(row["place"]), display(row["name"]))
        if show_f:
            cells += '<td>%s</td>' % display(row["from"])
        if show_n:
            cells += '<td class="num">%s</td>' % esc(row["nat"])
        cells += '<td class="num">%s</td>' % esc(row["id"])
        if full:
            for hc in row["heats"]:
                cells += '<td class="num">%s</td><td class="num">%s</td>' % (hc["result"], esc(hc["points"]))
        cells += ('<td class="num summary">%s</td><td class="num summary">%s</td>'
                  % (esc(row["best"]), esc(row["sumpoints"])))
        body.append("<tr>%s</tr>" % cells)
        for extra in row["extra"]:
            body.append('<tr class="sub"><td></td><td class="name">%s</td><td colspan="%d"></td></tr>'
                        % (display(extra), ncols - 2))
    colgroup = "<colgroup>%s</colgroup>" % "".join(cols)
    html = '<h3 class="class-heading">%s %s</h3>' % (esc(L["Class"]), display(t["class"]))
    html += ('<table class="results" style="font-size:%.1fpt">%s<thead>%s%s</thead>'
             '<tbody>%s</tbody></table>' % (fs, colgroup, head1, head2, "".join(body)))
    if t["legend"]:
        html += '<div class="legend">%s</div>' % t["legend"]
    return html


def _results_html(model):
    show_f, show_n = model.get("show_from", True), model.get("show_nat", False)
    body = [_table_html(t, model["labels"], model["full"], show_f, show_n) for t in model["tables"]]
    nh = penalty_notes_html(model.get("penalty_notes"), model["labels"])   # issue #33 (native only; ''
    if nh:                                                                 # for legacy -> byte-faithful)
        body.append(nh)
    return document_html(model["orientation"], model["labels"], model["meta"], model["heading"],
                         body, subtitle=model.get("subtitle", ""),
                         posting=model.get("posting", False))


def full_final_html(model):
    return _results_html(model)


def short_final_html(model):
    return _results_html(model)


# Legacy reports share the same HTML (a legacy model has subtitle="" -> no subtitle line).
full_final_legacy_html = full_final_html
short_final_legacy_html = short_final_html


def render_full_final(eventdata, out_path, classes=None, heat_map=None, options=None):
    model = build_full_final(eventdata, classes, heat_map, options)
    html = full_final_html(model)
    render_pdf(html, out_path)
    return model, html


def render_short_final(eventdata, out_path, classes=None, heat_map=None, options=None):
    model = build_short_final(eventdata, classes, heat_map, options)
    html = short_final_html(model)
    render_pdf(html, out_path)
    return model, html


def render_full_final_legacy(eventdata, out_path, classes=None, heat_map=None):
    model = build_full_final_legacy(eventdata, classes, heat_map)
    html = full_final_legacy_html(model)
    render_pdf(html, out_path)
    return model, html


def render_short_final_legacy(eventdata, out_path, classes=None, heat_map=None):
    model = build_short_final_legacy(eventdata, classes, heat_map)
    html = short_final_legacy_html(model)
    render_pdf(html, out_path)
    return model, html
