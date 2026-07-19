"""Tests for the phase view / compat transform (cozer/phases.py) — PHASES.md §8 step 1.

The load-bearing test is round-trip identity: ``to_legacy(to_phases(ed)) ==
ed['record']`` for every bundled event. Because the reconstructed record is
byte-identical (same class names, heat ids, and ``[info, boats]`` objects), the
golden equivalence of ``analyze``/``sumanalyze`` is preserved *by construction* —
the compat view feeds them exactly what they saw before. A file that cannot round-
trip losslessly fails here loudly, as a flagged edge case rather than a silent gap.
"""
import glob
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer import analyzer  # noqa: E402
from cozer.phases import (Phase, synth_heat_id, to_legacy, to_phases,  # noqa: E402
                          _parse_heat_id)
from cozer.store import read_legacy_coz  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENTS_DIR = os.path.join(REPO, "legacy", "events")
DATA_DIR = os.path.join(REPO, "legacy", "cozer", "data")


def _coz_files():
    return sorted(glob.glob(os.path.join(EVENTS_DIR, "*.coz")) +
                  glob.glob(os.path.join(DATA_DIR, "*.coz")))


def _ev(classes, record):
    return {"classes": classes, "record": record, "scoringsystem": [400, 300, 225],
            "participants": [], "races": [], "rules": []}


# --- the round-trip proof over every bundled event ---------------------------

@pytest.mark.parametrize("path", _coz_files(),
                         ids=[os.path.basename(p) for p in _coz_files()])
def test_roundtrip_identity(path):
    ed = read_legacy_coz(path)
    record = ed.get("record", {}) or {}
    rebuilt = to_legacy(to_phases(ed))
    assert rebuilt == record                         # byte-identical: same classes, heats, records


@pytest.mark.parametrize("path", _coz_files(),
                         ids=[os.path.basename(p) for p in _coz_files()])
def test_to_phases_does_not_mutate_eventdata(path):
    ed = read_legacy_coz(path)
    before = repr(ed.get("record", {}))
    to_phases(ed)
    assert repr(ed.get("record", {})) == before      # transform is read-only


def test_analyze_identical_through_compat_view():
    """Make the invariant explicit on a restart-bearing event: ``analyze`` on the
    reconstructed heat (addressed by the synthesized legacy id) equals ``analyze``
    on the original — the goldens 'pass through the compat view' (§3)."""
    path = os.path.join(EVENTS_DIR, "WC 2024.coz")
    if not os.path.exists(path):
        pytest.skip("WC 2024.coz not present")
    ed = read_legacy_coz(path)
    ss = ed.get("scoringsystem", [])
    orig = ed["record"]
    rebuilt = to_legacy(to_phases(ed))
    for cl in orig:
        assert cl in rebuilt
        for h in orig[cl]:
            a = analyzer.analyze(h, orig[cl][h], ss)
            b = analyzer.analyze(h, rebuilt[cl][h], ss)
            assert a == b, (cl, h)


# --- structural unit tests ---------------------------------------------------

def test_synth_heat_id_forms():
    assert synth_heat_id("timetrial", 2, 0) == "2t"
    assert synth_heat_id("qualification", 1, 0) == "1q"
    assert synth_heat_id("circuit", 1, 0) == "1"
    assert synth_heat_id("circuit", 1, 1) == "1r"
    assert synth_heat_id("circuit", 3, 2) == "3R"
    assert synth_heat_id("endurance", 2, 0) == "2"      # endurance uses the circuit form


@pytest.mark.parametrize("hid,expect", [
    ("1", (1, "")), ("1r", (1, "r")), ("3R", (3, "R")), ("2t", (2, "t")), ("10q", (10, "q"))])
def test_parse_heat_id(hid, expect):
    assert _parse_heat_id(hid) == expect


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        _parse_heat_id("x")


def test_suffix_classes_collapse_to_one_base_ordered():
    # F-4 (circuit) + F-4/T (time-trial) -> one base "F-4", time-trial phase first
    classes = [["", "F-4", "3*(1000):1"], ["", "F-4/T", "3*(1000):1"]]
    record = {"F-4": {"1": [{"course": [1000]}, {"7": [(1, 30.0)]}]},
              "F-4/T": {"1t": [{"course": [1000]}, {"7": [(1, 20.0)]}]}}
    ph = to_phases(_ev(classes, record))
    assert list(ph.keys()) == ["F-4"]
    assert [p.kind for p in ph["F-4"]] == ["timetrial", "circuit"]


def test_restart_is_a_repeated_number():
    classes = [["", "F125", "4*(1000):4"]]
    r = lambda s: [{"course": [1000]}, {"7": [(1, s)]}]
    record = {"F125": {"1": r(30.0), "1r": r(31.0), "1R": r(32.0), "2": r(33.0)}}
    ph = to_phases(_ev(classes, record))
    p = ph["F125"][0]
    assert p.kind == "circuit"
    assert p.numbers == [1, 1, 1, 2]                   # three records share number 1 = two restarts
    assert len(p.heats) == 4


def test_timetrial_heats_map_to_numbers():
    classes = [["", "GT-15/T", "1*(1000):1"]]
    record = {"GT-15/T": {"1t": [{"course": [1000]}, {"7": [(1, 20.0)]}],
                          "2t": [{"course": [1000]}, {"7": [(1, 21.0)]}]}}
    ph = to_phases(_ev(classes, record))
    p = ph["GT-15"]                                    # base is GT-15 (the /T suffix stripped)
    assert p[0].kind == "timetrial"
    assert p[0].numbers == [1, 2]


def test_qualification_roundtrip_synthetic():
    # No bundled event uses /Q, but the model must handle it — round-trip a synthetic
    # qualification + finals class (covers the /Q reconstruction path).
    classes = [["", "F125/Q", "3*(1000):1"], ["", "F125", "4*(1000):4"]]
    r = lambda s: [{"course": [1000]}, {"7": [(1, s)]}]
    record = {"F125/Q": {"1q": r(20.0), "2q": r(21.0), "3q": r(22.0)},
              "F125": {"1": r(30.0), "1r": r(31.0), "2": r(32.0)}}
    ph = to_phases(_ev(classes, record))
    assert list(ph.keys()) == ["F125"]
    assert [p.kind for p in ph["F125"]] == ["qualification", "circuit"]
    assert ph["F125"][0].numbers == [1, 2, 3]          # three qheats -> numbers 1,2,3
    assert to_legacy(ph) == record                     # /Q + base reconstruct exactly


def test_phase_equality():
    a = Phase("circuit", "p", [[{}, {}]], [1])
    b = Phase("circuit", "p", [[{}, {}]], [1])
    c = Phase("timetrial", "p", [[{}, {}]], [1])
    assert a == b and a != c
