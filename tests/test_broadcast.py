"""Tests for cozer/app/broadcast.py — live-broadcast slugs & URLs (docs/broadcast-urls.md)."""
from datetime import datetime

from cozer.app import broadcast


def test_slugify():
    assert broadcast.slugify("Harku 2026") == "harku-2026"
    assert broadcast.slugify("  A  ") == "a"
    assert broadcast.slugify("F 500 / Finals!") == "f-500-finals"
    assert broadcast.slugify("_leading_underscore") == "leading-underscore"   # strips a leading _
    assert broadcast.slugify("dots.and.dashes--x") == "dots-and-dashes-x"
    assert broadcast.slugify("ÕÄÖÜ") == ""                # nothing usable -> "" (caller supplies default)
    assert broadcast.slugify("") == "" and broadcast.slugify(None) == ""


def test_is_slug():
    # exactly the server's route regex, so what cozer accepts is what the server routes
    assert broadcast.is_slug("0726") and broadcast.is_slug("harku-2026") and broadcast.is_slug("a")
    assert not broadcast.is_slug("Harku") and not broadcast.is_slug("_x")
    assert not broadcast.is_slug("-x") and not broadcast.is_slug("a b") and not broadcast.is_slug("")


def test_default_event_name():
    assert broadcast.default_event_name(datetime(2026, 7, 22)) == "0726"    # MMYY
    assert broadcast.default_event_name(datetime(2026, 12, 1)) == "1226"


def test_event_name_and_channel_defaults():
    assert broadcast.event_channel({}) == "a"
    assert broadcast.event_channel({"broadcast": {"channel": "b"}}) == "b"
    assert broadcast.event_name({"broadcast": {"eventname": "worlds"}}) == "worlds"
    assert broadcast.event_name({}) == broadcast.default_event_name()       # MMYY fallback, never blank
    assert broadcast.event_channel({"broadcast": {"channel": ""}}) == "a"   # empty -> default too


def test_set_broadcast_slugifies_and_defaults():
    ed = {}
    assert broadcast.set_broadcast(ed, "Harku 2026", "B") == ("harku-2026", "b")
    assert ed["broadcast"] == {"eventname": "harku-2026", "channel": "b"}
    en, ch = broadcast.set_broadcast(ed, "", "")                            # blank -> MMYY / 'a'
    assert en == broadcast.default_event_name() and ch == "a"


def test_feed_path_and_viewer_url():
    assert broadcast.feed_path("0726", "a") == "0726/feed/a"
    assert broadcast.viewer_url("https://live.cozer.ee/", "0726", "a") == "https://live.cozer.ee/0726/feed/a/"
    assert broadcast.viewer_url("https://live.cozer.ee", "worlds", "b") == "https://live.cozer.ee/worlds/feed/b/"


def test_server_url_defaults_to_live_cozer_ee():
    # issue #34: an unset / blank server URL resolves to the public default, so an operator only needs
    # a publish secret; a configured URL wins.
    assert broadcast.server_url(None) == "https://live.cozer.ee"
    assert broadcast.server_url({}) == "https://live.cozer.ee"
    assert broadcast.server_url({"live_server_url": "  "}) == "https://live.cozer.ee"
    assert broadcast.server_url({"live_server_url": "http://ex:8099"}) == "http://ex:8099"
