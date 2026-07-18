"""Where generated report PDFs are written.

Each event gets a per-event ``<event>.reports/`` folder next to its ``.cozj`` so
viewing a report needs no Save dialog and different events never collide. Each
generation overwrites ``<report>.pdf`` (the current copy) and also archives a
timestamped copy under ``postings/``. The whole ``*.reports/`` tree is
git-ignored (see .gitignore); an event's own ``.cozj`` is committed separately.

Pure path derivation -- the caller creates the directories and renders.
"""
import os
import tempfile


def report_stem(label):
    """Report display label -> file stem, e.g. 'Full Final' -> 'full_final'."""
    return "_".join(str(label).lower().split())


def report_dir(event_path):
    """The report directory for an event: ``<event>.reports/`` beside a saved
    ``.cozj``, or a stable temp dir when the event is unsaved (``event_path``
    falsy) so viewing still works before the first save."""
    if event_path:
        return os.path.splitext(os.path.abspath(event_path))[0] + ".reports"
    return os.path.join(tempfile.gettempdir(), "cozer-reports")


def report_output_paths(event_path, label, stamp):
    """``(latest_pdf, posting_pdf)`` for a report: the overwritten current copy
    and the timestamped archive copy. Paths only; the caller makes the dirs."""
    d = report_dir(event_path)
    stem = report_stem(label)
    return (os.path.join(d, stem + ".pdf"),
            os.path.join(d, "postings", "%s_%s.pdf" % (stem, stamp)))
