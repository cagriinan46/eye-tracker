"""Continuous dwell in an application-owned region. No OS actions."""

from math import isfinite


class RegionDwell:
    def __init__(self, seconds=1.2, max_gap=0.3):
        if not all(isfinite(x) and x > 0 for x in (seconds, max_gap)):
            raise ValueError("Invalid dwell timing")
        self.seconds, self.max_gap = seconds, max_gap
        self.reset()

    def reset(self):
        self.target = self.started = self.last = None
        self.progress = 0.0
        self.fired = False

    def update(self, now, target):
        if not isfinite(now):
            raise ValueError("Invalid timestamp")
        if target is None:
            self.reset()
            return False
        if (
            target != self.target
            or self.last is None
            or now < self.last
            or now - self.last > self.max_gap
        ):
            self.target, self.started, self.fired = target, now, False
        self.last = now
        self.progress = min(1.0, max(0.0, (now - self.started) / self.seconds))
        if self.progress >= 1 and not self.fired:
            self.fired = True
            return True
        return False
