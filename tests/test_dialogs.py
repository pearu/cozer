"""Tests for cozer.app.dialogs — the front-forcing / non-blocking dialog helpers.

The modal helpers (question/warn/error/info/run_modal) block in exec() until dismissed, so they can't be
unit-tested headlessly without driving the event loop; the meaningful, safely-testable contract is that
``notify`` is NON-blocking and routes to the window Log (the purely-informational path), and that
``bring_to_front`` runs its raise/activate/alert without error.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cozer.app import dialogs  # noqa: E402


class _Win:
    def __init__(self):
        self.logged = []

    def log(self, m):
        self.logged.append(m)


class _Widget:
    def __init__(self, win):
        self._win = win

    def window(self):
        return self._win


def test_notify_is_nonblocking_and_logs():
    win = _Win()
    dialogs.notify(_Widget(win), "COZER 3.0.0 is up to date.")
    assert win.logged == ["COZER 3.0.0 is up to date."]   # went to the Log, no modal, no return value


def test_notify_tolerates_missing_logger():
    class _NoLog:
        def window(self):
            return object()          # a window without .log()
    dialogs.notify(_NoLog(), "x")    # must not raise
    dialogs.notify(None, "x")        # widget None -> no-op


def test_api_surface():
    for name in ("question", "warn", "error", "info", "notify", "run_modal", "bring_to_front"):
        assert callable(getattr(dialogs, name))


def test_bring_to_front_smoke():
    from PySide6.QtWidgets import QApplication, QWidget
    QApplication.instance() or QApplication([])
    w = QWidget()
    w.show()
    dialogs.bring_to_front(w)        # raise_() + activateWindow() + QApplication.alert() must not raise
    w.close()
