#!/usr/bin/env python3
"""Install cozer into the freshly-laid-down environment (run by post_install.bat on Windows).

The installer ships the ENVIRONMENT only (Python + PySide6 + WeasyPrint + ca-certificates + the
launcher/shortcut files) -- NOT cozer, which changes far more often than the environment. This
fetches the LATEST cozer wheel from GitHub and pip-installs it. If there is no internet, it falls
back to a ``cozer-*.whl`` sitting next to the installer (or in the usual download spots); if there is
none, it fails with a clear message -- the environment is intact, so a later online run or first
launch can finish the job.

Standalone: it must NOT import cozer (cozer isn't installed yet). Standard library only.
"""
import glob
import json
import os
import subprocess
import sys
import urllib.request

REPO = "pearu/cozer"
# releases/latest = the newest WHEEL release (the on-demand installer release is a prerelease and is
# excluded), so this always resolves the current cozer. Overridable for tests.
LATEST_API = os.environ.get("COZER_RELEASE_API",
                            "https://api.github.com/repos/%s/releases/latest" % REPO)


def _ensure_ca_bundle():
    """Point OpenSSL at the env's CA bundle (we run python.exe directly, without `conda activate`,
    so SSL_CERT_FILE is unset -> HTTPS would fail with CERTIFICATE_VERIFY_FAILED). Mirrors
    cozer-launch.pyw."""
    if os.environ.get("SSL_CERT_FILE"):
        return
    for cert in (os.path.join(sys.prefix, "Library", "ssl", "cacert.pem"),
                 os.path.join(sys.prefix, "Library", "ssl", "cert.pem"),
                 os.path.join(sys.prefix, "ssl", "cacert.pem")):
        if os.path.isfile(cert):
            os.environ["SSL_CERT_FILE"] = cert
            return


def _pip_install(target):
    print("cozer install: pip install --no-deps %s" % target, flush=True)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-deps",
                           "--disable-pip-version-check", target])


def _latest_wheel_url():
    req = urllib.request.Request(LATEST_API, headers={"Accept": "application/vnd.github+json",
                                                      "User-Agent": "cozer-bootstrap"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for asset in data.get("assets", []):
        if (asset.get("name") or "").endswith(".whl"):
            return asset.get("browser_download_url")
    return None


def _offline_search_dirs():
    """Where to look for an ``cozer-*.whl`` when offline, most-specific first. The installer's own
    directory (where the user would drop a wheel "next to the installer") is exposed by NSIS as
    $EXEDIR; constructor forwards a few dir env vars, so try those, then the usual download spots."""
    dirs = []
    for var in ("COZER_OFFLINE_WHEEL_DIR", "COZER_INSTALLER_DIR", "INSTALLER_UNPACK_DIR", "EXEDIR"):
        if os.environ.get(var):
            dirs.append(os.environ[var])
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    dirs += [os.getcwd(), sys.prefix, os.path.join(home, "Downloads"), home]
    return dirs


def _offline_wheel():
    for d in _offline_search_dirs():
        hits = sorted(glob.glob(os.path.join(d, "cozer-*.whl")))
        if hits:
            return hits[-1]
    return None


def main():
    _ensure_ca_bundle()
    try:                                        # 1) online: install the latest published wheel
        url = _latest_wheel_url()
        if url:
            _pip_install(url)
            print("cozer install: installed the latest cozer from GitHub.", flush=True)
            return 0
        print("cozer install: the latest release has no wheel asset; trying offline.", flush=True)
    except Exception as exc:                    # offline / API / network error -> offline fallback
        print("cozer install: could not reach GitHub (%s); trying offline." % exc, flush=True)
    wheel = _offline_wheel()                    # 2) offline: a wheel next to the installer / nearby
    if wheel:
        _pip_install(wheel)
        print("cozer install: installed cozer from %s (offline)." % wheel, flush=True)
        return 0
    sys.stderr.write(                           # 3) neither -> fail gracefully (environment intact)
        "\nCOZER could not be installed: no internet connection, and no cozer wheel (cozer-*.whl)\n"
        "was found next to the installer. Connect to the internet and run the installer again, or\n"
        "download a cozer-*.whl, put it in the same folder as the installer, and re-run it.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
