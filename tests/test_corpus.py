"""Real-event corpus tests — real developer input, kept off the public build.

They run ONLY when the private events corpus (pearu/cozer-events) is checked out beside the cozer repo
(or at $COZER_EVENTS_DIR); on CI, where it isn't, they skip, so real driver data never touches the public
build. On a dev host they give full real-event coverage: every collected event must still open under the
current cozer and round-trip through the codec unchanged (a fixed point), which guards the .cozj format as
it evolves. Collect events with tools/collect_event.py.
"""
import glob
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from cozer.store import load_event, dump_event


def _corpus_dir():
    return os.environ.get("COZER_EVENTS_DIR") or os.path.join(REPO, "..", "cozer-events")


def _events():
    d = _corpus_dir()
    return sorted(glob.glob(os.path.join(d, "**", "*.cozj"), recursive=True)) if os.path.isdir(d) else []


_EVENTS = _events()
_needs_corpus = pytest.mark.skipif(
    not _EVENTS, reason="no events corpus (clone pearu/cozer-events beside cozer, or set COZER_EVENTS_DIR)")


@_needs_corpus
@pytest.mark.parametrize("path", _EVENTS, ids=[os.path.basename(p) for p in _EVENTS])
def test_corpus_event_opens_and_round_trips(path):
    # every real event still opens under the current cozer, and its serialized form is a FIXED POINT:
    # load -> dump -> load -> dump is byte-stable, so the codec preserves real data as the format evolves.
    ed = load_event(open(path, encoding="utf-8").read())
    dumped = dump_event(ed)
    assert dump_event(load_event(dumped)) == dumped
