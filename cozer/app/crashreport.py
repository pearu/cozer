"""Crash & bug reporting engine.

Layer 1 (always, offline-safe): capture any unhandled error into a local crash
report — traceback + context + a full event snapshot — so nothing is lost and
the program can keep running. Layer 2 (online, opt-in via a GitHub device-flow
login): auto-file the report as an issue on the cozer repo, labelled
``needs-triage`` and deduped by a traceback fingerprint.

All GitHub network calls go through an injectable ``transport`` so the logic is
unit-tested without touching the network. Uses only the standard library
(``urllib``), so it adds no dependency and never breaks an offline install.
"""
import base64
import hashlib
import json
import os
import platform
import sys
import time
import traceback

from cozer import __version__
from cozer.store import atomic_write, dumps, to_jsonable

REPO = "pearu/cozer"
# public_repo: file bug reports (issues) + push bug screenshots. gist: publish the live-order feed
# (LIVE.md) -- creating a gist needs its own scope, separate from repo access. Tokens issued before
# `gist` was added lack it, so the live feed asks such users to sign out and back in (see timer.py).
SCOPE = "public_repo gist"
LABEL = "needs-triage"
SCREENSHOT_BRANCH = "bug-screenshots"   # side branch that holds bug-report screenshots (off main)
# cozer's registered GitHub OAuth App (Device Flow). The client id is public and
# safe to ship; the flow needs no client secret. Overridable via env/config.
DEFAULT_CLIENT_ID = "Ov23lixGVzLMEmj1QaHv"
GITHUB_API = "https://api.github.com"
DEVICE_CODE_URL = "https://github.com/login/device/code"
DEVICE_TOKEN_URL = "https://github.com/login/oauth/access_token"
BODY_LIMIT = 60000       # keep the issue body under GitHub's ~65k-char cap


# --- config / paths ---------------------------------------------------------

def config_dir():
    override = os.environ.get("COZER_CONFIG_DIR")
    if override:
        base = override
    elif sys.platform.startswith("win"):
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "cozer")
    else:
        base = os.path.join(os.environ.get("XDG_CONFIG_HOME")
                            or os.path.join(os.path.expanduser("~"), ".config"), "cozer")
    os.makedirs(base, exist_ok=True)
    return base


def _config_path():
    return os.path.join(config_dir(), "config.json")


DEFAULT_CONFIG = {"token": None, "client_id": None, "auto_submit": True, "submitted": {}}


def load_config():
    try:
        with open(_config_path()) as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def save_config(cfg):
    atomic_write(_config_path(), json.dumps(cfg, indent=2).encode("utf-8"))


def client_id(cfg=None):
    return (os.environ.get("COZER_GITHUB_CLIENT_ID")
            or (cfg or load_config()).get("client_id") or DEFAULT_CLIENT_ID)


# --- report model -----------------------------------------------------------

def fingerprint(exc_type_name, tb):
    frames = traceback.extract_tb(tb) if tb is not None else []
    sig = exc_type_name + "|" + "|".join(
        "%s:%s" % (os.path.basename(f.filename), f.name) for f in frames[-6:])
    return hashlib.sha1(sig.encode("utf-8")).hexdigest()[:12]


def build_report(exc_type, exc, tb, eventdata=None, event_path=None, action=None, now=None):
    name = exc_type.__name__ if exc_type else "Error"
    return {
        "time": now if now is not None else time.time(),
        "cozer_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "action": action,
        "event_path": event_path,
        "exc_type": name,
        "exc_msg": str(exc) if exc is not None else "",
        "traceback": "".join(traceback.format_exception(exc_type, exc, tb)),
        "fingerprint": fingerprint(name, tb),
        "event": to_jsonable(eventdata),   # JSON-safe: legacy savechecked has tuple keys
    }


def build_user_report(description, eventdata=None, event_path=None, action=None, now=None):
    """A user-initiated bug report (no exception) — the current event is attached
    for reproduction, same as a crash."""
    text = (description or "").strip()
    return {
        "time": now if now is not None else time.time(),
        "cozer_version": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "action": action or "user bug report",
        "event_path": event_path,
        "exc_type": "BugReport",
        "exc_msg": (text.splitlines()[0][:80] if text else "(no description)"),
        "traceback": text,
        "fingerprint": hashlib.sha1(("bug|" + text).encode("utf-8")).hexdigest()[:12],
        "event": to_jsonable(eventdata),   # JSON-safe: legacy savechecked has tuple keys
    }


def _venue_tag(eventdata):
    eventdata = eventdata or {}
    date = (eventdata.get("date") or "").strip() or "?"
    venue = (eventdata.get("venue") or "").strip() or "?"
    return "%s/%s" % (date, venue.split(",")[0][:24])


def report_title(report):
    tag = _venue_tag(report.get("event"))
    msg = (report["exc_msg"] or "")[:80]
    if report["exc_type"] == "BugReport":
        return "[%s] Bug report: %s" % (tag, msg)
    return "[%s] Crash: %s: %s" % (tag, report["exc_type"], msg)


def report_body(report, screenshot_url=None):
    is_bug = report["exc_type"] == "BugReport"
    lines = [
        "User bug report from cozer." if is_bug else "Automated crash report from cozer.", "",
        "| field | value |", "|---|---|",
        "| cozer | %s |" % report["cozer_version"],
        "| python | %s |" % report["python"],
        "| platform | %s |" % report["platform"],
        "| action | %s |" % (report.get("action") or "—"),
        "| fingerprint | `%s` |" % report["fingerprint"], "",
        "### Description" if is_bug else "### Traceback",
        "```", report["traceback"].rstrip(), "```",
    ]
    ev = report.get("event")
    if ev is not None:
        try:
            js = dumps(ev)
        except Exception:        # pragma: no cover - event always serializes in practice
            js = None
        if js:
            note = ""
            if len(js) > BODY_LIMIT:
                js = js[:BODY_LIMIT]
                note = "\n_(truncated — full data is in the local crash file)_"
            lines += ["", "<details><summary>Event data (for reproduction)</summary>", "",
                      "```json", js, "```", "</details>" + note]
    if screenshot_url:                       # uploaded (B1) -> render it inline in the issue
        lines += ["", "### Screenshot", "", "![screenshot](%s)" % screenshot_url]
    elif report.get("screenshot"):
        # not uploaded: reference the local copy by basename only — never leak the reporter's
        # local filesystem path into a public issue.
        lines += ["", "_A GUI screenshot was saved next to the local report (`%s`); "
                  "attach it here if filing manually._" % os.path.basename(report["screenshot"])]
    lines += ["", "<!-- crash-fingerprint:%s -->" % report["fingerprint"]]
    return "\n".join(lines)


# --- local storage / offline queue ------------------------------------------

def crashes_dir(event_path=None):
    if event_path:
        d = os.path.join(os.path.dirname(os.path.abspath(event_path)), "cozer-crashes")
    else:
        d = os.path.join(config_dir(), "crashes")
    os.makedirs(d, exist_ok=True)
    return d


def write_local(report, event_path=None, screenshot=None):
    d = crashes_dir(event_path)
    stem = "crash-%d-%s" % (int(report["time"]), report["fingerprint"])
    if screenshot:                          # a GUI snapshot (PNG bytes) attached to the report
        report["screenshot"] = os.path.join(d, stem + ".png")
    path = os.path.join(d, stem + ".json")
    atomic_write(path, json.dumps(report, indent=2, default=str).encode("utf-8"))
    if screenshot:                          # JSON first, so a PNG-write failure can't lose the report
        atomic_write(report["screenshot"], screenshot)
    return path


def _queue_dir():
    d = os.path.join(config_dir(), "pending")
    os.makedirs(d, exist_ok=True)
    return d


def queue_pending(report):
    path = os.path.join(_queue_dir(), "%d-%s.json" % (int(report["time"]), report["fingerprint"]))
    atomic_write(path, json.dumps(report, default=str).encode("utf-8"))
    return path


def list_pending():
    d = _queue_dir()
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".json")]


# --- GitHub transport (urllib; injectable for tests) ------------------------

def _parse_body(body):
    """GitHub's login/oauth endpoints reply form-encoded unless asked for JSON;
    accept either so a token response is never silently missed."""
    if not body:
        return {}
    try:
        return json.loads(body)
    except ValueError:
        import urllib.parse
        return {k: v[0] for k, v in urllib.parse.parse_qs(body).items()}


def _urllib_transport(method, url, headers, data):     # pragma: no cover - real network
    import urllib.request
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, _parse_body(resp.read().decode("utf-8"))


def _http(method, url, token=None, data=None, transport=None, accept="application/vnd.github+json"):
    transport = transport or _urllib_transport
    headers = {"Accept": accept, "User-Agent": "cozer"}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return transport(method, url, headers, payload)


def device_start(cid, transport=None):
    import urllib.parse
    _, js = _http("POST", "%s?client_id=%s&scope=%s" % (DEVICE_CODE_URL, cid,
                  urllib.parse.quote(SCOPE)),      # SCOPE is now space-separated -> must be encoded
                  transport=transport, accept="application/json")
    return js       # device_code, user_code, verification_uri, interval, expires_in


def device_poll_once(cid, device_code, transport=None):
    url = ("%s?client_id=%s&device_code=%s&grant_type=urn:ietf:params:oauth:grant-type:device_code"
           % (DEVICE_TOKEN_URL, cid, device_code))
    _, js = _http("POST", url, transport=transport, accept="application/json")
    return js       # {access_token: ...} or {error: authorization_pending|slow_down|...}


def device_poll(cid, device_code, interval=5, timeout=300, transport=None,
                sleep=time.sleep, clock=time.monotonic):
    deadline = clock() + timeout
    while clock() < deadline:
        js = device_poll_once(cid, device_code, transport=transport)
        if js.get("access_token"):
            return js["access_token"]
        err = js.get("error")
        if err == "slow_down":
            interval += int(js.get("interval", 5))
        elif err not in ("authorization_pending", None):
            raise RuntimeError(err)
        sleep(interval)
    raise TimeoutError("device authorization timed out")


def github_login(token, transport=None):
    """The authenticated user's GitHub login name (for showing signed-in state)."""
    _, js = _http("GET", GITHUB_API + "/user", token=token, transport=transport)
    return js.get("login")


def search_fingerprint(token, fp, repo=REPO, transport=None):
    import urllib.parse
    q = 'repo:%s in:body "crash-fingerprint:%s"' % (repo, fp)
    _, js = _http("GET", GITHUB_API + "/search/issues?q=" + urllib.parse.quote(q),
                  token=token, transport=transport)
    items = js.get("items", [])
    return items[0]["html_url"] if items else None


def create_issue(token, title, body, repo=REPO, labels=(LABEL,), transport=None):
    _, js = _http("POST", GITHUB_API + "/repos/%s/issues" % repo, token=token,
                  data={"title": title, "body": body, "labels": list(labels)}, transport=transport)
    return js.get("html_url")


def _branch_sha(token, repo, branch, transport=None):
    """The head commit sha of ``branch``, or None if it doesn't exist (a 404 raises in the real
    urllib transport -> None)."""
    try:
        _, js = _http("GET", GITHUB_API + "/repos/%s/git/ref/heads/%s" % (repo, branch),
                      token=token, transport=transport)
    except Exception:
        return None
    return ((js or {}).get("object") or {}).get("sha")


def ensure_screenshot_branch(token, repo=REPO, branch=SCREENSHOT_BRANCH, transport=None):
    """Make sure the screenshot side branch exists (create it off the default branch if not).
    Returns True if it exists/was created."""
    if _branch_sha(token, repo, branch, transport):
        return True
    _, repo_js = _http("GET", GITHUB_API + "/repos/%s" % repo, token=token, transport=transport)
    base = _branch_sha(token, repo, (repo_js or {}).get("default_branch", "main"), transport)
    if not base:
        return False
    _http("POST", GITHUB_API + "/repos/%s/git/refs" % repo, token=token,
          data={"ref": "refs/heads/%s" % branch, "sha": base}, transport=transport)
    return True


def upload_screenshot(token, png_bytes, name, repo=REPO, branch=SCREENSHOT_BRANCH, transport=None):
    """Commit a screenshot PNG to the side branch and return a raw URL that renders inline in
    markdown (option B1). Returns None on any failure, so the caller falls back to a local-file
    note rather than losing the whole bug report."""
    if not ensure_screenshot_branch(token, repo, branch, transport):
        return None
    path = "screenshots/%s" % name
    _, js = _http("PUT", GITHUB_API + "/repos/%s/contents/%s" % (repo, path), token=token,
                  data={"message": "bug screenshot %s" % name, "branch": branch,
                        "content": base64.b64encode(png_bytes).decode("ascii")}, transport=transport)
    return ((js or {}).get("content") or {}).get("download_url") or \
        ("https://raw.githubusercontent.com/%s/%s/%s" % (repo, branch, path))


# --- orchestrator -----------------------------------------------------------

class Reporter:
    def __init__(self, config=None, transport=None):
        self.config = config if config is not None else load_config()
        self.transport = transport

    def logged_in(self):
        return bool(self.config.get("token"))

    def handle(self, report, event_path=None, online=True, screenshot=None):
        """Always write locally; auto-submit if logged-in + online + new, else
        queue for later. Returns the issue URL if filed, else None. Never raises."""
        try:
            write_local(report, event_path, screenshot)
        except Exception:        # a report-write failure must never propagate (it crashed the
            pass                 # bug-report flow when the event had tuple keys); submit anyway
        fp = report["fingerprint"]
        already = self.config.get("submitted", {}).get(fp)
        if already:
            return already
        if not (self.config.get("auto_submit") and self.logged_in() and online):
            queue_pending(report)
            return None
        try:
            return self._submit(report)
        except Exception:        # pragma: no cover - network hiccup -> keep it queued
            queue_pending(report)
            return None

    def _submit(self, report):
        fp = report["fingerprint"]
        known = self.config.get("submitted", {}).get(fp)
        if known:
            return known         # already filed this fingerprint -> trust our local record,
                                 # not GitHub search (which lags: a just-created issue isn't
                                 # searchable for seconds, so draining N same-fp queued reports
                                 # would otherwise create N duplicate issues)
        token = self.config["token"]
        url = search_fingerprint(token, fp, transport=self.transport)
        if not url:
            url = create_issue(token, report_title(report),
                               report_body(report, screenshot_url=self._upload_shot(report, token)),
                               transport=self.transport)
        self.config.setdefault("submitted", {})[fp] = url
        save_config(self.config)
        return url

    def _upload_shot(self, report, token):
        """Upload the report's local screenshot (if any) for inline embedding; return its URL or
        None. A failure here must never block filing the bug report, so it degrades to the local
        note rather than propagating."""
        spath = report.get("screenshot")
        if not spath or not os.path.exists(spath):
            return None
        try:
            with open(spath, "rb") as f:
                return upload_screenshot(token, f.read(), os.path.basename(spath),
                                         transport=self.transport)
        except Exception:        # pragma: no cover - network hiccup -> fall back to the local note
            return None

    def submit_pending(self, online=True):
        if not (self.logged_in() and online):
            return []
        done = []
        for path in list_pending():
            try:
                with open(path) as f:
                    report = json.load(f)
                done.append(self._submit(report))
                os.remove(path)
            except Exception:    # pragma: no cover - best-effort drain
                pass
        return done
