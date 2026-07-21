#!/usr/bin/env python3
"""Set cozer's versions.

cozer has TWO independent version lines (docs/RELEASE.md, wheel-only pipeline):

  - **cozer (wheel/code) version** — what users update to via the in-app updater and what
    ``releases/latest`` tracks. Single source: ``cozer/__init__.py``'s ``__version__``
    (``pyproject.toml`` reads it via ``dynamic = ["version"]``; ``post_install.bat`` globs the wheel).
    We also stamp the ``installer/construct.yaml`` ``extra_files`` wheel filename so an installer build
    bundles the matching wheel.
        python tools/bump_version.py 3.0.0

  - **Windows-installer version** — the environment bootstrap, bumped ONLY when the installer's
    contents change (Python/PySide6/WeasyPrint/ca-certificates or the launcher/shortcut files), NOT
    per cozer release. Date-based (e.g. 2026.07). Lives in ``installer/construct.yaml`` ``version:``.
        python tools/bump_version.py --installer 2026.07
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([.-]?(dev|a|b|rc)\d+)?$")
_INSTALLER_RE = re.compile(r"^\d{4}\.\d{2}(\.\d+)?$")   # date-based: YYYY.MM or YYYY.MM.N


def _sub_file(path, subs):
    """Apply (pattern, repl) substitutions to ``path``; return True if the file changed."""
    s = open(path, encoding="utf-8").read()
    s2 = s
    for pat, repl in subs:
        s2 = re.sub(pat, repl, s2)
    if s2 != s:
        open(path, "w", encoding="utf-8").write(s2)
        return True
    return False


def set_version(version, root=ROOT):
    """Set the cozer (wheel/code) version: ``cozer/__init__.py`` ``__version__`` + the installer's
    bundled-wheel filename in construct.yaml. Does NOT touch construct.yaml's ``version:`` (that is the
    separate Windows-installer version). Returns the list of files changed."""
    changed = []
    init = os.path.join(root, "cozer", "__init__.py")
    if _sub_file(init, [(r'(?m)^__version__ = ".*"$', '__version__ = "%s"' % version)]):
        changed.append(init)
    yaml = os.path.join(root, "installer", "construct.yaml")
    if _sub_file(yaml, [(r"dist/cozer-.*-py3-none-any\.whl",
                         "dist/cozer-%s-py3-none-any.whl" % version)]):
        changed.append(yaml)
    return changed


def set_installer_version(iversion, root=ROOT):
    """Set the Windows-installer version (construct.yaml ``version:``). Returns the files changed."""
    changed = []
    yaml = os.path.join(root, "installer", "construct.yaml")
    if _sub_file(yaml, [(r"(?m)^version: .*$", "version: %s" % iversion)]):
        changed.append(yaml)
    return changed


def main(argv):
    if len(argv) == 2 and argv[0] == "--installer":
        iversion = argv[1]
        if not _INSTALLER_RE.match(iversion):
            print("refusing suspicious installer version %r (want YYYY.MM)" % iversion, file=sys.stderr)
            return 2
        changed = set_installer_version(iversion)
        for f in changed:
            print("set installer version %s in %s" % (iversion, os.path.relpath(f, ROOT)))
        if not changed:
            print("installer version already %s" % iversion)
        return 0
    if len(argv) != 1:
        print("usage: python tools/bump_version.py <cozer-version> | --installer <YYYY.MM>",
              file=sys.stderr)
        return 2
    version = argv[0]
    if not _VERSION_RE.match(version):
        print("refusing suspicious version %r" % version, file=sys.stderr)
        return 2
    changed = set_version(version)
    for f in changed:
        print("set version %s in %s" % (version, os.path.relpath(f, ROOT)))
    if not changed:
        print("version already %s everywhere" % version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
