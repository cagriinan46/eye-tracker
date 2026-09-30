"""Checks for the offline, causally ordered one-point offset comparison."""

import pytest

from experiments.vertical_offset.analysis import apply_offsets, center_offset, checkpoint_segments


def test_center_offset_changes_intercept_only() -> None:
    assert center_offset(0.5, 0.37) == pytest.approx(0.13)


def test_checkpoint_refresh_uses_only_preceding_checkpoint() -> None:
    events = [
        ("checkpoint", 0, None),
        ("validation", None, ("V-1", 1)),
        ("validation", None, ("V-2", 1)),
        ("checkpoint", 1, None),
        ("validation", None, ("V-1", 2)),
        ("checkpoint", 2, None),
    ]
    segments = checkpoint_segments(events)
    assert segments == {("V-1", 1): 0, ("V-2", 1): 0, ("V-1", 2): 1}
    trials = [
        {"target_id": "V-1", "trial_number": 1, "predicted_y": 0.2},
        {"target_id": "V-2", "trial_number": 1, "predicted_y": 0.3},
        {"target_id": "V-1", "trial_number": 2, "predicted_y": 0.4},
    ]
    corrected = apply_offsets(trials, segments, {0: 0.1, 1: 0.2, 2: 99})
    assert [trial["predicted_y"] for trial in corrected] == pytest.approx([0.3, 0.4, 0.6])


def test_trials_before_first_checkpoint_cannot_use_future_anchor() -> None:
    with pytest.raises(ValueError, match="before checkpoint"):
        checkpoint_segments([("validation", None, ("V-1", 1)), ("checkpoint", 0, None)])


def test_missing_or_duplicate_checkpoint_and_trial_rejected() -> None:
    with pytest.raises(ValueError):
        checkpoint_segments([("checkpoint", 1, None)])
    with pytest.raises(ValueError):
        checkpoint_segments(
            [
                ("checkpoint", 0, None),
                ("validation", None, ("V-1", 1)),
                ("validation", None, ("V-1", 1)),
            ]
        )
