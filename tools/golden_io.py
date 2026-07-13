"""Canonical, Python-2.7/3.13-identical JSON serialization for golden fixtures.

The SAME rules must run on both interpreters so a golden written by the legacy
harness (py2.7) compares byte-for-byte against the cozer port (py3.13):

- bytes / py2 ``str``  -> latin-1 decoded text (lossless, reversible)
- tuple               -> list
- dict                -> keys canonicalized to text, sorted
- int/long/float/bool/None/text -> unchanged

``ensure_ascii=True`` keeps the on-disk form pure ASCII, avoiding any file
encoding differences between the two interpreters.
"""
import json

try:
    _text = unicode          # noqa: F821  (py2)
    _integer = (int, long)   # noqa: F821
    _binary = str
except NameError:
    _text = str              # py3
    _integer = (int,)
    _binary = bytes


def canon(obj):
    if obj is None or isinstance(obj, bool):
        return obj
    if isinstance(obj, _binary):
        return obj.decode('latin-1')
    if isinstance(obj, _text):
        return obj
    if isinstance(obj, _integer):
        return obj
    if isinstance(obj, float):
        return obj
    if isinstance(obj, (list, tuple)):
        return [canon(x) for x in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[_canon_key(k)] = canon(v)
        return out
    return canon(repr(obj))


def _canon_key(k):
    c = canon(k)
    if isinstance(c, _text):
        return c
    return json.dumps(c, sort_keys=True)


def dumps(obj):
    return json.dumps(canon(obj), sort_keys=True, indent=2, ensure_ascii=True)
