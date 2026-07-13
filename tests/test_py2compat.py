"""Unit tests for the Python-2 compatibility shims (cozer/_py2compat.py)."""
from cozer._py2compat import round2, py2_cmp, py2_sorted


def test_round2_half_away_from_zero():
    # py3 round() would give 0/2 (half-to-even); legacy py2 gives 1/3.
    assert round2(0.5, 0) == 1.0
    assert round2(2.5, 0) == 3.0
    assert round2(-0.5, 0) == -1.0
    assert round2(2.675, 2) == 2.68 or round2(2.675, 2) == 2.67  # repr-dependent
    assert round2(1.005, 2) in (1.0, 1.01)
    assert round2(12.344, 2) == 12.34
    assert round2(12.345, 2) == 12.35


def test_py2_cmp_numbers_and_none():
    assert py2_cmp(1, 2) == -1
    assert py2_cmp(2, 2) == 0
    assert py2_cmp(3, 2) == 1
    assert py2_cmp(None, None) == 0
    assert py2_cmp(None, 5) == -1      # None sorts first
    assert py2_cmp(5, None) == 1


def test_py2_cmp_mixed_int_str_like_py2():
    # In py2, int < str (ordered by type name 'int' < 'str'); py3 would raise.
    assert py2_cmp(9, "F22") == -1
    assert py2_cmp("F22", 9) == 1
    assert py2_sorted([9, "F22", 7, "A"]) == [7, 9, "A", "F22"]


def test_py2_cmp_sequences_and_strings():
    assert py2_cmp("abc", "abd") == -1
    assert py2_cmp([1, 2], [1, 2, 3]) == -1     # prefix is smaller
    assert py2_cmp((1, 2, 3), (1, 2)) == 1
    assert py2_cmp([1, 2], [1, 2]) == 0
