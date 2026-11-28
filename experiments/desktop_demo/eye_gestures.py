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

A second recording (``face-gestures-fatih-2``, extended phases) added held face
gestures and re-tested the wink thresholds on new data:

- jawOpen: 0.84-0.91 for about 2 s when opening the mouth; at most 0.27 while
  talking; it shifts the head-pitch reading by up to 11 degrees
- browInnerUp: 0.94-0.96 for 0.6-1.3 s, only when raising the brows; 4-5 degrees
- mouthPucker: 1.0 for 0.9-2.7 s, but talking also reached 0.7+ for 0.73 s
- winks in that recording: 6 right, 7 left detected for 5 requested each, no
  wrong side and no false events while talking or blinking
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
SMILING = 0.15  # above rest (max 0.06): smiling has begun, so the cursor is held
# Held face gestures: blendshape, fire level, re-arm level, cursor-hold level, hold (s).
HELD = {
    "mouth_open": ("jawOpen", 0.5, 0.3, 0.3, 0.5),
    "pucker": ("mouthPucker", 0.7, 0.4, 0.5, 0.8),
    "brows": ("browInnerUp", 0.6, 0.4, 0.5, 0.4),
}
# Scores at or above these during an eye closure mean it is part of another
# expression, not a wink (none of them occurred during recorded winks).
WINK_VETO = {"mouth_open": 0.3, "pucker": 0.5, "brows": 0.6}
FACE_GESTURES = ("smile", *HELD)
SMILE_HOLD_SECONDS = 0.4
REFRACTORY_SECONDS = 0.35
MAX_GAP_SECONDS = 0.25
GESTURE_ACTIONS = ("left", "right", "off")
# MediaPipe's eyeBlinkLeft/eyeBlinkRight are the user's own left/right eyes on the
# unmirrored camera frame: in the recording, right winks raised eyeBlinkRight most.
BLENDSHAPE_LEFT_IS_USER_LEFT = True


def user_scores(sample):
    """``(stamp, eyeBlinkLeft, eyeBlinkRight[, smile, jaw, pucker, brows])`` in user order."""
    stamp, first, second, *rest = sample
    if BLENDSHAPE_LEFT_IS_USER_LEFT:
        return (stamp, first, second, *rest)
    return (stamp, second, first, *rest)


SENSITIVITY = {  # (right, left) mean-asymmetry thresholds
    "high": (0.05, -0.04),
    "medium": (RIGHT_ASYMMETRY, LEFT_ASYMMETRY),
    "low": (0.10, -0.09),
}


class EyeGestures:
    def __init__(self):
        self.last_event = None
        self.smiling = False
        self.right_asymmetry, self.left_asymmetry = RIGHT_ASYMMETRY, LEFT_ASYMMETRY
        self.right_min, self.left_min = RIGHT_WINK_MIN_SECONDS, LEFT_WINK_MIN_SECONDS
        self.wink_max, self.long_blink = WINK_MAX_SECONDS, LONG_BLINK_SECONDS
        self.smile_hold = SMILE_HOLD_SECONDS
        self.holds = {name: spec[4] for name, spec in HELD.items()}
        self.active = set()
        self.reset()

    def configure(self, settings):
        """Per-user values from the preferences (milliseconds and a sensitivity)."""
        self.right_asymmetry, self.left_asymmetry = SENSITIVITY[settings["wink_sensitivity"]]
        self.right_min = settings["wink_right_min_ms"] / 1000
        self.left_min = settings["wink_left_min_ms"] / 1000
        self.wink_max = settings["wink_max_ms"] / 1000
        self.long_blink = settings["long_blink_ms"] / 1000
        self.smile_hold = settings["smile_hold_ms"] / 1000
        for name in HELD:
            self.holds[name] = settings[f"{name}_hold_ms"] / 1000

    def reset(self):
        self.start = None
        self.asymmetry = []
        self.long_fired = False
        self.smile_since = None
        self.smile_fired = False
        self.smiling = False
        self.vetoed = False
        self.held_since = dict.fromkeys(HELD)
        self.held_fired = dict.fromkeys(HELD, False)
        self.active = set()
        self.last = None

    @property
    def pending(self):
        """True while an eye closure (a possible wink) is in progress."""
        return self.start is not None

    def _emit(self, events, name, stamp):
        if self.last_event is None or stamp - self.last_event >= REFRACTORY_SECONDS:
            events.append(name)
            self.last_event = stamp

    def update(self, stamp, left, right, smile=None, *held):
        events = []
        if self.last is not None and stamp <= self.last:
            return events  # the desktop loop may hand over the same samples twice
        if self.last is not None and stamp - self.last > MAX_GAP_SECONDS:
            self.reset()
        if left is None or right is None:
            self.reset()
            return events
        self.last = stamp
        values = dict(zip(HELD, held, strict=False))
        closed = max(left, right) >= (CLOSE_END if self.start is not None else CLOSE_START)
        if closed:
            if self.start is None:
                self.start, self.asymmetry, self.long_fired = stamp, [], False
                self.vetoed = False
            self.asymmetry.append(right - left)
            self.vetoed |= any(
                values.get(name) is not None and values[name] >= level
                for name, level in WINK_VETO.items()
            )
            both = min(left, right) >= CLOSE_START
            if both and not self.long_fired and stamp - self.start >= self.long_blink:
                self.long_fired = True
                events.append("long_blink")
        elif self.start is not None:
            duration = stamp - self.start
            mean = sum(self.asymmetry) / len(self.asymmetry)
            if not self.long_fired and not self.vetoed and duration <= self.wink_max:
                if mean >= self.right_asymmetry and duration >= self.right_min:
                    self._emit(events, "wink_right", stamp)
                elif mean <= self.left_asymmetry and duration >= self.left_min:
                    self._emit(events, "wink_left", stamp)
            self.start = None
        self.active = set()
        for name, (_, fire, rearm, hold_level, _) in HELD.items():
            value = values.get(name)
            if value is None:
                continue
            if value >= hold_level:
                self.active.add(name)
            if value < rearm:
                self.held_since[name], self.held_fired[name] = None, False
            elif value >= fire and not self.held_fired[name] and self.start is None:
                if self.held_since[name] is None:
                    self.held_since[name] = stamp
                if stamp - self.held_since[name] >= self.holds[name]:
                    self.held_fired[name] = True
                    self._emit(events, name, stamp)
            elif value < fire:
                self.held_since[name] = None
        if smile is not None:
            self.smiling = smile >= SMILING
            if self.smiling:
                self.active.add("smile")
            if self.start is not None or smile < SMILE_OFF:
                # A squint during a wink raises the smile score; never count it.
                self.smile_since = None
                if smile < SMILE_OFF:
                    self.smile_fired = False
            elif smile >= SMILE_ON and not self.smile_fired:
                if self.smile_since is None:
                    self.smile_since = stamp
                if stamp - self.smile_since >= self.smile_hold:
                    self.smile_fired = True
                    self._emit(events, "smile", stamp)
        return events

    def feed(self, samples):
        """Process raw ``(stamp, eyeBlinkLeft, eyeBlinkRight, ...)`` samples in order."""
        events = []
        for sample in samples or ():
            events.extend(self.update(*user_scores(sample)))
        return events


def scroll_step(offset_px, dead_zone=40.0, gain=0.25, limit=60.0):
    """Head-scroll pixels per sample from the cursor's vertical offset (down positive)."""
    magnitude = max(0.0, abs(offset_px) - dead_zone) * gain
    magnitude = min(limit, magnitude)
    return round(magnitude if offset_px >= 0 else -magnitude)
