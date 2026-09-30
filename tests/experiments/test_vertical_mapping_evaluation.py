"""Hardware-free checks for Issue #50's calibration-only model comparison."""

import math

import pytest

from experiments.vertical_mapping_evaluation.analysis import (
    evaluate_held_out,
    summarize_calibration,
)
from experiments.vertical_mapping_evaluation.mapping import (
    CombinedMapping,
    PiecewiseVerticalMapping,
    fit_row_anchor_mapping,
)
from eye_tracker.gaze.calibration import CalibrationSample, IndependentLinearMapping
from validation.real_calibration import VALIDATION_TARGETS


def _samples(features: tuple[tuple[float, float, float], ...]) -> tuple[CalibrationSample, ...]:
    return tuple(
        CalibrationSample(horizontal_feature=x, vertical_feature=vertical, target_x=x, target_y=y)
        for y, row in zip((0.2, 0.5, 0.8), features, strict=True)
        for x, vertical in zip((0.2, 0.5, 0.8), row, strict=True)
    )


def test_row_anchors_use_median_of_target_medians_and_hit_exact_anchors() -> None:
    samples = _samples(((0.0, 0.1, 0.2), (0.3, 0.4, 0.5), (0.6, 0.7, 0.8)))
    mapping = fit_row_anchor_mapping(samples)

    for actual, expected in zip(mapping.anchors, ((0.1, 0.2), (0.4, 0.5), (0.7, 0.8)), strict=True):
        assert actual == pytest.approx(expected)
    assert [mapping.predict_vertical(value) for value in (0.1, 0.4, 0.7)] == pytest.approx(
        (0.2, 0.5, 0.8)
    )
    assert mapping.predict_vertical(0.25) == pytest.approx(0.35)
    assert mapping.predict_vertical(0.55) == pytest.approx(0.65)


def test_reversed_feature_direction_remains_monotonic_in_screen_y() -> None:
    mapping = PiecewiseVerticalMapping(((0.7, 0.2), (0.4, 0.5), (0.1, 0.8)))

    assert [mapping.predict_vertical(value) for value in (0.6, 0.4, 0.2)] == pytest.approx(
        (0.3, 0.5, 0.7)
    )


def test_outside_anchor_range_extrapolates_nearest_segment_without_clipping() -> None:
    mapping = PiecewiseVerticalMapping(((0.1, 0.2), (0.2, 0.5), (0.4, 0.8)))

    assert mapping.predict_vertical(0.0) == pytest.approx(-0.1)
    assert mapping.predict_vertical(0.5) == pytest.approx(0.95)
    assert mapping.predict_vertical(0.6) == pytest.approx(1.1)


@pytest.mark.parametrize(
    "anchors",
    [
        ((0.1, 0.2), (0.1, 0.5), (0.4, 0.8)),
        ((0.1, 0.2), (0.4, 0.5), (0.3, 0.8)),
        ((0.1, 0.2), (0.2, 0.2), (0.4, 0.8)),
        ((0.1, 0.2), (math.nan, 0.5), (0.4, 0.8)),
    ],
)
def test_nonmonotonic_or_nonfinite_anchors_rejected(anchors: tuple) -> None:
    with pytest.raises(ValueError):
        PiecewiseVerticalMapping(anchors)


def test_incomplete_rows_or_nonfinite_prediction_input_rejected() -> None:
    samples = _samples(((0.0, 0.1, 0.2), (0.3, 0.4, 0.5), (0.6, 0.7, 0.8)))
    with pytest.raises(ValueError):
        fit_row_anchor_mapping(samples[:-1])
    with pytest.raises(ValueError):
        fit_row_anchor_mapping(_samples(((0.0, 0.1, 0.2), (0.3, 0.4, 0.5), (0.2, 0.3, 0.4))))
    with pytest.raises(ValueError):
        fit_row_anchor_mapping([*samples[:-1], object()])
    with pytest.raises(ValueError):
        fit_row_anchor_mapping(samples).predict_vertical(float("inf"))


def test_combined_mapping_leaves_horizontal_prediction_unchanged() -> None:
    baseline = IndependentLinearMapping(x_slope=-2, x_intercept=1, y_slope=1, y_intercept=0)
    alternative = PiecewiseVerticalMapping(((0.1, 0.2), (0.2, 0.5), (0.4, 0.8)))

    assert CombinedMapping(baseline, alternative).predict(0.3, 0.3) == pytest.approx((0.4, 0.65))


def test_calibration_metrics_report_each_target_row_and_center_residual() -> None:
    samples = _samples(((0.0, 0.1, 0.2), (0.3, 0.4, 0.45), (0.6, 0.7, 0.8)))
    baseline = IndependentLinearMapping(1, 0, 1, 0)
    mapping = CombinedMapping(baseline, fit_row_anchor_mapping(samples))

    result = summarize_calibration(samples, mapping)

    assert len(result["targets"]) == 9
    assert [row["target_y"] for row in result["rows"]] == [0.2, 0.5, 0.8]
    assert result["center_signed_residual"] == pytest.approx(0)
    assert result["targets"][0]["predicted_y"] == pytest.approx(0.1)
    assert result["targets"][0]["signed_residual"] == pytest.approx(-0.1)
    assert result["rows"][0]["mae"] == pytest.approx(2 / 30)


def test_held_out_metrics_use_per_trial_medians_and_original_target_ordering() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    rows = [
        {
            "phase": "validation",
            "target_id": target.name,
            "trial_number": trial,
            "target_x": target.x,
            "target_y": target.y,
            "status": "usable",
            "horizontal": target.x,
            "vertical": target.y + offset,
        }
        for target in VALIDATION_TARGETS
        for trial in (1, 2)
        for offset in (0.05, 0.1, 0.1, 0.1, 0.2)
    ]

    result = evaluate_held_out(rows, mapping, 1200, 700)

    assert len(result["trials"]) == 16
    assert result["summary"]["mean_vertical_absolute_error"] == pytest.approx(0.1)
    assert result["summary"]["median_vertical_absolute_error"] == pytest.approx(0.1)
    assert result["summary"]["p95_vertical_absolute_error"] == pytest.approx(0.1)
    assert result["summary"]["mean_signed_y_bias"] == pytest.approx(0.1)
    assert result["spatial_ordering"]["y"] == {"consistent_pairs": 21, "total_pairs": 21}
    assert result["prediction_range_y"] == pytest.approx((0.45, 0.75))
    assert result["outside_anchor_frame_count"] is None


def test_malformed_or_missing_held_out_rows_rejected() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    with pytest.raises(ValueError):
        evaluate_held_out([], mapping, 1200, 700)
    with pytest.raises(ValueError):
        evaluate_held_out(
            [
                {
                    "phase": "validation",
                    "target_id": "V-1",
                    "trial_number": 1,
                    "target_x": 0.35,
                    "target_y": 0.35,
                    "status": "usable",
                    "horizontal": 0.35,
                    "vertical": math.nan,
                }
            ],
            mapping,
            1200,
            700,
        )
