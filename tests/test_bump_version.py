"""Tests for tools/bump_version.py (two version lines: cozer wheel vs Windows installer)."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bump_version  # noqa: E402


def _fixture(tmp_path):
    os.makedirs(tmp_path / "cozer")
    os.makedirs(tmp_path / "installer")
    shutil.copy(os.path.join(ROOT, "cozer", "__init__.py"), tmp_path / "cozer" / "__init__.py")
    shutil.copy(os.path.join(ROOT, "installer", "construct.yaml"),
                tmp_path / "installer" / "construct.yaml")


def test_set_version_rewrites_only_init(tmp_path):
    _fixture(tmp_path)
    bump_version.set_version("1.2.3", root=str(tmp_path))               # known baseline
    changed = bump_version.set_version("9.9.9rc3", root=str(tmp_path))
    assert len(changed) == 1                                           # env-only installer: only cozer/__init__.py
    init = (tmp_path / "cozer" / "__init__.py").read_text()
    yaml = (tmp_path / "installer" / "construct.yaml").read_text()
    assert '__version__ = "9.9.9rc3"' in init and "1.2.3" not in init
    assert "9.9.9rc3" not in yaml                                      # construct.yaml carries no cozer version
    assert bump_version.set_version("9.9.9rc3", root=str(tmp_path)) == []  # idempotent


def test_set_installer_version_syncs_version_and_prefix(tmp_path):
    _fixture(tmp_path)
    bump_version.set_installer_version("1999.01", root=str(tmp_path))  # known baseline (repo-independent)
    changed = bump_version.set_installer_version("2026.08", root=str(tmp_path))
    yaml = (tmp_path / "installer" / "construct.yaml").read_text()
    assert changed
    assert "version: 2026.08" in yaml                                 # installer version:
    assert "cozer-2026.08" in yaml and "cozer-1999.01" not in yaml     # versioned default_prefix dirs kept in sync
    assert bump_version.set_installer_version("2026.08", root=str(tmp_path)) == []  # idempotent


def test_version_regexes_guard_garbage():
    assert bump_version.main(["not-a-version"]) == 2
    assert bump_version.main([]) == 2
    assert bump_version.main(["--installer", "not-a-date"]) == 2
    assert bump_version._VERSION_RE.match("3.0.0rc1")
    assert bump_version._VERSION_RE.match("3.0.0")
    assert bump_version._VERSION_RE.match("3.1.0.dev0")
    assert bump_version._INSTALLER_RE.match("2026.07")
    assert bump_version._INSTALLER_RE.match("2026.07.2")
    assert not bump_version._INSTALLER_RE.match("3.0.0")               # a cozer version is not an installer version
