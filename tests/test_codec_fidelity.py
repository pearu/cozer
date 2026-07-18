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


@pytest.mark.parametrize("name,path", _EV, ids=[e[0] for e in _EV])
def test_roundtrip_preserves_analysis_and_reports(name, path):
    ed = store.read_legacy_coz(path)
    rt = store.loads(store.dumps(ed))                     # legacy -> save -> reopen
    assert store.dumps(rt) == store.dumps(store.loads(store.dumps(rt)))   # codec idempotent

    ss1, ss2 = ed.get("scoringsystem", []), rt.get("scoringsystem", [])
    for cl in ed.get("record", {}):
        for h in ed["record"][cl]:
            a1 = _canon(analyzer.analyze(h, copy.deepcopy(ed["record"][cl][h]), ss1))
            a2 = _canon(analyzer.analyze(h, copy.deepcopy(rt["record"][cl][h]), ss2))
            assert a1 == a2, (name, cl, h, "analyze changed under round-trip")

    for build in _BUILDS:
        assert _canon(build(ed)) == _canon(build(rt)), \
            (name, build.__name__, "report model changed under round-trip")


def test_sweep_sees_events():
    assert _EV, "no legacy events found -- fidelity sweep would pass vacuously"
