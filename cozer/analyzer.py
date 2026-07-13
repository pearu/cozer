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
from cozer.records import invreccodemap, insertmark, gettimes

roundopt = ROUND_OPT
_log = logging.getLogger("cozer.analyzer")


def _info(*mess):
    # Legacy Info(): a status message with no effect on results.
    _log.debug("Info: %s", " ".join(str(m) for m in mess))


def _warning(*mess):
    _log.debug("Warning: %s", " ".join(str(m) for m in mess))


def getresorder(res):
    rks = []
    for k in res:
        if res[k]['place'] > 0:
            rks.append([res[k]['place'], k])
        else:
            rks.append([99999, k])
    rks = py2_sorted(rks)
    return [i[1] for i in rks]


def get_racetime(record):
    info, rec = record
    info['course']  # (referenced in legacy; kept for parity)
    if 'racetime' not in info:
        racetime = 1
        for pid in rec:
            t = 0
            for m in rec[pid]:
                if abs(m[0]) in (1, 2):
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
        didntstart = 0
        notes = {}
        for m in rec[pid]:
            if m[0] in (4, 5, 8, 9):
                if m[1] <= racetime:
                    penlaps = penlaps + {4: 1, 5: 5, 8: 8, 9: 10}[m[0]]
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
            if abs(m[0]) in (1, 2):
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
            elif m[0] in (3, 6):  # lost one or two laps
                if m[1] <= racetime:
                    lapslost = lapslost + {3: 1, 6: 2}[m[0]]
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
            elif m[0] == 4:  # penalty lap
                pass
            elif m[0] == 5:  # 5 penalty laps
                pass
            elif m[0] == 8:  # 8 penalty laps
                pass
            elif m[0] == 10:  # DS
                didntstart = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 11:  # IR
                if m[1] <= racetime:
                    interruption = 1
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n and n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == 12:  # DQ
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 13:  # yellow card
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == 14:  # red card
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 20:
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

        code = 10 * didntstart + interruption + 100 * disqualification
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
                    points = ceil(scoringsystem[ip] * pointscoeff)
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


def analyze(heat, record, scoringsystem=[]):
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
            if m[0] in (4, 5, 8):
                if m[1] <= racetime:
                    penlaps = penlaps + {4: 1, 5: 5, 8: 8}[m[0]]
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
        if isendurance:
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
            if abs(m[0]) in (1, 2):
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
            elif m[0] == 3:
                if m[1] <= racetime and laps < lapsrequired + penlaps:
                    lapslost = lapslost + 1
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n:
                        notes[k].append(n)
            elif m[0] == 4:  # penalty lap
                pass
            elif m[0] == 5:  # 5 penalty laps
                pass
            elif m[0] == 8:  # 8 penalty laps
                pass
            elif m[0] == 10:  # DS
                didntstart = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 11:  # IR
                if m[1] <= racetime:
                    interruption = 1
                    n = m[2].strip()
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n and n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == 12:  # DQ
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 13:  # yellow card
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == 14:  # red card
                disqualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 20:
                n = m[2].strip()
                if n:
                    k = invreccodemap[m[0]]
                    if k not in notes:
                        notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0] == 30:  # Q
                qualification = 1
                n = m[2].strip()
                k = invreccodemap[m[0]]
                if k not in notes:
                    notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0] == 31:  # NQ
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
                else:
                    avgspeed = 0
            if penlapsleft:
                if t > 0:
                    penlapavgspeed = round2(3.6 * (distcovered - penlapsleft * course[li]) / float(t), roundopt)
                else:
                    penlapavgspeed = 0
            else:
                penlapavgspeed = avgspeed
        if isendurance:
            lapsleft = 0
        else:
            lapsleft = lapsrequired - laps + penlaps
        code = 10 * didntstart + interruption + 100 * disqualification
        if lapsleft and (not pastafterstoppage) and (code == 0):
            if t + 2.5 * esttime < racetime and not istimetrial:
                if laps:
                    _warning('Appended IR mark for %s' % pid)
                    code = 1
                    insertmark(rec[pid], 11, t + 2.5 * esttime, '')
                    k = invreccodemap[11]
                    if k not in notes:
                        notes[k] = []
                else:
                    _warning('Appended DS mark for %s' % pid)
                    code = 10
                    insertmark(rec[pid], 10, t + 2.5 * esttime, '')
                    k = invreccodemap[10]
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
                            points = scoringsystem[ip]
                        elif totallaps > 0:
                            points = 0.5 * scoringsystem[ip]
                elif isrestarted2:  # UIM09 311.02.7_4
                    if totallaps:
                        points = scoringsystem[ip]
                else:
                    if totallaps >= minlaps4points:
                        points = scoringsystem[ip]
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
        rks = py2_sorted(rec.keys())
        laps = [[(k, 1) for k in rks]]
        for i in range(len(course)):
            laps.append([(0, 0) for k in rks])
        return transpose(laps)
    if 'racetime' not in info:
        racetime = 1
        for pid in rec:
            t = 0
            for m in rec[pid]:
                if abs(m[0]) in (1, 2):
                    t = t + m[1]
                else:
                    racetime = max(racetime, m[1])
            racetime = max(racetime, t)
        racetime = 1.05 * racetime
    else:
        racetime = info['racetime']
    sarr = []
    rks = py2_sorted(rec.keys())
    for pid in rks:
        t0 = 0
        for t in gettimes(rec[pid]):
            t0 = t0 + t
            sarr.append([t0, pid])
    sarr = py2_sorted(sarr)
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
