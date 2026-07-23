import os

import pytest

# Any Qt usage in the test suite must run headless: no display on the dev
# server or in CI. Setting this before PySide6 is imported selects the
# offscreen platform plugin.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Never let constructing a MainWindow fire the startup update check (a real network call to
# GitHub) during the suite.
os.environ.setdefault("COZER_NO_UPDATE_CHECK", "1")


@pytest.fixture(autouse=True)
def _auto_confirm_dialogs(monkeypatch):
    """Keep modal dialogs non-blocking under the offscreen platform. cozer routes every modal through
    ``cozer.app.dialogs`` (front-forced so a prompt can't hide behind other windows); those helpers
    ``exec()`` and would hang a headless run. Default the blocking ones to a proceed/OK answer
    (question -> Yes, run_modal -> Accepted, warn/error/info -> Ok) so nothing hangs; a test that
    asserts a specific answer re-patches the relevant ``dialogs`` helper (its own setattr wins).
    ``notify`` is already non-blocking (it only writes to the Log), so it is left real."""
    from PySide6.QtWidgets import QDialog, QMessageBox
    from cozer.app import dialogs
    monkeypatch.setattr(dialogs, "question", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(dialogs, "run_modal", lambda *a, **k: QDialog.Accepted)
    monkeypatch.setattr(dialogs, "warn", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(dialogs, "error", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(dialogs, "info", lambda *a, **k: QMessageBox.Ok)
    yield


@pytest.fixture(autouse=True)
def _close_event_stores():
    """Stop EventStore background fsync threads after each test: no leaked daemon
    threads, and no stray fsyncs polluting fsync-counting assertions in later
    tests."""
    yield
    from cozer.store import EventStore
    for s in list(EventStore._live):
        try:
            s.close()
        except Exception:
            pass
