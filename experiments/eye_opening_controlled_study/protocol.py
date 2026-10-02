"""Fixed schedule for three blocks of comfortable opening at fixed targets."""

from dataclasses import dataclass

from validation.real_calibration import CALIBRATION_TARGETS, Presentation, Target

CONDITIONS = ("narrow", "natural", "wide")
TARGETS = (
    Target("upper", 0.5, 0.25),
    Target("center", 0.5, 0.5),
    Target("lower", 0.5, 0.75),
)
INSTRUCTIONS = {
    "natural": "NATURAL",
    "narrow": "GENTLY NARROW",
    "wide": "COMFORTABLY WIDE",
}


@dataclass(frozen=True, slots=True)
class StudyPresentation:
    phase: str
    target: Target
    condition: str
    block: int
    order: int

    def capture_presentation(self) -> Presentation:
        return Presentation(self.phase, self.target, self.block)


def schedule() -> tuple[StudyPresentation, ...]:
    """Nine natural calibration points, then Latin-rotated condition order per row.

    Each block visits each row once and runs all conditions consecutively there.
    Row order rotates by block; condition order rotates by block + row index.
    """
    result = [
        StudyPresentation("calibration", target, "natural", 0, index)
        for index, target in enumerate(CALIBRATION_TARGETS, start=1)
    ]
    for block in range(1, 4):
        for row_offset in range(3):
            row_index = (row_offset + block - 1) % 3
            for condition_offset in range(3):
                condition = CONDITIONS[(condition_offset + block - 1 + row_index) % 3]
                result.append(
                    StudyPresentation(
                        "diagnostic", TARGETS[row_index], condition, block, len(result) + 1
                    )
                )
    return tuple(result)
