"""Frozen v2 target order, timed fixation cue, and target screen phases."""

from dataclasses import dataclass

from experiments.coarse_gaze_targeting_validation.protocol import ORDER_SEED as ORDER_SEED
from experiments.coarse_gaze_targeting_validation.protocol import TARGETS as TARGETS
from experiments.coarse_gaze_targeting_validation.protocol import schedule as v1_schedule
from validation.real_calibration import Target

PROTOCOL_NAME = "intentional_gaze_targeting"
PROTOCOL_VERSION = 2
TARGET_HALF_WIDTH = 0.10
TARGET_HALF_HEIGHT = 0.10
TARGET_DWELL_SECONDS = 1.0
TARGET_TIMEOUT_SECONDS = 5.0
FIXATION_CUE_SECONDS = 0.75
FEEDBACK_SECONDS = 0.5
CUE_ASSIGNMENT = "opposite_point_center_top_left_v1"


@dataclass(frozen=True, slots=True)
class Trial:
    order: int
    block: int
    target: Target
    cue_x: float
    cue_y: float

    def identity(self) -> dict:
        return {
            "trial_order": self.order,
            "block": self.block,
            "target_id": self.target.name,
            "target_x": self.target.x,
            "target_y": self.target.y,
            "cue_x": self.cue_x,
            "cue_y": self.cue_y,
        }


@dataclass(frozen=True, slots=True)
class ScreenContent:
    kind: str
    target: Target | None
    lines: tuple[str, ...]
    show_cursor: bool = False
    show_region: bool = False


def cue_for_target(target: Target) -> tuple[float, float]:
    """Predeclared opposite cue point, with a distinct center-target cue."""
    if target.x == target.y == 0.5:
        return 0.2, 0.2
    return round(1.0 - target.x, 10), round(1.0 - target.y, 10)


def schedule() -> tuple[Trial, ...]:
    """Preserve v1's seeded permutation and three block offsets exactly."""
    return tuple(
        Trial(item.order, item.block, item.target, *cue_for_target(item.target))
        for item in v1_schedule()
    )


def inside_region(
    x: float, y: float, center_x: float, center_y: float, half_width: float, half_height: float
) -> bool:
    """Inclusive acceptance on the raw, unclipped gaze prediction."""
    return abs(x - center_x) <= half_width + 1e-12 and abs(y - center_y) <= half_height + 1e-12


def screen_content(phase: str, trial: Trial | None = None) -> ScreenContent:
    if phase == "calibration_ready":
        return ScreenContent(
            phase,
            None,
            (
                "READY - press SPACE to begin",
                "Use natural relaxed eye opening and your normal comfortable posture.",
                "Keep the physical setup consistent; natural blinking is allowed.",
                "q / Esc: cancel",
            ),
        )
    if phase == "targeting_ready":
        return ScreenContent(
            phase,
            None,
            (
                "INTENTIONAL TARGETING TEST - press SPACE to begin",
                "Look at the fixation cue, then directly at TARGET when it appears.",
                "Do not chase the cursor, change eye opening, or steer with your head.",
                "Natural blinking is allowed. Failed trials are valid; do not game the test.",
                "q / Esc: cancel",
            ),
        )
    if phase == "calibration" and trial is not None:
        return ScreenContent(phase, trial.target, ())
    if phase == "cue" and trial is not None:
        return ScreenContent(phase, Target(f"C-{trial.target.name}", trial.cue_x, trial.cue_y), ())
    if phase == "target" and trial is not None:
        return ScreenContent(phase, trial.target, (), show_cursor=True, show_region=True)
    if phase in ("success", "timeout"):
        labels = {
            "success": "ACQUIRED",
            "timeout": "TARGET TIMEOUT",
        }
        return ScreenContent(phase, None, (labels[phase],))
    raise ValueError("invalid display phase or missing trial")
