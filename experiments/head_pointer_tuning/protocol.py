"""Frozen Issue #158 protocol: three RAY conditions sharing the #156 test."""

import random
from dataclasses import dataclass

from experiments.head_pointer import protocol as base

SEED = 158
SIGNAL = "RAY"  # Issue #156 winner


@dataclass(frozen=True, slots=True)
class Condition:
    name: str
    min_cutoff: float
    beta: float
    gain: float


CONDITIONS = (
    Condition("BASE", base.ONE_EURO_MIN_CUTOFF, base.ONE_EURO_BETA, 1.0),
    Condition("STEADY", 0.3, 0.03, 1.0),
    Condition("STEADY_GAIN", 0.3, 0.03, 1.5),
)
CONDITION_NAMES = tuple(c.name for c in CONDITIONS)
BY_NAME = {c.name: c for c in CONDITIONS}
SESSION_ORDER = {"A": CONDITION_NAMES, "B": tuple(reversed(CONDITION_NAMES))}
SESSIONS = tuple(SESSION_ORDER)
COMFORT_SCALE = (1, 5)
RECENTRE_KEY = "r"


@dataclass(frozen=True, slots=True)
class TargetTrial:
    candidate: str  # condition name; key kept for the shared #156 analysis
    number: int
    practice: bool
    x: float
    y: float
    diameter: int


def target_schedule(session: str, seed: int = SEED) -> tuple[TargetTrial, ...]:
    """The #156 block design (practice + 8 directions x 2 sizes) per condition."""
    if session not in SESSION_ORDER:
        raise ValueError(f"unknown session {session!r}")
    generator = random.Random(f"{seed}-{session}-targets")
    trials: list[TargetTrial] = []
    for name in SESSION_ORDER[session]:
        practice = [
            (generator.choice(base.TARGET_ANGLES), max(base.TARGET_DIAMETERS))
            for _ in range(base.PRACTICE_TRIALS)
        ]
        scored = [(a, d) for a in base.TARGET_ANGLES for d in base.TARGET_DIAMETERS]
        generator.shuffle(scored)
        for i in range(1, len(scored)):
            if scored[i][0] == scored[i - 1][0]:
                j = next(
                    (k for k in range(i + 1, len(scored)) if scored[k][0] != scored[i - 1][0]),
                    None,
                )
                if j is not None:
                    scored[i], scored[j] = scored[j], scored[i]
        for number, (angle, diameter) in enumerate(practice + scored, start=1):
            x, y = base.target_position(angle)
            trials.append(TargetTrial(name, number, number <= base.PRACTICE_TRIALS, x, y, diameter))
    return tuple(trials)
