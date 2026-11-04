"""Hold isolated gaze outliers, such as frames around a blink. No OS actions."""

from math import hypot, isfinite


class GazeStabilizer:
    """Accept a large jump only when the following sample confirms it.

    Frames while the eyes close or reopen can pass validity checks and still point
    far away. A real saccade stays at its new position, so a jump over ``jump_px``
    is held until a second sample lands within ``confirm_px`` of it, which delays
    real saccades by one sample. A missing sample clears the pending jump, so
    outliers on both sides of a blink cannot confirm each other. ``max_hold`` stops
    scattered samples from freezing the point. Points are normalized; ``size`` is
    the viewport in pixels.
    """

    def __init__(self, jump_px=120.0, confirm_px=80.0, max_hold=0.4, max_gap=1.0):
        if not all(isfinite(v) and v > 0 for v in (jump_px, confirm_px, max_hold, max_gap)):
            raise ValueError("Invalid stabilizer settings")
        self.jump_px, self.confirm_px = jump_px, confirm_px
        self.max_hold, self.max_gap = max_hold, max_gap
        self.reset()

    def reset(self):
        self.point = self.pending = self.held_since = self.last = None

    def missing(self):
        self.pending = None

    def _distance(self, a, b, size):
        return hypot((a[0] - b[0]) * size[0], (a[1] - b[1]) * size[1])

    def update(self, now, point, size):
        if not isfinite(now):
            raise ValueError("Invalid timestamp")
        if self.last is not None and (now < self.last or now - self.last > self.max_gap):
            self.reset()
        self.last = now
        point = list(point)
        if self.point is None or self._distance(point, self.point, size) <= self.jump_px:
            return self._accept(point)
        confirmed = (
            self.pending is not None
            and self._distance(point, self.pending, size) <= self.confirm_px
        )
        if self.held_since is None:
            self.held_since = now
        if confirmed or now - self.held_since >= self.max_hold:
            return self._accept(point)
        self.pending = point
        return list(self.point)

    def _accept(self, point):
        self.point = point
        self.pending = self.held_since = None
        return list(point)
