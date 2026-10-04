"""Fixed calibration, balanced targeting schedule, and display-only geometry."""

import random
from dataclasses import dataclass

from validation.real_calibration import Target

PROTOCOL_NAME = "coarse_gaze_targeting"
PROTOCOL_VERSION = 1
ORDER_SEED = 20261006
TARGET_HALF_WIDTH = 0.14
TARGET_HALF_HEIGHT = 0.14
DWELL_SECONDS = 0.300
TIMEOUT_SECONDS = 4.0
FEEDBACK_SECONDS = 0.5
TARGETS = tuple(
    Target(f"T-{row}-{column}", x, y)
    for row, y in enumerate((0.2, 0.5, 0.8), start=1)
    for column, x in enumerate((0.2, 0.5, 0.8), start=1)
)


@dataclass(frozen=True, slots=True)
class TargetingTrial:
    order: int
    block: int
    target: Target

    def identity(self) -> dict:
        return {
            "trial_order": self.order,
            "block": self.block,
            "target_id": self.target.name,
            "target_x": self.target.x,
            "target_y": self.target.y,
        }


@dataclass(frozen=True, slots=True)
class ScreenContent:
    kind: str
    target: Target | None
    lines: tuple[str, ...]


def schedule() -> tuple[TargetingTrial, ...]:
    """One seeded permutation, cyclically offset by three places per block."""
    base = random.Random(ORDER_SEED).sample(TARGETS, len(TARGETS))
    return tuple(
        TargetingTrial(
            (block - 1) * 9 + position + 1, block, base[(position + 3 * (block - 1)) % 9]
        )
        for block in (1, 2, 3)
        for position in range(9)
    )


def screen_content(phase: str, target: Target | None = None) -> ScreenContent:
    """Keep pre-run instructions and trial target/cursor display disjoint."""
    if phase == "calibration_ready":
        return ScreenContent(
            phase,
            None,
            (
                "READY - press SPACE to begin",
                "Use normal relaxed eye opening. Sit comfortably.",
                "Keep your head reasonably steady; natural blinking is allowed.",
                "q / Esc: cancel",
            ),
        )
    if phase == "targeting_ready":
        return ScreenContent(
            phase,
            None,
            (
                "TARGETING TEST - press SPACE to begin",
                "Look naturally at the highlighted target, not the moving cursor.",
                "The moving dot represents the current gaze estimate.",
                "Keep looking at the target until the trial completes.",
                "q / Esc: cancel",
            ),
        )
    if phase == "calibration" and target is not None:
        return ScreenContent(phase, target, ())
    if phase == "trial" and target is not None:
        return ScreenContent(phase, target, ())
    if phase in ("success", "timeout"):
        return ScreenContent(phase, None, ("ACQUIRED" if phase == "success" else "TIMEOUT",))
    raise ValueError("invalid display phase or missing target")


def inside_target(x: float, y: float, target: Target) -> bool:
    """Inclusive rectangle test on RAW, unclipped production predictions."""
    return abs(x - target.x) <= TARGET_HALF_WIDTH and abs(y - target.y) <= TARGET_HALF_HEIGHT


def cursor_pixel(x: float, y: float, width: int, height: int) -> tuple[int, int] | None:
    """Omit only the marker when a raw prediction is outside the visible screen."""
    if not 0 <= x <= 1 or not 0 <= y <= 1:
        return None
    return round(x * width), round(y * height)
