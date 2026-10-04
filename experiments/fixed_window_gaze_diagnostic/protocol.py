"""Predeclared fixed-window protocol: progress depends only on elapsed time."""

from dataclasses import dataclass

from experiments.intentional_gaze_targeting.protocol import (
    CUE_ASSIGNMENT,
    ORDER_SEED,
    TARGETS,
    Trial,
    schedule,
)
from validation.real_calibration import (
    CALIBRATION_TARGETS,
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    Target,
)

PROTOCOL_NAME = "fixed_window_gaze_diagnostic"
PROTOCOL_VERSION = 1
CUE_SECONDS = 0.75
TARGET_SECONDS = 3.0
TRANSITION_SECONDS = 0.5
# Names are explicitly exported for callers; ordering is the existing frozen v1/v2 order.
__all__ = ["CALIBRATION_TARGETS", "schedule"]


@dataclass(frozen=True)
class ScreenContent:
    target: Target | None
    lines: tuple[str, ...] = ()


def screen_content(phase: str, trial: Trial | None = None) -> ScreenContent:
    if phase == "ready":
        return ScreenContent(
            None,
            (
                "READY - press SPACE to begin",
                "Measurement, not a game: acquisition is never graded.",
                "Each target stays visible for a fixed time; gaze output is not shown.",
                "Use natural relaxed eyes and comfortable posture; blink naturally.",
                "Look at the CENTER of the target; do not change eye opening or steer with head.",
                "Keep your physical setup reasonably consistent after calibration.",
                "Look at each cue, then the target until it disappears. q / Esc: cancel.",
            ),
        )
    if phase == "transition":
        return ScreenContent(None)
    if trial is not None and phase == "cue":
        return ScreenContent(Target(f"cue-{trial.target.name}", trial.cue_x, trial.cue_y))
    if trial is not None and phase in ("calibration", "target"):
        return ScreenContent(trial.target)
    raise ValueError("invalid screen phase or missing trial")


def configuration() -> dict:
    return {
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "order_seed": ORDER_SEED,
        "cue_seconds": CUE_SECONDS,
        "cue_assignment": CUE_ASSIGNMENT,
        "target_seconds": TARGET_SECONDS,
        "transition_seconds": TRANSITION_SECONDS,
        "calibration_settle_seconds": SETTLE_SECONDS,
        "calibration_sample_seconds": SAMPLE_SECONDS,
        "calibration_min_usable_samples": MIN_USABLE_SAMPLES,
        "target_centers": [
            {"target_id": t.name, "target_x": t.x, "target_y": t.y} for t in TARGETS
        ],
    }
