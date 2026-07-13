"""Class-name predicates, ported from legacy cozer/prefs.py.

A class name may carry a ``/Q`` (qualification) or ``/T`` (time-trial) suffix.
Return ints (1/0) to match legacy exactly.
"""

_Q = ('/Q', r'\Q', '/q', r'\q')
_T = ('/T', r'\T', '/t', r'\t')


def isqclass(cl):
    return 1 if cl[-2:] in _Q else 0


def istclass(cl):
    return 1 if cl[-2:] in _T else 0


def gettclass(cl):
    return cl[:-2] if cl[-2:] in _T else cl


def getqclass(cl):
    return cl[:-2] if cl[-2:] in _Q else cl


def getclass(cl):
    return cl[:-2] if (isqclass(cl) or istclass(cl)) else cl
