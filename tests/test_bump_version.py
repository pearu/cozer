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


def test_set_version_rewrites_init_and_wheel_name(tmp_path):
    _fixture(tmp_path)
    bump_version.set_version("1.2.3", root=str(tmp_path))               # known baseline
    changed = bump_version.set_version("9.9.9rc3", root=str(tmp_path))
    assert len(changed) == 2
    init = (tmp_path / "cozer" / "__init__.py").read_text()
    yaml = (tmp_path / "installer" / "construct.yaml").read_text()
    assert '__version__ = "9.9.9rc3"' in init
    assert "dist/cozer-9.9.9rc3-py3-none-any.whl" in yaml               # installer bundles the matching wheel
    assert "version: 9.9.9rc3" not in yaml                              # cozer version does NOT set the installer version:
    assert "1.2.3" not in init and "cozer-1.2.3" not in yaml            # prior version fully replaced
    assert bump_version.set_version("9.9.9rc3", root=str(tmp_path)) == []  # idempotent


def test_set_installer_version_is_independent(tmp_path):
    _fixture(tmp_path)
    bump_version.set_version("9.9.9rc3", root=str(tmp_path))            # cozer wheel version
    bump_version.set_installer_version("1999.01", root=str(tmp_path))  # known baseline (repo-independent)
    changed = bump_version.set_installer_version("2026.08", root=str(tmp_path))
    yaml = (tmp_path / "installer" / "construct.yaml").read_text()
    assert changed and "version: 2026.08" in yaml                      # installer version set
    assert "dist/cozer-9.9.9rc3-py3-none-any.whl" in yaml              # cozer wheel name left intact
    assert "version: 9.9.9rc3" not in yaml                             # never the cozer version
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
