"""Phase 1: validate the golden reference fixtures generated from the LEGACY
core (see tools/refharness.py).

These lock the golden format and guard against silent truncation. The actual
differential comparison (cozer port == goldens) lands in Phase 2, once the
ported core exists.
"""
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import golden_io  # noqa: E402  (shared py2.7/py3.13 serializer)

GOLDEN_DIR = os.path.join(REPO, "tests", "golden", "analyze")

EXPECTED_EVENTS = {
    "wc2000", "ec2001_o125", "EMVIetapp_2001", "EMV_3_Parnu_2006",
    "EMV_I_Harku_2025", "Endurance_EC1_Parnu_2013", "Liepaja_2006",
    "p2rnu_lahtised_meistriv6istlused", "template", "template_estonian",
}


def _load_all():
    files = sorted(glob.glob(os.path.join(GOLDEN_DIR, "*.json")))
    out = {}
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        if name.startswith("_"):   # e.g. _synthetic.json (different schema)
            continue
        out[name] = json.load(open(f))
    return out


def test_expected_golden_files_present():
    missing = EXPECTED_EVENTS - set(_load_all())
    assert not missing, "missing goldens: %s" % missing


def test_golden_structure_and_volume():
    total = 0
    for name, g in _load_all().items():
        assert {"event", "scoringsystem", "analyze"} <= set(g), name
        for key, rec in g["analyze"].items():
            assert "||" in key, (name, key)          # "<class>||<heat>"
            assert "analyze" in rec, (name, key)
            assert "countlaps" in rec, (name, key)
            total += 1
    assert total >= 100, total  # 115 today; guards against silent truncation


def test_golden_io_is_deterministic_and_idempotent():
    # The py3 side of the shared serializer used to compare against the py2.7
    # goldens in Phase 2: canon() is a fixed point and dumps() is stable.
    sample = {"b": (1, 2), "a": [b"x", 3.5, {"k": True, "n": None}]}
    once = golden_io.dumps(sample)
    twice = golden_io.dumps(json.loads(once))
    assert once == twice
    assert golden_io.canon(golden_io.canon(sample)) == golden_io.canon(sample)
