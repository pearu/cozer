"""Report-content property tests: internal-consistency invariants that hold for
every report over every bundled legacy event, regardless of formatting -- these
catch bugs a "builds without crashing" sweep and the analyze-level differential
goldens can miss.

Per class table in the Full/Short Final and Intermediate reports:
- no boat appears in two rows;
- scored places are strictly increasing (unique + ascending -- NOT necessarily
  contiguous: legacy leaves a gap when an unscored boat led the field on the
  water, e.g. Liepaja F-2 heat 3 places [2, 3] with the fastest boat unscored);
- every footnote reference in a result cell resolves to a legend definition.
"""
import glob
import os
import re
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cozer import store  # noqa: E402
from cozer.reports.final import build_full_final, build_short_final  # noqa: E402
from cozer.reports.intermediate import build_intermediate  # noqa: E402

_REPORTS = [("full_final", build_full_final),
            ("short_final", build_short_final),
            ("intermediate", build_intermediate)]


def _events():
    coz = sorted(glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")) +
                 glob.glob(os.path.join(REPO, "legacy", "cozer", "data", "*.coz")))
    return [(os.path.splitext(os.path.basename(p))[0], p) for p in coz]


_EV = _events()


def _sups(s):
    return set(re.findall(r"<sup>(\d+)</sup>", s or ""))


@pytest.mark.parametrize("name,path", _EV, ids=[e[0] for e in _EV])
def test_report_model_invariants(name, path):
    ed = store.read_legacy_coz(path)
    for label, build in _REPORTS:
        model = build(ed)
        for t in model["tables"]:
            ctx = (name, label, t["class"])
            ids = [r["id"] for r in t["rows"]]
            assert len(ids) == len(set(ids)), (ctx, "duplicate boat rows", ids)

            places = [int(r["place"]) for r in t["rows"] if r.get("place")]
            assert all(places[i] < places[i + 1] for i in range(len(places) - 1)), \
                (ctx, "places not strictly increasing", places)

            refs = set()
            for r in t["rows"]:
                for hc in r.get("heats", []):
                    refs |= _sups(hc.get("result"))
                refs |= _sups(r.get("result"))          # intermediate rows carry the cell here
            defs = _sups(t.get("legend"))
            assert refs <= defs, (ctx, "dangling footnote refs", sorted(refs - defs))


def test_sweep_sees_events():
    assert _EV, "no legacy events found -- property sweep would pass vacuously"
