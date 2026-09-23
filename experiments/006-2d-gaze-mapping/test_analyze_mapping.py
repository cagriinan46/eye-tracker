"""Deterministic checks for the experiment-only mapping and quality logic."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("analyze_mapping.py")
SPEC = importlib.util.spec_from_file_location("analyze_mapping", SCRIPT)
mapping = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mapping)


def target(horizontal, vertical, x, y):
    return {
        "horizontal_feature": horizontal,
        "vertical_feature": vertical,
        "target_x": x,
        "target_y": y,
    }


def test_independent_linear_mapping_recovers_axis_relationship():
    calibration = [
        target(h, v, 2 * h + 0.1, -3 * v + 0.8) for h in (0.1, 0.2, 0.3) for v in (0.1, 0.2, 0.3)
    ]
    models = mapping.fit_models(calibration)
    assert mapping.predict(models["independent_linear"], 0.15, 0.25) == pytest.approx((0.4, 0.05))


def test_affine_mapping_recovers_cross_axis_relationship():
    calibration = [
        target(h, v, 2 * h + 3 * v + 0.1, -h + 4 * v + 0.2)
        for h in (0.1, 0.2, 0.3)
        for v in (0.1, 0.2, 0.3)
    ]
    models = mapping.fit_models(calibration)
    assert mapping.predict(models["affine_2d"], 0.15, 0.25) == pytest.approx((1.15, 1.05))


def test_degenerate_calibration_is_rejected():
    calibration = [target(0.2, 0.1, 0.2, 0.2)] * 9
    with pytest.raises(ValueError, match="rank"):
        mapping.fit_models(calibration)


def test_quality_gate_rejects_only_obvious_blink_collapse():
    rows = [
        {
            "presentation_index": 1,
            "timestamp_s": i * 0.04,
            "face_detected": 1,
            "geometry_valid": 1,
            "horizontal_feature": 0.2,
            "vertical_feature": 0.1,
            "eyeBlinkLeft": 0.1,
            "eyeBlinkRight": 0.1,
            "binocular_eye_opening": 0.1,
        }
        for i in range(3)
    ]
    rows += [
        {**rows[-1], "timestamp_s": 0.12, "eyeBlinkLeft": 0.8, "binocular_eye_opening": 0.03},
        {**rows[-1], "timestamp_s": 0.16, "binocular_eye_opening": 0.03},
    ]
    assert mapping.quality_flags(rows) == [True, True, True, False, True]


def test_validation_error_is_not_replaced_by_calibration_fit_error():
    calibration = [target(h, v, h, v) for h in (0.2, 0.5, 0.8) for v in (0.2, 0.5, 0.8)]
    held_out = [target(0.35, 0.35, 0.45, 0.35)]
    model = mapping.fit_models(calibration)["independent_linear"]
    fit = mapping.evaluate_targets(model, calibration, 1000, 500)
    validation = mapping.evaluate_targets(model, held_out, 1000, 500)
    assert fit["summary"]["mean_normalized_error"] == pytest.approx(0.0, abs=1e-10)
    assert validation["summary"]["mean_normalized_error"] == pytest.approx(0.1)
    assert validation["targets"][0]["pixel_equivalent_error"] == pytest.approx(100.0)


def test_validation_before_calibration_is_rejected():
    rows = [
        {
            "phase": "validation" if first else "calibration",
            "timestamp_s": index * 0.04,
            "presentation_index": 1 if first else 2,
            "target_id": "held-out" if first else "center",
            "trial_number": 1,
            "target_x": 0.35 if first else 0.5,
            "target_y": 0.35 if first else 0.5,
            "face_detected": 1,
            "geometry_valid": 1,
            "horizontal_feature": 0.2,
            "vertical_feature": 0.1,
            "eyeBlinkLeft": 0.1,
            "eyeBlinkRight": 0.1,
            "binocular_eye_opening": 0.1,
            "left_horizontal": 0.2,
            "right_horizontal": 0.2,
            "head_center_y": 0.5,
            "window_width": 1000,
            "window_height": 500,
        }
        for index, first in enumerate([True] * 5 + [False] * 5)
    ]
    with pytest.raises(ValueError, match="after calibration"):
        mapping.analyze_rows(rows)


def test_target_summary_uses_median_and_records_eye_disagreement():
    rows = [
        {
            "phase": "calibration",
            "presentation_index": 1,
            "target_id": "center",
            "trial_number": 1,
            "target_x": 0.5,
            "target_y": 0.5,
            "horizontal_feature": value,
            "vertical_feature": value / 10,
            "left_horizontal": 0.2,
            "right_horizontal": 0.3,
            "left_vertical_local_axis": 0.01,
            "right_vertical_local_axis": 0.03,
            "head_center_y": 0.5,
        }
        for value in (0.4, 0.5, 0.5, 0.6, 9.0)
    ]
    summary = mapping.target_summaries(rows, [True] * 5)[0]
    assert summary["horizontal_feature"] == pytest.approx(0.5)
    assert summary["horizontal_mad"] == pytest.approx(0.1)
    assert summary["vertical_feature"] == pytest.approx(0.05)
    assert summary["left_right_vertical_gap"] == pytest.approx(0.02)
