"""Phase 2 (b): differential equivalence for the race-pattern / heat logic
(CrackRacePattern / GetClasses / GetAllowedHeats / GetHeats).

Mirrors tools/refharness.process_model so a whole per-event dict compares
against the golden generated from the legacy MainFrame methods.
"""
import glob
import json
import os
import pickle
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import golden_io  # noqa: E402

from cozer import racepattern  # noqa: E402

EVENTS_DIR = os.path.join(REPO, "legacy", "events")
DATA_DIR = os.path.join(REPO, "legacy", "cozer", "data")
GOLDEN_DIR = os.path.join(REPO, "tests", "golden", "model")


def _norm(x):
    return json.loads(golden_io.dumps(x))


def _err(e):
    return {"__error__": "%s: %s" % (type(e).__name__, e)}


def _cases():
    coz = sorted(glob.glob(os.path.join(EVENTS_DIR, "*.coz")) +
                 glob.glob(os.path.join(DATA_DIR, "*.coz")))
    out = []
    for p in coz:
        name = os.path.splitext(os.path.basename(p))[0]
        g = os.path.join(GOLDEN_DIR, name + ".json")
        if os.path.exists(g):
            out.append((name, p, g))
    return out


@pytest.mark.parametrize("name,path,gpath", _cases(), ids=[c[0] for c in _cases()])
def test_model_matches_golden(name, path, gpath):
    with open(path, "rb") as f:
        data = pickle.load(f, encoding="latin-1")
    g = json.load(open(gpath))

    assert _norm(racepattern.get_classes(data)) == g["classes"], (name, "classes")

    crack, allowed = {}, {}
    for l in data.get("classes", []):
        cl = l[1] if len(l) > 1 else ""
        pat = l[2] if len(l) > 2 else ""
        if cl and pat:
            try:
                crack[cl] = racepattern.crack_race_pattern(pat, cl)
            except Exception as e:
                crack[cl] = _err(e)
        if cl:
            try:
                allowed[cl] = racepattern.get_allowed_heats(data, cl)
            except Exception as e:
                allowed[cl] = _err(e)
    assert _norm(crack) == g["crack"], (name, "crack")
    assert _norm(allowed) == g["allowedheats"], (name, "allowedheats")

    getheats = {}
    for raceid in range(len(data.get("races", [])) + 1):
        try:
            getheats[str(raceid)] = racepattern.get_heats(data, raceid)
        except Exception as e:
            getheats[str(raceid)] = _err(e)
    assert _norm(getheats) == g["getheats"], (name, "getheats")


def _check_model(data, exp, name):
    assert _norm(racepattern.get_classes(data)) == exp["classes"], (name, "classes")
    crack, allowed = {}, {}
    for l in data.get("classes", []):
        cl = l[1] if len(l) > 1 else ""
        pat = l[2] if len(l) > 2 else ""
        if cl and pat:
            try:
                crack[cl] = racepattern.crack_race_pattern(pat, cl)
            except Exception as e:
                crack[cl] = _err(e)
        if cl:
            try:
                allowed[cl] = racepattern.get_allowed_heats(data, cl)
            except Exception as e:
                allowed[cl] = _err(e)
    assert _norm(crack) == exp["crack"], (name, "crack")
    assert _norm(allowed) == exp["allowedheats"], (name, "allowedheats")
    getheats = {}
    for raceid in range(len(data.get("races", [])) + 1):
        try:
            getheats[str(raceid)] = racepattern.get_heats(data, raceid)
        except Exception as e:
            getheats[str(raceid)] = _err(e)
    assert _norm(getheats) == exp["getheats"], (name, "getheats")


def test_synthetic_model_matches_golden():
    import synthetic_cases

    g = json.load(open(os.path.join(GOLDEN_DIR, "_synthetic.json")))
    cases = synthetic_cases.get_model_cases()
    for name, data in cases.items():
        assert name in g, name
        _check_model(data, g[name], name)
    assert len(cases) == len(g)


def test_get_heats_warn_callback():
    # The optional warn callback (no effect on the returned dict; not part of the
    # goldens) fires on a heat-number mismatch and on a not-allowed heat.
    warned = []
    racepattern.get_heats(
        {"classes": [["x", "A", "2*(3*1000):1"]], "races": [[["x", "A", "2"]]]},
        1, warn=lambda m: warned.append(("mismatch", m)))
    racepattern.get_heats(
        {"classes": [["x", "A", "2*(3*1000):1"]], "races": [[["x", "A", "9"]]]},
        1, warn=lambda m: warned.append(("notallowed", m)))
    kinds = {k for k, _ in warned}
    assert "mismatch" in kinds and "notallowed" in kinds

    # crack_race_pattern warns when scored-heats is missing (no ':') and cl+warn given.
    cw = []
    rpat, sheats = racepattern.crack_race_pattern("3*(4*1000)", "X", warn=lambda m: cw.append(m))
    assert sheats == len(rpat) and cw
