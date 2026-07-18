"""Phase 2: differential equivalence proof.

Load each legacy ``.coz`` in Python 3, run the PORTED ``cozer.analyzer`` over
every (class, heat), and assert the canonical result equals the golden captured
from the legacy Python-2 core (``tools/refharness.py``).

``_run`` mirrors ``refharness.run_one`` exactly so a per-record dict compares
whole against the golden.
"""
import copy
import glob
import json
import os
import pickle
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import golden_io  # noqa: E402

from cozer import analyzer  # noqa: E402

EVENTS_DIR = os.path.join(REPO, "legacy", "events")
DATA_DIR = os.path.join(REPO, "legacy", "cozer", "data")
GOLDEN_DIR = os.path.join(REPO, "tests", "golden", "analyze")


def _norm(x):
    """Same normalization the goldens went through (canon -> json -> back)."""
    return json.loads(golden_io.dumps(x))


def _err(e):
    return {"__error__": "%s: %s" % (type(e).__name__, e)}


def _run(heat, record_ch, scoringsystem):
    """Mirror of tools/refharness.run_one (must stay in sync)."""
    out = {}
    rc = copy.deepcopy(record_ch)
    try:
        res = analyzer.analyze(heat, rc, scoringsystem)
        out["analyze"] = res
        out["record_after_analyze"] = rc
        try:
            out["resorder"] = analyzer.getresorder(res)
        except Exception as e:               # pragma: no cover - defensive
            out["resorder"] = _err(e)
    except Exception as e:                    # pragma: no cover - defensive
        out["analyze"] = _err(e)
    rc2 = copy.deepcopy(record_ch)
    try:
        out["countlaps"] = analyzer.countlaps(heat, rc2)
    except Exception as e:                    # pragma: no cover - defensive
        out["countlaps"] = _err(e)
    return out


def _cases():
    coz = sorted(glob.glob(os.path.join(EVENTS_DIR, "*.coz")) +
                 glob.glob(os.path.join(DATA_DIR, "*.coz")))
    out = []
    for path in coz:
        name = os.path.splitext(os.path.basename(path))[0]
        gpath = os.path.join(GOLDEN_DIR, name + ".json")
        if os.path.exists(gpath):
            out.append((name, path, gpath))
    return out


# §6.6 deliberate divergences: events where the new core intentionally differs
# from the legacy golden because legacy crashes and the ported code was hardened.
# For these events, a golden entry that recorded a legacy ``__error__`` is not
# required to match; instead the new code must now succeed where legacy crashed
# (and non-crashing entries must still match exactly). See analyzer._score.
DIVERGENCES = {
    # Empty scoring system: legacy indexes ``scoringsystem[ip]`` and raises
    # IndexError; new ``_score`` returns 0 points so analyze completes.
    "p2rnu_lahtised_meistriv6istlused":
        "empty scoring system -> analyze awards 0 points instead of IndexError",
}

@pytest.mark.parametrize("name,path,gpath", _cases(), ids=[c[0] for c in _cases()])
def test_event_matches_golden(name, path, gpath):
    with open(path, "rb") as f:
        data = pickle.load(f, encoding="latin-1")
    scoringsystem = data.get("scoringsystem", [])
    record = data.get("record", {}) or {}
    full = json.load(open(gpath))
    g = full["analyze"]
    diverges = name in DIVERGENCES

    checked = 0
    for cl in sorted(record.keys()):
        for h in sorted(record[cl].keys()):
            key = u"%s||%s" % (cl, h)
            assert key in g, (name, key)
            got = _norm(_run(h, record[cl][h], scoringsystem))
            if diverges and "__error__" in g[key].get("analyze", {}):
                # legacy crashed here; the hardened core must now succeed
                assert "__error__" not in got.get("analyze", {}), \
                    (name, key, "expected §6.6 fix to avoid the legacy crash")
                assert got["countlaps"] == g[key]["countlaps"], (name, key)
            else:
                assert got == g[key], (name, key)
            checked += 1
    assert checked == len(g), (name, checked, len(g))

    # sum: final standings across heats (mirrors refharness.process_analyze).
    for cl, sinfo in full.get("sum", {}).items():
        heats = sinfo["heats"]
        sheats = sinfo["sheats"]
        res = {}
        for h in heats:
            try:
                res[h] = analyzer.analyze(h, copy.deepcopy(record[cl][h]), scoringsystem)
            except Exception:
                res[h] = None
        got = {"heats": heats, "sheats": sheats}
        try:
            sa = analyzer.sumanalyze(heats, res, sheats)
            got["sumanalyze"] = sa
            got["getsumresorder"] = analyzer.getsumresorder(sa)
        except Exception as e:
            got["sumanalyze"] = _err(e)
        if diverges and "__error__" in sinfo.get("sumanalyze", {}):
            # legacy's crash cascaded into sum; the hardened core must now succeed
            assert "__error__" not in got["sumanalyze"], \
                (name, cl, "sum", "expected §6.6 fix to avoid the legacy crash")
        else:
            assert _norm(got) == sinfo, (name, cl, "sum")


def test_synthetic_matches_golden():
    import synthetic_cases

    g = json.load(open(os.path.join(GOLDEN_DIR, "_synthetic.json")))
    checked = 0
    for case in synthetic_cases.get_cases():
        name = case["name"]
        assert name in g, name
        got = _norm(_run(case["heat"], (case["info"], case["rec"]), case["scoringsystem"]))
        assert got == g[name], name
        checked += 1
    assert checked == len(g)


def test_boat_order_is_numeric_and_storage_independent():
    """The §6.6 fix: boats order by number (2 before 10), identical whether ids are
    ints or strings -- so a report's order is stable across a save/reopen."""
    res = {pid: {"place": -1, "points": 0, "avgspeed": 0, "maxlapspeed": 0}
           for pid in (2, 10, 1)}
    assert analyzer.getsumresorder(res) == [10, 2, 1]              # numeric, reversed (desc)
    sres = {str(pid): v for pid, v in res.items()}
    assert analyzer.getsumresorder(sres) == ["10", "2", "1"]       # same order for str ids
    place = {pid: {"place": p} for pid, p in {2: 1, 10: 1, 1: 1}.items()}
    assert analyzer.getresorder(place) == [1, 2, 10]               # ties -> ascending by number
