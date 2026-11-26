"""One-shot confirmation from sampled bilateral eyelid closures."""

from math import isfinite


class Confirmation:
    def __init__(self):
        self.reset()

    def reset(self):
        self.target = self.last = self.started = self.closed_at = self.first = None
        self.phase = "idle"

    def update(self, stamp, target, closed):
        if target is None or closed is None or not isfinite(stamp):
            self.reset()
            return self.phase
        if target != self.target or self.last is None or not 0 < stamp - self.last <= 0.3:
            self.reset()
            if not closed:
                self.target, self.started, self.last, self.phase = target, stamp, stamp, "aiming"
            return self.phase
        self.last = stamp
        if self.phase == "confirmed":
            return self.phase
        if self.phase == "aiming":
            if closed:
                self.started = None
            elif self.started is None:
                self.started = stamp
            elif stamp - self.started >= 1.2:
                self.phase = "armed"
            return self.phase
        if closed:
            if self.closed_at is None:
                self.closed_at = stamp
            elif stamp - self.closed_at > 0.35:
                self.reset()
            return self.phase
        if self.closed_at is None:
            if self.first is not None and stamp - self.first > 0.55:
                self.first = None
            return self.phase
        duration = stamp - self.closed_at
        open_gap = None if self.first is None else self.closed_at - self.first
        self.closed_at = None
        if 0.055 <= duration <= 0.35:
            if open_gap is not None and 0.07 <= open_gap <= 0.55:
                self.phase = "confirmed"
            else:
                self.first = stamp
        else:
            self.first = None
        return self.phase
