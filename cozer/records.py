"""Record codes and low-level record helpers, ported from legacy
``cozer/prefs.py``.  Behavior matches legacy exactly (verified by the golden
equivalence tests).

A race record for one competitor is a list of marks ``(code, time[, mess])``:
``1``=completed lap, ``2``=inserted lap, a **negative** code = disabled mark;
plus the event codes below.
"""

reccodemap = {
    'LL': 3, 'PL': 4, 'LL2': 6,
    'PL5': 5, 'PL8': 8, 'PL10': 9,
    'DS': 10, 'IR': 11, 'DQ': 12, 'YC': 13, 'RC': 14,
    'NT': 20, 'Q': 30, 'NQ': 31,
}
invreccodemap = {v: k for k, v in reccodemap.items()}


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
