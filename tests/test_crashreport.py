"""Unit tests for the crash/bug-reporting engine — no network, via a fake transport."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cozer.app.crashreport as cr


def _boom():
    def inner():
        raise ValueError("kaboom")
    inner()


def _report(action="Timer", event=None):
    try:
        _boom()
    except ValueError:
        et, ev, tb = sys.exc_info()
        return cr.build_report(et, ev, tb, eventdata=event, event_path=None, action=action, now=1000)


def _cfg(tmp, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)


class FakeGitHub:
    """Records requests; returns canned issue/search/device responses."""
    def __init__(self, existing=None):
        self.calls = []
        self.existing = existing
        self.created = []

    def __call__(self, method, url, headers, data):
        self.calls.append((method, url))
        body = json.loads(data) if data else {}
        if "/search/issues" in url:
            return 200, {"items": ([{"html_url": self.existing}] if self.existing else [])}
        if url.endswith("/issues"):
            n = len(self.created) + 1
            u = "https://github.com/pearu/cozer/issues/%d" % n
            self.created.append((body["title"], body["body"]))
            return 201, {"html_url": u, "number": n}
        if "device/code" in url:
            return 200, {"device_code": "DEV", "user_code": "ABCD-1234",
                         "verification_uri": "https://github.com/login/device", "interval": 1}
        if "oauth/access_token" in url:
            return 200, self.token_resp()
        raise AssertionError("unexpected url %s" % url)

    def token_resp(self):
        return {"access_token": "gho_test"}


def test_fingerprint_stable_and_type_sensitive():
    r1, r2 = _report(), _report()
    assert r1["fingerprint"] == r2["fingerprint"]          # same code path -> same fp
    assert len(r1["fingerprint"]) == 12
    assert cr.fingerprint("ValueError", None) != cr.fingerprint("KeyError", None)


def test_build_report_and_title_and_body():
    ev = {"date": "2026-07-24", "venue": "Tallinn, Estonia", "title": "WC"}
    r = _report(event=ev)
    assert r["exc_type"] == "ValueError" and r["exc_msg"] == "kaboom"
    assert "kaboom" in r["traceback"] and r["cozer_version"]
    assert cr.report_title(r) == "[2026-07-24/Tallinn] Crash: ValueError: kaboom"
    body = cr.report_body(r)
    assert "crash-fingerprint:%s" % r["fingerprint"] in body
    assert "```json" in body and "2026-07-24" in body     # event attached for reproduction


def test_title_without_event():
    assert cr.report_title(_report(event=None)).startswith("[?/?] Crash: ValueError")


def test_write_local_and_config_dir(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    p = cr.write_local(_report())                          # no event path -> config crashes dir
    assert os.path.exists(p) and p.startswith(str(tmp_path)) and "crashes" in p
    assert json.load(open(p))["exc_type"] == "ValueError"


def test_write_local_next_to_event(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    ev = str(tmp_path / "sub" / "e.cozj")
    os.makedirs(os.path.dirname(ev))
    p = cr.write_local(_report(), event_path=ev)
    assert p.startswith(str(tmp_path / "sub" / "cozer-crashes"))


def test_handle_offline_queues(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    rep = cr.Reporter(config={"token": "t", "auto_submit": True, "submitted": {}})
    assert rep.handle(_report(), online=False) is None
    assert len(cr.list_pending()) == 1                     # queued, not submitted


def test_handle_not_logged_in_queues(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    rep = cr.Reporter(config={"token": None, "auto_submit": True, "submitted": {}})
    assert rep.handle(_report()) is None
    assert len(cr.list_pending()) == 1


def test_handle_auto_submits_and_dedupes(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    fake = FakeGitHub()
    rep = cr.Reporter(config={"token": "gho_test", "auto_submit": True, "submitted": {}},
                      transport=fake)
    url = rep.handle(_report(event={"date": "2026-07-24", "venue": "Tallinn"}))
    assert url and url.endswith("/issues/1")
    assert rep.config["submitted"][_report()["fingerprint"]] == url
    # same fingerprint again -> no second issue created
    assert rep.handle(_report()) == url
    assert len(fake.created) == 1


def test_handle_uses_existing_issue(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    fake = FakeGitHub(existing="https://github.com/pearu/cozer/issues/9")
    rep = cr.Reporter(config={"token": "gho_test", "auto_submit": True, "submitted": {}},
                      transport=fake)
    url = rep.handle(_report())
    assert url.endswith("/issues/9") and not fake.created  # matched existing, none created


def test_submit_pending_drains_queue(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    cr.Reporter(config={"token": None}).handle(_report())  # queue one
    assert len(cr.list_pending()) == 1
    fake = FakeGitHub()
    rep = cr.Reporter(config={"token": "gho_test", "auto_submit": True, "submitted": {}},
                      transport=fake)
    done = rep.submit_pending()
    assert len(done) == 1 and not cr.list_pending()        # drained


def test_parse_body_json_or_form_encoded():
    # GitHub's device endpoints reply form-encoded unless asked for JSON — accept both
    assert cr._parse_body("") == {}
    assert cr._parse_body('{"access_token": "gho_x"}') == {"access_token": "gho_x"}
    assert cr._parse_body("access_token=gho_x&token_type=bearer") == {
        "access_token": "gho_x", "token_type": "bearer"}
    assert cr._parse_body("error=authorization_pending")["error"] == "authorization_pending"


def test_github_login():
    class Who(FakeGitHub):
        def __call__(self, method, url, headers, data):
            if url.endswith("/user"):
                return 200, {"login": "pearu"}
            return super().__call__(method, url, headers, data)
    assert cr.github_login("gho_x", transport=Who()) == "pearu"


def test_device_flow(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    fake = FakeGitHub()
    start = cr.device_start("CID", transport=fake)
    assert start["user_code"] == "ABCD-1234"
    token = cr.device_poll("CID", "DEV", interval=0, transport=fake, sleep=lambda *_: None)
    assert token == "gho_test"


def test_device_poll_pending_then_success(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    class Pend(FakeGitHub):
        def __init__(self):
            super().__init__()
            self.n = 0

        def token_resp(self):
            self.n += 1
            return {"error": "authorization_pending"} if self.n < 3 else {"access_token": "gho_x"}

    token = cr.device_poll("CID", "DEV", interval=0, timeout=10, transport=Pend(),
                           sleep=lambda *_: None, clock=lambda: 0.0)
    assert token == "gho_x"


def test_device_poll_error_raises(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)

    class Denied(FakeGitHub):
        def token_resp(self):
            return {"error": "access_denied"}

    try:
        cr.device_poll("CID", "DEV", interval=0, transport=Denied(), sleep=lambda *_: None)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "access_denied" in str(e)


def test_build_user_report_and_bug_title():
    r = cr.build_user_report("It froze when I clicked Start\nmore detail",
                             eventdata={"date": "2026-07-24", "venue": "Tallinn"}, now=1)
    assert r["exc_type"] == "BugReport" and r["exc_msg"] == "It froze when I clicked Start"
    assert cr.report_title(r) == "[2026-07-24/Tallinn] Bug report: It froze when I clicked Start"
    body = cr.report_body(r)
    assert body.startswith("User bug report") and "### Description" in body


def test_client_id_default(tmp_path, monkeypatch):
    monkeypatch.setenv("COZER_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COZER_GITHUB_CLIENT_ID", raising=False)
    assert cr.client_id() == cr.DEFAULT_CLIENT_ID


def test_config_roundtrip(tmp_path, monkeypatch):
    _cfg(tmp_path, monkeypatch)
    cfg = cr.load_config()
    assert cfg["auto_submit"] is True and cfg["token"] is None
    cfg["token"] = "gho_z"
    cr.save_config(cfg)
    assert cr.load_config()["token"] == "gho_z"
    monkeypatch.setenv("COZER_GITHUB_CLIENT_ID", "envcid")
    assert cr.client_id() == "envcid"                      # env overrides config
