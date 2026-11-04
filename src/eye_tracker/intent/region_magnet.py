"""Gradual pull toward an application-owned region near a gaze point. No OS actions."""

from math import hypot, isfinite


class RegionMagnet:
    """Pull a point toward the nearest region that overlaps a ring around it.

    The decision always uses the unassisted point, so looking away releases the
    pull at once and the assisted point can never trap the user on a control.
    Pull strength grows over ``pull_seconds`` while one region stays selected and
    restarts on any change. ``switch_margin`` keeps adjacent controls from
    alternating on small jitter. Regions are normalized (x, y, w, h); ``size`` is
    the viewport in pixels, in which ``radius`` and ``switch_margin`` are given.
    """

    def __init__(self, radius=35.0, pull_seconds=0.8, max_gap=0.5, switch_margin=20.0):
        if not all(isfinite(v) and v > 0 for v in (radius, pull_seconds, max_gap, switch_margin)):
            raise ValueError("Invalid magnet settings")
        self.radius, self.pull_seconds = radius, pull_seconds
        self.max_gap, self.switch_margin = max_gap, switch_margin
        self.reset()

    def reset(self):
        self.target = self.last = None
        self.progress = 0.0

    @property
    def settled(self):
        return self.target is not None and self.progress >= 1

    @property
    def strength(self):
        # Starts and ends gently, so the cursor is not yanked toward the control.
        return self.progress * self.progress * (3 - 2 * self.progress)

    def _choose(self, point, regions, size):
        distances = {}
        for name, (x, y, w, h) in regions.items():
            dx = max(x * size[0] - point[0], 0.0, point[0] - (x + w) * size[0])
            dy = max(y * size[1] - point[1], 0.0, point[1] - (y + h) * size[1])
            distance = hypot(dx, dy)
            if distance <= self.radius:
                distances[name] = distance
        if not distances:
            return None
        nearest = min(distances, key=distances.get)
        if (
            self.target in distances
            and distances[self.target] - distances[nearest] < self.switch_margin
        ):
            return self.target
        return nearest

    def update(self, now, point, regions, size):
        """Return the assisted normalized point for one unassisted normalized point."""
        if not isfinite(now):
            raise ValueError("Invalid timestamp")
        if self.last is not None and (now < self.last or now - self.last > self.max_gap):
            self.reset()
        pixel = (point[0] * size[0], point[1] * size[1])
        target = self._choose(pixel, regions, size)
        if target != self.target:
            self.target, self.progress = target, 0.0
        elif target is not None:
            self.progress = min(1.0, self.progress + (now - self.last) / self.pull_seconds)
        self.last = now
        if target is None:
            return list(point)
        x, y, w, h = regions[target]
        center = (x + w / 2, y + h / 2)
        pull = self.strength
        return [point[0] + pull * (center[0] - point[0]), point[1] + pull * (center[1] - point[1])]
