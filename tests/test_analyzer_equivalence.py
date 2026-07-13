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


@pytest.mark.parametrize("name,path,gpath", _cases(), ids=[c[0] for c in _cases()])
def test_event_matches_golden(name, path, gpath):
    with open(path, "rb") as f:
        data = pickle.load(f, encoding="latin-1")
    scoringsystem = data.get("scoringsystem", [])
    record = data.get("record", {}) or {}
    g = json.load(open(gpath))["analyze"]

    checked = 0
    for cl in sorted(record.keys()):
        for h in sorted(record[cl].keys()):
            key = u"%s||%s" % (cl, h)
            assert key in g, (name, key)
            got = _norm(_run(h, record[cl][h], scoringsystem))
            assert got == g[key], (name, key)
            checked += 1
    assert checked == len(g), (name, checked, len(g))
