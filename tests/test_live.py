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
    # pass standings-style dicts -> laps/time flow through + started is derived
    order = [{"id": "7", "laps": 2, "time": 40.0}, {"id": "14", "laps": 2, "time": 41.5},
             {"id": "9", "laps": 1, "time": 22.0}]
    snap = live.snapshot(ED, "F 500", "2", order, "T")
    assert snap["started"] is True
    assert snap["order"][0] == {"pos": 1, "boat": "7", "surname": "Tamm", "nat": "EST",
                                "laps": 2, "time": 40.0}
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


def test_create_gist_returns_id_and_posts_order_file():
    t = FakeTransport(resp={"id": "abc123"})
    snap = live.snapshot(ED, "F 500", "1", ["7"], "T")
    assert live.create_gist("tok", snap, transport=t) == "abc123"
    method, url, headers, body = t.calls[0]
    assert method == "POST" and url.endswith("/gists")
    assert headers["Authorization"] == "Bearer tok"
    assert body["public"] is True and body["description"]
    content = json.loads(body["files"]["order.json"]["content"])
    assert content["class"] == "F 500" and content["order"][0]["surname"] == "Tamm"


def test_update_gist_patches_by_id():
    t = FakeTransport()
    snap = live.snapshot(ED, "F 500", "1", ["7"], "T")
    live.update_gist("tok", "gid9", snap, transport=t)
    method, url, _headers, body = t.calls[0]
    assert method == "PATCH" and url.endswith("/gists/gid9")
    assert "order.json" in body["files"]


def test_publish_updates_when_id_else_creates():
    snap = live.snapshot(ED, "F 500", "1", ["7"], "T")
    t1 = FakeTransport()
    assert live.publish("tok", "g1", snap, transport=t1) == "g1"
    assert t1.calls[0][0] == "PATCH"
    t2 = FakeTransport(resp={"id": "new9"})
    assert live.publish("tok", None, snap, transport=t2) == "new9"
    assert t2.calls[0][0] == "POST"
