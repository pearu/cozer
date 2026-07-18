"""Correct race-elapsed timing under clock anomalies.

Race timing must survive two clock hazards that can occur *during* a race:

* an **NTP or manual step** of the wall clock, forward or backward; and
* the machine going to **sleep** — endurance races run for hours or days, and a
  laptop lid can close by accident; real race time keeps elapsing while asleep.

``time.monotonic`` is immune to NTP steps but on Linux/macOS it *pauses* during
system suspend, so on its own it under-counts a sleep. The wall clock counts sleep
but is NTP-corruptible. This module yields an elapsed time correct under both, by
choosing the cleanest correct source per platform:

* **Linux** — ``CLOCK_BOOTTIME``: a single native clock that is monotonic,
  NTP-immune, *and* counts suspend. Exact; no heuristic.
* **Windows** — ``time.monotonic`` (QueryPerformanceCounter) counts suspend, so it
  is exact for both hazards too.
* **Otherwise** (macOS, or any platform whose monotonic clock turns out to freeze
  on suspend) — a dual-clock reconstruction from wall + monotonic (:class:`DualRaceClock`)
  that recovers a sleep gap from the wall clock while ignoring NTP steps via the
  monotonic one.

All arithmetic is in **integer nanoseconds**. Python ``int`` is arbitrary
precision, so ``elapsed_ns`` cannot overflow even for a days-long race, and there
is no floating-point accumulation drift; callers convert the small per-lap delta
to seconds only at the end.
"""
import sys
import time

# Wall-vs-monotonic divergence beyond this (dual-clock fallback only) is treated as
# real time the monotonic clock missed — a system sleep. It sits far above awake
# jitter (sub-millisecond) and far below any real gap. A forward NTP step is
# indistinguishable from a sleep here and is treated as one: the fail-safe
# direction (never under-count race time).
_GAP_NS = 500_000_000     # 0.5 s


class RaceClock:
    """Elapsed race time in integer nanoseconds from a single sleep-inclusive,
    NTP-immune monotonic clock (Linux ``CLOCK_BOOTTIME`` / Windows monotonic).

    ``clock_ns`` (a callable returning int ns) is injectable for tests. ``read_ns``
    is a pure read — ``clock_ns() - origin`` — so it can be called at any rate.
    """

    def __init__(self, clock_ns):
        self._clock_ns = clock_ns
        self._origin = None

    def start(self, elapsed_ns=0):
        """Pin the origin. Pass ``elapsed_ns > 0`` to resume a race already that
        many nanoseconds in (e.g. bridging downtime after a restart)."""
        self._origin = self._clock_ns() - int(elapsed_ns)

    def read_ns(self):
        return 0 if self._origin is None else self._clock_ns() - self._origin


class DualRaceClock:
    """Fallback for platforms lacking a sleep-inclusive monotonic clock:
    reconstruct elapsed from a wall clock plus a (sleep-pausing) monotonic clock.

    Per sampled interval (``read_ns`` is called at each lap, and may be polled for a
    live display), advance by the **monotonic** delta — which never jumps on an NTP
    step — *except* when the wall clock ran ahead of it by more than ``_GAP_NS``,
    which means real time passed while monotonic was frozen (a sleep): then advance
    by the **wall** delta to recover it. A backward wall step (NTP) shows up as the
    wall running behind monotonic and is ignored. Elapsed never decreases.

    Correct regardless of whether the platform's monotonic already counts sleep: if
    it does, ``dw ≈ dm`` so nothing is double-counted; if it doesn't, the gap is
    recovered.
    """

    def __init__(self, wall_ns, mono_ns):
        self._wall_ns = wall_ns
        self._mono_ns = mono_ns
        self._elapsed = 0
        self._last_wall = None
        self._last_mono = None

    def start(self, elapsed_ns=0):
        self._elapsed = int(elapsed_ns)
        self._last_wall = self._wall_ns()
        self._last_mono = self._mono_ns()

    def read_ns(self):
        if self._last_wall is None:
            return self._elapsed
        w, m = self._wall_ns(), self._mono_ns()
        dw, dm = w - self._last_wall, m - self._last_mono
        self._last_wall, self._last_mono = w, m
        inc = dw if dw - dm > _GAP_NS else dm     # recover a sleep gap; else trust monotonic
        if inc > 0:                               # never let elapsed run backward
            self._elapsed += inc
        return self._elapsed


def make_race_clock():
    """The :class:`RaceClock`-like object for this platform: a native
    sleep-inclusive monotonic clock where one exists (exact), else a
    :class:`DualRaceClock` reconstruction."""
    if hasattr(time, "CLOCK_BOOTTIME"):                       # Linux: exact
        return RaceClock(lambda: time.clock_gettime_ns(time.CLOCK_BOOTTIME))
    if sys.platform == "win32":                               # Windows monotonic counts suspend
        return RaceClock(time.monotonic_ns)
    return DualRaceClock(time.time_ns, time.monotonic_ns)     # macOS / unconfirmed: reconstruct
