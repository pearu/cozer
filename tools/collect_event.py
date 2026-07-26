"""Collect a real cozer event (.cozj) into the private backup + dev corpus (pearu/cozer-events).

Two jobs: an OFF-LAPTOP versioned backup, and real-event input for developing cozer. It validates the
file opens under the current cozer, copies it under a STABLE canonical path (so re-collecting the same
event as it keeps being recorded builds a git version history at that path), and commits + pushes to the
private corpus repo (which holds driver PII — private only).

The corpus repo is a plain git checkout. The same ``ingest()`` is meant to be reused by the future
``cozer -> live.cozer.ee -> cozer-events`` pipeline (operators publish with a per-operator secret token,
no GitHub account needed; the live server commits on their behalf).

Usage:
  python tools/collect_event.py <event.cozj> [--corpus <dir>] [--no-push] [--message <msg>]
Corpus dir resolves to: --corpus, else $COZER_EVENTS_DIR, else the sibling ``../cozer-events``.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.store import load_event


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "event"


def canonical_relpath(eventdata):
    """``<year>/<slug>.cozj`` — STABLE per event (slug from the broadcast eventname, else the title/venue),
    so re-collecting the same event versions the same path instead of piling up copies."""
    m = re.search(r"(19|20)\d\d", str(eventdata.get("date") or ""))
    year = m.group(0) if m else "undated"
    bc = eventdata.get("broadcast") or {}
    slug = _slug(bc.get("eventname") or eventdata.get("title") or eventdata.get("venue"))
    return os.path.join(year, slug + ".cozj")


def _git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit("git %s failed:\n%s" % (" ".join(args), r.stderr.strip()))
    return r


def ingest(event_path, corpus_dir, push=True, message=None):
    """Validate ``event_path``, copy it into ``corpus_dir`` at its canonical path, and commit (push
    optional). Returns ``(relpath, committed)``. Reusable by the live-server pipeline."""
    with open(event_path, encoding="utf-8") as f:
        text = f.read()
    eventdata = load_event(text)          # raises if the file doesn't open under the current cozer
    rel = canonical_relpath(eventdata)
    dst = os.path.join(corpus_dir, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:      # keep the ORIGINAL bytes (exact operator file)
        f.write(text)
    _git(corpus_dir, "add", rel)
    if _git(corpus_dir, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return rel, False                            # unchanged -> a no-op re-collect
    n = len(eventdata.get("participants") or [])
    msg = message or ("collect %s  (%s · %s · %d participants)"
                      % (rel, eventdata.get("venue") or "?", eventdata.get("date") or "?", n))
    _git(corpus_dir, "commit", "-m", msg)
    if push:
        _git(corpus_dir, "push")
    return rel, True


def _default_corpus():
    return (os.environ.get("COZER_EVENTS_DIR")
            or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "cozer-events"))


def main():
    ap = argparse.ArgumentParser(description="Collect a cozer .cozj event into the private backup corpus.")
    ap.add_argument("event", help="path to the event .cozj")
    ap.add_argument("--corpus", help="corpus git checkout (default $COZER_EVENTS_DIR or ../cozer-events)")
    ap.add_argument("--no-push", action="store_true", help="commit locally but do not push")
    ap.add_argument("--message", help="override the commit message")
    a = ap.parse_args()
    corpus = os.path.abspath(a.corpus or _default_corpus())
    if not os.path.isdir(os.path.join(corpus, ".git")):
        raise SystemExit("not a git checkout (clone pearu/cozer-events there first): %s" % corpus)
    rel, committed = ingest(a.event, corpus, push=not a.no_push, message=a.message)
    print(("collected %s -> %s" % (rel, corpus)) if committed else ("no change: %s already current" % rel))


if __name__ == "__main__":
    main()
