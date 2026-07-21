"""Live-broadcast identifiers & URLs (docs/broadcast-urls.md) — the light, Qt-free helpers shared by
the Timer, the Reports settings, and the publish path (cozer/app/live.py).

Kept deliberately import-cheap (only ``re`` + ``datetime``): the GUI thread builds viewer links and
validates slugs through here without pulling in the report stack (weasyprint), which ``live.py`` does.

The *storage split* (docs/broadcast-urls.md §3): the **event name + channel live in the event** (they
travel with the .coz, so a different event → a different URL → no multi-instance clash), while the
server URL + publish secret live in cozer config (the secret must NEVER reach the .coz — its content
is embedded verbatim in bug reports).
"""
import re
from datetime import datetime

DEFAULT_CHANNEL = "a"
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def slugify(text):
    """Coerce free text to a broadcast slug: lowercase; spaces/underscores/dots → hyphens; drop
    anything else; collapse and trim hyphens. Returns ``""`` if nothing usable survives (the caller
    supplies a default). E.g. ``"Harku 2026"`` → ``"harku-2026"``, ``"A"`` → ``"a"``, ``"_x"`` → ``"x"``."""
    s = re.sub(r"[\s_.]+", "-", (text or "").strip().lower())
    s = re.sub(r"[^a-z0-9-]+", "", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def is_slug(text):
    """True if ``text`` is already a valid slug (``^[a-z0-9][a-z0-9-]*$``) — matches the server's route
    regex, so what cozer accepts is exactly what the server will route."""
    return bool(_SLUG_RE.match(text or ""))


def default_event_name(now=None):
    """The default broadcast name when the organizers haven't picked one: the current month+year
    digits, e.g. July 2026 → ``"0726"`` (docs/broadcast-urls.md §1). ``now`` is injectable for tests."""
    return (now or datetime.now()).strftime("%m%y")


def event_name(eventdata):
    """The broadcast event name stored in the event, or the ``MMYY`` default (never blank)."""
    b = (eventdata or {}).get("broadcast") or {}
    return b.get("eventname") or default_event_name()


def event_channel(eventdata):
    """The broadcast channel stored in the event, or the ``"a"`` default (never blank)."""
    b = (eventdata or {}).get("broadcast") or {}
    return b.get("channel") or DEFAULT_CHANNEL


def set_broadcast(eventdata, eventname, channel):
    """Store the (slugified) event name + channel in the event. Blank input → the default. Returns the
    ``(eventname, channel)`` actually stored so the caller can echo the normalized values back."""
    en = slugify(eventname) or default_event_name()
    ch = slugify(channel) or DEFAULT_CHANNEL
    eventdata.setdefault("broadcast", {})
    eventdata["broadcast"]["eventname"] = en
    eventdata["broadcast"]["channel"] = ch
    return en, ch


def feed_path(eventname, channel):
    """A feed's path segment: ``<eventname>/feed/<channel>`` (docs/broadcast-urls.md §2)."""
    return "%s/feed/%s" % (eventname, channel)


def viewer_url(base_url, eventname, channel):
    """The public viewer URL for a feed: ``<base_url>/<eventname>/feed/<channel>/``."""
    return "%s/%s/" % ((base_url or "").rstrip("/"), feed_path(eventname, channel))
