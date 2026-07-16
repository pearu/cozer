"""`python -m cozer` shows the splash early, then delegates to the GUI run()."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_main_shows_splash_then_invokes_run(monkeypatch):
    import cozer.app.main as appmain

    calls = []
    monkeypatch.setattr(appmain, "run",
                        lambda argv=None, app=None, splash=None: calls.append((argv, splash is not None)) or 0)
    from cozer.__main__ import main
    assert main([]) == 0
    # run() is called with the parsed argv and an already-created splash
    assert calls == [([], True)]
