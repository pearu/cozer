"""Cover the `python -m cozer` placeholder entry point (Phase 5 replaces it)."""
from cozer.__main__ import main


def test_main_returns_zero(capsys):
    assert main() == 0
    assert "cozer" in capsys.readouterr().out.lower()
