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
    # a Windows install whose (wheel-only) latest release lacks a wheel -> fall back to the FIXED
    # windows-installer release URL (which always exists), regardless of what assets `rel` carries
    r = update.recommend(_res("windows-installer", assets=["COZER-Setup-Windows.exe"]))
    assert r["action"] == "installer" and r["url"] == update.WINDOWS_INSTALLER_URL
    r = update.recommend(_res("windows-installer", assets=[]))
    assert r["action"] == "installer" and r["url"] == update.WINDOWS_INSTALLER_URL
    # a plain pip/wheel install whose release somehow has no wheel -> just open the release page
    r = update.recommend(_res("wheel", assets=[]))
    assert r["action"] == "link" and r["url"] == "https://rel"


def test_env_version_from_prefix(monkeypatch):
    # the ENVIRONMENT version is read from the versioned install dir name (cozer-<YYYY.MM>)
    monkeypatch.setattr("sys.prefix", "/opt/cozer-2026.07")
    assert update.env_version() == "2026.07"
    monkeypatch.setattr("sys.prefix", "/opt/cozer-2026.07.3")
    assert update.env_version() == "2026.07.3"
    monkeypatch.setattr("sys.prefix", "/home/x/miniconda3/envs/cozer")     # not versioned -> None
    assert update.env_version() is None


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def test_git_hash_reads_dot_git_without_git(tmp_path):
    sha = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
    g = tmp_path / "loose" / ".git"
    _write(str(g / "HEAD"), "ref: refs/heads/main\n")
    _write(str(g / "refs" / "heads" / "main"), sha + "\n")
    assert update.git_hash(str(g)) == sha[:7]                              # loose ref

    g2 = tmp_path / "packed" / ".git"
    _write(str(g2 / "HEAD"), "ref: refs/heads/main\n")                     # ref file absent -> packed-refs
    _write(str(g2 / "packed-refs"), "# pack-refs with: peeled\n%s refs/heads/main\n" % sha)
    assert update.git_hash(str(g2)) == sha[:7]

    g3 = tmp_path / "detached" / ".git"
    _write(str(g3 / "HEAD"), sha + "\n")                                   # detached HEAD: raw sha
    assert update.git_hash(str(g3)) == sha[:7]

    assert update.git_hash(str(tmp_path / "nope" / ".git")) is None        # no .git -> None


def test_version_label_leads_with_cozer_version():
    from cozer import __version__
    assert update.version_label().split(" · ")[0] == __version__      # "<version> [· env …] [· git …]"
