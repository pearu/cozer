"""Tests for tools/bump_version.py (version single-sourcing)."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bump_version  # noqa: E402


def test_set_version_rewrites_init_and_construct(tmp_path):
    os.makedirs(tmp_path / "cozer")
    os.makedirs(tmp_path / "installer")
    shutil.copy(os.path.join(ROOT, "cozer", "__init__.py"), tmp_path / "cozer" / "__init__.py")
    shutil.copy(os.path.join(ROOT, "installer", "construct.yaml"),
                tmp_path / "installer" / "construct.yaml")

    bump_version.set_version("1.2.3", root=str(tmp_path))               # a known baseline (repo-version-independent)
    changed = bump_version.set_version("9.9.9rc3", root=str(tmp_path))
    assert len(changed) == 2
    init = (tmp_path / "cozer" / "__init__.py").read_text()
    yaml = (tmp_path / "installer" / "construct.yaml").read_text()
    assert '__version__ = "9.9.9rc3"' in init
    assert "version: 9.9.9rc3" in yaml
    assert "dist/cozer-9.9.9rc3-py3-none-any.whl" in yaml
    assert "1.2.3" not in init and "cozer-1.2.3" not in yaml            # prior version fully replaced
    assert bump_version.set_version("9.9.9rc3", root=str(tmp_path)) == []  # idempotent


def test_version_regex_guards_garbage():
    assert bump_version.main(["not-a-version"]) == 2
    assert bump_version.main([]) == 2
    # accepts the real shapes we use
    import re
    assert bump_version._VERSION_RE.match("3.0.0rc1")
    assert bump_version._VERSION_RE.match("3.0.0")
    assert bump_version._VERSION_RE.match("3.1.0.dev0")
