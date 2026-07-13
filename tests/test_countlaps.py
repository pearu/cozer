"""Cover countlaps(-1) -- the start-list grid (a display helper, faithfully
ported; not part of the scoring goldens)."""
from cozer.analyzer import countlaps


def test_countlaps_startlist_heat_minus_one():
    info = {"course": [1000, 1000]}
    rec = {2: [(1, 10.0)], 1: [(1, 12.0)], "A": []}
    grid = countlaps(-1, (info, rec))
    # rows = ids in py2 order (ints before strings); each row starts marked,
    # followed by (0,0) fillers, one per course lap.
    assert grid[0][0] == (1, 1)
    assert grid[1][0] == (2, 1)
    assert grid[2][0] == ("A", 1)
    assert all(cell == (0, 0) for row in grid for cell in row[1:])
    assert len(grid[0]) == 1 + len(info["course"])
