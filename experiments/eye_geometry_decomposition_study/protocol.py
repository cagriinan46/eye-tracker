"""Predeclared balanced schedule and disjoint cue/target display content."""

import random
from dataclasses import dataclass

from validation.real_calibration import CALIBRATION_TARGETS, Presentation, Target

PROTOCOL_NAME = "eye_geometry_decomposition"
PROTOCOL_VERSION = 1
ORDER_SEED = 20261004
CUE_SECONDS = 1.5
CONDITIONS = (
    "comfortably_narrow",
    "slightly_narrow",
    "natural",
    "slightly_wide",
    "comfortably_wide",
)
INSTRUCTIONS = {
    "comfortably_narrow": "COMFORTABLY NARROW",
    "slightly_narrow": "SLIGHTLY NARROW",
    "natural": "NATURAL",
    "slightly_wide": "SLIGHTLY WIDE",
    "comfortably_wide": "COMFORTABLY WIDE",
}
TARGETS = (
    Target("upper", 0.5, 0.25),
    Target("center", 0.5, 0.50),
    Target("lower", 0.5, 0.75),
)


@dataclass(frozen=True, slots=True)
class ScreenContent:
    target: Target | None
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StudyPresentation:
    phase: str
    target: Target
    condition: str
    block: int
    order: int

    def capture_presentation(self) -> Presentation:
        return Presentation(self.phase, self.target, self.block)

    def identity(self) -> dict:
        return {
            "phase": self.phase,
            "target_id": self.target.name,
            "target_x": self.target.x,
            "target_y": self.target.y,
            "condition": self.condition,
            "block": self.block,
        }


def screen_content(item: StudyPresentation | None, phase: str) -> ScreenContent:
    """There is no fixation target during a cue and no text during sampling."""
    if phase == "ready":
        return ScreenContent(
            None,
            (
                "READY - press SPACE to begin",
                "Keep head and sitting position as constant as practical.",
                "First nine dots: normal, relaxed eye opening.",
                "Read each later cue; set opening BEFORE the dot appears.",
                "When cue disappears, look ONLY at the dot and hold that state.",
                "Blink naturally; avoid strain. q / Esc: cancel.",
            ),
        )
    if item is None:
        raise ValueError("a presentation is required after ready")
    if phase == "cue" and item.phase == "diagnostic":
        return ScreenContent(None, (INSTRUCTIONS[item.condition],))
    if phase in ("settling", "sampling"):
        return ScreenContent(item.target, ())
    raise ValueError("unexpected display phase")


def schedule() -> tuple[StudyPresentation, ...]:
    """Seeded condition permutation with cyclic position balance and row rotation."""
    base = random.Random(ORDER_SEED).sample(list(CONDITIONS), len(CONDITIONS))
    plan = [
        StudyPresentation("calibration", target, "natural", 0, index)
        for index, target in enumerate(CALIBRATION_TARGETS, start=1)
    ]
    for block in range(1, 4):
        for row_offset in range(3):
            row_index = (row_offset + block - 1) % 3
            offset = ((block - 1) * 3 + row_index) % len(base)
            for condition_offset in range(len(base)):
                condition = base[(offset + condition_offset) % len(base)]
                plan.append(
                    StudyPresentation(
                        "diagnostic", TARGETS[row_index], condition, block, len(plan) + 1
                    )
                )
    return tuple(plan)
