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
from cozer.racepattern import crack_race_pattern, get_classes, pattern_speed, race_kind
from cozer.records import gettimes

# severity is advisory only; cl/heat may be None for event-level findings.
Finding = namedtuple("Finding", "severity cl heat code message")

# A recorded lap FASTER than the class could physically go is a MIS-CLICK: the
# operator clicked the wrong boat (a spurious crossing at another boat's line time)
# or double-tapped when several boats cross close together. The fastest possible lap
# is the class's shortest lap length / its top speed (the pattern's '@<speed>' km/h
# hint, default DEFAULT_CLASS_SPEED); a lap under that is impossible. Per-class speed
# beats a fixed window -- an F-500 runs ~3x a GT-15, so a "short" lap differs by
# class. Reported for Edit-Records review, NEVER auto-corrected (scoring stays the
# analyzer's). Uses gettimes, so a mis-click the operator already disabled is
# absorbed into the next lap and not re-flagged. Time-trials excluded (solo runs).
#
# The opposite mis-click is a MISSED click: the operator didn't click a crossing, so
# one recorded lap spans two -- it reads ~2x the boat's median. This can't be decided
# physically (a boat CAN run slow), so it is only a POSSIBLE finding, corrected by
# INSERTING a mark in Edit Records. Circuit and endurance need SEPARATE handling
# because their lap-time distributions differ completely: a circuit boat never pits,
# so any lap well above typical is worth a look (unbounded); an endurance boat pits
# and breaks down (huge laps that are NOT missed clicks -- clear outliers that must
# not be allowed to shape the circuit rule), so only a lap in a narrow band around 2x
# counts.
_MISSED_CLICK_FACTOR = 1.8      # lower edge, both disciplines (~2x with margin)
_ENDURANCE_MISSED_MAX = 2.5     # endurance upper edge: above this it's a pit/breakdown, not a miss
_MISSED_CLICK_MIN_LAPS = 4      # need a few laps for a stable median


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

        classes = [c for c in get_classes(eventdata) if c in record]
        for cl in classes:
            heats = record.get(cl) or {}
            for h in sorted(heats):
                if h and h[-1] in ("q", "t"):       # qualification / time-trial: scored differently
                    continue
                info, rec = heats[h]

                # Mis-click detection: a boat whose EFFECTIVE lap (gettimes absorbs a
                # disabled/already-corrected click) is faster than physically possible
                # (or, for a missed click, ~2x its median) likely got a spurious/absent
                # crossing. Runs independent of analyze/placements (a heat where everyone
                # DNF'd can still have a click error). Report for Edit-Records review;
                # scoring is unchanged. Only mass-start racing -- a time-trial or
                # qualifier runs solo, so no pack and no wrong-boat click.
                kind = race_kind(eventdata, cl)
                if kind in ("circuit", "endurance"):
                    min_lap = _class_min_lap_time(eventdata, cl)
                    if min_lap:
                        findings.extend(_misclick_findings(
                            cl, h, rec, min_lap, kind == "endurance"))

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


def _class_min_lap_time(eventdata, cl):
    """Fastest physically-possible lap (seconds) for class ``cl``: its shortest lap
    length / its top speed (pattern ``'@<speed>'`` km/h, default 150). ``None`` if
    the class has no usable pattern."""
    for l in eventdata.get("classes", []):
        if len(l) > 2 and l[1] == cl and l[2]:
            try:
                lengths = [x for hh in crack_race_pattern(l[2])[0] for x in hh if x > 0]
                speed_ms = pattern_speed(l[2]) / 3.6
            except Exception:
                return None
            return min(lengths) / speed_ms if lengths and speed_ms > 0 else None
    return None


def _misclick_findings(cl, h, rec, min_lap, endurance):
    out = []
    for pid in sorted(rec, key=str):
        laps = gettimes(rec[pid])
        fast = [round(t, 2) for t in laps if 0 <= t < min_lap]
        if fast:
            out.append(Finding(
                "warning", cl, h, "misclick",
                "boat %s has %d lap(s) faster than physically possible for this class (< %.0fs, "
                "%s) — likely a mis-click (wrong boat / double tap when boats cross together); "
                "review and correct in Edit Records" % (pid, len(fast), min_lap, fast)))
        # Missed click: a lap ~2x the boat's median. Circuit (no pits) flags any lap
        # well above typical; endurance (pits are huge legit outliers) only a narrow band.
        if len(laps) >= _MISSED_CLICK_MIN_LAPS:
            med = statistics.median(laps)
            if med > 0:
                lo, hi = _MISSED_CLICK_FACTOR * med, (_ENDURANCE_MISSED_MAX * med if endurance
                                                      else float("inf"))
                slow = [round(t, 2) for t in laps if lo <= t <= hi]
                if slow:
                    out.append(Finding(
                        "warning", cl, h, "missed-click",
                        "boat %s has %d lap(s) roughly 2x its typical %.0fs (%s) — a lap crossing "
                        "may have been MISSED (or the boat ran slow); if a click was missed, insert "
                        "a mark in Edit Records" % (pid, len(slow), med, slow)))
    return out


def format_findings(findings):
    """One human-readable line per finding, for a log or a warnings panel."""
    out = []
    for f in findings:
        where = ("class %s heat %s: " % (f.cl, f.heat) if f.cl and f.heat else
                 "class %s: " % f.cl if f.cl else "")
        out.append("%s %s%s" % (f.severity.upper(), where, f.message))
    return out
