"""Race-pattern parsing and heat logic -- Python-3 port of the
CrackRacePattern / GetClasses / GetAllowedHeats / GetHeats methods from legacy
``cozer/__init__.py`` (MainFrame). Pure functions over ``eventdata``;
equivalence enforced by ``tests/test_model_equivalence.py``.

``crack_race_pattern`` uses ``eval()`` to parse the arithmetic in a (trusted,
operator-entered) pattern string, exactly as legacy did. Replacing it with a
safe arithmetic parser is a candidate for the later security-hardening pass;
kept as-is here to preserve equivalence.
"""
from cozer.classes import isqclass, istclass


def markoutercomma(line, comma=','):
    """Mark top-level (unparenthesised) occurrences of ``comma`` as ``@<c>@``."""
    l = ''
    f = 0
    for c in line:
        if c == '(':
            f = f + 1
        elif c == ')':
            f = f - 1
        elif c == comma and f == 0:
            l = l + '@' + comma + '@'
            continue
        l = l + c
    return l


def crack_race_pattern(pat, cl='', warn=None):
    """Parse a race pattern.

    ``'NofHeats*(NofLaps*LapLength+..)+..:Scored'`` -> ``(heats, sheats)`` where
    ``heats`` is a list (one per heat) of lap-length lists; or endurance
    ``'NofEstLaps*LapLength/Hours'`` -> ``([[LapLength]*NofEstLaps], 1, seconds)``.
    """
    pat = pat.replace(' ', '')
    if '/' in pat:
        ll, hours = pat.split('/')
        if '*' in ll:
            nlaps, ll = ll.split('*')
            nlaps = '1'
        else:
            nlaps = '1'
        return [[eval(ll)] * eval(nlaps)], 1, eval(hours) * 60 * 60
    apat = pat.split(':')
    pat = apat[0]
    apat = apat[1:]
    ret = []
    for s in markoutercomma(pat, '+').split('@+@'):
        m = markoutercomma(s, '*').split('@*@')
        if len(m) == 1:
            m = ['1', m[0]]
        elif len(m) == 2:
            m = [m[0], m[1]]
        else:
            m = [m[0], '*'.join(m[1:])]
        m[1] = m[1].strip()
        if m[1][0] == '(' and m[1][-1] == ')':
            m[1] = m[1][1:-1]
        hh = eval(m[0])
        for _i in range(hh):
            ret.append([])
            for t in markoutercomma(m[1], '+').split('@+@'):
                k = markoutercomma(t, '*').split('@*@')
                if len(k) == 1:
                    k = ['1', k[0]]
                elif len(k) == 2:
                    k = [k[0], k[1]]
                else:
                    k = [k[0], '*'.join(k[1:])]
                nl = eval(k[0])
                llen = eval(k[1])
                for _j in range(nl):
                    ret[-1].append(llen)
    try:
        sheats = eval(apat[0])
    except Exception:
        sheats = len(ret)
        if cl and warn:
            warn('Scored heats for class %s is set %s' % (cl, sheats))
    return ret, sheats


def get_classes(eventdata):
    try:
        classes = [x[1] for x in eventdata['classes']]
    except KeyError:
        classes = []
    return [c for c in classes if c]


# --- structured circuit-pattern helpers (for the pattern-entry dialog) -------
# The common circuit form is ``H*(first + (L-1)*other):B`` — H heats, each of L
# laps (a distinct first-lap length + uniform remaining laps), best B scored.

def _num(x):
    return "%g" % x                       # 1430.0 -> "1430", 1390.5 -> "1390.5"


def format_circuit_pattern(first, other, laps, heats, scored):
    """Build the pattern string for the common circuit case."""
    laps = max(1, int(laps))
    heats = max(1, int(heats))
    scored = int(scored)
    if laps == 1:
        inner = _num(first)
    elif first == other:
        inner = "%d*%s" % (laps, _num(other))
    else:
        inner = "%s+%d*%s" % (_num(first), laps - 1, _num(other))
    return "%d*(%s):%d" % (heats, inner, scored)


def parse_simple_pattern(pat):
    """Best-effort parse of a pattern into the common circuit fields
    ``{first, other, laps, heats, scored}``, or None if it isn't that simple
    shape (endurance, per-heat differences, non-uniform lap lengths)."""
    if not pat or "/" in pat:             # endurance is handled via the raw field
        return None
    try:
        heats, sheats = crack_race_pattern(pat)[:2]
    except Exception:
        return None
    if not heats or any(h != heats[0] for h in heats):
        return None
    h0 = heats[0]
    if not h0:
        return None
    rest = h0[1:]
    if rest and any(x != rest[0] for x in rest):
        return None
    return {"first": h0[0], "other": rest[0] if rest else h0[0],
            "laps": len(h0), "heats": len(heats), "scored": sheats}


def describe_pattern(pat):
    """A short human description of a pattern for a summary line."""
    try:
        r = crack_race_pattern(pat)
    except Exception:
        return "invalid pattern"
    heats, sheats = r[0], r[1]
    if not heats or not heats[0]:
        return "no laps"
    if len(r) == 3:                        # endurance: (laps, 1, seconds)
        return "endurance · ~%d laps of %s m · %g h" % (
            len(heats[0]), _num(heats[0][0]), r[2] / 3600.0)
    h0 = heats[0]
    if all(x == h0[0] for x in h0):
        laps = "%d laps of %s m" % (len(h0), _num(h0[0]))
    elif len(h0) > 1:
        laps = "first %s m, then %d×%s m" % (_num(h0[0]), len(h0) - 1, _num(h0[1]))
    else:
        laps = "%s m" % _num(h0[0])
    mixed = "" if all(h == h0 for h in heats) else " (mixed heats)"
    return "%d heat(s)%s · %s · best %s" % (len(heats), mixed, laps, sheats)


def get_allowed_heats(eventdata, cl):
    rpat = None
    for l in eventdata['classes']:
        if l[1] and l[2] and l[1] == cl:
            rpat = crack_race_pattern(l[2])[0]
            break
    if not rpat:
        return []
    n = len(rpat)
    ret = []
    if isqclass(cl):
        for h in range(1, 1 + n):
            ret += [str(h), str(h) + 'q']
    elif istclass(cl):
        for h in range(1, 1 + n):
            ret += [str(h), str(h) + 't']
    else:
        for h in range(1, 1 + n):
            ret += [str(h), str(h) + 'r', str(h) + 'R']
    return ret


def get_heats(eventdata, raceid, warn=None):
    nofh = {}
    allowedheats = {}
    tmp = {}
    restarts = {}
    quals = {}
    tims = {}
    for l in eventdata['classes']:
        if l[1] and l[2]:
            n = len(crack_race_pattern(l[2])[0])
            nofh[l[1]] = n
            if isqclass(l[1]):
                allowedheats[l[1]] = [str(x) + 'q' for x in range(1, 1 + n)]
                quals[l[1]] = []
            elif istclass(l[1]):
                allowedheats[l[1]] = [str(x) + 't' for x in range(1, 1 + n)]
                tims[l[1]] = []
            else:
                allowedheats[l[1]] = ([str(x) for x in range(1, 1 + n)] +
                                      [str(x) + 'r' for x in range(1, 1 + n)] +
                                      [str(x) + 'R' for x in range(1, 1 + n)])
                restarts[l[1]] = []
            tmp[l[1]] = 0
    for i in range(min(raceid, len(eventdata['races']))):
        for d in eventdata['races'][i]:
            if not d[1]:
                continue
            if d[1] in nofh:
                if d[2] in allowedheats[d[1]]:
                    if d[2][-1] not in ('r', 'q', 't', 'R'):
                        tmp[d[1]] = tmp[d[1]] + 1
                        if not str(tmp[d[1]]) == d[2] and warn:
                            warn('Expected heat %s but got %s (class=%s).' % (tmp[d[1]], d[2], d[1]))
                    elif d[2][-1] in ('r', 'R'):
                        restarts[d[1]].append(d[2])
                    elif d[2][-1] == 'q':
                        tmp[d[1]] = tmp[d[1]] + 1
                        quals[d[1]].append(d[2])
                    elif d[2][-1] == 't':
                        tmp[d[1]] = tmp[d[1]] + 1
                        tims[d[1]].append(d[2])
                elif warn:
                    warn('Heat %s is not allowed for class %s.' % (d[2], d[1]))
    ret = {}
    for k in tmp.keys():
        if isqclass(k):
            if tmp[k] < nofh[k]:
                ret[k] = [str(tmp[k] + 1) + 'q']
            else:
                ret[k] = [str(tmp[k]) + 'q']
            if ret[k][-1] in quals[k]:
                del ret[k][-1]
        elif istclass(k):
            if tmp[k] < nofh[k]:
                ret[k] = [str(tmp[k] + 1) + 't']
            else:
                ret[k] = [str(tmp[k]) + 't']
            if ret[k][-1] in tims[k]:
                del ret[k][-1]
        else:
            if 1 <= tmp[k] < nofh[k]:
                ret[k] = [str(tmp[k] + 1), str(tmp[k]) + 'r', str(tmp[k]) + 'R']
            elif tmp[k] == 0:
                ret[k] = [str(1)]
            else:
                ret[k] = [str(tmp[k]) + 'r']
            if ret[k][-1] in restarts[k]:
                del ret[k][-1]
    return ret
