"""Causal fixation filter for the desktop pointer and gaze hit testing."""

from collections import deque
from math import dist
from statistics import median


class DesktopGazeFilter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.samples = deque(maxlen=3)
        self.stamp = self.point = None

    def update(self, stamp, point):
        if point is None:
            return None
        if self.stamp is not None:
            if stamp <= self.stamp:
                return self.point
            if stamp - self.stamp > 0.45:
                self.reset()
        self.stamp = stamp
        self.samples.append(point)
        if self.point is None:
            self.point = point
        if len(self.samples) == 3:
            candidate = tuple(median(axis) for axis in zip(*self.samples, strict=True))
            gap = dist(self.point, candidate)
            if gap > 55 and dist(self.samples[-2], self.samples[-1]) > 45:
                return self.point
            if gap > 16:
                gain = min(1.0, (gap - 16) / 52)
                self.point = tuple(
                    old + gain * (new - old) for old, new in zip(self.point, candidate, strict=True)
                )
        return self.point


class HeldDirection:
    """Turn a maintained direction into a bounded, continuous pixel offset."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.direction = self.since = self.last_frame = None

    def step(self, now, direction):
        if direction is None:
            self.reset()
            return 0.0
        if direction != self.direction:
            self.direction, self.since, self.last_frame = direction, now, now
        elapsed = now - self.since - 0.30
        dt = min(max(0.0, now - self.last_frame), 0.05)
        self.last_frame = now
        return (28 + 124 * min(1.0, elapsed / 1.2)) * dt if elapsed >= 0 else 0.0
