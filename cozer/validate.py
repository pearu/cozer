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
import copy
from collections import namedtuple

from cozer.analyzer import analyze, rule_action_codes, LAP, INSERTED_LAP
from cozer.racepattern import get_classes

# severity is advisory only; cl/heat may be None for event-level findings.
Finding = namedtuple("Finding", "severity cl heat code message")


def _laps(marks):
    return sum(1 for m in marks if abs(m[0]) in (LAP, INSERTED_LAP) and m[0] > 0)


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
                    res = analyze(h, copy.deepcopy(heats[h]), ss, rulecodes)
                except Exception:
                    continue                        # analyze errors are the analyzer's to report
                places = sorted(res[p]["place"] for p in res if res[p]["place"] > 0)
                if not places:
                    continue

                # A fixed-lap heat nobody finished, with no restart recorded, was
                # probably stopped early (accident/red flag) -- the classic case
                # that yields a confusing report (e.g. Liepaja 2006 F-2 heat 3).
                course_len = len(info.get("course", []) or [])
                if info.get("duration") is None and course_len:
                    maxlaps = max((_laps(rec[p]) for p in rec), default=0)
                    if maxlaps < course_len and not (
                            (h + "r") in heats or (h + "R") in heats):
                        findings.append(Finding(
                            "warning", cl, h, "incomplete-heat",
                            "no boat completed the %d-lap course (best %d laps) and no restart is "
                            "recorded — the heat may have been stopped early" % (course_len, maxlaps)))

                # Scored results with no 1st place: a leading boat is unclassified.
                if 1 not in places:
                    findings.append(Finding(
                        "warning", cl, h, "no-first-place",
                        "results have places %s but no 1st place — a leading boat is unclassified"
                        % (places[:6],)))
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
