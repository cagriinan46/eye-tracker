"""Checkpoint scheduling must preserve the established held-out protocol."""

from experiments.vertical_drift_diagnostics.protocol import build_checkpoint_schedule
from validation.real_calibration import build_presentations


def test_schedule_inserts_center_before_and_after_four_trial_blocks() -> None:
    original = build_presentations(seed=42)
    scheduled = build_checkpoint_schedule(seed=42)

    assert [item for item in scheduled if item.phase != "checkpoint"] == list(original)
    assert len(scheduled) == 30
    assert [
        (index, item.trial) for index, item in enumerate(scheduled) if item.phase == "checkpoint"
    ] == [
        (9, 0),
        (14, 1),
        (19, 2),
        (24, 3),
        (29, 4),
    ]
    assert all(
        (item.target.name, item.target.x, item.target.y) == ("CENTER", 0.5, 0.5)
        for item in scheduled
        if item.phase == "checkpoint"
    )


def test_schedule_reproducible_without_reordering_held_out_trials() -> None:
    assert build_checkpoint_schedule(seed=7) == build_checkpoint_schedule(seed=7)
    assert [item for item in build_checkpoint_schedule(seed=7) if item.phase == "validation"] == [
        item for item in build_presentations(seed=7) if item.phase == "validation"
    ]
