"""Fire once when a key is held long enough, so ordinary typing taps never trigger."""

RECENTRE_HOLD_SECONDS = 0.35
R_KEY_CODE = 15  # macOS virtual key code for R


class HoldKey:
    def __init__(self, hold=RECENTRE_HOLD_SECONDS):
        self.hold = hold
        self.since = None
        self.fired = False

    def update(self, now, down):
        if not down:
            self.since, self.fired = None, False
            return False
        if self.since is None:
            self.since = now
        if not self.fired and now - self.since >= self.hold:
            self.fired = True
            return True
        return False
