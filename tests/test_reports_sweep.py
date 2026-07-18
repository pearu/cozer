"""Regression sweep: build every report over every bundled legacy event.

The scoring core feeds nine reports, and a crash in analyze/sumanalyze or in the
report formatting only surfaces when a report is built over real data across all
classes and heats -- e.g. a boat that skipped a heat (KeyError in sumanalyze) or
an event with an empty scoring system (IndexError in analyze). Those exact bugs
were fixed in "Harden scoring core against missing-heat and empty-scoring
crashes"; this sweep builds the model + HTML for all nine reports over every
legacy .coz so the whole class of crash cannot regress silently.

HTML (not PDF) is built on purpose: it exercises the scoring + formatting code
where the crashes live, without the cost of WeasyPrint rendering.
"""
import glob
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import cozer.reports as R  # noqa: E402
from cozer.app.main import _REPORTS  # noqa: E402  (label, render_name, takes) x9
from cozer.store import read_legacy_coz  # noqa: E402


def _events():
    coz = sorted(glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")) +
                 glob.glob(os.path.join(REPO, "legacy", "cozer", "data", "*.coz")))
    return [(os.path.splitext(os.path.basename(p))[0], p) for p in coz]


_EVENTS = _events()


@pytest.mark.parametrize("name,path", _EVENTS, ids=[e[0] for e in _EVENTS])
def test_all_reports_build(name, path):
    """Every report builds a non-empty HTML document from every legacy event."""
    eventdata = read_legacy_coz(path)
    built = 0
    for _label, render_name, takes in _REPORTS:
        stem = render_name[len("render_"):]           # render_full_final -> full_final
        build = getattr(R, "build_" + stem)
        to_html = getattr(R, stem + "_html")
        model = build(eventdata, classes=None) if takes else build(eventdata)
        html = to_html(model)
        assert isinstance(html, str) and html.strip(), (name, stem, "empty HTML")
        built += 1
    assert built == len(_REPORTS)


def test_sweep_covers_all_events_and_reports():
    """Guard the guard: the sweep must actually see events and all nine reports."""
    assert _EVENTS, "no legacy .coz events found -- sweep would pass vacuously"
    assert len(_REPORTS) == 9, len(_REPORTS)
