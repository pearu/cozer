#!/usr/bin/env python3
"""cozer live-order server -- the self-hosted transport for the Phase-7 live feed.

Replaces the GitHub gist (which was ~60 s stale on its raw path). cozer POSTs a snapshot per channel;
viewers GET the latest. Fresh (viewers poll every few seconds and always see the newest), no rate
limit, no token in any URL. Fronted by Caddy (HTTPS via Let's Encrypt) at https://live.cozer.ee/.

Endpoints
  POST /publish/<channel>   operator -> store the latest snapshot for <channel>. Auth: the shared
                            secret in the `X-Publish-Secret` header (== env PUBLISH_SECRET). Body is
                            the snapshot JSON. -> {"ok": true}
  GET  /live/<channel>.json viewers -> the latest snapshot JSON (public, read-only, CORS: *). 404 if
                            the channel has nothing yet.
  GET  /healthz             -> "ok" (liveness).

Config (env): PUBLISH_SECRET (required), PORT (default 8099), BIND (default 127.0.0.1).
Stdlib only; binds localhost -- Caddy is the only internet-facing process. Snapshots are held in
memory (a restart drops them; cozer re-publishes on the next tick, so the feed self-heals).
"""
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
CHANNEL_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
FLAG_RE = re.compile(r"^/flags/([A-Za-z0-9_-]{1,16}\.svg)$")
# Static web root -- the viewer + flags, so live.cozer.ee/?channel=X serves the overlay same-origin.
WEB_ROOT = os.environ.get("WEB_ROOT", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs"))

_store = {}                                # channel -> (json_bytes, updated_epoch)
_subscribers = {}                          # channel -> set of queue.Queue (open SSE streams)
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

    def _serve_static(self, relpath, ctype, cache="no-store"):
        full = os.path.normpath(os.path.join(WEB_ROOT, relpath))
        root = os.path.normpath(WEB_ROOT)
        if full != root and not full.startswith(root + os.sep):   # path-traversal guard
            return self._json(400, {"error": "bad path"})
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            return self._json(404, {"error": "not found"})
        return self._send(200, data, ctype, cache=cache)

    def log_message(self, fmt, *args):     # route through _log (journald), not stderr
        _log("%s - %s" % (self.address_string(), fmt % args))

    # --- GET: viewers read the latest snapshot -----------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]         # self.path includes the query (e.g. /?channel=X)
        if path == "/healthz":
            return self._send(200, b"ok", "text/plain")
        if path in ("/", "/index.html", "/live-viewer.html"):          # the viewer overlay
            return self._serve_static("live-viewer.html", "text/html; charset=utf-8")
        if path == "/favicon.ico":
            return self._send(204)
        mflag = FLAG_RE.match(path)
        if mflag:                                                      # a bundled flag SVG
            return self._serve_static("flags/" + mflag.group(1), "image/svg+xml",
                                      cache="public, max-age=86400")
        mstream = re.match(r"^/stream/([^/]+)$", path)
        if mstream:                                                    # SSE push (sub-second)
            return self._sse(mstream.group(1))
        m = re.match(r"^/live/([^/]+)\.json$", path)
        if not m:
            return self._json(404, {"error": "not found"})
        channel = m.group(1)
        if not CHANNEL_RE.match(channel):
            return self._json(400, {"error": "bad channel"})
        with _lock:
            entry = _store.get(channel)
        if entry is None:
            return self._json(404, {"error": "no data for channel", "channel": channel})
        return self._send(200, entry[0])

    def do_HEAD(self):
        self.do_GET()                              # same routing/headers; _send drops the body for HEAD

    def _sse(self, channel):
        """Server-Sent Events: push each new snapshot for <channel> the instant it's published, so the
        viewer updates sub-second (LIVE.md §8). Chunked HTTP/1.1; one thread per open stream. Sends the
        current snapshot immediately, then blocks on a per-stream queue that publish() feeds."""
        if not CHANNEL_RE.match(channel):
            return self._json(400, {"error": "bad channel"})
        q = queue.Queue(maxsize=8)
        with _lock:
            _subscribers.setdefault(channel, set()).add(q)
            current = _store.get(channel)
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
                subs = _subscribers.get(channel)
                if subs:
                    subs.discard(q)
                    if not subs:
                        _subscribers.pop(channel, None)

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
        m = re.match(r"^/publish/([^/]+)$", self.path.split("?", 1)[0])
        if not m:
            return self._json(404, {"error": "not found"})
        channel = m.group(1)
        if not CHANNEL_RE.match(channel):
            return self._json(400, {"error": "bad channel"})
        if not SECRET or self.headers.get("X-Publish-Secret", "") != SECRET:
            return self._json(401, {"error": "unauthorized"})
        try:
            json.loads(body.decode("utf-8"))       # validate it's JSON (store the raw bytes)
        except Exception:
            return self._json(400, {"error": "body is not valid JSON"})
        with _lock:
            _store[channel] = (body, time.time())
            subs = list(_subscribers.get(channel, ()))
        for sub in subs:                           # push to open SSE streams (sub-second)
            try:
                sub.put_nowait(body)
            except queue.Full:                     # slow client -> drop; it gets the next/current on reconnect
                pass
        _log("publish %s (%d bytes) -> %d stream(s)" % (channel, len(body), len(subs)))
        return self._json(200, {"ok": True, "channel": channel, "bytes": len(body)})


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
