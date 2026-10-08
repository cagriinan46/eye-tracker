"""Frozen Issue #77 presentation schedule: checkpoints, 5×5 calibration, 4×4 validation."""

import random

from validation.real_calibration import Presentation, Target

CALIBRATION_VALUES = (0.1, 0.3, 0.5, 0.7, 0.9)
VALIDATION_VALUES = (0.2, 0.4, 0.6, 0.8)
CHECKPOINT_TARGETS = (
    Target("K-top", 0.5, 0.1),
    Target("K-center", 0.5, 0.5),
    Target("K-bottom", 0.5, 0.9),
)
CALIBRATION_TARGETS = tuple(
    Target(f"C-{row}-{column}", x, y)
    for row, y in enumerate(CALIBRATION_VALUES, start=1)
    for column, x in enumerate(CALIBRATION_VALUES, start=1)
)
VALIDATION_TARGETS = tuple(
    Target(f"V-{row}-{column}", x, y)
    for row, y in enumerate(VALIDATION_VALUES, start=1)
    for column, x in enumerate(VALIDATION_VALUES, start=1)
)


def _checkpoints(block: int) -> list[Presentation]:
    return [Presentation("checkpoint", target, block) for target in CHECKPOINT_TARGETS]


def build_schedule(seed: int = 77) -> tuple[Presentation, ...]:
    """Shuffle calibration and validation so time is not confounded with screen row."""
    generator = random.Random(seed)
    calibration = [Presentation("calibration", target, 1) for target in CALIBRATION_TARGETS]
    validation = [Presentation("validation", target, 1) for target in VALIDATION_TARGETS]
    generator.shuffle(calibration)
    generator.shuffle(validation)
    return tuple(_checkpoints(1) + calibration + _checkpoints(2) + validation + _checkpoints(3))
