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
    """Report display label -> a single safe filename component, e.g. 'Full Final' -> 'full_final',
    'Practice / Time-trial' -> 'practice_time-trial'. Path separators (/ \\ :) in a label must NOT
    become directories (issue #31 crashed on 'practice_/_time-trial.pdf'), so they are flattened to
    whitespace before words are joined with underscores."""
    s = str(label).lower()
    for sep in "/\\:":
        s = s.replace(sep, " ")
    return "_".join(s.split())


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
