"""Continuous dwell in an application-owned region. No OS actions."""

from math import isfinite


class RegionDwell:
    """Accumulate observed in-region time until ``seconds`` is reached.

    Only intervals between consecutive same-region observations (at most
    ``max_gap`` apart) count. A missing measurement (blink, no face, late frame)
    may hold the progress for up to ``max_interruption`` seconds after the last
    in-region observation; the interruption itself is never credited, so a hold
    can only delay a selection. A valid point outside the region, another region,
    a longer interruption or out-of-order time resets the dwell.
    """

    def __init__(self, seconds=1.2, max_gap=0.3, max_interruption=0.5):
        if not all(isfinite(x) and x > 0 for x in (seconds, max_gap, max_interruption)):
            raise ValueError("Invalid dwell timing")
        self.seconds, self.max_gap = seconds, max_gap
        self.max_interruption = max_interruption
        self.reset()

    def reset(self):
        self.target = self.started = self.last = self.interrupted = None
        self.uncredited = 0.0
        self.progress = 0.0
        self.fired = False

    def update(self, now, target):
        if not isfinite(now):
            raise ValueError("Invalid timestamp")
        if target is None:
            self.reset()
            return False
        held = self.interrupted is not None
        if (
            target != self.target
            or self.last is None
            or now < self.last
            or now - self.last > (self.max_interruption if held else self.max_gap)
        ):
            self.target, self.started, self.fired = target, now, False
            self.uncredited = 0.0
        elif held:
            self.uncredited += now - self.last
        self.interrupted = None
        self.last = now
        observed = now - self.started - self.uncredited
        self.progress = min(1.0, max(0.0, observed / self.seconds))
        if self.progress >= 1 and not self.fired:
            self.fired = True
            return True
        return False

    def missing(self, now):
        """Record a measurement gap; it never completes or advances a dwell."""
        if not isfinite(now):
            raise ValueError("Invalid timestamp")
        if self.target is None:
            return
        if now < self.last or now - self.last > self.max_interruption:
            self.reset()
        elif self.interrupted is None:
            self.interrupted = now
