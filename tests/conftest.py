import os

import pytest

# Any Qt usage in the test suite must run headless: no display on the dev
# server or in CI. Setting this before PySide6 is imported selects the
# offscreen platform plugin.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
