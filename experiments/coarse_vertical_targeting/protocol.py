"""Frozen Issue #81 schedule: shuffled 5×5 calibration, then 3×3 and 4×4 zone trials."""

import random
from dataclasses import dataclass

from experiments.vertical_signal_comparison.protocol import CALIBRATION_TARGETS
from validation.real_calibration import Presentation

LAYOUTS = {"3x3": (3, 3), "4x4": (4, 4)}
REPEATS = {"3x3": 2, "4x4": 1}
SESSION_LAYOUT_ORDER = {"A": ("3x3", "4x4"), "B": ("4x4", "3x3")}


@dataclass(frozen=True, slots=True)
class Trial:
    layout: str
    rows: int
    columns: int
    target: tuple[int, int]
    cue: tuple[int, int]


def calibration_schedule(seed: int = 81) -> tuple[Presentation, ...]:
    presentations = [Presentation("calibration", target, 1) for target in CALIBRATION_TARGETS]
    random.Random(seed).shuffle(presentations)
    return tuple(presentations)


def mirrored_cue(target: tuple[int, int], rows: int, columns: int) -> tuple[int, int]:
    """Opposite cell forces a gaze shift; the exact center cell cues the top-left cell."""
    cue = (rows - 1 - target[0], columns - 1 - target[1])
    return (0, 0) if cue == target else cue


def trial_schedule(session: str, seed: int = 81) -> tuple[Trial, ...]:
    generator = random.Random(f"{seed}-{session}")
    trials: list[Trial] = []
    for layout in SESSION_LAYOUT_ORDER[session]:
        rows, columns = LAYOUTS[layout]
        cells = [(r, c) for r in range(rows) for c in range(columns)] * REPEATS[layout]
        generator.shuffle(cells)
        trials.extend(
            Trial(layout, rows, columns, cell, mirrored_cue(cell, rows, columns)) for cell in cells
        )
    return tuple(trials)
