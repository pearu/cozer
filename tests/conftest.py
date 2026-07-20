import os

import pytest

# Any Qt usage in the test suite must run headless: no display on the dev
# server or in CI. Setting this before PySide6 is imported selects the
# offscreen platform plugin.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _auto_confirm_dialogs(monkeypatch):
    """Keep modal confirm dialogs non-blocking under the offscreen platform: default
    ``QMessageBox.question`` to Yes so a delete-confirm ("are you sure?") doesn't hang the
    headless run. A test that asserts on a specific answer re-patches it (its own setattr wins)."""
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.Yes), raising=False)
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
