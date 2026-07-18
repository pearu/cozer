"""Scoring core -- Python-3 port of legacy ``cozer/analyzer.py``.

Behavior must match the legacy Python-2 core exactly; this is enforced by the
golden equivalence tests (``tests/test_analyzer_equivalence.py``) over the real
event fixtures.  Ordering uses :func:`py2_sorted` and rounding uses
:func:`round2` to reproduce Python-2 semantics (see ``cozer/_py2compat.py`` and
``MAINTENANCE_PLAN.md`` section 6.8).
"""
import logging
import math

from cozer._py2compat import ROUND_OPT, round2, py2_sorted
from cozer.records import (
    invreccodemap, insertmark, gettimes,
    LAP, INSERTED_LAP, LL, PL, PL5, LL2, PL8, PL10, DS, IR, DQ, YC, RC,
    BC, NC, PL3, PL4, PL15, LP2, DSQ, DNS, DNR, ACC, DNQ, DNF, NT, Q, NQ,
)

roundopt = ROUND_OPT
_log = logging.getLogger("cozer.analyzer")


def _info(*mess):
    # Legacy Info(): a status message with no effect on results.
    _log.debug("Info: %s", " ".join(str(m) for m in mess))


def _warning(*mess):
    _log.debug("Warning: %s", " ".join(str(m) for m in mess))


def rule_action_codes(eventdata):
    """The set of action-code names an event's rules define. Lets the analyzer
    pick era-appropriate auto-insert codes: §209 DNF/DNS when a 2026+ ruleset
    defines them, else the pre-§209 IR/DS (the default when unknown)."""
    return {r[1] for r in eventdata.get("rules", []) if len(r) > 1 and r[1]}


def deprecation_warning(eventdata, code_name):
    """If ``eventdata`` is a 2026+ event (its rules use §209 outcome codes) and
    ``code_name`` is a deprecated pre-§209 code, return the §209 code to use
    instead; otherwise None. An authoring hint only -- legacy events are never
    flagged (they correctly keep DQ/DS/NQ/IR)."""
    from cozer.records import DEPRECATED_209, UIM209_CODES
    repl = DEPRECATED_209.get(code_name)
    if repl and (rule_action_codes(eventdata) & UIM209_CODES):
        return repl
    return None


def _boat_key(pid):
    """Deterministic, storage-independent sort order for a boat id: by numeric
    value (2 before 10), identical whether ids are stored as ints (legacy pickle)
    or strings (JSON round-trip), so a report's boat order never changes when an
    event is saved and reopened. Non-numeric ids fall back to their string form,
    after all numeric ids (matching legacy, which ordered str ids after int ids)."""
    s = str(pid)
    return (0, int(s)) if s.isdigit() else (1, s)


def getresorder(res):
    rks = []
    for k in res:
        place = res[k]['place'] if res[k]['place'] > 0 else 99999
        rks.append((place, k))
    rks.sort(key=lambda r: (r[0], _boat_key(r[1])))
    return [r[1] for r in rks]


def _score(scoringsystem, ip):
    """Points for finishing position index ``ip``. Legacy indexes
    ``scoringsystem[ip]`` directly and crashes when the scoring system is empty or
    shorter than the field (e.g. a not-yet-configured event); positions beyond the
    scored tiers earn 0 (deliberate robustness divergence, MAINTENANCE_PLAN §6.6)."""
    return scoringsystem[ip] if 0 <= ip < len(scoringsystem) else 0


def getsumresorder(res):
    ids = []
    for pid in res.keys():
        ids.append((res[pid]['points'], res[pid]['avgspeed'], res[pid]['maxlapspeed'], pid))
    ids.sort(key=lambda x: (x[0], x[1], x[2], _boat_key(x[3])))
    ids.reverse()
    return [i[3] for i in ids]


def sumanalyze(heats, res, sheats):
    """Final standings across ``heats``: each competitor's best ``sheats`` heat
    scores summed; placed by (sumpoints, best avg/max speed). Port of legacy
    ``analyzer.sumanalyze``."""
    invres = {}
    for h in heats:
        for pid in res[h].keys():   # legacy uses .keys() -> None.keys() raises AttributeError
            if pid not in invres:
                invres[pid] = {}
            invres[pid][h] = res[h][pid]
    sumres = {}
    for pid in invres.keys():
        points = []
        bestavg = -1
        bestmax = -1
        for h in heats:
            r = invres[pid].get(h)      # a boat need not have raced every heat
            if r and r['place'] > 0:
                points.append(r['points'])
                bestavg = max(bestavg, r['avgspeed'])
                bestmax = max(bestmax, r['maxlapspeed'])
        sumpoints = -1
        if points:
            points.sort()
            points.reverse()
            sumpoints = sum(points[:sheats])
        sumres[pid] = {'points': sumpoints, 'avgspeed': bestavg, 'maxlapspeed': bestmax}
    i = 0
    for pid in getsumresorder(sumres):
        if sumres[pid]['points'] >= 0:
            i = i + 1
            sumres[pid]['place'] = i
        else:
            sumres[pid]['place'] = -1
    return sumres


def get_racetime(record):
    info, rec = record
    info['course']  # (referenced in legacy; kept for parity)
    if 'racetime' not in info:
        racetime = 1
        for pid in rec:
            t = 0
            for m in rec[pid]:
                if abs(m[0]) in (LAP, INSERTED_LAP):
                    t = t + m[1]
                else:
                    racetime = max(racetime, m[1])
            racetime = max(racetime, t)
        info['racetime'] = 1.05 * racetime
    return info['racetime']


def ceil(f):
    if int(f) < f:
        return int(f + 1)
    return int(f)


def analyze_endurance(heat, record, scoringsystem=[]):
    info, rec = record
    racetime = info.get('racetime', info.get('duration'))
    course = info['course']
    duration = info.get('duration', racetime)
    if racetime >= 0.9 * duration:
        pointscoeff = 1.0
    elif racetime >= 0.75 * duration:
        pointscoeff = 0.75
    elif racetime >= 0.5 * duration:
        pointscoeff = 0.5
    elif racetime >= 0.25 * duration:
        pointscoeff = 0.25
    else:
        pointscoeff = 0
    preres = []
    for pid in rec:
        penlaps = 0
        t = 0
        laps = 0
        ignorelaps = 0
        interruption = 0
        disqualification = 0
        notclassified = 0
        didntstart = 0
        notes = {}
        for m in rec[pid]:
            if m[0] in (PL, PL5, PL8, PL10, PL3, PL4, PL15):
                if m[1] <= racetime:
                    penlaps = penlaps + {PL: 1, PL5: 5, PL8: 8, PL10: 10, PL3: 3, PL4: 4, PL15: 15}[m[0]]
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
        maxlapspeed = 0
        avgspeed = 0
        distcovered = 0
        lapslost = 0
        penlapsleft = penlaps
        pastafterstoppage = 0
        lapstime = []
        dt = 0
        li = 0
        for m in rec[pid]:
            if abs(m[0]) in (LAP, INSERTED_LAP):
                if (not ignorelaps) and t + m[1] <= racetime + 10 * 60:
                    if t + m[1] > racetime:
                        ignorelaps = 1
                    t = t + m[1]
                    if m[0] < 0:
                        dt = dt + m[1]
                        continue
                    elif dt:
                        dt = dt + m[1]
                    else:
                        dt = m[1]
                    if lapslost:
                        lapslost = lapslost - 1
                    else:
                        laps = laps + 1
                        li = 0
                        distcovered = distcovered + course[li]
                        lapspeed = round2(3.6 * course[li] / float(dt), roundopt)
                        if lapspeed > maxlapspeed:
                            maxlapspeed = lapspeed
                        lapstime.append(t)
                    dt = 0
                else:
                    pastafterstoppage = 1
                    ignorelaps = 1
            elif m[0] in (LL, LL2):  # lost one or two laps
                if m[1] <= racetime:
                    lapslost = lapslost + {LL: 1, LL2: 2}[m[0]]
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
            elif m[0] in (PL, PL5, PL8, PL10, PL3, PL4, PL15):  # penalty laps (counted above)
                pass
            elif m[0] in (DS, DNS, DNR, ACC):  # did not start / restart / accident (all excluded)
                didntstart = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] in (IR, DNF):  # interruption / did not finish (excluded)
                if m[1] <= racetime:
                    interruption = 1
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n and n not in notes[k]:
                        notes[k].append(n)
            elif m[0] in (DQ, DSQ):  # disqualified
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == YC:  # yellow card
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == RC:  # red card
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == BC:  # blue card (406.05): note only. Cards accrue across
                # events/disciplines, so a repeat-offence DSQ is entered manually.
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == NC:  # not classified (endurance 902.47)
                notclassified = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == NT:  # note
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            else:
                _log.debug("analyze_endurance: unused code %s", m[0])
            avgspeed = 0
        if laps and t > 0:
            avgspeed = round2(3.6 * distcovered / float(t), roundopt)

        code = 10 * didntstart + interruption + 100 * disqualification + 100 * notclassified
        preres.append((code,
                       -(laps - penlaps - lapslost),
                       -avgspeed, -maxlapspeed, lapstime,
                       (pastafterstoppage, penlapsleft, laps),
                       pid, notes))
    preres = py2_sorted(preres)

    requiredlaps4pointscoef = 0.4
    notrunningrequiredlaps4pointscoef = 0.9

    leaderlaps = -preres[0][1]
    leadertime = 0
    if preres[0][4]:
        leadertime = preres[0][4][-1]
    minlaps4points = max(1, requiredlaps4pointscoef * leaderlaps)
    notrunningminlaps4points = max(1, notrunningrequiredlaps4pointscoef * leaderlaps)

    res = {}
    for i, item in enumerate(preres):
        ip = min(i, len(scoringsystem) - 1)
        code, countedlaps, avgspeed, maxlapspeed, lapstime, (pastafterstoppage, penlapsleft, laps), pid, notes = item
        avgspeed, maxlapspeed = -avgspeed, -maxlapspeed
        countedlaps = -countedlaps
        points = -1
        place = -1
        ll = 0
        lasttime = 0
        totallapstime = None
        bestlaptime = None
        bestlap = None
        totallaps = len(lapstime)
        if lapstime:
            lasttime = lapstime[-1]
            totallapstime = lasttime
            for t in lapstime:
                ll = ll + 1
                if t > leadertime:
                    lasttime = t
                    break
            for j in range(len(lapstime)):
                if bestlap is None:
                    bestlaptime = lapstime[j]
                    bestlap = j + 1
                else:
                    lt = lapstime[j] - lapstime[j - 1]
                    if lt < bestlaptime:
                        bestlaptime = lt
                        bestlap = j + 1
        totallaps = countedlaps
        getspoints = (lasttime > min(duration, leadertime)) or (totallaps >= notrunningminlaps4points)
        if code == 0:
            if getspoints:
                place = i + 1
                points = 0
                if totallaps >= minlaps4points and ip >= 0:
                    points = ceil(_score(scoringsystem, ip) * pointscoeff)
        res[pid] = {}
        res[pid]['points'] = points
        res[pid]['place'] = place
        res[pid]['avgspeed'] = avgspeed
        res[pid]['maxlapspeed'] = maxlapspeed
        res[pid]['bestlap'] = bestlaptime, bestlap
        res[pid]['totallaps'] = totallapstime, totallaps
        res[pid]['lapinfo'] = laps, penlapsleft, 0
        res[pid]['notes'] = notes

    return res


def analyze(heat, record, scoringsystem=[], rulecodes=()):
    info, rec = record
    duration = info.get('duration')
    if duration is not None:
        return analyze_endurance(heat, record, scoringsystem)
    course = info['course']
    racetime = get_racetime(record)

    isrestarted = (heat and heat[-1] == 'r')
    isrestarted2 = (heat and heat[-1] == 'R')
    isqualification = (heat and heat[-1] == 'q')
    istimetrial = (heat and heat[-1] == 't')
    isendurance = duration is not None
    # LP2 (307.01/307.02): positions to lose per boat, applied after placement.
    losepos = {}
    for pid in rec:
        n2 = 2 * sum(1 for m in rec[pid] if m[0] == LP2 and m[1] <= racetime)
        if n2:
            losepos[pid] = n2
    preres = []
    for pid in rec:
        penlaps = 0
        t = 0
        laps = 0
        ignorelaps = 0
        interruption = 0
        disqualification = 0
        qualification = 3
        didntstart = 0
        notes = {}
        for m in rec[pid]:
            if m[0] in (PL, PL5, PL8):
                if m[1] <= racetime:
                    penlaps = penlaps + {PL: 1, PL5: 5, PL8: 8}[m[0]]
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
        if isendurance:  # pragma: no cover - dead in analyze: duration!=None returns analyze_endurance above
            lapsrequired = 10000  # large number
        else:
            lapsrequired = len(course)
        maxlapspeed = 0
        avgspeed = 0
        distcovered = 0
        lapslost = 0
        penlapsleft = penlaps
        pastafterstoppage = 0
        esttime = 0
        lapstime = []
        dt = 0
        li = 0
        for m in rec[pid]:
            if abs(m[0]) in (LAP, INSERTED_LAP):
                if (not ignorelaps) and t + m[1] <= racetime and laps < lapsrequired + penlaps:
                    t = t + m[1]
                    if m[0] < 0:
                        dt = dt + m[1]
                        continue
                    elif dt:
                        dt = dt + m[1]
                    else:
                        dt = m[1]
                    if lapslost:
                        lapslost = lapslost - 1
                    else:
                        laps = laps + 1
                        li = min(len(course), laps) - 1
                        if penlaps and laps > lapsrequired:
                            penlapsleft = penlapsleft - 1
                        else:
                            distcovered = distcovered + course[li]
                        lapspeed = round2(3.6 * course[li] / float(dt), roundopt)
                        if lapspeed > maxlapspeed:
                            maxlapspeed = lapspeed
                        esttime = round2(3.6 * course[min(len(course) - 1, li + 1)] / float(maxlapspeed), roundopt)
                        lapstime.append(t)
                    dt = 0
                else:
                    pastafterstoppage = 1
                    ignorelaps = 1
            elif m[0] == LL:  # lost a lap
                if m[1] <= racetime and laps < lapsrequired + penlaps:
                    lapslost = lapslost + 1
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
            elif m[0] in (PL, PL5, PL8):  # penalty laps (counted above)
                pass
            elif m[0] in (DS, DNS, DNR, ACC):  # did not start / restart / accident (all excluded)
                didntstart = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] in (IR, DNF):  # interruption / did not finish (excluded)
                if m[1] <= racetime:
                    interruption = 1
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n and n not in notes[k]:
                        notes[k].append(n)
            elif m[0] in (DQ, DSQ):  # disqualified
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == YC:  # yellow card
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == RC:  # red card
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == BC:  # blue card (406.05): note only. Cards accrue across
                # events/disciplines, so a repeat-offence DSQ is entered manually.
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == LP2:  # lose two positions (reorder applied after placement)
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == NT:  # note
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == Q:  # qualified
                qualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] in (NQ, DNQ):  # not qualified
                qualification = 2
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            else:
                _log.debug("analyze: unused code %s", m[0])
        if istimetrial:
            if laps > 1:
                avgspeed = round2(3.6 * course[-1] / float(lapstime[-1] - lapstime[-2]), roundopt)
            penlapavgspeed = avgspeed
        else:
            if laps:
                if t > 0:
                    avgspeed = round2(3.6 * distcovered / float(t), roundopt)
                else:  # pragma: no cover - a counted lap always has t>0 (0-time lap divides by zero earlier)
                    avgspeed = 0
            if penlapsleft:
                if t > 0:
                    penlapavgspeed = round2(3.6 * (distcovered - penlapsleft * course[li]) / float(t), roundopt)
                else:  # pragma: no cover - unreachable (see above)
                    penlapavgspeed = 0
            else:
                penlapavgspeed = avgspeed
        if isendurance:  # pragma: no cover - dead in analyze (see lapsrequired above)
            lapsleft = 0
        else:
            lapsleft = lapsrequired - laps + penlaps
        code = 10 * didntstart + interruption + 100 * disqualification
        if lapsleft and (not pastafterstoppage) and (code == 0):
            if t + 2.5 * esttime < racetime and not istimetrial:
                if laps:
                    # non-finisher: §209 DNF if the ruleset uses it, else legacy IR
                    nf = DNF if 'DNF' in rulecodes else IR
                    _warning('Appended %s mark for %s' % (invreccodemap[nf], pid))
                    code = 1
                    insertmark(rec[pid], nf, t + 2.5 * esttime, '')
                    k = invreccodemap[nf]
                    if k not in notes:
                        notes[k] = []
                else:
                    # never started: §209 DNS if the ruleset uses it, else legacy DS
                    ns = DNS if 'DNS' in rulecodes else DS
                    _warning('Appended %s mark for %s' % (invreccodemap[ns], pid))
                    code = 10
                    insertmark(rec[pid], ns, t + 2.5 * esttime, '')
                    k = invreccodemap[ns]
                    if k not in notes:
                        notes[k] = []
        preres.append((code,
                       qualification,
                       lapsleft, -penlapavgspeed,
                       -avgspeed, -maxlapspeed, lapstime,
                       (pastafterstoppage, penlapsleft, laps),
                       pid, notes))
    preres = py2_sorted(preres)

    requiredlapscoef = 0.70           # U.I.M. 2000,2009 311.02.1
    restartrequiredlapscoef = 0.35    # U.I.M. 2000.2009 311.02.7_1
    requiredlaps4pointscoef = 0.75    # U.I.M. 2009 318.02_1, must cross the lane
    minrequiredlaps = requiredlapscoef * len(course)
    minrestartrequiredlaps = restartrequiredlapscoef * len(course)
    leaderlaps = preres[0][7][2] - preres[0][7][1]
    leadertime = 0
    if preres[0][6]:
        leadertime = preres[0][6][-1]
    minlaps4points = max(1, requiredlaps4pointscoef * leaderlaps)

    # UIM09 318.02_2 exception (legacy kept this active branch):
    minrequiredlaps, minrestartrequiredlaps = int(minrequiredlaps), int(minrestartrequiredlaps)
    minlaps4points = int(math.ceil(minlaps4points))

    needsrestart = (not (isrestarted or isrestarted2)) and leaderlaps < minrequiredlaps
    if needsrestart:
        _info('Restart is required by U.I.M. rule 311.02.1: leaderslaps,minrequiredlaps=',
              leaderlaps, minrequiredlaps)

    res = {}
    i = -1
    for item in preres:
        i = i + 1
        ip = min(i, len(scoringsystem) - 1)
        code, qualification, lapsleft, penlapavgspeed, avgspeed, maxlapspeed, lapstime, (pastafterstoppage, penlapsleft, laps), pid, notes = item
        penlapavgspeed, avgspeed, maxlapspeed = -penlapavgspeed, -avgspeed, -maxlapspeed
        points = -1
        place = -1
        ll = 0
        lasttime = 0
        if lapstime:
            lasttime = lapstime[-1]
            for t in lapstime:
                ll = ll + 1
                if t > leadertime:
                    lasttime = t
                    break
            if ll < len(lapstime):
                laps = laps - (len(lapstime) - ll)
                lapsleft = lapsleft + (len(lapstime) - ll)
                _info('You must disable last %s lapmarks for %s' % (len(lapstime) - ll, pid))
        totallaps = laps - penlapsleft
        getspoints = (not lapsleft) or (pastafterstoppage) or (lasttime > leadertime)
        if isqualification:
            if qualification == 3 and code == 0:
                _info("Check %s for qualification or nonqualification or didn't start." % (pid))
            if (code == 0 and getspoints):
                place = i + 1
        elif code == 0:
            if getspoints:
                place = i + 1
                points = 0
                if isrestarted:
                    if totallaps >= minlaps4points:
                        if totallaps >= minrestartrequiredlaps:
                            points = _score(scoringsystem, ip)
                        elif totallaps > 0:
                            points = 0.5 * _score(scoringsystem, ip)
                elif isrestarted2:  # UIM09 311.02.7_4
                    if totallaps:
                        points = _score(scoringsystem, ip)
                else:
                    if totallaps >= minlaps4points:
                        points = _score(scoringsystem, ip)
            else:
                if lapsleft:
                    _info('Check %s for interruption or insert a lapmark after stoppage.' % (pid))
        res[pid] = {}
        if istimetrial or isqualification:
            res[pid]['points'] = 0
            if istimetrial:
                if len(lapstime) > 1:
                    res[pid]['laptime'] = lapstime[-1] - lapstime[-2]
                else:
                    res[pid]['laptime'] = 0
        else:
            res[pid]['points'] = points
        res[pid]['place'] = place
        res[pid]['avgspeed'] = avgspeed
        res[pid]['maxlapspeed'] = maxlapspeed
        res[pid]['lapinfo'] = laps, penlapsleft, lapsleft
        res[pid]['notes'] = notes

    # LP2 (307.01/307.02): each carrying boat drops two places in the classified
    # order; points stay with positions, so the boats it passes move up and gain
    # the corresponding points. No effect on unclassified boats (DS/DQ/NC).
    if losepos and not istimetrial and not isqualification:
        ordered = [pid for pid in getresorder(res) if res[pid]['place'] > 0]
        pts_by_pos = [res[pid]['points'] for pid in ordered]
        for pid in [p for p in ordered if p in losepos]:
            idx = ordered.index(pid)
            newidx = min(idx + losepos[pid], len(ordered) - 1)
            ordered.pop(idx)
            ordered.insert(newidx, pid)
        for newi, pid in enumerate(ordered):
            res[pid]['place'] = newi + 1
            res[pid]['points'] = pts_by_pos[newi]

    return res


def transpose(l):
    o = []
    for i in range(len(l)):
        for j in range(len(l[i])):
            try:
                o[j].append(l[i][j])
            except IndexError:
                o.append([l[i][j]])
    return o


def countlaps(heat, record):
    info, rec = record
    course = info['course']
    if heat == -1:
        rks = sorted(rec.keys(), key=_boat_key)
        laps = [[(k, 1) for k in rks]]
        for i in range(len(course)):
            laps.append([(0, 0) for k in rks])
        return transpose(laps)
    if 'racetime' not in info:
        racetime = 1
        for pid in rec:
            t = 0
            for m in rec[pid]:
                if abs(m[0]) in (LAP, INSERTED_LAP):
                    t = t + m[1]
                else:
                    racetime = max(racetime, m[1])
            racetime = max(racetime, t)
        racetime = 1.05 * racetime
    else:
        racetime = info['racetime']
    sarr = []
    rks = sorted(rec.keys(), key=_boat_key)
    for pid in rks:
        t0 = 0
        for t in gettimes(rec[pid]):
            t0 = t0 + t
            sarr.append([t0, pid])
    sarr.sort(key=lambda s: (s[0], _boat_key(s[1])))
    idseq = [s[1] for s in sarr]

    laps = [[(k, 1) for k in rks]]
    i = -1
    for pid in idseq:
        i = i + 1
        fl = sarr[i][0] <= racetime
        flag = 1
        for l in laps:
            if ((pid, 1) not in l) and ((pid, 0) not in l):
                l.append((pid, fl))
                flag = 0
                break
        if flag:
            laps.append([(pid, fl)])
    for i in range(1, len(laps)):
        laps[i] = laps[i] + [(0, 0) for _ in range(len(laps[0]) - len(laps[i]))]
    return transpose(laps)
