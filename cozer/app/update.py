"""In-app update check (read-only core; see docs/RELEASE.md).

Reuses the crashreport GitHub transport to read the latest published release and decide what an
update *would* do on this install. The actual apply (fast wheel `pip -U` vs full installer) is
Phase 2 and lives elsewhere; this module only reports.
"""
import os
import re
import sys

from cozer import __version__
from cozer.app import crashreport

LATEST_RELEASE_URL = "%s/repos/%s/releases/latest" % (crashreport.GITHUB_API, crashreport.REPO)


def install_kind():
    """How this cozer is installed, which bounds what an update can do (docs/RELEASE.md §3):

    - ``"source"``      — running from the repo working tree (a ``.git`` above the package);
                          an update is informational only (never mutate a checkout).
    - ``"windows-installer"`` — the constructor/NSIS bundle: a conda env whose ``sys.prefix``
                          carries the installer's ``cozer-launch.pyw``; can fast-update the wheel
                          OR run a full installer.
    - ``"wheel"``       — a plain pip install; can pip-upgrade the wheel.
    """
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../cozer
    if os.path.isdir(os.path.join(os.path.dirname(pkg_root), ".git")):
        return "source"
    if sys.platform.startswith("win") and \
            os.path.exists(os.path.join(sys.prefix, "cozer-launch.pyw")):
        return "windows-installer"
    return "wheel"


def _clean(v):
    return (v or "").strip().lstrip("vV")


# fallback pre-release ranks when `packaging` is unavailable (dev < a < b < rc < final)
_PRE_RANK = {"dev": 0, "a": 1, "alpha": 1, "b": 2, "beta": 2, "rc": 3, "c": 3}


def _key(v):
    """A comparable key for a version string, without `packaging`. Handles ``X.Y.Z`` plus an
    optional ``.devN`` / ``aN`` / ``bN`` / ``rcN`` suffix; a plain release outranks its pre-releases."""
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.?(dev|a|alpha|b|beta|rc|c)(\d+)?)?", _clean(v))
    if not m:
        return (0, 0, 0, 4, 0)
    major, minor, patch = (int(m.group(i) or 0) for i in (1, 2, 3))
    pre, prenum = m.group(4), int(m.group(5) or 0)
    return (major, minor, patch, _PRE_RANK.get(pre, 4), prenum)   # no pre -> rank 4 (final)


def is_newer(remote, local):
    """True if release version ``remote`` is strictly newer than the running version ``local``."""
    try:
        from packaging.version import Version           # correct PEP 440 semantics if available
        return Version(_clean(remote)) > Version(_clean(local))
    except Exception:
        return _key(remote) > _key(local)


def latest_release(transport=None):
    """The latest *published* GitHub release, or ``None`` when there is none yet / GitHub is
    unreachable (a guarded, surfaced degradation — the caller tells the user it couldn't check,
    it is not swallowing a logic error). Shape:
    ``{tag, name, notes, url, assets: [{name, url, size}]}``."""
    try:
        _, js = crashreport._http("GET", LATEST_RELEASE_URL, transport=transport)
    except Exception:
        return None
    if not isinstance(js, dict) or not js.get("tag_name"):
        return None
    return {
        "tag": js["tag_name"],
        "name": js.get("name") or js["tag_name"],
        "notes": js.get("body") or "",
        "url": js.get("html_url") or "",
        "assets": [{"name": a.get("name"), "url": a.get("browser_download_url"), "size": a.get("size")}
                   for a in (js.get("assets") or [])],
    }


def check(transport=None):
    """Check for a newer release. Returns
    ``{current, kind, latest (release dict or None), available (bool)}``; ``available`` is True
    only when a newer release than the running version exists."""
    rel = latest_release(transport=transport)
    return {
        "current": __version__,
        "kind": install_kind(),
        "latest": rel,
        "available": bool(rel and is_newer(rel["tag"], __version__)),
    }
