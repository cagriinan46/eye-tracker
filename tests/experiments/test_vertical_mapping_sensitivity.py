"""Deterministic accounting checks for the offline sensitivity diagnostic."""

import pytest

from experiments.vertical_mapping_sensitivity.analysis import (
    amplification,
    analyze_session,
    calibration_geometry,
    reconstruct_feature,
    repeated_target_differences,
)
from validation.real_calibration import (
    CALIBRATION_TARGETS,
    VALIDATION_TARGETS,
    _evaluate_predictions,
)


def _grid(top: tuple[float, ...], center: tuple[float, ...], bottom: tuple[float, ...]):
    return [
        {
            "target_id": f"C-{row}-{column}",
            "target_x": x,
            "target_y": y,
            "vertical_feature": feature,
        }
        for row, y, values in ((1, 0.2, top), (2, 0.5, center), (3, 0.8, bottom))
        for column, (x, feature) in enumerate(zip((0.2, 0.5, 0.8), values, strict=True), 1)
    ]


def test_reconstruct_feature_inverts_independent_linear_prediction() -> None:
    feature = reconstruct_feature(0.3284315545243972, 61.964504093626374, 2.8420287151330954)
    assert feature == pytest.approx(-0.040565113807910634)
    assert 61.964504093626374 * feature + 2.8420287151330954 == pytest.approx(0.3284315545243972)
    with pytest.raises(ValueError, match="nonzero"):
        reconstruct_feature(0.5, 0, 0.5)


def test_calibration_geometry_uses_target_medians_and_spans() -> None:
    result = calibration_geometry(_grid((0.00, 0.01, 0.02), (0.03, 0.04, 0.05), (0.07, 0.08, 0.09)))
    assert result["full_span"] == pytest.approx(0.09)
    assert result["top_to_center"] == pytest.approx(0.03)
    assert result["center_to_bottom"] == pytest.approx(0.04)
    assert result["minimum_adjacent_row_separation"] == pytest.approx(0.03)
    assert result["rows"]["top"]["median"] == pytest.approx(0.01)
    assert result["rows"]["center"]["spread"] == pytest.approx(0.02)
    assert len(result["targets"]) == 9


def test_calibration_geometry_rejects_missing_target() -> None:
    with pytest.raises(ValueError, match="nine"):
        calibration_geometry(_grid((0.0, 0.01, 0.02), (0.03, 0.04, 0.05), (0.07, 0.08, 0.09))[:-1])


def test_slope_amplification_keeps_direction_and_magnitude() -> None:
    assert amplification(61.9645, 0.003) == pytest.approx(0.1858935)
    assert amplification(20.0718, -0.003) == pytest.approx(-0.0602154)


def test_repeated_target_differences_use_later_minus_earlier() -> None:
    presentations = [
        {
            "phase": "validation",
            "target_id": "V-1",
            "order": 1,
            "vertical_feature": -0.05,
            "predicted_y": 0.4,
        },
        {
            "phase": "validation",
            "target_id": "V-1",
            "order": 4,
            "vertical_feature": -0.047,
            "predicted_y": 0.46,
        },
    ]
    result = repeated_target_differences(presentations, 20.0)
    assert result[0]["feature_delta"] == pytest.approx(0.003)
    assert result[0]["mapped_y_delta"] == pytest.approx(0.06)
    assert result[0]["prediction_delta"] == pytest.approx(0.06)


def test_missing_optional_feature_does_not_fabricate_repeat_value() -> None:
    presentations = [
        {
            "phase": "validation",
            "target_id": "V-1",
            "order": 1,
            "vertical_feature": None,
            "predicted_y": 0.4,
        },
        {
            "phase": "validation",
            "target_id": "V-1",
            "order": 4,
            "vertical_feature": None,
            "predicted_y": 0.46,
        },
    ]
    result = repeated_target_differences(presentations, 20.0)
    assert result[0]["feature_delta"] is None
    assert result[0]["mapped_y_delta"] is None
    assert result[0]["prediction_delta"] == pytest.approx(0.06)


def test_live_report_reconstructs_only_calibration_features() -> None:
    calibration = _evaluate_predictions(
        [(target, 1, target.x, target.y) for target in CALIBRATION_TARGETS], 1200, 700
    )
    held_out = _evaluate_predictions(
        [
            (target, trial, target.x, target.y + 0.02 * trial)
            for trial in (1, 2)
            for target in VALIDATION_TARGETS
        ],
        1200,
        700,
    )
    report = {
        "participant": "person",
        "session": "live",
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 10.0,
            "y_intercept": 0.0,
        },
        "calibration_fit": calibration,
        "calibration_center_vertical_feature": 0.05,
        "baseline": held_out,
    }
    result = analyze_session(report)
    assert result["calibration_feature_source"] == "reconstructed_from_linear_predictions"
    assert result["calibration"]["full_span"] == pytest.approx(0.06)
    assert result["calibration_fit"]["y_mae"] == pytest.approx(0)
    assert result["held_out"]["y_mae"] == pytest.approx(0.03)
    assert result["repeats"][0]["feature_delta"] is None
    assert result["repeats"][0]["prediction_delta"] == pytest.approx(0.02)


def test_report_without_held_out_keeps_metrics_missing() -> None:
    calibration = _evaluate_predictions(
        [(target, 1, target.x, target.y) for target in CALIBRATION_TARGETS], 1200, 700
    )
    report = {
        "participant": "person",
        "session": "diagnostic",
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 10.0,
            "y_intercept": 0.0,
        },
        "calibration_fit": calibration,
        "calibration_center_vertical_feature": 0.05,
    }
    result = analyze_session(report)
    assert result["held_out"] is None
    assert result["repeats"] == []


def test_original_calibration_features_work_without_saved_fit() -> None:
    report = {
        "participant": "person",
        "session": "original",
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 10.0,
            "y_intercept": 0.0,
        },
        "calibration_samples": [
            {
                "target_id": target.name,
                "target_x": target.x,
                "target_y": target.y,
                "horizontal_feature": target.x,
                "vertical_feature": target.y / 10,
            }
            for target in CALIBRATION_TARGETS
        ],
        "window_image_area": [1200, 700],
    }
    result = analyze_session(report)
    assert result["calibration_feature_source"] == "recorded_calibration_features"
    assert result["calibration_fit"]["y_mae"] == pytest.approx(0)
    assert result["held_out"] is None
