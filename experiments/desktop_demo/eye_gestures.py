"""One-eye winks and long blinks from per-eye blink scores (Issue #160).

Scores are MediaPipe ``eyeBlink`` blendshapes in [0, 1] for the user's own left and
right eye. A natural blink closes both eyes briefly and never counts as a wink.
"""

CLOSED = 0.5  # an eye at or above this score is closed
OTHER_OPEN = 0.35  # during a wink the other eye must stay at or below this
REOPENED = 0.3  # the winking eye counts as released at or below this
WINK_MIN_SECONDS = 0.12  # shorter closures are noise
WINK_MAX_SECONDS = 0.9  # longer one-eye closures are not a click
LONG_BLINK_SECONDS = 0.3  # both eyes closed this long: "long_blink" (stops head scroll)
REFRACTORY_SECONDS = 0.35
MAX_GAP_SECONDS = 0.25
WINK_ACTIONS = ("left", "right", "off")
# MediaPipe's eyeBlinkLeft/eyeBlinkRight relative to the user's own eyes on an
# unmirrored camera frame; verified live with Fatih (see README, Issue #160).
BLENDSHAPE_LEFT_IS_USER_LEFT = True


def user_eyes(sample):
    """``(stamp, eyeBlinkLeft, eyeBlinkRight)`` -> ``(stamp, user_left, user_right)``."""
    stamp, first, second = sample
    return (stamp, first, second) if BLENDSHAPE_LEFT_IS_USER_LEFT else (stamp, second, first)


class EyeGestures:
    def __init__(self):
        self.reset()
        self.last_event = None

    def reset(self):
        self.candidate = self.since = None
        self.spoiled = False
        self.both_since = None
        self.long_fired = False
        self.last = None

    @property
    def pending(self):
        """True while one eye is closing as a possible wink."""
        return self.candidate is not None

    def update(self, stamp, left, right):
        events = []
        if self.last is not None and stamp <= self.last:
            return events  # the desktop loop may hand over the same samples twice
        if (
            left is None
            or right is None
            or (self.last is not None and stamp - self.last > MAX_GAP_SECONDS)
        ):
            self.reset()
            if left is None or right is None:
                return events
        self.last = stamp
        if left >= CLOSED and right >= CLOSED:
            self.candidate = None  # a blink, not a wink
            if self.both_since is None:
                self.both_since = stamp
            if not self.long_fired and stamp - self.both_since >= LONG_BLINK_SECONDS:
                self.long_fired = True
                events.append("long_blink")
            return events
        self.both_since = None
        self.long_fired = False
        winking = (
            "left"
            if left >= CLOSED and right <= OTHER_OPEN
            else "right"
            if right >= CLOSED and left <= OTHER_OPEN
            else None
        )
        if self.candidate is None:
            if winking is not None:
                self.candidate, self.since, self.spoiled = winking, stamp, False
            return events
        own, other = (left, right) if self.candidate == "left" else (right, left)
        if stamp - self.since > WINK_MAX_SECONDS:
            self.spoiled = True
        if other > OTHER_OPEN:
            self.spoiled = True
        if own <= REOPENED:
            duration = stamp - self.since
            if (
                not self.spoiled
                and WINK_MIN_SECONDS <= duration <= WINK_MAX_SECONDS
                and (self.last_event is None or stamp - self.last_event >= REFRACTORY_SECONDS)
            ):
                events.append("wink_" + self.candidate)
                self.last_event = stamp
            self.candidate = None
        return events

    def feed(self, samples):
        """Process ``(stamp, left, right)`` samples in order; return all events."""
        events = []
        for sample in samples or ():
            events.extend(self.update(*user_eyes(sample)))
        return events


def scroll_step(offset_px, dead_zone=40.0, gain=0.25, limit=60.0):
    """Head-scroll pixels per sample from the cursor's vertical offset (down positive)."""
    magnitude = max(0.0, abs(offset_px) - dead_zone) * gain
    magnitude = min(limit, magnitude)
    return round(magnitude if offset_px >= 0 else -magnitude)
