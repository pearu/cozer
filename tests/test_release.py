"""Tests for tools/release.py — the one-command release cutter.

Focus: the pure, AI-independent preflight guards (the validation that must hold whether or not AI is in
the loop) and the idempotent doc-insertion helpers. ``git`` is monkeypatched with canned porcelain so
the guards are exercised without a real repo/network.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import release  # noqa: E402

TOUCHED = ["cozer/__init__.py", "docs/whats-new.md", "docs/whats-new.et.md", "docs/RELEASE.md"]


def _fake_git(status_out="", tag_local="", tag_remote="", counts="0\t1", branch="main"):
    """A stand-in for release.git(). Dispatches on the git subcommand. ``status_out`` must be given as
    release.git() would actually return it — i.e. already .strip()ed, so the first porcelain line has
    lost its leading space (this is exactly the ' M path' case that regressed)."""
    def fake(*args, check=True):
        a = list(args)
        if a[:2] == ["rev-parse", "--abbrev-ref"]:
            return branch
        if a[:1] == ["tag"]:
            return tag_local
        if a[:1] == ["ls-remote"]:
            return tag_remote
        if a[:1] == ["rev-list"]:
            return counts
        if a[:1] == ["status"]:
            return status_out
        return ""
    return fake


# --- preflight: the ' M path' regression (934c068) --------------------------
def test_preflight_touched_file_not_flagged(monkeypatch):
    # Two unstaged *touched* edits (a filled whats-new.md is exactly this). git() strips the whole
    # output, so the FIRST line lost its leading space: "M docs/whats-new.md". A fixed ln[3:] slice
    # would misread it and abort; the split-based parse must keep it recognised as a touched file.
    monkeypatch.setattr(release, "git",
                        _fake_git(status_out="M docs/whats-new.md\n M docs/RELEASE.md"))
    release.preflight("3.0.0rc7", TOUCHED, dry_run=True)  # must NOT raise


def test_preflight_stray_file_aborts(monkeypatch):
    monkeypatch.setattr(release, "git", _fake_git(status_out="M cozer/app/timer.py"))
    with pytest.raises(SystemExit):
        release.preflight("3.0.0rc7", TOUCHED, dry_run=True)


def test_preflight_wrong_branch_aborts(monkeypatch):
    monkeypatch.setattr(release, "git", _fake_git(branch="feature"))
    with pytest.raises(SystemExit):
        release.preflight("3.0.0rc7", TOUCHED, dry_run=True)


def test_preflight_duplicate_tag_local_aborts(monkeypatch):
    monkeypatch.setattr(release, "git", _fake_git(tag_local="v3.0.0rc7"))
    with pytest.raises(SystemExit):
        release.preflight("3.0.0rc7", TOUCHED, dry_run=True)


def test_preflight_duplicate_tag_remote_aborts(monkeypatch):
    # No local tag, but it exists on origin — must be caught before main is advanced.
    monkeypatch.setattr(release, "git", _fake_git(tag_remote="abc123\trefs/tags/v3.0.0rc7"))
    with pytest.raises(SystemExit):
        release.preflight("3.0.0rc7", TOUCHED, dry_run=True)


def test_preflight_behind_origin_aborts(monkeypatch):
    monkeypatch.setattr(release, "git", _fake_git(counts="2\t0"))  # behind=2
    with pytest.raises(SystemExit):
        release.preflight("3.0.0rc7", TOUCHED, dry_run=True)


# --- downgrade guard --------------------------------------------------------
def test_is_newer():
    pytest.importorskip("packaging")
    assert release.is_newer("3.0.0rc7", "v3.0.0rc6") is True
    assert release.is_newer("3.0.1", "3.0.0") is True                 # tolerates a missing 'v'
    assert release.is_newer("3.0.0rc5", "v3.0.0rc6") is False
    assert release.is_newer("3.0.0rc6", "v3.0.0rc6") is False         # equal is not strictly newer
    assert release.is_newer("3.0.0", "(none)") is None                # no prior tag → can't decide
    assert release.is_newer("3.0.0", "") is None


# --- doc insertion: newest-first, idempotent --------------------------------
WHATSNEW = ("# What's new\n\nintro\n\n---\n\n<!-- marker -->\n\n"
            "## COZER 3.0.0rc6 (July 2026)\n\nold notes\n")


def test_whatsnew_insert_newest_first_and_idempotent():
    anchor = "<!-- release-notes:3.0.0rc7 -->"
    block = release._mechanical_block("3.0.0rc7", "July 2026", anchor, ["Subject one", "Subject two"])
    out = release._insert_before_first_h2(WHATSNEW, block)
    assert out.index("## COZER 3.0.0rc7") < out.index("## COZER 3.0.0rc6")  # newest first
    assert out.count(anchor) == 1
    assert "- Subject one" in out
    # write_docs guards re-insertion on the anchor; emulate it — a re-run is a no-op.
    out2 = out if anchor in out else release._insert_before_first_h2(out, block)
    assert out2 == out


def test_whatsnew_insert_when_no_section_yet():
    text = "# What's new\n\nintro\n"                                   # no '## ' section yet
    block = release._et_stub("3.0.0rc7", "July 2026", "<!-- release-notes:3.0.0rc7 -->")
    out = release._insert_before_first_h2(text, block)
    assert out.rstrip().endswith("-->")
    assert "## COZER 3.0.0rc7" in out


RELEASE_MD = ("# Release\n\n## 4. Safety\n- x\n\n## Change log\n"
              "- **2026-07-21** — first\n- **2026-07-22** — second\n")


def test_changelog_append_newest_last_and_idempotent():
    bullet = release._changelog_bullet("3.0.0rc7", "2026-07-22", "curated", 2, "v3.0.0rc6")
    out = release._append_changelog(RELEASE_MD, bullet)
    assert out.index("second") < out.index("v3.0.0rc7` cut")          # appended after existing entries
    guard = "`v3.0.0rc7`"
    out2 = out if guard in out else release._append_changelog(out, bullet)
    assert out2 == out


def test_changelog_append_before_trailing_section():
    # Change log is NOT the last section — the bullet must land inside it, before the next heading.
    text = RELEASE_MD + "\n## Appendix\n- z\n"
    bullet = release._changelog_bullet("3.0.0rc7", "2026-07-22", "mechanical", 3, "v3.0.0rc6")
    out = release._append_changelog(text, bullet)
    assert out.index("v3.0.0rc7` cut") < out.index("## Appendix")
    assert out.index("second") < out.index("v3.0.0rc7` cut")


def test_changelog_bullet_labels_mechanical_honestly():
    mech = release._changelog_bullet("3.0.0rc7", "2026-07-22", "mechanical", 5, "v3.0.0rc6")
    assert "mechanical notes" in mech and "5 commit" in mech
    cur = release._changelog_bullet("3.0.0rc7", "2026-07-22", "curated", 5, "v3.0.0rc6")
    assert "mechanical" not in cur
