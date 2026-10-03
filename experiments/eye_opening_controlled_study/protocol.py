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
CUE_SECONDS = 1.5
PROTOCOL_VERSION = 2


@dataclass(frozen=True, slots=True)
class ScreenContent:
    target: Target | None
    lines: tuple[str, ...]


def screen_content(presentation: "StudyPresentation | None", phase: str) -> ScreenContent:
    """Keep every condition cue separate from target fixation and sampling."""
    if phase == "ready":
        return ScreenContent(
            None,
            (
                "READY - press SPACE to begin",
                "First nine dots: look naturally for calibration.",
                "Read each later cue; set your eyes BEFORE the dot appears.",
                "Hold that state while looking only at the dot.",
                "Blink naturally; avoid strain and intentional head movement.",
                "q / Esc: cancel",
            ),
        )
    if presentation is None:
        raise ValueError("a presentation is required after the ready screen")
    if phase == "cue" and presentation.phase == "diagnostic":
        return ScreenContent(None, (INSTRUCTIONS[presentation.condition],))
    if phase in ("settling", "sampling"):
        return ScreenContent(presentation.target, ())
    raise ValueError("unexpected presentation/display phase")


def ready_key_action(key: int) -> str | None:
    """Interpret the ready screen key without starting on an unrelated press."""
    normalized = key & 0xFF
    if normalized == 32:
        return "start"
    if normalized in (ord("q"), 27):
        return "abort"
    return None


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
        """Persist the intended condition even while target screens contain no text."""
        return {
            "phase": self.phase,
            "target_id": self.target.name,
            "target_x": self.target.x,
            "target_y": self.target.y,
            "condition": self.condition,
            "block": self.block,
        }


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
