"""Codec round-trip fidelity.

The real workflow: import a legacy ``.coz`` -> save as ``.cozj`` (which round-trips
the eventdata through the JSON codec: tuples become lists, int boat keys become
strings) -> reopen. That must NEVER change analysis or any report. This sweep
round-trips every bundled legacy event and asserts analyze + all nine report
models are byte-identical before vs after -- guarding the storage layer against
silently altering results, e.g. the boat ordering that used to depend on whether
ids were stored as ints or strings (fixed by analyzer._boat_key).
"""
import copy
import glob
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import golden_io  # noqa: E402

from cozer import store, analyzer  # noqa: E402
import cozer.reports as R  # noqa: E402

_BUILDS = [R.build_full_final, R.build_short_final, R.build_participants, R.build_checklist,
           R.build_intermediate, R.build_laps_protocol, R.build_endurance_final,
           R.build_info_letter, R.build_registration_letter]


def _events():
    coz = sorted(glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")) +
                 glob.glob(os.path.join(REPO, "legacy", "cozer", "data", "*.coz")))
    return [(os.path.splitext(os.path.basename(p))[0], p) for p in coz]


_EV = _events()


def _canon(x):
    return golden_io.dumps(x)


def _report_canon(model):
    """Report model canon that is INSENSITIVE to class-table order: the native save shape
    regroups classes base-grouped, so a table may move but its content must not change."""
    m = dict(model)
    if isinstance(m.get("tables"), list):
        m["tables"] = sorted(m["tables"], key=_canon)
    return _canon(m)


@pytest.mark.parametrize("name,path", _EV, ids=[e[0] for e in _EV])
def test_roundtrip_preserves_analysis_and_reports(name, path):
    ed = store.read_legacy_coz(path)
    rt = store.load_event(store.dump_event(ed))            # legacy -> save (native) -> reopen
    assert store.dump_event(rt) == store.dump_event(store.load_event(store.dump_event(rt)))  # idempotent

    ss1, ss2 = ed.get("scoringsystem", []), rt.get("scoringsystem", [])
    # rt is the native shape (store saves/loads native); enumerate + access heats via the
    # dual-shape phase view so the same heat is analyzed on the legacy `ed` and the native `rt`.
    from cozer.phases import class_phase_map, phase_heat_ids
    from cozer.native import record_heat
    for cl, phase in class_phase_map(ed).items():
        for h in phase_heat_ids(phase):
            a1 = _canon(analyzer.analyze(h, copy.deepcopy(record_heat(ed, cl, h)), ss1))
            a2 = _canon(analyzer.analyze(h, copy.deepcopy(record_heat(rt, cl, h)), ss2))
            assert a1 == a2, (name, cl, h, "analyze changed under round-trip")

    for build in _BUILDS:
        assert _report_canon(build(ed)) == _report_canon(build(rt)), \
            (name, build.__name__, "report content changed under round-trip")


def test_sweep_sees_events():
    assert _EV, "no legacy events found -- fidelity sweep would pass vacuously"
