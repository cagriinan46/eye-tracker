"""Dwell intent on final pointer coordinates; no OS actions."""

from math import dist, isfinite


class DwellClick:
    """One click after 1.5 s within 30 pixels of a fixed anchor.

    Missing input or a >0.5 s observation gap restarts the timer. After firing,
    leaving the anchor circle is required to rearm, even across tracking loss.
    """

    def __init__(self, radius=30.0, seconds=1.5, max_gap=0.5):
        if not all(isfinite(v) and v > 0 for v in (radius, seconds, max_gap)):
            raise ValueError("dwell parameters must be finite and positive")
        self.radius, self.seconds, self.max_gap = radius, seconds, max_gap
        self.anchor = None
        self.started = None
        self.last_time = None
        self.fired = False

    def update(self, now, point):
        if not isfinite(now):
            raise ValueError("time must be finite")
        gap = self.last_time is not None and (
            now < self.last_time or now - self.last_time > self.max_gap
        )
        self.last_time = now
        if point is None or not all(isfinite(v) for v in point):
            self.started = None
            return False
        if self.anchor is None or dist(point, self.anchor) > self.radius:
            self.anchor, self.started, self.fired = tuple(point), now, False
            return False
        if self.fired:
            return False
        if gap or self.started is None:
            self.started = now
        if now - self.started >= self.seconds:
            self.fired = True
            return True
        return False
