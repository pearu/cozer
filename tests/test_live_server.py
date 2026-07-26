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


def test_event_page_route(srv):
    # /<event>/ (and no trailing slash) is the public event page; it must not swallow the feed sub-paths,
    # the root, index.html, or any /_… path.
    assert srv.EVENT_RE.match("/harku/").group(1) == "harku"
    assert srv.EVENT_RE.match("/harku").group(1) == "harku"
    for p in ("/harku/feed/", "/harku/feed/a/", "/harku/feed/index.json",
              "/", "/index.html", "/_healthz", "/_flags/EST.svg", "/a/b/c"):
        assert srv.EVENT_RE.match(p) is None, p


def test_event_channels_are_sorted_so_the_event_page_picks_the_first(srv):
    # the event page follows the alphanumerically-FIRST channel; _event_channels returns them sorted,
    # so channels[0] is that first channel regardless of publish order.
    srv._store.clear()
    srv._store["harku/feed/c"] = (b"{}", srv.time.time())
    srv._store["harku/feed/a"] = (b"{}", srv.time.time())
    srv._store["harku/feed/b"] = (b"{}", srv.time.time())
    assert [c["channel"] for c in srv._event_channels("harku")] == ["a", "b", "c"]
    srv._store.clear()


def test_event_channels_report_viewer_count(srv):
    # each channel carries `viewers` = the number of currently-connected SSE streams (_subscribers),
    # which the event page shows as "👁 N" for the followed channel.
    srv._store.clear(); srv._subscribers.clear()
    srv._store["harku/feed/a"] = (b"{}", srv.time.time())
    srv._store["harku/feed/b"] = (b"{}", srv.time.time())
    srv._subscribers["harku/feed/a"] = {object(), object(), object()}   # 3 open streams on 'a'
    chans = {c["channel"]: c["viewers"] for c in srv._event_channels("harku")}
    assert chans == {"a": 3, "b": 0}                                    # b has no viewers
    srv._store.clear(); srv._subscribers.clear()


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
