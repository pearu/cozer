"""Live ordering feed — the *unofficial* running order published during a race (LIVE.md, Phase 7).

Builds a small snapshot (the "machine feed", LIVE.md §4) and publishes it to the self-hosted live
server (deploy/live-server, ``https://live.cozer.ee/``). Pure and headless-testable: the caller (the
Timer) supplies the leader-first boat order — e.g. ``timer.standings(rec)`` — so nothing here
imports Qt.

Network errors are **not** swallowed here — the caller (Timer) guards them so a failed publish
never blocks timing (LIVE.md §5). Keeping this layer raise-on-error keeps it testable.
"""
import json

from cozer.app.broadcast import feed_path        # light, shared with the Timer / Reports settings
from cozer.classes import getclass
from cozer.racepattern import race_kind
from cozer.reports.common import nationalities_index, participants_index

# Default display config; the operator overrides it in cozer and it ships in the feed (LIVE.md §4).
DEFAULT_VIEW = {"page_size": 10, "top_dwell_s": 20, "page_dwell_s": 6, "poll_s": 0.5}


def snapshot(eventdata, cl, heat, order, updated, view=None, live=True):
    """The unofficial live-order snapshot ``dict`` for class ``cl`` heat ``heat``.

    ``order`` — leader-first, one item per boat. Each item is either a **boat id** (scalar) or a
    **standings dict** ``{"id"|"boat", "laps", "time"}`` (pass ``timer.standings(rec)`` directly).
    When laps/time are present they flow into the feed so the viewer can show laps-completed + the
    time gap to the boat one place ahead, and switch from the pre-start (nat/boat/surname) layout to
    the running layout once the field has started.
    ``updated`` — the publish timestamp (ISO-8601 string; the caller stamps it).
    ``view``    — the operator's display config (page size / dwell times); ``DEFAULT_VIEW`` if None.

    The ``order`` carries the **full** field; paging is the viewer's job (LIVE.md §7).
    """
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    rows, started = [], False
    for i, item in enumerate(order):
        bid = item.get("id", item.get("boat")) if isinstance(item, dict) else item
        _, last, _ = parts.get((cl, str(bid)), ("", "", ""))
        row = {"pos": i + 1, "boat": str(bid), "surname": last,
               "nat": nats.get((cl, str(bid)), "")}
        if isinstance(item, dict):
            if item.get("laps") is not None:
                row["laps"] = item["laps"]
                if item["laps"] >= 1:
                    started = True
            if item.get("time") is not None:
                row["time"] = item["time"]          # cumulative seconds at the last crossing
        rows.append(row)
    return {
        "class": getclass(cl),
        "phase": race_kind(eventdata, cl),
        "heat": str(heat),
        "updated": updated,
        "unofficial": True,
        "live": live,
        "started": started,                          # any boat has completed >=1 lap
        "view": dict(view) if view else dict(DEFAULT_VIEW),
        "order": rows,
    }


def stopped(eventdata, cl, heat, updated, view=None):
    """A "broadcast off" snapshot — empty ``order`` + ``live: False`` — published when the operator
    unticks, so the viewer shows a "live stream disabled" state instead of stale positions."""
    return snapshot(eventdata, cl, heat, [], updated, view=view, live=False)


def _http_post(method, url, headers, data):        # pragma: no cover - real network
    import urllib.request
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status, resp.read()


def publish_server(base_url, eventname, channel, secret, snap, transport=None):
    """Publish ``snap`` to the self-hosted live server: POST the snapshot JSON to
    ``<base_url>/_publish/<eventname>/feed/<channel>`` with the shared secret in the
    ``X-Publish-Secret`` header (docs/broadcast-urls.md). Fresh, no token in any URL, no rate limit.
    ``transport(method, url, headers, data)`` is injectable for tests. Raises on a non-2xx or network
    error (the Timer guards it)."""
    url = "%s/_publish/%s" % (base_url.rstrip("/"), feed_path(eventname, channel))
    body = json.dumps(snap, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Publish-Secret": secret, "User-Agent": "cozer"}
    status, _ = (transport or _http_post)("POST", url, headers, body)
    if not 200 <= (status or 0) < 300:
        raise RuntimeError("live server publish failed: HTTP %s" % status)
    return feed_path(eventname, channel)
