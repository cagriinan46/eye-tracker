"""Frozen Issue #156 protocol: shared calibration, candidate order, targets, constants."""

import random
from dataclasses import dataclass
from math import cos, radians, sin

from experiments.head_pointer.signals import CANDIDATES

SEED = 156

# Calibration: 3x3 grid, nose pointed at each dot, order shuffled.
CALIBRATION_POSITIONS = (0.1, 0.5, 0.9)
SETTLE_SECONDS = 0.8
SAMPLE_SECONDS = 1.0
MIN_FRAMES_PER_POINT = 5
MIN_POINTS = 7  # of 9 presentations, per candidate

# Filter shared by every candidate (screen pixels, seconds).
ONE_EURO_MIN_CUTOFF = 1.0
ONE_EURO_BETA = 0.01
ONE_EURO_D_CUTOFF = 1.0
GAP_RESET_SECONDS = 0.5  # longer face loss restarts the filter

# Target test.
TARGET_DIAMETERS = (30, 60)  # logical pixels
TARGET_ANGLES = tuple(range(0, 360, 45))  # eight directions on an ellipse
TARGET_RADII = (0.40, 0.38)  # fraction of width / height from the centre
PRACTICE_TRIALS = 4
DWELL_SECONDS = 0.8
TIMEOUT_SECONDS = 8.0
FEEDBACK_SECONDS = 0.4

# Frozen winner rule.
MAX_TIMEOUTS_PER_SESSION = 1
TIE_FRACTION = 0.05

SESSION_ORDER = {
    "A": CANDIDATES,
    "B": tuple(reversed(CANDIDATES)),
}
SESSIONS = tuple(SESSION_ORDER)


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    index: int
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class TargetTrial:
    candidate: str
    number: int  # 1-based within the candidate block, practice included
    practice: bool
    x: float  # normalized screen position
    y: float
    diameter: int


def calibration_schedule(seed: int = SEED) -> tuple[CalibrationPoint, ...]:
    cells = [(x, y) for y in CALIBRATION_POSITIONS for x in CALIBRATION_POSITIONS]
    random.Random(f"{seed}-calibration").shuffle(cells)
    return tuple(CalibrationPoint(i, x, y) for i, (x, y) in enumerate(cells, start=1))


def target_position(angle_deg: int) -> tuple[float, float]:
    rx, ry = TARGET_RADII
    return (0.5 + rx * cos(radians(angle_deg)), 0.5 - ry * sin(radians(angle_deg)))


def target_schedule(session: str, seed: int = SEED) -> tuple[TargetTrial, ...]:
    """Practice then 16 scored targets (8 directions x 2 sizes) per candidate block."""
    if session not in SESSION_ORDER:
        raise ValueError(f"unknown session {session!r}")
    generator = random.Random(f"{seed}-{session}-targets")
    trials: list[TargetTrial] = []
    for candidate in SESSION_ORDER[session]:
        practice = [
            (generator.choice(TARGET_ANGLES), max(TARGET_DIAMETERS)) for _ in range(PRACTICE_TRIALS)
        ]
        scored = [(a, d) for a in TARGET_ANGLES for d in TARGET_DIAMETERS]
        generator.shuffle(scored)
        # Never repeat the same position twice in a row (no movement needed).
        for i in range(1, len(scored)):
            if scored[i][0] == scored[i - 1][0]:
                j = next(
                    (k for k in range(i + 1, len(scored)) if scored[k][0] != scored[i - 1][0]),
                    None,
                )
                if j is not None:
                    scored[i], scored[j] = scored[j], scored[i]
        for number, (angle, diameter) in enumerate(practice + scored, start=1):
            x, y = target_position(angle)
            trials.append(TargetTrial(candidate, number, number <= PRACTICE_TRIALS, x, y, diameter))
    return tuple(trials)
