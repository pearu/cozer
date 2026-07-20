"""Race-pattern parsing and heat logic -- Python-3 port of the
CrackRacePattern / GetClasses / GetAllowedHeats / GetHeats methods from legacy
``cozer/__init__.py`` (MainFrame). Pure functions over ``eventdata``;
equivalence enforced by ``tests/test_model_equivalence.py``.

``crack_race_pattern`` parses the arithmetic in an operator-entered pattern
string with a small AST-walking evaluator (``_parse_num``) rather than ``eval``: a
pattern can never execute code, and none of eval's py2/py3 quirks (integer
division, octal literals) can leak in. Equivalence with legacy on every real
pattern is enforced by ``tests/test_model_equivalence.py``.
"""
import ast

from cozer.classes import getclass, isqclass, istclass


def _synth_name(base, kind):
    """Canonical legacy class name for a native (base, kind) — the synthesized legacy view a
    consumer still addresses classes by while the migration is in flight."""
    return base + "/T" if kind == "timetrial" else base + "/Q" if kind == "qualification" else base


def _name_kind(cl):
    """The phase kind a (synthesized) legacy class name denotes: ``timetrial`` for ``/T``,
    ``qualification`` for ``/Q``, else ``None`` = the finals phase (circuit or endurance)."""
    return "timetrial" if istclass(cl) else "qualification" if isqclass(cl) else None


_ALLOWED_BINOP = (ast.Add, ast.Sub, ast.Mult)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


def _parse_num(expr):
    """Safely evaluate a race-pattern numeric sub-expression.

    The grammar reduces every leaf to plain arithmetic over numbers (``+ - *``,
    unary sign, parentheses) -- e.g. ``'1500'`` or ``'3*1000'``. Parse it to an
    AST and walk a strict whitelist instead of calling ``eval``. Anything else
    -- names, calls, division, ``**`` -- raises ValueError.
    """
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        raise ValueError("invalid race-pattern number: %r" % (expr,))
    return _num_node(tree.body, expr)


def _num_node(node, expr):
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOP):
        left, right = _num_node(node.left, expr), _num_node(node.right, expr)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        return left * right
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARY):
        val = _num_node(node.operand, expr)
        return +val if isinstance(node.op, ast.UAdd) else -val
    if (isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)):
        return node.value
    raise ValueError("unsupported race-pattern expression: %r" % (expr,))


# Domain caps on a parsed pattern, so a fat-fingered or pasted count (e.g.
# ``10000000*1000``) raises a clean ValueError instead of hanging the parser in
# range() -- which runs live on every keystroke of the pattern-entry preview, so a
# hang would freeze the whole UI. A class realistically races well under 10 heats,
# so 100 is a very safe ceiling. Laps run higher -- an endurance heat can be ~300
# laps -- so the lap ceiling is set far above any conceivable real value (still
# instant to expand); both caps exist only to stop a pathological count, never to
# reject a legitimate pattern.
_MAX_HEATS = 100
_MAX_LAPS_PER_HEAT = 10000


def _count(expr):
    """A repetition count (number of heats or laps) as a non-negative int. A
    fraction like ``1.5`` cannot index range() (legacy raised TypeError); reject it
    -- and any negative -- with a clean, catchable ValueError instead."""
    n = _parse_num(expr)
    if isinstance(n, float):
        if not n.is_integer():
            raise ValueError("race-pattern count must be a whole number: %r" % (expr,))
        n = int(n)
    if n < 0:
        raise ValueError("race-pattern count must be non-negative: %r" % (expr,))
    return n


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


DEFAULT_CLASS_SPEED = 150.0   # km/h, when a pattern carries no '@<speed>' hint

# Race kinds -- an explicit '!<kind>' pattern hint, else inferred (see race_kind).
RACE_KINDS = ("circuit", "endurance", "timetrial", "training", "qualification")

# Trailing pattern hints, in any order: '@<speed>' (km/h) and '!<kind>'. They are
# not part of the lap structure; crack_race_pattern strips them.
_HINT_SIGILS = ("@", "!")


def _bare_pattern(pat):
    """The lap-structure part of ``pat`` -- everything before the first hint sigil."""
    cut = len(pat)
    for sig in _HINT_SIGILS:
        i = pat.find(sig)
        if 0 <= i < cut:
            cut = i
    return pat[:cut]


def _hint(pat, sig):
    """The token following hint sigil ``sig`` (up to the next hint), or None."""
    i = pat.find(sig)
    if i < 0:
        return None
    rest = pat[i + 1:]
    for s in _HINT_SIGILS:
        j = rest.find(s)
        if j >= 0:
            rest = rest[:j]
    return rest.replace(" ", "")


def pattern_speed(pat, default=DEFAULT_CLASS_SPEED):
    """The class's fastest expected speed in km/h, from an optional ``'@<speed>'``
    hint on the race pattern (e.g. ``'2*(1600+4*1600):2@150'``); ``default`` if
    absent or unparseable. Used to estimate the fastest physically possible lap
    (mis-click detection) and the timer's lap-line closing hint."""
    tok = _hint(pat, "@")
    if tok is None:
        return default
    try:
        v = float(tok)
        return v if v > 0 else default
    except ValueError:
        return default


def pattern_kind(pat, default=None):
    """The explicit race kind from a ``'!<kind>'`` pattern hint (one of
    ``RACE_KINDS``, e.g. ``'...:2@150!circuit'``), or ``default`` if absent/unknown.
    Prefer ``race_kind`` for the full picture (it also infers)."""
    tok = _hint(pat, "!")
    if tok and tok.lower() in RACE_KINDS:
        return tok.lower()
    return default


def class_pattern(eventdata, cl):
    """The race-pattern string for class ``cl`` (a legacy name, real or synthesized), or None.
    Handles both event shapes: native ``classes`` = ``[{name, phases:[{kind, pattern, …}]}]``
    and the legacy suffixed rows."""
    if eventdata.get("schema", 1) >= 2:
        base, target = getclass(cl), _name_kind(cl)
        for entry in eventdata.get("classes", []) or []:
            if entry.get("name") != base:
                continue
            for ph in entry.get("phases", []) or []:
                if ph["kind"] == target or (target is None and ph["kind"] in ("circuit", "endurance")):
                    pat = ph.get("pattern", "") or ""
                    if ph.get("qualifiers"):
                        pat = "%s!qualification[%s]" % (pat, ",".join(str(c) for c in ph["qualifiers"]))
                    return pat or None
        return None
    for l in eventdata.get("classes", []):
        if len(l) > 2 and l[1] == cl and l[2]:
            return l[2]
    return None


def race_kind(eventdata, cl):
    """The race kind for class ``cl``: an explicit ``'!<kind>'`` pattern hint if
    present, else inferred -- a ``/T`` class is timetrial, ``/Q`` qualification, an
    endurance pattern (has a duration) endurance, else circuit. Central so callers
    stop inferring discipline from side-effects (a duration present, a class suffix)."""
    pat = class_pattern(eventdata, cl)
    explicit = pattern_kind(pat) if pat else None
    if explicit:
        return explicit
    if istclass(cl):
        return "timetrial"
    if isqclass(cl):
        return "qualification"
    if pat:
        try:
            if len(crack_race_pattern(pat)) == 3:      # endurance -> (laps, 1, seconds)
                return "endurance"
        except Exception:
            pass
    return "circuit"


def crack_race_pattern(pat, cl='', warn=None):
    """Parse a race pattern.

    ``'NofHeats*(NofLaps*LapLength+..)+..:Scored'`` -> ``(heats, sheats)`` where
    ``heats`` is a list (one per heat) of lap-length lists; or endurance
    ``'NofEstLaps*LapLength/Hours'`` -> ``([[LapLength]*NofEstLaps], 1, seconds)``.

    Trailing ``'@<speed>'`` (see ``pattern_speed``) and ``'!<kind>'`` (see
    ``race_kind``) hints are stripped here -- they aren't part of the lap structure.
    """
    pat = _bare_pattern(pat.replace(' ', ''))
    if '/' in pat:
        parts = pat.split('/')
        if len(parts) != 2:
            raise ValueError("invalid endurance race pattern: %r" % (pat,))
        ll, hours = parts
        if '*' in ll:
            nlaps, ll = ll.split('*', 1)
            nlaps = '1'
        else:
            nlaps = '1'
        return [[_parse_num(ll)] * _count(nlaps)], 1, _parse_num(hours) * 60 * 60
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
        if not m[1]:
            raise ValueError("empty lap spec in race pattern: %r" % (pat,))
        if m[1][0] == '(' and m[1][-1] == ')':
            m[1] = m[1][1:-1]
        hh = _count(m[0])
        for _i in range(hh):
            if len(ret) >= _MAX_HEATS:          # bound before range(hh) expands
                raise ValueError("too many heats for a class (max %d): %r"
                                 % (_MAX_HEATS, pat))
            ret.append([])
            for t in markoutercomma(m[1], '+').split('@+@'):
                k = markoutercomma(t, '*').split('@*@')
                if len(k) == 1:
                    k = ['1', k[0]]
                elif len(k) == 2:
                    k = [k[0], k[1]]
                else:
                    k = [k[0], '*'.join(k[1:])]
                nl = _count(k[0])
                llen = _parse_num(k[1])
                if len(ret[-1]) + nl > _MAX_LAPS_PER_HEAT:   # bound before range(nl) expands
                    raise ValueError("too many laps in a heat (max %d): %r"
                                     % (_MAX_LAPS_PER_HEAT, pat))
                for _j in range(nl):
                    ret[-1].append(llen)
    try:
        sheats = _parse_num(apat[0])
    except Exception:
        sheats = len(ret)
        if cl and warn:
            warn('Scored heats for class %s is set %s' % (cl, sheats))
    return ret, sheats


def get_classes(eventdata):
    if eventdata.get("schema", 1) >= 2:                 # native: synthesize a legacy name per phase
        return [_synth_name(entry.get("name"), ph["kind"])
                for entry in eventdata.get("classes", []) or []
                for ph in entry.get("phases", []) or []]
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
