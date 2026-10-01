"""Insert one post-calibration CENTER without changing held-out order."""

from validation.real_calibration import (
    CALIBRATION_TARGETS,
    Presentation,
    Target,
    build_presentations,
)

CENTER = Target("CENTER", 0.5, 0.5)


def build_schedule(seed: int = 42) -> tuple[Presentation, ...]:
    original = build_presentations(seed=seed)
    boundary = len(CALIBRATION_TARGETS)
    return original[:boundary] + (Presentation("anchor", CENTER, 1),) + original[boundary:]
