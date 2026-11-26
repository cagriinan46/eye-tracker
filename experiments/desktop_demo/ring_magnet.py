"""Determine assisted pointer location from an unassisted ring."""


class RingMagnet:
    def __init__(self, radius=45, separation=12, dwell=0.22):
        self.radius = radius
        self.separation = separation
        self.dwell = dwell
        self.reset()

    def reset(self):
        self.key = self.started = self.last = self.locked = None
        self.status = "idle"

    def update(self, stamp, point, candidates):
        ranked = sorted(
            ((rect.distance_to(*point), key, rect, enabled) for key, rect, enabled in candidates),
            key=lambda candidate: candidate[0],
        )
        reason = None
        if not ranked:
            reason = "no_targets"
        elif ranked[0][0] > self.radius:
            reason = "outside_ring"
        elif not ranked[0][3]:
            reason = "unverified_target"
        elif len(ranked) > 1 and ranked[1][0] - ranked[0][0] < self.separation:
            reason = "ambiguous"
        if reason:
            self.reset()
            self.status = reason
            return point
        _, key, rect, _ = ranked[0]
        if self.last is None or key != self.key or not 0 <= stamp - self.last <= 0.3:
            self.key, self.started, self.locked = key, stamp, None
        self.last = stamp
        if stamp - self.started >= self.dwell:
            self.locked = rect
            self.status = "locked"
            return rect.center
        self.status = "waiting"
        return point
