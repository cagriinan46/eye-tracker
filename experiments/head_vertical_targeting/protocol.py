"""Frozen Issue #84 schedule: three short calibration blocks, then zone trials."""

import random
from dataclasses import dataclass

from validation.real_calibration import Presentation, Target

POSITIONS = (0.1, 0.3, 0.5, 0.7, 0.9)
BLOCKS = {
    "eye_x": "EYES: keep your head still and look at the dot",
    "head_y": "HEAD: point your nose at the dot",
    "head_x": "HEAD: point your nose at the dot",
}
CONDITIONS = ("HYBRID", "HEAD")
SESSION_CONDITION_ORDER = {"A": ("HYBRID", "HEAD"), "B": ("HEAD", "HYBRID")}
LAYOUTS = {"3x3": (3, 3), "4x4": (4, 4)}
CONDITION_HINTS = {
    "HYBRID": "Look at the target; move your head up/down for the row",
    "HEAD": "Point your nose at the target",
}


@dataclass(frozen=True, slots=True)
class Trial:
    condition: str
    layout: str
    rows: int
    columns: int
    target: tuple[int, int]
    cue: tuple[int, int]


def _block_targets(block: str) -> list[Target]:
    if block == "head_y":
        return [Target(f"{block}-{i}", 0.5, v) for i, v in enumerate(POSITIONS, start=1)]
    return [Target(f"{block}-{i}", v, 0.5) for i, v in enumerate(POSITIONS, start=1)]


def calibration_schedule(seed: int = 84) -> tuple[Presentation, ...]:
    """Eye block first (head still), then head blocks; order shuffled within each block."""
    generator = random.Random(seed)
    presentations: list[Presentation] = []
    for block in BLOCKS:
        targets = _block_targets(block)
        generator.shuffle(targets)
        presentations.extend(Presentation(block, target, 1) for target in targets)
    return tuple(presentations)


def mirrored_cue(target: tuple[int, int], rows: int, columns: int) -> tuple[int, int]:
    cue = (rows - 1 - target[0], columns - 1 - target[1])
    return (0, 0) if cue == target else cue


def trial_schedule(session: str, seed: int = 84) -> tuple[Trial, ...]:
    generator = random.Random(f"{seed}-{session}")
    trials: list[Trial] = []
    for condition in SESSION_CONDITION_ORDER[session]:
        for layout, (rows, columns) in LAYOUTS.items():
            cells = [(r, c) for r in range(rows) for c in range(columns)]
            generator.shuffle(cells)
            trials.extend(
                Trial(condition, layout, rows, columns, cell, mirrored_cue(cell, rows, columns))
                for cell in cells
            )
    return tuple(trials)
