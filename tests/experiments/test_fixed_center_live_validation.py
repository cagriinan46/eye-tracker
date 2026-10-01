"""Hardware-free checks for the fixed-center live experiment."""

import pytest

from experiments.fixed_center_live_validation.analysis import compare_predictions, derive_offset
from experiments.fixed_center_live_validation.protocol import build_schedule
from eye_tracker.gaze.calibration import CalibrationSample, IndependentLinearMapping
from eye_tracker.gaze.estimator import GazeEstimate
from validation.real_calibration import VALIDATION_TARGETS, TrialEstimate, build_presentations


def _held_out(y_shift: float = -0.1) -> list[TrialEstimate]:
    return [
        TrialEstimate(
            target,
            trial,
            tuple(GazeEstimate(target.x, target.y + y_shift) for _ in range(5)),
        )
        for trial in (1, 2)
        for target in VALIDATION_TARGETS
    ]


def test_schedule_inserts_only_one_center_after_calibration() -> None:
    original = build_presentations(seed=42)
    schedule = build_schedule(seed=42)

    assert len(schedule) == 26
    assert schedule[:9] == original[:9]
    assert schedule[10:] == original[9:]
    assert (schedule[9].phase, schedule[9].target.x, schedule[9].target.y) == (
        "anchor",
        0.5,
        0.5,
    )
    assert [item.phase for item in schedule].count("anchor") == 1


def test_offset_uses_only_fixed_center_observations() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    anchor = ((0.5, 0.3), (0.5, 0.4), (0.5, 0.4), (0.5, 0.4), (0.5, 0.9))

    result = derive_offset(mapping, anchor)

    assert result["anchor_vertical_feature"] == pytest.approx(0.4)
    assert result["anchor_baseline_predicted_y"] == pytest.approx(0.4)
    assert result["fixed_vertical_offset"] == pytest.approx(0.1)


def test_comparison_reuses_same_held_out_observations_and_preserves_x() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    calibration_center = CalibrationSample(0.5, 0.45, 0.5, 0.5)
    anchor = ((0.5, 0.4),) * 5
    held_out = _held_out()

    report = compare_predictions(mapping, calibration_center, anchor, held_out, 1200, 700)

    assert report["anchor"]["fixed_vertical_offset"] == pytest.approx(0.1)
    assert report["calibration_center_vertical_feature"] == pytest.approx(0.45)
    assert report["baseline"]["summary"]["mean_vertical_absolute_error"] == pytest.approx(0.1)
    assert report["corrected"]["summary"]["mean_vertical_absolute_error"] == pytest.approx(0)
    assert report["baseline"]["spatial_ordering"] == report["corrected"]["spatial_ordering"]
    assert len(report["trials"]) == 16
    for row, baseline, corrected in zip(
        report["trials"],
        report["baseline"]["trials"],
        report["corrected"]["trials"],
        strict=True,
    ):
        assert row["baseline_predicted_x"] == row["corrected_predicted_x"]
        assert row["baseline_predicted_x"] == baseline["predicted_x"]
        assert row["corrected_predicted_x"] == corrected["predicted_x"]
        assert row["corrected_predicted_y"] == pytest.approx(row["baseline_predicted_y"] + 0.1)
        assert row["corrected_signed_y_error"] == pytest.approx(0)
    assert all(len(trial.estimates) == 5 for trial in held_out)


def test_held_out_values_cannot_change_derived_offset() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    calibration_center = CalibrationSample(0.5, 0.45, 0.5, 0.5)
    anchor = ((0.5, 0.4),) * 5

    first = compare_predictions(mapping, calibration_center, anchor, _held_out(-0.1), 1200, 700)
    second = compare_predictions(mapping, calibration_center, anchor, _held_out(0.2), 1200, 700)

    assert first["anchor"] == second["anchor"]
    assert first["corrected"]["summary"] != second["corrected"]["summary"]


def test_incomplete_anchor_or_held_out_cannot_produce_comparison() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    calibration_center = CalibrationSample(0.5, 0.45, 0.5, 0.5)

    with pytest.raises(ValueError, match="anchor needs"):
        derive_offset(mapping, ((0.5, 0.4),) * 4)
    with pytest.raises(ValueError, match="16 distinct"):
        compare_predictions(
            mapping, calibration_center, ((0.5, 0.4),) * 5, _held_out()[:-1], 1200, 700
        )


def test_out_of_range_predictions_are_reported_unclipped() -> None:
    report = compare_predictions(
        IndependentLinearMapping(1, 0, 1, 0),
        CalibrationSample(0.5, 0.45, 0.5, 0.5),
        ((0.5, 0.4),) * 5,
        _held_out(0.7),
        1200,
        700,
    )

    assert max(row["baseline_predicted_y"] for row in report["trials"]) > 1
    assert max(row["corrected_predicted_y"] for row in report["trials"]) > 1
