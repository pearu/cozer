"""The race-pattern parser must evaluate the pattern arithmetic WITHOUT eval:
an operator-entered string can never execute code, and eval's py2/py3 quirks
(integer division, octal literals, unbounded ``**``) cannot leak in.

Equivalence with the legacy parser on every real pattern is covered by
tests/test_model_equivalence.py; this file pins the arithmetic + safety of the
``_parse_num`` replacement directly.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.racepattern import crack_race_pattern, _parse_num


def test_parse_num_arithmetic():
    assert _parse_num("1500") == 1500
    assert _parse_num("3*1000") == 3000
    assert _parse_num("2*3*1000") == 6000
    assert _parse_num("(5-1)*1500") == 6000     # parenthesised subtraction (the (L-1) form)
    assert _parse_num(" 4 ") == 4               # surrounding whitespace tolerated
    assert _parse_num("-2") == -2


@pytest.mark.parametrize("bad", [
    "__import__('os')",          # code execution attempt
    "os.system('touch pwned')",  # attribute + call
    "x",                         # bare name
    "2**64",                     # power: eval would allow a DoS (9**9**9); we reject
    "10/2",                      # division: eval's py2/py3 semantics differ; we reject
    "",                          # empty
    "()",                        # empty tuple / no value
    "1,2",                       # tuple
    "[1]",                       # list literal
])
def test_parse_num_rejects_unsafe(bad):
    with pytest.raises(ValueError):
        _parse_num(bad)


def test_crack_expected_structure():
    heats, sheats = crack_race_pattern("3*(1500+4*1500):3")
    assert sheats == 3
    assert heats == [[1500] * 5] * 3            # 3 heats, each 1 + 4 laps of 1500

    heats, sheats = crack_race_pattern("2*(3*1000+2*500):2")
    assert sheats == 2
    assert heats == [[1000, 1000, 1000, 500, 500]] * 2


def test_crack_endurance():
    heats, sheats, seconds = crack_race_pattern("2110/6")
    assert heats == [[2110]] and sheats == 1 and seconds == 6 * 3600


def test_crack_never_executes_code(tmp_path):
    """A malicious leaf must raise, never run — the whole point of dropping eval."""
    marker = tmp_path / "pwned"
    payload = "1*(__import__('os').system('touch %s')*1):1" % marker
    with pytest.raises(Exception):
        crack_race_pattern(payload)
    assert not marker.exists()
