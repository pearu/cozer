"""Routing + channel-index logic for the self-hosted live server (deploy/live-server/server.py).

The server is a standalone script (not part of the cozer package), so it is loaded from its path. These
tests cover the issue-#34 channel switcher: the /<event>/feed/ + index.json routes and the derivation of
an event's live channels from what has been published (no separate registration)."""
import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRV = os.path.join(REPO, "deploy", "live-server", "server.py")


@pytest.fixture(scope="module")
def srv():
    spec = importlib.util.spec_from_file_location("cozer_live_server", _SRV)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_feed_index_and_root_routes(srv):
    # the switcher page + its channel-list JSON, distinct from the per-channel overlay/data routes
    assert srv.FEED_INDEX_RE.match("/harku/feed/index.json").group(1) == "harku"
    assert srv.FEED_ROOT_RE.match("/harku/feed/").group(1) == "harku"
    assert srv.FEED_ROOT_RE.match("/harku/feed").group(1) == "harku"        # trailing slash optional
    # the switcher root must NOT swallow a real channel overlay, and index.json is not a channel
    assert srv.FEED_ROOT_RE.match("/harku/feed/a/") is None
    assert srv.FEED_RE.match("/harku/feed/index.json") is None              # 'index.json' isn't a slug
    assert srv.FEED_RE.match("/harku/feed/") is None                       # overlay needs a channel
    assert srv.FEED_DATA_RE.match("/harku/feed/index.json") is None


def test_event_channels_derived_from_store(srv):
    srv._store.clear()
    srv._store["harku/feed/a"] = (b"{}", srv.time.time())
    srv._store["harku/feed/b"] = (b"{}", srv.time.time() - 45)              # older publish
    srv._store["other/feed/a"] = (b"{}", srv.time.time())                   # a different event
    chans = srv._event_channels("harku")
    assert [c["channel"] for c in chans] == ["a", "b"]                      # this event only, sorted
    ages = {c["channel"]: c["age_s"] for c in chans}
    assert ages["a"] < 5 and ages["b"] >= 44                               # age = seconds since publish
    assert srv._event_channels("missing") == []
    srv._store.clear()
