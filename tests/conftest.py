import os

# Any Qt usage in the test suite must run headless: no display on the dev
# server or in CI. Setting this before PySide6 is imported selects the
# offscreen platform plugin.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
