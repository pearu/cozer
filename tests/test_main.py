"""`python -m cozer` prints a startup line, then delegates to the GUI run()."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_invokes_run(monkeypatch):
    monkeypatch.setenv("COZER_NO_FONT_FIX", "1")        # don't touch fontconfig in tests
    import cozer.app.main as appmain

    calls = []
    monkeypatch.setattr(appmain, "run", lambda argv=None, app=None: calls.append(argv) or 0)
    from cozer.__main__ import main
    assert main([]) == 0
    assert calls == [[]]
