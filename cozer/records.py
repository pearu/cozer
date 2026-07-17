"""Record codes and low-level record helpers, ported from legacy
``cozer/prefs.py``.  Behavior matches legacy exactly (verified by the golden
equivalence tests).

A race record for one competitor is a list of marks ``(code, time[, mess])``:
``1``=completed lap, ``2``=inserted lap, a **negative** code = disabled mark;
plus the event codes below.
"""

# Record-code constants. The integer VALUES are the on-disk / legacy ``.coz``
# encoding and MUST NOT change. A completed lap is ``LAP`` and an inserted lap is
# ``INSERTED_LAP``; a *negative* code is that same mark disabled (see the
# analyzer's ``abs(m[0])`` handling).
LAP = 1
INSERTED_LAP = 2
LL = 3            # lost a lap
PL = 4            # penalty lap (1)
PL5 = 5           # 5 penalty laps
LL2 = 6           # lost two laps
PL8 = 8           # 8 penalty laps
PL10 = 9          # 10 penalty laps
DS = 10           # did not start
IR = 11           # interruption
DQ = 12           # disqualified
YC = 13           # yellow card
RC = 14           # red card
BC = 15           # blue card            -- 2026 UIM 406.05
NC = 16           # not classified       -- 2026 UIM endurance 902.47
PL3 = 17          # 3 penalty laps       -- 2026 UIM endurance
PL4 = 18          # 4 penalty laps       -- 2026 UIM endurance
PL15 = 19         # 15 penalty laps      -- 2026 UIM endurance
NT = 20           # note
LP2 = 21          # lose two positions  -- 2026 UIM 307.01 / 307.02
# 2026 UIM §209 result-outcome codes. New (2026+) events use these; pre-§209
# events keep the equivalent DS/DQ/NQ so their reports reproduce exactly. Each
# has the SAME scoring effect as its pre-§209 counterpart -- only the printed
# abbreviation differs (see analyzer parity + reports/labels.py).
DSQ = 22          # disqualified      (== DQ)
DNS = 23          # did not start     (== DS: excluded)
DNR = 24          # did not restart   (== DS: excluded)
ACC = 25          # accident/stoppage (== DS: excluded)
DNQ = 26          # did not qualify   (== NQ)
DNF = 27          # did not finish    (== IR: started, no finish after stoppage)
Q = 30            # qualified
NQ = 31           # not qualified

# name -> code, used by the record editor's rules menu and the reports layer.
reccodemap = {
    'LL': LL, 'PL': PL, 'LL2': LL2, 'PL5': PL5, 'PL8': PL8, 'PL10': PL10,
    'DS': DS, 'IR': IR, 'DQ': DQ, 'YC': YC, 'RC': RC, 'BC': BC, 'NC': NC,
    'PL3': PL3, 'PL4': PL4, 'PL15': PL15, 'LP2': LP2,
    'DSQ': DSQ, 'DNS': DNS, 'DNR': DNR, 'ACC': ACC, 'DNQ': DNQ, 'DNF': DNF,
    'NT': NT, 'Q': Q, 'NQ': NQ,
}
invreccodemap = {v: k for k, v in reccodemap.items()}

# The 2026 §209 outcome codes, and the pre-§209 codes they deprecate for 2026+
# events. Legacy events keep the pre-§209 codes (backward compatible); this only
# drives an authoring hint, never scoring.
UIM209_CODES = frozenset(('DSQ', 'DNS', 'DNR', 'ACC', 'DNQ', 'DNF'))
DEPRECATED_209 = {'DQ': 'DSQ', 'DS': 'DNS', 'NQ': 'DNQ', 'IR': 'DNF'}


def insertmark(rec, code, ct, mess=''):
    """Insert a ``(code, ct, mess)`` mark into ``rec`` at time position ``ct``.

    Faithful port of legacy ``prefs.insertmark``.
    """
    t = 0
    j = 0
    for j in range(len(rec)):
        if rec[j][0] in (1, 2, -1, -2):
            t = t + rec[j][1]
            if ct < t:
                break
        else:
            if ct < rec[j][1]:
                t = rec[j][1]
                break
    if ct < t:
        rec.insert(j, (code, ct, mess))
    else:
        rec.append((code, ct, mess))


def gettimes(race, stime=-1):
    """Cumulative completed-lap times (legacy ``prefs.gettimes``)."""
    ret = []
    dt = 0
    t = 0
    for r in race:
        if r:
            if r[0] in (1, 2):
                t = t + r[1] + dt
                if stime < 0 or t < stime:
                    ret.append(r[1] + dt)
                dt = 0
            elif r[0] in (-1, -2):
                dt = dt + r[1]
    return ret
