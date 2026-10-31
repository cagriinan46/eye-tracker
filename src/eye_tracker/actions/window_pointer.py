"""Move-only mapping for a bounded desktop demonstration; never emits a click."""

from math import exp, hypot, isfinite


def window_point(point, region):
    if point is None or len(point) != 2 or not all(isfinite(v) and 0 <= v <= 1 for v in point):
        return None
    x, y, w, h = region
    if not all(isfinite(v) for v in region) or w < 1 or h < 1:
        return None
    return (x + min(w - 1, point[0] * w), y + min(h - 1, point[1] * h))


class PointerSmoother:
    """Display-only glide of the cursor toward the latest gaze estimate.

    Gaze estimates arrive at inference rate (about 8 Hz for UniGaze) while the
    cursor is redrawn at 60 Hz. Instead of jumping at each estimate, the shown
    point approaches it exponentially: the time constant shrinks from ``slow``
    for small fixation jitter to ``fast`` for moves of ``distance`` pixels or
    more, so large gaze shifts follow with little added delay. It never passes
    the estimate or extrapolates, and it does not affect dwell selection. A
    missing estimate moves nothing; after ``max_gap`` seconds it snaps instead
    of gliding from an old position.
    """

    def __init__(self, fast=0.03, slow=0.1, distance=80.0, max_gap=0.15):
        if not all(isfinite(v) and v > 0 for v in (fast, slow, distance, max_gap)):
            raise ValueError("Invalid pointer smoothing")
        if fast > slow:
            raise ValueError("fast time constant must not exceed slow")
        self.fast, self.slow, self.distance, self.max_gap = fast, slow, distance, max_gap
        self.reset()

    def reset(self):
        self.point = self.last = None

    def update(self, now, target):
        if not isfinite(now):
            raise ValueError("Invalid timestamp")
        if target is None or len(target) != 2 or not all(isfinite(v) for v in target):
            return None
        x, y = target
        if self.point is None or now < self.last or now - self.last > self.max_gap:
            self.point = (x, y)
        else:
            px, py = self.point
            dx, dy = x - px, y - py
            gap = hypot(dx, dy)
            tau = self.slow + (self.fast - self.slow) * min(1.0, gap / self.distance)
            alpha = 1 - exp(-(now - self.last) / tau)
            # Stop sub-pixel creeping once the remaining distance is invisible.
            self.point = (x, y) if gap * (1 - alpha) < 0.5 else (px + alpha * dx, py + alpha * dy)
        self.last = now
        return self.point
