"""Non-fatal validation of computed race results.

A safeguard layer ON TOP of the analyzer: it inspects the analyzed results and
surfaces data an operator should double-check -- a heat that looks stopped but
was entered without a restart, results with no 1st place, an empty scoring
system -- as WARNINGS. It never raises and never changes results (scoring stays
the analyzer's job); the GUI shows the findings so suspicious data is *loud*
rather than silently producing a confusing report.

Add checks by appending to ``_CHECKS``; each takes the per-heat context and
yields ``Finding``s.
"""
import statistics
from collections import namedtuple

from cozer.analyzer import analyze, rule_action_codes, LAP, INSERTED_LAP
from cozer.phases import class_phase_map, phase_heat_map
from cozer.racepattern import get_classes

# severity is advisory only; cl/heat may be None for event-level findings.
Finding = namedtuple("Finding", "severity cl heat code message")

# Mis-click detection is SELF-CALIBRATING: each enabled lap is compared to the boat's OWN median lap,
# not to a physics limit derived from the entered course length + class speed. Operators routinely enter
# an approximate course length (a real event had 1100m laps that boats ran in ~11s -> a physics minimum
# of 26s flagged EVERY normal lap), so a per-boat median is far more robust. The SAME detector drives the
# Edit-Records timeline (blink + hover) and this status-bar summary, so they always agree.
#
#   * too-short  (< _OUTLIER_LOW x median): a double-click, or two crossings merged into one tiny lap.
#   * out-of-order (duration <= 0): the crossing time does not advance -- an impossible ordering.
#   * too-long   (> _OUTLIER_HIGH x median): a MISSED crossing (one lap spans two). A boat CAN run slow,
#     so this is only POSSIBLE. Disciplines differ: a circuit boat never pits, so any lap well above
#     typical is worth a look (unbounded); an endurance boat pits / breaks down (huge legit outliers), so
#     only a lap in a band up to _ENDURANCE_HIGH_MAX x median counts. A time-trial is a solo best-lap run
#     with no useful missed-click distribution, so it gets the too-short/out-of-order checks only.
#
# gettimes absorbs a disabled (already-corrected) click into the next lap, so it is never re-flagged.
# The FIRST lap is the shorter start-line-to-first-lap-line leg (legitimately faster) -> excluded from
# the median and never flagged. Only the first `need` laps are examined; clicks past the finish line are
# ignored (frozen out by the running order, not an operator error). NEVER auto-corrected.
_OUTLIER_LOW = 0.5              # < 50% of the median lap -> a double-click / merged crossing
_OUTLIER_HIGH = 1.75           # > 175% -> a missed crossing (owner-confirmed thresholds)
_ENDURANCE_HIGH_MAX = 2.5      # endurance: a lap past 250% of the median is a pit/breakdown, not a miss
_MIN_BODY_LAPS = 3             # laps (excluding the start leg) needed for a median one outlier can't skew


def suspect_marks(marks, need, kind="circuit"):
    """Enabled lap marks that look like operator mis-clicks: ``{mark_index: (category, hint)}`` where
    category is ``"short"`` / ``"long"`` / ``"order"`` and hint is a plain-terms tooltip. See the module
    comment for the model. Pure; shared by ``check_results`` (status-bar count) and the Edit-Records
    timeline (blink + hover)."""
    laps = []                        # (mark_index, effective_duration) for the enabled laps, in order
    dt = 0.0                         # a disabled lap's time is rolled into the next enabled lap
    for i, m in enumerate(marks):
        code = m[0]
        t = m[1] if len(m) > 1 else 0
        if abs(code) in (LAP, INSERTED_LAP):
            if code > 0:             # enabled lap
                laps.append((i, t + dt))
                dt = 0.0
            else:                    # disabled lap
                dt += t
    if need:
        laps = laps[:need]           # ignore clicks past the finish line
    out = {}
    for idx, dur in laps:            # out-of-order: the crossing time did not advance
        if dur <= 0:
            out[idx] = ("order", "Crossing time does not advance (%.2fs) — an impossible ordering (a "
                        "timing glitch, not a normal click). Right-click the mark to disable it." % dur)
    body = [(idx, dur) for idx, dur in laps[1:] if idx not in out]   # skip lap 1 (the start leg)
    durs = [dur for _, dur in body]
    if len(durs) >= _MIN_BODY_LAPS:
        med = statistics.median(durs)
        if med > 0:
            solo = kind in ("timetrial", "training")
            hi_max = _ENDURANCE_HIGH_MAX * med if kind == "endurance" else float("inf")
            for idx, dur in body:
                if dur < _OUTLIER_LOW * med:
                    out[idx] = ("short", "This lap (%.2fs) is far shorter than the ~%.1fs median — "
                                "likely a double-click or two merged crossings. Right-click to disable "
                                "it." % (dur, med))
                elif not solo and _OUTLIER_HIGH * med < dur <= hi_max:
                    out[idx] = ("long", "This lap (%.2fs) is far longer than the ~%.1fs median — a "
                                "crossing may have been missed. Right-click to check/disable." % (dur, med))
    return out


def _laps(marks):
    return sum(1 for m in marks if abs(m[0]) in (LAP, INSERTED_LAP) and m[0] > 0)


# The "restart required" lap fraction is a DISCIPLINE rule, not a fixed constant:
# U.I.M. 311.02.1 uses 0.70, but non-UIM competitions may differ. Read it from
# event config (defaulting to the UIM value) so it can be exposed/edited per event
# in the Rules tab. NOTE: the analyzer still hardcodes requiredlapscoef=0.70; the
# follow-up (Rules-tab exposure) should thread this same value into analyze() so
# the two agree. Keep the default in sync with the analyzer until then.
_DEFAULT_REQUIRED_LAPS_COEF = 0.70


def _required_laps_coef(eventdata):
    try:
        v = (eventdata.get("configure") or {}).get("requiredlapscoef")
        return float(v) if v is not None else _DEFAULT_REQUIRED_LAPS_COEF
    except (TypeError, ValueError):
        return _DEFAULT_REQUIRED_LAPS_COEF


def check_results(eventdata):
    """Return a list of :class:`Finding` warnings about suspicious result data.

    Pure and defensive: never raises (a failing check is swallowed) and never
    mutates ``eventdata``. Ordered by class then heat for stable display.
    """
    findings = []
    try:
        record = eventdata.get("record", {}) or {}
        ss = eventdata.get("scoringsystem", []) or []
        rulecodes = rule_action_codes(eventdata)

        if not ss and any(record.get(cl) for cl in record):
            findings.append(Finding("warning", None, None, "empty-scoring",
                                    "scoring system is empty — every result scores 0 points"))

        # Per-kind validation dispatch on the phase model (PHASES.md §4 / §4.1): a class's
        # kind + pattern come from its Phase, not from re-inferring the class/heat suffix.
        # phase_of maps each legacy class name to its Phase; the legacy record dict is still
        # iterated (class-then-heat order) for stable output. The kinds diverge:
        #
        #  - TIME-TRIAL (and training, which folds into it): a SOLO run scored by BEST LAP.
        #    A too-fast lap is still a double-tap/spurious crossing that would corrupt the
        #    best lap, so a PHYSICS-ONLY mis-click check applies -- but there is no pack
        #    (no wrong-boat case), the median missed-click check has no useful distribution
        #    on a best-lap run, and there is no leader, so no restart / place-gap checks.
        #  - QUALIFICATION / CIRCUIT / ENDURANCE: a real MASS START. A qheat is analyzed
        #    like a circuit heat (§4.1), so all of them get the full machinery -- fast +
        #    missed mis-click (endurance uses the narrow missed band) plus the restart and
        #    place-gap checks below.
        phase_of = class_phase_map(eventdata)

        for cl in get_classes(eventdata):
            ph = phase_of.get(cl)
            if ph is None:
                continue
            heats = phase_heat_map(ph)          # dual-shape: native record is keyed by base/kind
            if not heats:                       # (was `record.get(cl)`, which missed native heats)
                continue
            for h in sorted(heats):
                info, rec = heats[h]
                need = len(info.get("course", []) or [])

                if ph.kind in ("timetrial", "training"):
                    findings.extend(_misclick_findings(cl, h, rec, need, ph.kind))
                    continue                        # best-lap scoring: no restart / place-gap
                if ph.kind not in ("circuit", "endurance", "qualification"):
                    continue                        # unknown kind: no click checks

                # Mis-click detection (shared self-calibrating detector, see suspect_marks): a boat with a
                # lap far off its OWN median -- too short (double-click) or too long (missed crossing) --
                # or a crossing that doesn't advance. Runs independent of analyze/placements (a heat where
                # everyone DNF'd can still have a click error). Report for Edit-Records review; unchanged.
                findings.extend(_misclick_findings(cl, h, rec, need, ph.kind))

                try:
                    res = analyze(h, heats[h], ss, rulecodes)
                except Exception:
                    continue                        # analyze errors are the analyzer's to report
                places = sorted(res[p]["place"] for p in res if res[p]["place"] > 0)
                if not places:
                    continue

                # A stopped fixed-lap heat only needs a restart if the leader
                # finished under the discipline threshold (U.I.M. 311.02.1: 70%);
                # and a stop already recorded via inserted-lap crossings is handled.
                # Flag only a genuinely missing restart, and say what to do.
                course_len = len(info.get("course", []) or [])
                if info.get("duration") is None and course_len:
                    maxlaps = max((_laps(rec[p]) for p in rec), default=0)
                    coef = _required_laps_coef(eventdata)
                    minrequired = int(coef * course_len)
                    stop_handled = any(abs(m[0]) == INSERTED_LAP for p in rec for m in rec[p])
                    has_restart = (h + "r") in heats or (h + "R") in heats
                    if maxlaps < minrequired and not has_restart and not stop_handled:
                        pct = int(coef * 100)
                        findings.append(Finding(
                            "warning", cl, h, "incomplete-heat",
                            "leader completed only %d of %d laps (< %d%%) and no restart is "
                            "recorded — the heat may have been stopped early. A boat scores only "
                            "with a lap after the race stop line: record each finished boat's "
                            "stop-race-line crossing (or insert a lap mark after it), or run a "
                            "restart (required only if the leader finished under %d%% of the "
                            "course)." % (maxlaps, course_len, pct, pct)))

                # Scored placings should be a contiguous 1..N. Any gap (or a missing
                # 1st) means a boat that would place is unclassified -- commonly a
                # stopped heat where it has no lap after the race stop line, so it is
                # DNF (see the analyzer's leadertime rule).
                if places != list(range(1, len(places) + 1)):
                    missing = sorted(set(range(1, len(places) + 1)) - set(places))
                    findings.append(Finding(
                        "warning", cl, h, "place-gap",
                        "scored placings are %s, not a contiguous 1..%d (missing %s) — a boat that "
                        "would place is unclassified (commonly DNF: no lap recorded after the race "
                        "stop line); if it finished, record its stop-line crossing"
                        % (places[:8], len(places), missing or "n/a")))
    except Exception:                               # validation must never break the app
        pass
    return findings


def _misclick_findings(cl, h, rec, need, kind):
    """Per-boat mis-click findings from the shared ``suspect_marks`` detector (see the module comment).
    Two codes for continuity: ``misclick`` (a lap far shorter than the boat's median, or a crossing that
    doesn't advance) and ``missed-click`` (a lap well above typical). The per-mark detail is shown on
    hover in Edit Records; this is the status-bar summary."""
    out = []
    for pid in sorted(rec, key=str):
        cats = [c for c, _hint in suspect_marks(rec[pid], need, kind).values()]
        n_low = cats.count("short") + cats.count("order")
        n_high = cats.count("long")
        if n_low:
            out.append(Finding(
                "warning", cl, h, "misclick",
                "boat %s has %d suspect lap mark%s — a lap far shorter than its median, or a crossing "
                "that doesn't advance (likely a double-click / wrong-boat click); review and disable in "
                "Edit Records" % (pid, n_low, "" if n_low == 1 else "s")))
        if n_high:
            out.append(Finding(
                "warning", cl, h, "missed-click",
                "boat %s has %d lap%s well above its typical time — a crossing may have been MISSED; if "
                "so, insert a mark in Edit Records" % (pid, n_high, "" if n_high == 1 else "s")))
    return out


def format_findings(findings):
    """One human-readable line per finding, for a log or a warnings panel."""
    out = []
    for f in findings:
        where = ("class %s heat %s: " % (f.cl, f.heat) if f.cl and f.heat else
                 "class %s: " % f.cl if f.cl else "")
        out.append("%s %s%s" % (f.severity.upper(), where, f.message))
    return out
