"""Interleave identical center checks without changing held-out trial order."""

from validation.real_calibration import (
    CALIBRATION_TARGETS,
    Presentation,
    Target,
    build_presentations,
)

CENTER = Target("CENTER", 0.5, 0.5)
VALIDATION_BLOCK_SIZE = 4


def build_checkpoint_schedule(seed: int = 42) -> tuple[Presentation, ...]:
    """Use the nine/16 baseline protocol plus center checkpoints 0 through 4."""
    original = build_presentations(seed=seed)
    calibration = original[: len(CALIBRATION_TARGETS)]
    validation = original[len(CALIBRATION_TARGETS) :]
    schedule = list(calibration)
    schedule.append(Presentation("checkpoint", CENTER, 0))
    for offset in range(0, len(validation), VALIDATION_BLOCK_SIZE):
        schedule.extend(validation[offset : offset + VALIDATION_BLOCK_SIZE])
        schedule.append(Presentation("checkpoint", CENTER, offset // VALIDATION_BLOCK_SIZE + 1))
    return tuple(schedule)
