"""Balanced same-Y target schedule for conditional Issue #52 capture."""

from validation.real_calibration import CALIBRATION_TARGETS, Presentation, Target


def build_schedule() -> tuple[Presentation, ...]:
    """Mirror both x and y order so each coordinate is revisited later."""
    calibration = [Presentation("calibration", target, 1) for target in CALIBRATION_TARGETS]
    first = [
        Presentation("diagnostic", Target(f"P-{row}-{column}", x, y), 1)
        for row, y in enumerate((0.2, 0.5, 0.8), start=1)
        for column, x in enumerate((0.2, 0.5, 0.8), start=1)
    ]
    second = [Presentation("diagnostic", item.target, 2) for item in reversed(first)]
    return tuple(calibration + first + second)
