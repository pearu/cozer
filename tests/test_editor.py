"""Unit tests for the pure record-editor mark operations (cozer/app/editor.py).

``insert_lap_split`` / ``toggle_nearest`` / ``delete_nearest`` are faithful ports
of the legacy ``RecordEditorMenu`` handlers (timers.py OnInsert/OnEnable/OnDelete).
They mutate a ``marks`` list of ``[code, time, ...]`` in place, where code 1 is a
timed lap, 2 an inserted lap, a negative code a disabled mark, and other codes are
event marks (DS/IR/DQ...) timed at their absolute time.

These functions had no direct unit coverage; a fuzz sweep found them robust (no
crash, structurally valid output over thousands of random op sequences), so these
tests pin the invariants that matter: total lap time is preserved by a split and by
a toggle, an insert then a delete of that inserted lap round-trips, and delete
honours the legacy rules (timed laps refuse, an inserted lap gives its time to the
FOLLOWING lap -- and a *trailing* inserted lap, having none, drops it, matching
legacy OnDelete exactly).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.app.editor import (
    delete_nearest,
    insert_lap_split,
    mark_positions,
    toggle_nearest,
)


def _laptime(marks):
    """Total cumulative lap time -- laps + inserted laps, disabled included."""
    return round(sum(m[1] for m in marks if abs(m[0]) in (1, 2)), 6)


def _valid(marks):
    return all(isinstance(m, list) and len(m) >= 2
               and isinstance(m[1], (int, float)) for m in marks)


def test_insert_split_preserves_total_and_splits():
    m = [[1, 30.0], [1, 40.0], [1, 35.0]]
    insert_lap_split(m, 50.0)                    # cut the 2nd lap (cum 30..70) at 50
    assert _laptime(m) == 105.0                  # total unchanged
    assert m == [[1, 30.0], [2, 20.0], [1, 20.0], [1, 35.0]]


def test_insert_beyond_end_appends_extension():
    m = [[1, 30.0], [1, 40.0]]
    insert_lap_split(m, 100.0)                    # past the recorded end (cum 70)
    assert m[-1] == [2, 30.0]                     # extends the race to ct
    assert _laptime(m) == 100.0


def test_insert_then_delete_round_trips():
    orig = [[1, 30.0], [1, 40.0], [1, 35.0]]
    m = [list(x) for x in orig]
    insert_lap_split(m, 50.0)                     # split the 2nd lap
    delete_nearest(m, 50.0, 1.0, tol=3)          # delete the inserted boundary
    assert m == orig                             # merged forward -> exact restore


def test_toggle_flips_sign_and_preserves_total():
    m = [[1, 30.0], [1, 40.0]]
    assert toggle_nearest(m, 70.0, 1.0, tol=3) is True   # cum 70 -> 2nd lap
    assert m == [[1, 30.0], [-1, 40.0]]
    assert _laptime(m) == 70.0                            # disabling keeps raw time
    assert toggle_nearest(m, 70.0, 1.0, tol=3) is True    # toggles back
    assert m == [[1, 30.0], [1, 40.0]]


def test_toggle_returns_false_when_nothing_near():
    m = [[1, 30.0]]
    assert toggle_nearest(m, 999.0, 1.0, tol=3) is False
    assert m == [[1, 30.0]]                                # untouched


def test_delete_refuses_timed_lap():
    m = [[1, 30.0]]
    msg = delete_nearest(m, 30.0, 1.0, tol=3)
    assert msg and "Enable/Disable" in msg                # refused with guidance
    assert m == [[1, 30.0]]                               # nothing deleted


def test_delete_removes_event_mark():
    m = [[1, 30.0], [10, 45.0]]                           # DS-like event at abs t=45
    assert delete_nearest(m, 45.0, 1.0, tol=3) is None
    assert m == [[1, 30.0]]


def test_delete_inserted_merges_time_forward():
    m = [[1, 30.0], [2, 20.0], [1, 25.0]]                 # inserted lap has a follower
    delete_nearest(m, 50.0, 1.0, tol=3)                   # remove the inserted lap
    assert m == [[1, 30.0], [1, 45.0]]                    # 20 given to the next lap
    assert _laptime(m) == 75.0


def test_delete_trailing_inserted_drops_time_legacy_faithful():
    # A trailing inserted lap (an extension via insert-beyond-end) has no following
    # lap, so legacy OnDelete just `del`s it -- its time is dropped, undoing the
    # extension. Ported faithfully; pinned so the behaviour stays deliberate.
    m = [[1, 30.0], [2, 20.0]]
    delete_nearest(m, 50.0, 1.0, tol=3)
    assert m == [[1, 30.0]]
    assert _laptime(m) == 30.0                            # 20 dropped, not merged


def test_mark_positions_cumulative_and_disabled_absorption():
    pos = mark_positions([[1, 30.0], [-1, 10.0], [1, 20.0]])
    kinds = [p[0] for p in pos]
    assert kinds == ["lap", "displap", "lap"]
    assert [p[1] for p in pos] == [30.0, 40.0, 60.0]      # cumulative, disabled incl.
    assert pos[2][3] == "30.0"                            # 20 lap absorbs 10 disabled


def test_edit_ops_fuzz_no_crash_and_time_preserved():
    """Random op sequences never crash or corrupt structure; insert and toggle
    preserve the total lap time (only delete is allowed to change it)."""
    rng = random.Random(20260718)
    for _ in range(3000):
        m = []
        for _ in range(rng.randint(1, 8)):
            r = rng.random()
            if r < 0.6:
                m.append([1, round(rng.uniform(20, 50), 1)])
            elif r < 0.75:
                m.append([2, round(rng.uniform(5, 30), 1)])
            elif r < 0.85:
                m.append([-1, round(rng.uniform(20, 50), 1)])
            else:
                m.append([rng.choice([10, 11, 12]), round(rng.uniform(0, 400), 1)])
        op = rng.choice(["ins", "tog", "del"])
        ct = round(rng.uniform(0, 300), 1)
        before = _laptime(m)
        if op == "ins":
            insert_lap_split(m, ct)
            # a within-range split preserves total; a beyond-end insert only grows it
            assert _laptime(m) >= before - 1e-6
        elif op == "tog":
            toggle_nearest(m, ct, 1.0, tol=8)
            assert _laptime(m) == before
        else:
            delete_nearest(m, ct, 1.0, tol=8)
        assert _valid(m)
