"""Hardware-free accounting for the Issue #48 offline diagnostic."""

import pytest

from experiments.vertical_error_decomposition.analysis import (
    calibration_from_rows,
    center_accounting,
    residual_summary,
    summarize_held_out,
    verify_recorded_mapping,
)
from eye_tracker.gaze.calibration import CalibrationSample, IndependentLinearMapping
from validation.real_calibration import CALIBRATION_TARGETS


def test_center_accounting_is_exact_at_identical_target() -> None:
    mapping = IndependentLinearMapping(2.0, -0.5, 4.0, -0.3)
    baseline = CalibrationSample(0.5, 0.15, 0.5, 0.5)
    result = center_accounting(mapping, baseline, 0.55, 0.10)

    assert result["y"]["calibration_signed_error"] == pytest.approx(-0.2)
    assert result["y"]["feature_output_change"] == pytest.approx(-0.2)
    assert result["y"]["total_signed_error"] == pytest.approx(-0.4)
    assert result["y"]["accounting_remainder"] == pytest.approx(0)
    assert result["x"]["feature_output_change"] == pytest.approx(0.1)


def test_residual_summary_uses_target_minus_prediction_sign() -> None:
    mapping = IndependentLinearMapping(1, 0, 2, 0)
    samples = [
        CalibrationSample(0.2, 0.1, 0.2, 0.3),
        CalibrationSample(0.8, 0.3, 0.8, 0.5),
    ]
    summary = residual_summary(mapping, samples)

    assert summary["y"]["mean_target_minus_predicted"] == pytest.approx(0)
    assert summary["y"]["mae"] == pytest.approx(0.1)
    assert summary["targets"][0]["y_target_minus_predicted"] == pytest.approx(0.1)


def test_held_out_summary_does_not_claim_attribution() -> None:
    trials = [
        {"target_x": 0.35, "target_y": 0.35, "predicted_x": 0.4, "predicted_y": 0.6},
        {"target_x": 0.65, "target_y": 0.65, "predicted_x": 0.6, "predicted_y": 0.5},
    ]
    result = summarize_held_out(trials)

    assert result["y"]["signed_bias"] == pytest.approx(0.05)
    assert result["y"]["mae"] == pytest.approx(0.2)
    assert result["attributable_remainder"] is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), None, True])
def test_non_finite_or_malformed_diagnostics_rejected(bad: object) -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    baseline = CalibrationSample(0.5, 0.5, 0.5, 0.5)
    with pytest.raises(ValueError):
        center_accounting(mapping, baseline, 0.5, bad)
    with pytest.raises(ValueError):
        summarize_held_out(
            [{"target_x": 0.5, "target_y": 0.5, "predicted_x": 0.5, "predicted_y": bad}]
        )


def test_empty_calibration_and_held_out_rejected() -> None:
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    with pytest.raises(ValueError):
        residual_summary(mapping, [])
    with pytest.raises(ValueError):
        summarize_held_out([])


def test_reconstructs_nine_aggregates_using_production_median_and_fitter() -> None:
    rows = []
    for target in CALIBRATION_TARGETS:
        for offset in (-0.01, 0, 0.04):
            rows.append(
                {
                    "phase": "calibration",
                    "target_id": target.name,
                    "target_x": target.x,
                    "target_y": target.y,
                    "status": "usable",
                    "horizontal": target.x + offset,
                    "vertical": target.y + offset,
                }
            )
    mapping, samples = calibration_from_rows(rows)

    assert len(samples) == 9
    assert samples[0].horizontal_feature == pytest.approx(0.2)
    assert samples[0].vertical_feature == pytest.approx(0.2)
    assert mapping.predict(0.5, 0.5) == pytest.approx((0.5, 0.5))
    verify_recorded_mapping(
        mapping,
        {key: getattr(mapping, key) for key in mapping.__dataclass_fields__},
    )
    with pytest.raises(ValueError):
        verify_recorded_mapping(
            mapping,
            {key: 999 for key in mapping.__dataclass_fields__},
        )
    with pytest.raises(ValueError):
        calibration_from_rows(rows[:-3])
    with pytest.raises(ValueError):
        calibration_from_rows([{**rows[0], "vertical": float("nan")}, *rows[1:]])
