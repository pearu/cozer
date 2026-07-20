#!/usr/bin/env python3
"""Set cozer's version.

``cozer/__init__.py``'s ``__version__`` is the single source of truth — ``pyproject.toml`` reads it
via ``dynamic = ["version"]`` and ``installer/post_install.bat`` globs the wheel — so this script
only needs to touch the two places that can't read it dynamically:

  - ``cozer/__init__.py``        ``__version__ = "<version>"``
  - ``installer/construct.yaml`` ``version: <version>`` + the ``extra_files`` wheel filename

Usage:  python tools/bump_version.py 3.0.0rc1
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([.-]?(dev|a|b|rc)\d+)?$")


def set_version(version, root=ROOT):
    """Write ``version`` into cozer/__init__.py and installer/construct.yaml.
    Returns the list of files actually changed."""
    changed = []

    init = os.path.join(root, "cozer", "__init__.py")
    s = open(init, encoding="utf-8").read()
    s2 = re.sub(r'(?m)^__version__ = ".*"$', '__version__ = "%s"' % version, s)
    if s2 != s:
        open(init, "w", encoding="utf-8").write(s2)
        changed.append(init)

    yaml = os.path.join(root, "installer", "construct.yaml")
    s = open(yaml, encoding="utf-8").read()
    s2 = re.sub(r'(?m)^version: .*$', "version: %s" % version, s)
    s2 = re.sub(r"dist/cozer-.*-py3-none-any\.whl",
                "dist/cozer-%s-py3-none-any.whl" % version, s2)
    if s2 != s:
        open(yaml, "w", encoding="utf-8").write(s2)
        changed.append(yaml)

    return changed


def main(argv):
    if len(argv) != 1:
        print("usage: python tools/bump_version.py <version>", file=sys.stderr)
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
