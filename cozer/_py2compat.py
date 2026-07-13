"""Python-2 compatibility shims so the ported scoring core reproduces legacy
(Python 2.7) numeric and ordering semantics exactly.

Verified against the legacy golden fixtures (``tests/golden/analyze``).
"""
from decimal import Decimal, ROUND_HALF_UP
from functools import cmp_to_key

ROUND_OPT = 2


def round2(x, ndigits=ROUND_OPT):
    """Python-2 ``round()``: round half **away from zero**.

    Python 3's ``round()`` rounds half to even, so the analyzer's rounded
    speeds would differ.  ``Decimal(repr(x))`` uses the shortest float repr
    (identical on py2/py3), then ROUND_HALF_UP rounds ties away from zero,
    matching what legacy produced.  Returns a ``float`` like py2 ``round``.
    """
    q = Decimal(1).scaleb(-ndigits)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def _is_num(x):
    # bool is an int subclass; py2 treats it numerically.
    return isinstance(x, (int, float))


def py2_cmp(a, b):
    """Emulate CPython-2 ``cmp(a, b)`` for the value types that occur in race
    records (numbers, None, str, list/tuple, dict).  Returns -1, 0 or 1.

    Needed because legacy relies on Python 2 ordering mixed int/str ids and
    heterogeneous tuples (Python 3 would raise ``TypeError``).
    """
    na, nb = _is_num(a), _is_num(b)
    if na and nb:
        return (a > b) - (a < b)
    if a is None or b is None:
        if a is None and b is None:
            return 0
        return -1 if a is None else 1           # py2: None sorts before all
    ta, tb = type(a).__name__, type(b).__name__
    if ta != tb:
        # py2 orders unlike (non-numeric) types by type name, e.g. int < str.
        return (ta > tb) - (ta < tb)
    if isinstance(a, str):
        return (a > b) - (a < b)
    if isinstance(a, (list, tuple)):
        for x, y in zip(a, b):
            c = py2_cmp(x, y)
            if c:
                return c
        return (len(a) > len(b)) - (len(a) < len(b))
    if isinstance(a, dict):  # pragma: no cover - unique ids prevent dict ties
        if len(a) != len(b):
            return (len(a) > len(b)) - (len(a) < len(b))
        return py2_cmp(py2_sorted(a.items()), py2_sorted(b.items()))
    return (id(a) > id(b)) - (id(a) < id(b))     # pragma: no cover


py2_key = cmp_to_key(py2_cmp)


def py2_sorted(iterable):
    return sorted(iterable, key=py2_key)
