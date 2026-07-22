#!/usr/bin/env python3
"""Cut a cozer release in one command.

This scripts the steps documented in ``docs/RELEASE.md`` (§3 + the "Per-release doc checklist"),
so a quick release-candidate cut is a single command instead of a manual sequence:

    preflight → bump version → release notes → test suite → commit + push main → tag → verify

**AI-optional by design.** The notes step does not require a human or an AI to be in the loop.
By default (``--mechanical-docs``) it derives the commit range from the last tag and writes a
clearly-labelled *mechanical summary* (raw ``git log`` subjects) — honest placeholder prose that a
human/AI replaces before the final release. Use ``--curated-docs`` when a hand-written "what's new"
section is expected; the tag is then blocked until the ``TODO(release)`` marker is gone.

Estonian (``docs/whats-new.et.md``) is **never** auto-translated: both modes leave a TODO stub for
the owner to fill (the owner verifies the Estonian). The et TODO never blocks the tag.

Run it as the human/session that holds git ownership (it makes real commits, a push, and a tag).

Examples
--------
    python tools/release.py 3.0.0rc7                 # mechanical notes, then tag + verify
    python tools/release.py 3.0.0rc7 --dry-run       # show every step, mutate nothing
    python tools/release.py 3.0.0rc7 --curated-docs  # expect hand-written notes (blocks on TODO)
    python tools/release.py 3.0.0 --installer 2026.08 --curated-docs   # final: also bump installer
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bump_version  # noqa: E402  (local tool — single source of truth for the version regex/setters)

WHATSNEW = ROOT / "docs" / "whats-new.md"
WHATSNEW_ET = ROOT / "docs" / "whats-new.et.md"
RELEASE_MD = ROOT / "docs" / "RELEASE.md"

TODO_MARK = "TODO(release)"

DRY = False  # set from --dry-run in main()


# --- tiny logging -----------------------------------------------------------
def step(msg):
    print("\n==> %s" % msg)


def info(msg):
    print("    %s" % msg)


def warn(msg):
    print("    ! %s" % msg)


def die(msg, code=1):
    print("\nrelease: %s" % msg, file=sys.stderr)
    raise SystemExit(code)


# --- git helpers ------------------------------------------------------------
def _run(cmd, check=True):
    r = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and r.returncode != 0:
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        die("command failed (%d): %s\n%s" % (r.returncode, " ".join(cmd), out))
    return (r.stdout or "").strip()


def git(*args, check=True):
    return _run(["git", *args], check=check)


# --- file editing (dry-run aware, idempotent) -------------------------------
def _read(p):
    return p.read_text(encoding="utf-8")


def _edit(path, transform, what):
    """Apply ``transform(old_text) -> new_text`` to ``path``, honouring --dry-run."""
    old = _read(path)
    new = transform(old)
    if new == old:
        info("%s: already up to date" % path.name)
        return
    if DRY:
        info("[dry-run] would update %s (%s)" % (path.name, what))
        return
    path.write_text(new, encoding="utf-8")
    info("updated %s (%s)" % (path.name, what))


def _insert_before_first_h2(text, block):
    """Insert ``block`` (a whole section) as newest-first, before the first existing ``## `` heading;
    if there is no section yet, append it at the end."""
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            prefix = "".join(lines[:i])
            prefix = prefix.rstrip("\n") + "\n\n"
            return prefix + block.rstrip("\n") + "\n\n" + "".join(lines[i:])
    return text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"


def _append_changelog(text, bullet):
    """Append ``bullet`` at the end of RELEASE.md's ``## Change log`` (entries run newest-last)."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "## Change log"), None)
    if start is None:
        die("could not find '## Change log' in docs/RELEASE.md")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    while end > start + 1 and lines[end - 1].strip() == "":
        end -= 1
    b = bullet if bullet.endswith("\n") else bullet + "\n"
    return "".join(lines[:end]) + b + "".join(lines[end:])


# --- section builders -------------------------------------------------------
def _mechanical_block(version, monthyear, anchor, subjects):
    body = "\n".join("- %s" % s for s in subjects) if subjects else "- (no commits since the last tag)"
    return (
        "## COZER %s — mechanical summary (%s)\n\n" % (version, monthyear)
        + "%s\n" % anchor
        + "<!-- MECHANICAL SUMMARY auto-generated from `git log` by tools/release.py. These are raw\n"
        "     commit subjects, NOT a curated plain-terms summary. Before the FINAL (non-rc) release,\n"
        "     replace this with organizer-facing notes (and translate them in whats-new.et.md). -->\n\n"
        + body + "\n"
    )


def _curated_template(version, monthyear, anchor):
    return (
        "## COZER %s (%s)\n\n" % (version, monthyear)
        + "%s\n" % anchor
        + "<!-- %s: write the plain-terms, organizer-facing \"what's new\" for %s here (newest first),\n"
        "     then delete this comment. release.py tags once no \"%s\" marker remains in this file. -->\n"
        % (TODO_MARK, version, TODO_MARK)
    )


def _et_stub(version, monthyear, anchor):
    return (
        "## COZER %s (%s)\n\n" % (version, monthyear)
        + "%s\n" % anchor
        + "<!-- %s: eestikeelne tõlge puudub — translate the %s section from whats-new.md. Do NOT\n"
        "     auto-generate; the owner verifies the Estonian. -->\n" % (TODO_MARK, version)
    )


def _changelog_bullet(version, isodate, mode, n_commits, last_tag):
    if mode == "mechanical":
        return (
            "- **%s** — **`v%s` cut** (mechanical notes): %d commit%s since %s. See "
            "`docs/whats-new.md` for the auto-generated change list (replace with a curated summary "
            "before the final release)." % (isodate, version, n_commits,
                                            "" if n_commits == 1 else "s", last_tag)
        )
    return "- **%s** — **`v%s` cut**. See `docs/whats-new.md`." % (isodate, version)


# --- steps ------------------------------------------------------------------
def preflight(version, touched, dry_run):
    step("Preflight")
    if not (ROOT / ".git").exists():
        die("not a git repository: %s" % ROOT)
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    info("branch: %s" % branch)
    if branch != "main":
        die("must be on 'main' (currently %r) — switch first." % branch)

    tag = "v%s" % version
    if git("tag", "--list", tag):
        die("tag %s already exists — pick a new version (or delete the tag)." % tag)

    # Clean tree, ignoring untracked cruft and the files this script itself edits ("bar the files it
    # will touch" — so a re-run after a curated-docs block, with the notes already written, is clean).
    stray = []
    for ln in git("status", "--porcelain", "--untracked-files=no").splitlines():
        path = ln[3:].split(" -> ")[-1].strip().strip('"')
        if path not in set(touched):
            stray.append(ln)
    if stray:
        die("working tree has uncommitted changes outside the release files:\n    "
            + "\n    ".join(stray) + "\n  Commit or stash them first.")

    if dry_run:
        info("[dry-run] skipping `git fetch`")
    else:
        info("fetching origin…")
        git("fetch", "origin", "--tags")

    counts = git("rev-list", "--left-right", "--count", "origin/main...HEAD", check=False)
    if counts and "\t" in counts:
        behind, ahead = (int(x) for x in counts.split("\t"))
        if behind:
            die("main is %d commit(s) BEHIND origin/main — integrate first (git pull --ff-only)." % behind)
        if ahead:
            warn("main is %d commit(s) ahead of origin/main — the release push will include them." % ahead)
        if not behind and not ahead:
            info("in sync with origin/main.")
    else:
        warn("could not compare with origin/main (no upstream tracking?). Continuing.")


def curated_ready(version, anchor):
    """True when a hand-written whats-new section for this version already exists and is filled."""
    txt = _read(WHATSNEW)
    return (anchor in txt) and (TODO_MARK not in txt)


def write_docs(mode, version, monthyear, isodate, anchor, subjects, last_tag):
    n = len(subjects)

    def add_whatsnew(builder):
        def t(old):
            return old if anchor in old else _insert_before_first_h2(old, builder())
        return t

    def add_et(old):
        return old if anchor in old else _insert_before_first_h2(old, _et_stub(version, monthyear, anchor))

    def add_changelog(old):
        # idempotent: skip if a change-log line already mentions this tag
        return old if ("`v%s`" % version) in old else _append_changelog(
            old, _changelog_bullet(version, isodate, mode, n, last_tag))

    if mode == "mechanical":
        _edit(WHATSNEW, add_whatsnew(lambda: _mechanical_block(version, monthyear, anchor, subjects)),
              "mechanical summary, %d commits" % n)
    else:
        _edit(WHATSNEW, add_whatsnew(lambda: _curated_template(version, monthyear, anchor)),
              "curated TODO template")
    _edit(WHATSNEW_ET, add_et, "Estonian TODO stub")
    _edit(RELEASE_MD, add_changelog, "change-log line")


def run_tests():
    step("Run the test suite")
    if DRY:
        info("[dry-run] would run: ./tools/test.sh fast")
        return
    info("running ./tools/test.sh fast …")
    r = subprocess.run(["bash", "tools/test.sh", "fast"], cwd=ROOT)
    if r.returncode != 0:
        die("tests failed — aborting. The version bump + notes remain in your working tree; review, "
            "fix, and re-run (preflight ignores the release files).")
    info("tests passed.")


def commit_and_push(version, touched):
    step("Commit + push main")
    msg = "Release v%s: bump version + release notes" % version
    if DRY:
        info("[dry-run] would: git add %s" % " ".join(touched))
        info("[dry-run] would: git commit -m %r" % msg)
        info("[dry-run] would: git push origin main")
        return
    git("add", *touched)
    if git("diff", "--cached", "--name-only"):
        git("commit", "-m", msg)
        info("committed the bump + notes.")
    else:
        info("nothing to commit (release files already committed).")
    git("push", "origin", "main")
    info("pushed main.")


def tag_and_push(version):
    tag = "v%s" % version
    step("Tag %s + push (triggers release.yml → wheel-only Release)" % tag)
    if DRY:
        info("[dry-run] would: git tag %s" % tag)
        info("[dry-run] would: git push origin %s" % tag)
        return
    git("tag", tag)
    git("push", "origin", tag)
    info("tagged + pushed %s — release.yml is now building the wheel." % tag)


def verify_release(version, timeout_s=360, interval_s=15):
    tag = "v%s" % version
    step("Verify the GitHub Release %s (polling `gh release view`)" % tag)
    deadline = time.monotonic() + timeout_s
    while True:
        r = subprocess.run(["gh", "release", "view", tag, "--json", "assets,url"],
                           cwd=ROOT, text=True, capture_output=True)
        if r.returncode == 0:
            try:
                data = json.loads(r.stdout)
            except json.JSONDecodeError:
                data = {}
            wheels = [a.get("name", "") for a in data.get("assets", []) if a.get("name", "").endswith(".whl")]
            if wheels:
                info("Release live: %s" % data.get("url", tag))
                info("Wheel asset(s): %s" % ", ".join(wheels))
                return True
            info("release exists; wheel not uploaded yet…")
        else:
            info("release not visible yet…")
        if time.monotonic() >= deadline:
            warn("timed out after %ds waiting for the wheel. Check: gh release view %s" % (timeout_s, tag))
            return False
        time.sleep(interval_s)


# --- main -------------------------------------------------------------------
def main(argv):
    global DRY
    ap = argparse.ArgumentParser(
        prog="tools/release.py",
        description="Cut a cozer release: bump → notes → test → commit/push → tag → verify.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run as the human/session holding git ownership (this makes real commits, a push, "
               "and a tag). Use --dry-run first to preview.",
    )
    ap.add_argument("version", help="cozer (wheel/code) version, e.g. 3.0.0 or 3.0.0rc7")
    ap.add_argument("--installer", metavar="YYYY.MM",
                    help="also bump the Windows-installer version (rare; not part of a wheel-only rc)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mechanical-docs", action="store_true",
                   help="(default) auto-write a git-log 'mechanical summary' — no AI needed")
    g.add_argument("--curated-docs", action="store_true",
                   help="expect a hand-written whats-new section; block the tag until the "
                        "TODO(release) marker is gone")
    ap.add_argument("--allow-todo", action="store_true",
                    help="with --curated-docs: tag even though a TODO(release) placeholder remains")
    ap.add_argument("--dry-run", action="store_true", help="print every step; mutate nothing")
    ap.add_argument("--no-verify", action="store_true", help="don't poll `gh release view` after tagging")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = ap.parse_args(argv)

    DRY = args.dry_run
    version = args.version
    if not bump_version._VERSION_RE.match(version):
        die("refusing suspicious version %r (want e.g. 3.0.0 or 3.0.0rc7)" % version)
    if args.installer and not bump_version._INSTALLER_RE.match(args.installer):
        die("refusing suspicious installer version %r (want YYYY.MM)" % args.installer)

    mode = "curated" if args.curated_docs else "mechanical"
    touched = ["cozer/__init__.py", "docs/whats-new.md", "docs/whats-new.et.md", "docs/RELEASE.md"]
    if args.installer:
        touched.append("installer/construct.yaml")

    preflight(version, touched, args.dry_run)

    last_tag = git("describe", "--tags", "--abbrev=0", check=False) or "(none)"
    if last_tag != "(none)":
        subjects = [s for s in git("log", "%s..HEAD" % last_tag, "--pretty=%s", "--no-merges").splitlines()
                    if s.strip()]
    else:
        subjects = []
    today = datetime.date.today()
    monthyear = today.strftime("%B %Y")
    isodate = today.isoformat()
    anchor = "<!-- release-notes:%s -->" % version

    step("Plan")
    info("version:      %s   (tag v%s)" % (version, version))
    if args.installer:
        info("installer:    %s" % args.installer)
    info("docs mode:    %s" % mode)
    info("commit range: %s..HEAD  (%d commit%s)" % (last_tag, len(subjects),
                                                    "" if len(subjects) == 1 else "s"))
    info("touches:      %s" % ", ".join(touched))
    info("then:         test → commit → push main → tag v%s%s"
         % (version, "" if args.no_verify else " → verify"))
    if DRY:
        info("(dry-run: nothing will be mutated)")

    if not DRY and not args.yes:
        if not sys.stdin.isatty():
            die("no TTY for confirmation — pass --yes to run non-interactively.")
        if input("\nProceed with the release? [y/N] ").strip().lower() not in ("y", "yes"):
            die("aborted.", code=1)

    # Bump.
    step("Bump version → %s" % version)
    if DRY:
        info("[dry-run] would set __version__ = %r in cozer/__init__.py" % version)
        if args.installer:
            info("[dry-run] would set installer version %s in construct.yaml" % args.installer)
    else:
        changed = bump_version.set_version(version, root=str(ROOT))
        info("set __version__ = %r (%s)" % (version, "changed" if changed else "already set"))
        if args.installer:
            ic = bump_version.set_installer_version(args.installer, root=str(ROOT))
            info("installer version %s (%s)" % (args.installer, "changed" if ic else "already set"))

    # Notes — decide the curated gate from the pre-write state so --dry-run is accurate.
    ready = curated_ready(version, anchor)
    step("Release notes (%s)" % mode)
    write_docs(mode, version, monthyear, isodate, anchor, subjects, last_tag)

    if mode == "curated" and not ready:
        if args.allow_todo:
            warn("--allow-todo: tagging with the %s placeholder still in docs/whats-new.md." % TODO_MARK)
        else:
            step("Curated docs gate — STOP")
            warn("docs/whats-new.md has a %s placeholder for %s." % (TODO_MARK, version))
            info("Write the '## COZER %s' section (delete the %s comment), then re-run:" % (version, TODO_MARK))
            info("    python tools/release.py %s --curated-docs%s"
                 % (version, " --installer %s" % args.installer if args.installer else ""))
            info("(or pass --allow-todo to tag with the placeholder in place).")
            info("The version bump + note templates stay in your working tree; preflight ignores them "
                 "on re-run, so nothing half-baked is committed or tagged.")
            return 0

    run_tests()
    commit_and_push(version, touched)
    tag_and_push(version)

    tag = "v%s" % version
    if DRY:
        step("Done (dry-run)")
        info("Re-run without --dry-run to cut the release.")
    elif args.no_verify:
        step("Done (verification skipped: --no-verify)")
        info("Watch it: gh run watch   |   gh release view %s" % tag)
    else:
        verify_release(version)
        step("Done")
        info("Release: https://github.com/pearu/cozer/releases/tag/%s" % tag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
