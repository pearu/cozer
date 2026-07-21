"""Live ordering feed — the *unofficial* running order published during a race (LIVE.md, Phase 7).

Builds a small snapshot (the "machine feed", LIVE.md §4) and publishes it to a GitHub **Gist**,
reusing the ``crashreport`` GitHub client (OAuth token + ``_http``). Pure and headless-testable:
the caller (the Timer) supplies the leader-first boat order — e.g.
``[b["id"] for b in timer.standings(rec)]`` — so nothing here imports Qt.

Network errors are **not** swallowed here — the caller (Timer) guards them so a failed publish
never blocks timing (LIVE.md §5). Keeping this layer raise-on-error keeps it testable.
"""
import json

from cozer.app import crashreport
from cozer.classes import getclass
from cozer.racepattern import race_kind
from cozer.reports.common import nationalities_index, participants_index

GIST_FILE = "order.json"
# Default display config; the operator overrides it in cozer and it ships in the feed (LIVE.md §4).
DEFAULT_VIEW = {"page_size": 10, "top_dwell_s": 20, "page_dwell_s": 6}


def snapshot(eventdata, cl, heat, order, updated, view=None):
    """The unofficial live-order snapshot ``dict`` for class ``cl`` heat ``heat``.

    ``order``   — boat ids leader-first (from :func:`timer.standings`).
    ``updated`` — the publish timestamp (ISO-8601 string; the caller stamps it).
    ``view``    — the operator's display config (page size / dwell times); ``DEFAULT_VIEW`` if None.

    The ``order`` carries the **full** field; paging is the viewer's job (LIVE.md §7).
    """
    parts = participants_index(eventdata)
    nats = nationalities_index(eventdata)
    rows = []
    for i, bid in enumerate(order):
        _, last, _ = parts.get((cl, str(bid)), ("", "", ""))
        rows.append({"pos": i + 1, "boat": str(bid), "surname": last,
                     "nat": nats.get((cl, str(bid)), "")})
    return {
        "class": getclass(cl),
        "phase": race_kind(eventdata, cl),
        "heat": str(heat),
        "updated": updated,
        "unofficial": True,
        "view": dict(view) if view else dict(DEFAULT_VIEW),
        "order": rows,
    }


def _files_payload(snap):
    return {"files": {GIST_FILE: {"content": json.dumps(snap, ensure_ascii=False)}}}


def create_gist(token, snap, transport=None):
    """Create the live gist; return its id. Store the id (persistent, LIVE.md §6) and reuse it."""
    data = {"description": "cozer live order (unofficial)", "public": True}
    data.update(_files_payload(snap))
    _, resp = crashreport._http("POST", crashreport.GITHUB_API + "/gists",
                                token=token, data=data, transport=transport)
    return (resp or {}).get("id")


def update_gist(token, gist_id, snap, transport=None):
    """Overwrite the live gist's ``order.json`` with a new snapshot."""
    crashreport._http("PATCH", "%s/gists/%s" % (crashreport.GITHUB_API, gist_id),
                      token=token, data=_files_payload(snap), transport=transport)


def publish(token, gist_id, snap, transport=None):
    """Publish ``snap``: PATCH the existing gist, or create one (returning the new id) if ``gist_id``
    is falsy. Returns the gist id in use (so a first publish can be persisted)."""
    if gist_id:
        update_gist(token, gist_id, snap, transport=transport)
        return gist_id
    return create_gist(token, snap, transport=transport)
