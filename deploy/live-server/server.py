#!/usr/bin/env python3
"""cozer live-order server -- the self-hosted transport for the Phase-7 live feed.

Replaces the GitHub gist (which was ~60 s stale on its raw path). cozer POSTs a snapshot per channel;
viewers GET the latest. Fresh (viewers poll every few seconds and always see the newest), no rate
limit, no token in any URL. Fronted by Caddy (HTTPS via Let's Encrypt) at https://live.cozer.ee/.

Endpoints (path model -- see docs/broadcast-urls.md)
  GET  /<event>/feed/<channel>/           the viewer overlay (HTML)
  GET  /<event>/feed/<channel>/data.json  the latest snapshot (public, read-only, CORS *); 404 if none
  GET  /<event>/feed/<channel>/stream     Server-Sent Events -- pushes each snapshot (sub-second)
  POST /_publish/<event>/feed/<channel>   store a snapshot. Auth: X-Publish-Secret == env PUBLISH_SECRET
  GET  /_flags/<IOC>.svg                  bundled flag SVG (shared).    GET /_healthz  ->  "ok"

Config (env): PUBLISH_SECRET (required), PORT (default 8099), BIND (default 127.0.0.1).
Stdlib only; binds localhost -- Caddy is the only internet-facing process. Snapshots are held in
memory (a restart drops them; cozer re-publishes on the next tick, so the feed self-heals).
"""
import hmac
import json
import os
import queue
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECRET = os.environ.get("PUBLISH_SECRET", "")
PORT = int(os.environ.get("PORT", "8099"))
BIND = os.environ.get("BIND", "127.0.0.1")
MAX_BODY = 256 * 1024                      # snapshots are tiny; cap to refuse abuse
MAX_STREAMS = int(os.environ.get("MAX_STREAMS", "200"))   # global SSE cap -> 503 past it (thread-flood
                                                          # guard; each open /stream holds one thread)
# eventname / channel: strict lowercase slugs -- can't start with '_' (never collide with /_… paths)
# and no dots/uppercase (never look like /favicon.ico etc.). See docs/broadcast-urls.md.
_SLUG = r"[a-z0-9][a-z0-9-]{0,62}"
FLAG_RE = re.compile(r"^/_flags/([A-Za-z0-9_-]{1,16}\.svg)$")             # shared bundled flags
FEED_RE = re.compile(r"^/(%s)/feed/(%s)/?$" % (_SLUG, _SLUG))             # the viewer overlay
FEED_DATA_RE = re.compile(r"^/(%s)/feed/(%s)/data\.json$" % (_SLUG, _SLUG))
FEED_STREAM_RE = re.compile(r"^/(%s)/feed/(%s)/stream$" % (_SLUG, _SLUG))
PUBLISH_RE = re.compile(r"^/_publish/(%s)/feed/(%s)$" % (_SLUG, _SLUG))
# Static web root -- the viewer + flags, so live.cozer.ee/<event>/feed/<channel>/ serves the overlay.
WEB_ROOT = os.environ.get("WEB_ROOT", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs"))


def _feed_key(event, channel):
    return "%s/feed/%s" % (event, channel)    # internal store/subscriber key for a live feed


_store = {}                                # <event>/feed/<channel> key -> (json_bytes, updated_epoch)
_subscribers = {}                          # <event>/feed/<channel> key -> set of queue.Queue (open SSE)
_open_streams = [0]                         # count of live SSE streams (capped at MAX_STREAMS)
_lock = threading.Lock()


def _log(msg):
    sys.stdout.write("[cozer-live] %s\n" % msg)
    sys.stdout.flush()


class Handler(BaseHTTPRequestHandler):
    server_version = "cozer-live/1.0"
    protocol_version = "HTTP/1.1"

    def _send(self, code, body=b"", ctype="application/json", cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")   # public read-only
        self.send_header("Cache-Control", cache)
        self.end_headers()
        if body and self.command != "HEAD":       # HEAD: send headers (incl. Content-Length) only
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _serve_static(self, relpath, ctype, cache="no-store", code=200):
        full = os.path.normpath(os.path.join(WEB_ROOT, relpath))
        root = os.path.normpath(WEB_ROOT)
        if full != root and not full.startswith(root + os.sep):   # path-traversal guard
            return self._json(400, {"error": "bad path"})
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            return self._json(404, {"error": "not found"})
        return self._send(code, data, ctype, cache=cache)

    def log_message(self, fmt, *args):     # route through _log (journald), not stderr
        _log("%s - %s" % (self.address_string(), fmt % args))

    # --- GET: viewers read the latest snapshot -----------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]         # self.path includes the query string
        if path == "/_healthz":
            return self._send(200, b"ok", "text/plain")
        if path == "/favicon.ico":
            return self._send(204)
        mflag = FLAG_RE.match(path)
        if mflag:                                                      # /_flags/<IOC>.svg (shared)
            return self._serve_static("flags/" + mflag.group(1), "image/svg+xml",
                                      cache="public, max-age=86400")
        if path in ("/", "/index.html") or FEED_RE.match(path):        # the viewer overlay
            return self._serve_static("live-viewer.html", "text/html; charset=utf-8")
        md = FEED_DATA_RE.match(path)
        if md:                                                         # the feed's latest snapshot
            with _lock:
                entry = _store.get(_feed_key(md.group(1), md.group(2)))
            if entry is None:
                return self._json(404, {"error": "no data yet"})
            return self._send(200, entry[0])
        ms = FEED_STREAM_RE.match(path)
        if ms:                                                         # SSE push (sub-second)
            return self._sse(_feed_key(ms.group(1), ms.group(2)))
        # Unknown GET path (e.g. /aaa, a mistyped or non-existent event) -> the neutral COZER landing
        # (HTML), not raw JSON, so a person who opens a wrong link sees a page. 404 keeps it honest.
        return self._serve_static("live-viewer.html", "text/html; charset=utf-8", code=404)

    def do_HEAD(self):
        self.do_GET()                              # same routing/headers; _send drops the body for HEAD

    def _sse(self, key):
        """Server-Sent Events: push each new snapshot for feed ``key`` (``<event>/feed/<channel>``,
        already route-validated) the instant it's published, so the viewer updates sub-second
        (LIVE.md §8). Chunked HTTP/1.1; one thread per open stream. Sends the current snapshot
        immediately, then blocks on a per-stream queue that publish() feeds."""
        if self.command == "HEAD":             # HEAD: advertise the stream headers, no body/no thread
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            return
        q = queue.Queue(maxsize=8)
        with _lock:
            over = _open_streams[0] >= MAX_STREAMS     # thread-flood guard (each stream holds a thread)
            if not over:
                _open_streams[0] += 1
                _subscribers.setdefault(key, set()).add(q)
                current = _store.get(key)
        if over:                               # at capacity -> the viewer falls back to polling data.json
            return self._json(503, {"error": "the live server is at capacity — try again shortly"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")           # ask proxies not to buffer
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self.close_connection = True                          # this connection IS the stream

        def chunk(b):
            self.wfile.write(b"%X\r\n" % len(b) + b + b"\r\n")
            self.wfile.flush()

        def event(body):
            chunk(b"".join(b"data: " + ln + b"\n" for ln in body.split(b"\n")) + b"\n")

        try:
            chunk(b": connected\n\n")
            if current:
                event(current[0])                            # a fresh viewer isn't blank
            while True:
                try:
                    data = q.get(timeout=15)
                except queue.Empty:
                    chunk(b": keepalive\n\n")                 # heartbeat -> surfaces a dead peer
                    continue
                event(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass                                             # the client went away
        finally:
            with _lock:
                _open_streams[0] -= 1
                subs = _subscribers.get(key)
                if subs:
                    subs.discard(q)
                    if not subs:
                        _subscribers.pop(key, None)

    # --- POST: operator publishes a snapshot -------------------------------------------------------
    def do_POST(self):
        # Read (drain) the body FIRST, before any early return -- otherwise an unread body would
        # corrupt the next request on a kept-alive connection (HTTP/1.1). Cap the size; close the
        # connection on an oversized body rather than trying to drain it.
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self.close_connection = True
            return self._json(413, {"error": "bad or too-large body"})
        body = self.rfile.read(n) if n else b""
        m = PUBLISH_RE.match(self.path.split("?", 1)[0])       # /_publish/<event>/feed/<channel>
        if not m:
            return self._json(404, {"error": "not found"})
        if not SECRET or not hmac.compare_digest(self.headers.get("X-Publish-Secret", ""), SECRET):
            return self._json(401, {"error": "unauthorized"})   # constant-time compare
        try:
            json.loads(body.decode("utf-8"))       # validate it's JSON (store the raw bytes)
        except Exception:
            return self._json(400, {"error": "body is not valid JSON"})
        key = _feed_key(m.group(1), m.group(2))
        with _lock:
            _store[key] = (body, time.time())
            subs = list(_subscribers.get(key, ()))
        for sub in subs:                           # push to open SSE streams (sub-second)
            try:
                sub.put_nowait(body)
            except queue.Full:                     # slow client -> drop; it gets the next/current on reconnect
                pass
        _log("publish %s (%d bytes) -> %d stream(s)" % (key, len(body), len(subs)))
        return self._json(200, {"ok": True, "channel": key, "bytes": len(body)})


def main():
    if not SECRET:
        _log("REFUSING TO START: PUBLISH_SECRET is not set (nobody could publish).")
        return 2
    httpd = ThreadingHTTPServer((BIND, PORT), Handler)
    _log("listening on %s:%d (publish needs the shared secret; GET is public)" % (BIND, PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
