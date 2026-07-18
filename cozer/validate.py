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
from collections import namedtuple

from cozer.analyzer import analyze, rule_action_codes, LAP, INSERTED_LAP
from cozer.racepattern import get_classes

# severity is advisory only; cl/heat may be None for event-level findings.
Finding = namedtuple("Finding", "severity cl heat code message")


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


def format_findings(findings):
    """One human-readable line per finding, for a log or a warnings panel."""
    out = []
    for f in findings:
        where = ("class %s heat %s: " % (f.cl, f.heat) if f.cl and f.heat else
                 "class %s: " % f.cl if f.cl else "")
        out.append("%s %s%s" % (f.severity.upper(), where, f.message))
    return out
