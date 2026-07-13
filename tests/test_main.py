"""`python -m cozer` delegates to the GUI run()."""


def test_main_invokes_run(monkeypatch):
    import cozer.app.main as appmain

    calls = []
    monkeypatch.setattr(appmain, "run", lambda argv=None: calls.append(argv) or 0)
    from cozer.__main__ import main
    assert main([]) == 0
    assert calls == [[]]
