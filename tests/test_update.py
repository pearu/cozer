"""Tests for the in-app update check — no network, via a fake GitHub transport."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.app import update  # noqa: E402


def _rel(tag, assets=()):
    """A fake transport returning a GitHub 'latest release' payload for ``tag``."""
    def fake(method, url, headers, data):
        assert method == "GET" and url.endswith("/releases/latest")
        return 200, {"tag_name": tag, "name": "cozer %s" % tag, "body": "release notes",
                     "html_url": "https://github.com/pearu/cozer/releases/tag/%s" % tag,
                     "assets": [{"name": n, "browser_download_url": "https://dl/%s" % n, "size": 10}
                                for n in assets]}
    return fake


def test_is_newer_handles_prereleases():
    assert update.is_newer("3.0.0", "3.0.0rc1")            # final > rc
    assert update.is_newer("v3.0.0rc2", "3.0.0rc1")        # rc2 > rc1, leading 'v' tolerated
    assert update.is_newer("3.0.0rc1", "3.0.0.dev0")       # rc > dev
    assert update.is_newer("3.1.0", "3.0.9")
    assert not update.is_newer("3.0.0rc1", "3.0.0")        # rc < final
    assert not update.is_newer("3.0.0", "3.0.0")           # equal -> not newer


def test_latest_release_shape_and_failure():
    rel = update.latest_release(transport=_rel("v3.5.0", assets=[
        "cozer-3.5.0-py3-none-any.whl", "COZER-3.5.0-Windows-x86_64.exe"]))
    assert rel["tag"] == "v3.5.0" and rel["notes"] == "release notes"
    assert {a["name"] for a in rel["assets"]} == {
        "cozer-3.5.0-py3-none-any.whl", "COZER-3.5.0-Windows-x86_64.exe"}
    # unreachable / no release yet -> None (transport raises, or a non-release response)
    assert update.latest_release(transport=lambda *a, **k: (_ for _ in ()).throw(OSError())) is None
    assert update.latest_release(transport=lambda *a, **k: (404, {})) is None


def test_check_available_vs_up_to_date(monkeypatch):
    monkeypatch.setattr(update, "__version__", "3.0.0rc1")
    res = update.check(transport=_rel("v3.0.0"))
    assert res["available"] and res["current"] == "3.0.0rc1" and res["latest"]["tag"] == "v3.0.0"
    assert not update.check(transport=_rel("v3.0.0rc1"))["available"]     # same version -> up to date
    off = update.check(transport=lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert off["latest"] is None and not off["available"]                 # offline -> no update


def test_install_kind_source_from_repo_tree():
    # the suite runs from the repo working tree (a .git above the package) -> "source"
    assert update.install_kind() == "source"


def _res(kind, available=True, assets=()):
    rel = {"tag": "v9.0.0", "name": "cozer v9.0.0", "notes": "n", "url": "https://rel",
           "assets": [{"name": n, "url": "https://dl/%s" % n, "size": 1} for n in assets]}
    return {"current": "3.0.0", "kind": kind, "latest": rel if available else None,
            "available": available}


def test_recommend_by_install_kind():
    assert update.recommend(_res("wheel", available=False))["action"] == "none"    # up to date
    assert update.recommend(_res("source"))["action"] == "source"                  # informational
    r = update.recommend(_res("wheel", assets=["cozer-9.0.0-py3-none-any.whl"]))
    assert r["action"] == "pip" and r["url"].endswith(".whl")                       # pip -U the wheel
    # the Windows constructor install ALSO fast-updates via the wheel (it is a real env with pip)
    r = update.recommend(_res("windows-installer",
                              assets=["cozer-9.0.0-py3-none-any.whl", "COZER-Setup-Windows.exe"]))
    assert r["action"] == "pip" and r["url"].endswith(".whl")
    # a Windows install whose release has only the installer (no wheel) -> full installer download
    r = update.recommend(_res("windows-installer", assets=["COZER-Setup-Windows.exe"]))
    assert r["action"] == "installer" and r["url"].endswith(".exe")
    r = update.recommend(_res("windows-installer", assets=[]))                      # nothing usable
    assert r["action"] == "link" and r["url"] == "https://rel"                      # -> release page
