"""Unit tests for class-name predicates (cozer/classes.py)."""
from cozer.classes import isqclass, istclass, gettclass, getqclass, getclass


def test_predicates():
    assert isqclass("O-125/Q") == 1
    assert isqclass("O-125") == 0
    assert istclass("GT/T") == 1
    assert istclass("GT") == 0
    assert gettclass("GT/T") == "GT"
    assert gettclass("GT") == "GT"
    assert getqclass("O/Q") == "O"
    assert getqclass("O") == "O"
    assert getclass("O/Q") == "O"
    assert getclass("GT/T") == "GT"
    assert getclass("plain") == "plain"
