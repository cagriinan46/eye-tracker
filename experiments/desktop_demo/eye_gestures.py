"""Winks, long blinks and smiles from MediaPipe blendshape scores (Issue #160).

Thresholds come from Fatih's face-gesture recording (``face_gestures_check``,
2026-11-28, one session; see the desktop demo README). His voluntary winks also
partly close the other eye, so a closure is classified when it ends, from its
duration and its mean right-minus-left asymmetry, not from one eye being open:

- natural blinks: 0.30-0.50 s, mean asymmetry -0.11..-0.02
- right winks: 0.40-0.80 s, +0.10..+0.17
- left winks: 0.63-0.90 s, -0.17..-0.06
- deliberate long closures: 1.20-1.67 s
- smiles: score about 0.8 for 0.3-1.3 s; at most 0.06 at rest or while talking
"""

CLOSE_START = 0.45  # an episode starts when either eye reaches this score
CLOSE_END = 0.40  # and ends when both are below this
RIGHT_ASYMMETRY = 0.07  # mean(right - left) at or above: right wink
LEFT_ASYMMETRY = -0.06  # mean(right - left) at or below: left wink (if long enough)
RIGHT_WINK_MIN_SECONDS = 0.25
LEFT_WINK_MIN_SECONDS = 0.55  # longer than this user's natural blinks
WINK_MAX_SECONDS = 1.0
LONG_BLINK_SECONDS = 1.0  # both eyes closed this long: "long_blink" (stops head scroll)
SMILE_ON = 0.5
SMILE_OFF = 0.3
SMILE_HOLD_SECONDS = 0.4
REFRACTORY_SECONDS = 0.35
MAX_GAP_SECONDS = 0.25
GESTURE_ACTIONS = ("left", "right", "off")
# MediaPipe's eyeBlinkLeft/eyeBlinkRight are the user's own left/right eyes on the
# unmirrored camera frame: in the recording, right winks raised eyeBlinkRight most.
BLENDSHAPE_LEFT_IS_USER_LEFT = True


def user_scores(sample):
    """``(stamp, eyeBlinkLeft, eyeBlinkRight[, smile])`` -> user-eye order + smile."""
    stamp, first, second, *rest = sample
    smile = rest[0] if rest else None
    if BLENDSHAPE_LEFT_IS_USER_LEFT:
        return stamp, first, second, smile
    return stamp, second, first, smile


class EyeGestures:
    def __init__(self):
        self.last_event = None
        self.reset()

    def reset(self):
        self.start = None
        self.asymmetry = []
        self.long_fired = False
        self.smile_since = None
        self.smile_fired = False
        self.last = None

    @property
    def pending(self):
        """True while an eye closure (a possible wink) is in progress."""
        return self.start is not None

    def _emit(self, events, name, stamp):
        if self.last_event is None or stamp - self.last_event >= REFRACTORY_SECONDS:
            events.append(name)
            self.last_event = stamp

    def update(self, stamp, left, right, smile=None):
        events = []
        if self.last is not None and stamp <= self.last:
            return events  # the desktop loop may hand over the same samples twice
        if self.last is not None and stamp - self.last > MAX_GAP_SECONDS:
            self.reset()
        if left is None or right is None:
            self.reset()
            return events
        self.last = stamp
        closed = max(left, right) >= (CLOSE_END if self.start is not None else CLOSE_START)
        if closed:
            if self.start is None:
                self.start, self.asymmetry, self.long_fired = stamp, [], False
            self.asymmetry.append(right - left)
            both = min(left, right) >= CLOSE_START
            if both and not self.long_fired and stamp - self.start >= LONG_BLINK_SECONDS:
                self.long_fired = True
                events.append("long_blink")
        elif self.start is not None:
            duration = stamp - self.start
            mean = sum(self.asymmetry) / len(self.asymmetry)
            if not self.long_fired and duration <= WINK_MAX_SECONDS:
                if mean >= RIGHT_ASYMMETRY and duration >= RIGHT_WINK_MIN_SECONDS:
                    self._emit(events, "wink_right", stamp)
                elif mean <= LEFT_ASYMMETRY and duration >= LEFT_WINK_MIN_SECONDS:
                    self._emit(events, "wink_left", stamp)
            self.start = None
        if smile is not None:
            if self.start is not None or smile < SMILE_OFF:
                # A squint during a wink raises the smile score; never count it.
                self.smile_since = None
                if smile < SMILE_OFF:
                    self.smile_fired = False
            elif smile >= SMILE_ON and not self.smile_fired:
                if self.smile_since is None:
                    self.smile_since = stamp
                if stamp - self.smile_since >= SMILE_HOLD_SECONDS:
                    self.smile_fired = True
                    self._emit(events, "smile", stamp)
        return events

    def feed(self, samples):
        """Process raw ``(stamp, eyeBlinkLeft, eyeBlinkRight[, smile])`` samples in order."""
        events = []
        for sample in samples or ():
            events.extend(self.update(*user_scores(sample)))
        return events


def scroll_step(offset_px, dead_zone=40.0, gain=0.25, limit=60.0):
    """Head-scroll pixels per sample from the cursor's vertical offset (down positive)."""
    magnitude = max(0.0, abs(offset_px) - dead_zone) * gain
    magnitude = min(limit, magnitude)
    return round(magnitude if offset_px >= 0 else -magnitude)
