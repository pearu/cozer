"""Tests for the live ordering feed (cozer/app/live.py, LIVE.md Phase 7)."""
import json

from cozer.app import live

ED = {
    "schema": 2,
    "classes": [{"name": "F 500", "phases": [{"kind": "circuit", "pattern": "1*(1000+2*1000):1"}]}],
    "participants": [
        ["", "Ann", "Tamm", "Club A", "F 500", "7", "EST"],
        ["", "Bo", "Ozols", "Club B", "F 500", "14", "LAT"],
        ["", "Cy", "Berg", "Club C", "F 500", "9", ""],        # no nationality set
    ],
    "record": {}, "races": [], "prevorder": {}, "savechecked": {},
}


class FakeTransport:
    """Records (method, url, headers, json-body) and returns a canned (status, json)."""
    def __init__(self, resp=None, status=200):
        self.calls = []
        self.resp = resp if resp is not None else {}
        self.status = status

    def __call__(self, method, url, headers, payload):
        body = json.loads(payload.decode("utf-8")) if payload else None
        self.calls.append((method, url, headers, body))
        return self.status, self.resp


def test_snapshot_shape():
    snap = live.snapshot(ED, "F 500", "2", ["7", "14", "9"], "2026-08-15T14:32:05Z")
    assert snap["class"] == "F 500"
    assert snap["phase"] == "circuit"
    assert snap["heat"] == "2"
    assert snap["updated"] == "2026-08-15T14:32:05Z"
    assert snap["unofficial"] is True
    assert snap["live"] is True
    assert snap["view"] == live.DEFAULT_VIEW and snap["view"] is not live.DEFAULT_VIEW  # a copy
    assert snap["order"] == [
        {"pos": 1, "boat": "7", "surname": "Tamm", "nat": "EST"},
        {"pos": 2, "boat": "14", "surname": "Ozols", "nat": "LAT"},
        {"pos": 3, "boat": "9", "surname": "Berg", "nat": ""},
    ]


def test_snapshot_custom_view_and_unknown_boat():
    view = {"page_size": 12, "top_dwell_s": 15, "page_dwell_s": 5}
    snap = live.snapshot(ED, "F 500", "1", ["7", "999"], "T", view=view)
    assert snap["view"] == view
    # an id not in participants -> blank surname/nat, still positioned
    assert snap["order"][1] == {"pos": 2, "boat": "999", "surname": "", "nat": ""}


def test_snapshot_standings_dicts_laps_time_and_started():
    # pass standings-style dicts -> laps/time/finished/laptimes flow through + started is derived
    order = [{"id": "7", "laps": 3, "time": 40.0, "finished": True, "laptimes": [15.0, 28.0, 40.0]},
             {"id": "14", "laps": 2, "time": 41.5, "finished": False},
             {"id": "9", "laps": 1, "time": 22.0}]
    snap = live.snapshot(ED, "F 500", "2", order, "T")
    assert snap["started"] is True
    assert snap["order"][0] == {"pos": 1, "boat": "7", "surname": "Tamm", "nat": "EST",
                                "laps": 3, "time": 40.0, "finished": True,
                                "laptimes": [15.0, 28.0, 40.0]}   # per-lap crossing times -> interval
    assert "finished" not in snap["order"][1]        # finished:False is omitted (only True flows)
    assert "laptimes" not in snap["order"][1]        # laptimes absent when the source omits it
    assert snap["order"][2]["laps"] == 1 and snap["order"][2]["time"] == 22.0


def test_snapshot_not_started_when_no_laps():
    order = [{"id": "7", "laps": 0, "time": 0.0}, {"id": "14", "laps": 0, "time": 0.0}]
    snap = live.snapshot(ED, "F 500", "1", order, "T")
    assert snap["started"] is False
    assert snap["order"][0]["laps"] == 0


def test_snapshot_scalar_ids_have_no_laps_and_not_started():
    snap = live.snapshot(ED, "F 500", "1", ["7", "14"], "T")   # back-compat scalar ids
    assert snap["started"] is False
    assert "laps" not in snap["order"][0] and "time" not in snap["order"][0]


def test_stopped_snapshot():
    snap = live.stopped(ED, "F 500", "2", "T")
    assert snap["live"] is False
    assert snap["order"] == []
    assert snap["class"] == "F 500" and snap["phase"] == "circuit"  # still identifies the heat


def test_publish_server_posts_snapshot_with_secret():
    snap = live.snapshot(ED, "F 500", "1", ["7"], "T")
    t = FakeTransport(status=200)
    # publish_server(base_url, eventname, channel, secret, snap) -> the feed path (docs/broadcast-urls.md)
    assert live.publish_server("https://live.cozer.ee/", "0726", "a", "s3cr3t", snap, transport=t) == "0726/feed/a"
    method, url, headers, body = t.calls[0]
    assert method == "POST" and url == "https://live.cozer.ee/_publish/0726/feed/a"   # trailing '/' stripped
    assert headers["X-Publish-Secret"] == "s3cr3t"                              # secret in the header
    assert body == snap                                                        # snapshot JSON is the body


def test_publish_server_raises_on_non_2xx():
    import pytest
    with pytest.raises(RuntimeError):
        live.publish_server("https://x", "e", "a", "bad", {"a": 1}, transport=FakeTransport(status=401))
