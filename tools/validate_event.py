#!/usr/bin/env python
"""Print the non-fatal results-validation warnings for one or more events.

Usage (run with the cozer env python -- `mamba activate cozer` first, or use the
env's python directly):

    python tools/validate_event.py                          # scan all bundled events
    python tools/validate_event.py legacy/events/Liepaja_2006.coz
    python tools/validate_event.py path/to/myevent.cozj     # new-format events too

Exit status is 0 always -- these are advisory warnings, not errors.
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

from cozer.store import read_legacy_coz, loads  # noqa: E402
from cozer.validate import check_results, format_findings  # noqa: E402


def _load(path):
    if path.lower().endswith(".cozj"):
        with open(path, encoding="utf-8") as f:
            return loads(f.read())
    return read_legacy_coz(path)                            # legacy .coz (pickle)


def _report(path):
    try:
        lines = format_findings(check_results(_load(path)))
    except Exception as exc:                                # a bad file shouldn't stop the scan
        print("# %s\n    (could not read: %s)" % (path, exc))
        return 0
    if lines:
        print("# %s" % path)
        for line in lines:
            print("    " + line)
    return len(lines)


def main(argv):
    paths = argv[1:] or sorted(
        glob.glob(os.path.join(REPO, "legacy", "events", "*.coz")) +
        glob.glob(os.path.join(REPO, "legacy", "cozer", "data", "*.coz")))
    total = sum(_report(p) for p in paths)
    print("\n%d warning(s) across %d event(s)." % (total, len(paths)))


if __name__ == "__main__":
    main(sys.argv)
