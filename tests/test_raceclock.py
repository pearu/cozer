"""Race-clock correctness under clock anomalies (cozer/raceclock.py).

These tests ARE the proof that race timing survives an NTP/manual clock step and a
system sleep -- neither of which can be reproduced in a unit test with a real
clock, so both clocks are injected and the anomaly is scripted.

``RaceClock`` (Linux CLOCK_BOOTTIME / Windows monotonic) is exact by construction:
the OS clock already is monotonic + sleep-inclusive, so its only logic is
``clock() - origin``. ``DualRaceClock`` is the fallback that reconstructs the same
guarantee from a wall + a sleep-pausing monotonic clock; its logic is what these
tests exercise hardest.

All values are integer nanoseconds.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cozer.raceclock import RaceClock, DualRaceClock, make_race_clock, _GAP_NS

NS = 1_000_000_000       # one second
DAY = 86_400 * NS


# --- RaceClock: exact single sleep-inclusive monotonic clock -----------------

def test_raceclock_tracks_its_clock():
    clk = [1000 * NS]
    c = RaceClock(lambda: clk[0])
    c.start()
    assert c.read_ns() == 0
    clk[0] += 5 * NS
    assert c.read_ns() == 5 * NS          # pure read; callable at any rate
    assert c.read_ns() == 5 * NS


def test_raceclock_resume_offset():
    clk = [1000 * NS]
    c = RaceClock(lambda: clk[0])
    c.start(elapsed_ns=42 * NS)           # resume a race already 42 s in
    assert c.read_ns() == 42 * NS
    clk[0] += NS
    assert c.read_ns() == 43 * NS


def test_raceclock_read_before_start_is_zero():
    assert RaceClock(lambda: 123).read_ns() == 0


def test_days_long_race_has_no_overflow_or_drift():
    clk = [0]
    c = RaceClock(lambda: clk[0])
    c.start()
    clk[0] = 30 * DAY + 45 * NS + 600_000_000     # 30 days + 45.6 s
    assert c.read_ns() == 30 * DAY + 45 * NS + 600_000_000     # exact python-int
    assert c.read_ns() / 1e9 == 30 * 86_400 + 45.6            # -> float seconds, still exact


# --- DualRaceClock: reconstruct from wall + sleep-pausing monotonic ----------

def _dual(w0=1000 * NS, m0=500 * NS):
    wall, mono = [w0], [m0]
    c = DualRaceClock(lambda: wall[0], lambda: mono[0])
    c.start()
    return c, wall, mono


def test_dual_normal_tracks_monotonic():
    c, wall, mono = _dual()
    wall[0] += 3 * NS; mono[0] += 3 * NS
    assert c.read_ns() == 3 * NS
    wall[0] += 2 * NS; mono[0] += 2 * NS
    assert c.read_ns() == 5 * NS


def test_dual_recovers_a_system_sleep():
    # monotonic freezes during suspend, the wall clock keeps real time. A 300 s
    # sleep between two reads must be recovered so race time isn't under-counted.
    c, wall, mono = _dual()
    wall[0] += NS; mono[0] += NS
    assert c.read_ns() == NS
    wall[0] += 300 * NS                   # slept 300 s: wall advances...
    mono[0] += 0                          # ...monotonic was frozen
    assert c.read_ns() == 301 * NS        # gap recovered
    wall[0] += NS; mono[0] += NS          # normal ticking resumes (mono now 300 s behind wall)
    assert c.read_ns() == 302 * NS


def test_dual_ignores_backward_ntp_step():
    # a backward wall step (NTP) must not rewind race time; advance by monotonic.
    c, wall, mono = _dual()
    wall[0] += NS; mono[0] += NS
    assert c.read_ns() == NS
    wall[0] -= 100 * NS                   # NTP steps the wall clock back 100 s
    mono[0] += NS                         # 1 s of real time elapsed (monotonic)
    assert c.read_ns() == 2 * NS          # backward ignored, +1 s from monotonic


def test_dual_forward_ntp_treated_as_sleep():
    # a forward NTP step is indistinguishable from a sleep by the clocks alone, so
    # it is added -- the fail-safe direction (never under-count race time).
    c, wall, mono = _dual()
    wall[0] += 10 * NS                     # wall jumps +10 s...
    mono[0] += NS // 10                    # ...only 0.1 s of real time
    assert c.read_ns() == 10 * NS


def test_dual_subgap_jitter_does_not_drift():
    # a sub-GAP wall/monotonic wobble must resolve to the monotonic delta every
    # interval (not max), so thousands of samples accumulate zero drift.
    c, wall, mono = _dual()
    jitter = _GAP_NS - 1                   # just under the threshold
    for _ in range(200):
        wall[0] += NS + jitter            # wall runs 0.499... s ahead each second
        mono[0] += NS
        c.read_ns()
    assert c.read_ns() == 200 * NS         # pure monotonic total, no accumulated drift


def test_dual_never_decreases():
    c, wall, mono = _dual()
    wall[0] += NS; mono[0] += NS
    assert c.read_ns() == NS
    wall[0] -= 50 * NS; mono[0] += 0       # wall back, monotonic still -> increment 0
    assert c.read_ns() == NS               # held, not rewound


def test_dual_resume_offset():
    wall, mono = [1000 * NS], [500 * NS]
    c = DualRaceClock(lambda: wall[0], lambda: mono[0])
    c.start(elapsed_ns=42 * NS)
    wall[0] += NS; mono[0] += NS
    assert c.read_ns() == 43 * NS


def test_dual_sequence_sleep_then_backward_ntp():
    # a compound scenario end-to-end: normal, sleep, normal, backward NTP, normal.
    c, wall, mono = _dual()
    wall[0] += 2 * NS; mono[0] += 2 * NS; assert c.read_ns() == 2 * NS
    wall[0] += 120 * NS; mono[0] += 0;    assert c.read_ns() == 122 * NS   # 2-min sleep
    wall[0] += 3 * NS; mono[0] += 3 * NS; assert c.read_ns() == 125 * NS
    wall[0] -= 7 * NS; mono[0] += NS;     assert c.read_ns() == 126 * NS   # NTP back, +1s real
    wall[0] += 2 * NS; mono[0] += 2 * NS; assert c.read_ns() == 128 * NS


# --- platform factory --------------------------------------------------------

def test_make_race_clock_is_usable_and_platform_appropriate():
    c = make_race_clock()
    c.start()
    a = c.read_ns()
    assert isinstance(a, int) and a >= 0
    b = c.read_ns()
    assert b >= a                          # monotonic non-decreasing
    if hasattr(time, "CLOCK_BOOTTIME"):    # Linux -> the exact CLOCK_BOOTTIME clock
        assert isinstance(c, RaceClock)
