"""Predeclared target sequence, shared with the controlled Issue #52 study."""

from experiments.vertical_position_variability.protocol import build_schedule


def schedule():
    """Nine calibration targets, then the same grid forward and in reverse."""
    return build_schedule()


def pass_name(phase: str, trial: int) -> str:
    if phase == "calibration" and trial == 1:
        return "calibration"
    if phase == "diagnostic" and trial in (1, 2):
        return "pass_a" if trial == 1 else "pass_b"
    raise ValueError("unexpected phase/trial in sensitivity protocol")
