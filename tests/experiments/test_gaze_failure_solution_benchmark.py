"""Deterministic offline replay checks; no local human captures needed in CI."""

from copy import deepcopy

import pytest

from experiments.gaze_failure_solution_benchmark.analysis import diagnose_records
from experiments.gaze_failure_solution_benchmark.benchmark import (
    AffineMapping,
    calibration_diagnostics,
    candidate_gates,
    evaluate,
    filter_predictions,
    fit_mapping,
    replay_trial,
    validate_report,
)
from experiments.intentional_gaze_targeting.analysis import DwellState, summarize_target
from experiments.intentional_gaze_targeting.protocol import CUE_ASSIGNMENT, schedule
from eye_tracker.gaze.calibration import CalibrationSample, IndependentLinearMapping
from eye_tracker.gaze.calibration import fit_independent_linear as fit_production
from validation.real_calibration import CALIBRATION_TARGETS


def calibration():
    return [
        {
            "target_x": x,
            "target_y": y,
            "median_horizontal_feature": x + 0.1 * y,
            "median_vertical_feature": y + 0.2 * x,
        }
        for y in (0.2, 0.5, 0.8)
        for x in (0.2, 0.5, 0.8)
    ]


def test_axis_level_mapping_uses_only_three_calibration_level_medians():
    points = calibration()
    fit = fit_mapping(points, "M1")
    assert isinstance(fit, IndependentLinearMapping)
    assert fit.x_slope == pytest.approx(1)
    assert fit.x_intercept == pytest.approx(-0.05)
    assert fit.y_slope == pytest.approx(1)
    assert fit.y_intercept == pytest.approx(-0.1)
    changed = deepcopy(points)
    changed[0]["median_horizontal_feature"] += 5
    assert fit_mapping(changed, "M1").x_slope != pytest.approx(fit.x_slope)


def test_affine_recovers_cross_axis_coupling_without_target_trials():
    fit = fit_mapping(calibration(), "M2")
    assert isinstance(fit, AffineMapping)
    assert fit.predict(0.6, 0.6) == pytest.approx((0.54 / 0.98, 0.48 / 0.98))
    assert fit.x_h == pytest.approx(1 / 0.98)
    assert fit.y_h == pytest.approx(-0.2 / 0.98)
    assert fit.x_v == pytest.approx(-0.1 / 0.98)
    assert fit.y_v == pytest.approx(1 / 0.98)
    assert calibration_diagnostics(calibration(), "M2")["leave_one_out_y_mae"] == pytest.approx(0)


def test_filters_are_causal_and_unavailable_resets_state():
    predictions = [(0.0, 0.0), (1.0, 1.0), None, (2.0, 2.0), (9.0, 9.0)]
    assert filter_predictions(predictions, "T0") == predictions
    ema = filter_predictions(predictions, "T1")
    assert ema[0] == pytest.approx((0.0, 0.0))
    assert ema[1] == pytest.approx((0.35, 0.35))
    assert ema[2] is None
    assert ema[3] == pytest.approx((2.0, 2.0))
    assert ema[4] == pytest.approx((4.45, 4.45))
    assert filter_predictions(predictions, "T2") == [
        (0.0, 0.0),
        (0.5, 0.5),
        None,
        (2.0, 2.0),
        (5.5, 5.5),
    ]


def test_replay_uses_original_timestamps_and_marks_early_stop_censoring():
    trial = {
        "target_x": 0.5,
        "target_y": 0.5,
        "target_onset_monotonic_seconds": 10.0,
        "target_end_monotonic_seconds": 11.2,
        "target_summary": {"outcome": "success"},
    }
    rows = [{"monotonic_seconds": t} for t in (10.1, 10.7, 11.1)]
    success = replay_trial(trial, rows, [(0.5, 0.5)] * 3)
    assert success["outcome"] == "success"
    assert success["successful_entry_seconds"] == pytest.approx(0.1)
    assert success["confirmed_acquisition_seconds"] == pytest.approx(1.1)
    censored = replay_trial(trial, rows, [(0.8, 0.5)] * 3)
    assert censored["outcome"] == "censored"
    assert censored["confirmed_acquisition_seconds"] is None
    trial["target_summary"]["outcome"] = "timeout"
    trial["target_end_monotonic_seconds"] = 15.0
    assert replay_trial(trial, rows, [(0.8, 0.5)] * 3)["outcome"] == "timeout"


def test_candidate_gates_apply_predeclared_thresholds():
    baseline = {
        "success_rate": 0.37,
        "session_rates": {"live-1": 0.37, "live-2": 0.37},
        "y_mae": 0.2,
        "x_mae": 0.05,
        "median_confirmed_acquisition_seconds": 2.0,
        "dwell_interruptions": 100,
        "target_reentries": 80,
    }
    passing = {**baseline, "success_rate": 0.48, "y_mae": 0.16, "x_mae": 0.05}
    passing["session_rates"] = {"live-1": 0.48, "live-2": 0.48}
    assert all(candidate_gates(baseline, passing, "mapping").values())
    failing = {**passing, "x_mae": 0.06}
    assert not candidate_gates(baseline, failing, "mapping")["x_mae"]
    temporal = {**passing, "dwell_interruptions": 79}
    assert all(candidate_gates(baseline, temporal, "temporal").values())


def test_incompatible_report_and_missing_feature_are_rejected():
    with pytest.raises(ValueError, match="protocol"):
        validate_report({"protocol_name": "coarse_gaze_targeting", "protocol_version": 1})
    with pytest.raises(ValueError, match="calibration"):
        fit_mapping(calibration()[:2], "M0")
    with pytest.raises(ValueError, match="feature"):
        fit_mapping([{**p, "median_vertical_feature": None} for p in calibration()], "M0")


def test_m0_matches_production_fitter():
    points = calibration()
    fit = fit_mapping(points, "M0")
    assert isinstance(fit, IndependentLinearMapping)
    expected = fit_production(
        CalibrationSample(
            p["median_horizontal_feature"],
            p["median_vertical_feature"],
            p["target_x"],
            p["target_y"],
        )
        for p in points
    )
    assert fit == expected


def test_residual_diagnosis_groups_signed_bias_spread_and_repeated_blocks():
    records = []
    for block, vertical in ((1, 0.6), (2, 0.7)):
        records.append(
            {
                "session": "live-1",
                "target_id": "T-2-2",
                "target_x": 0.5,
                "target_y": 0.5,
                "block": block,
                "target_onset": 10.0,
                "samples": [
                    {
                        "timestamp": t,
                        "target_x": 0.5,
                        "target_y": 0.5,
                        "prediction": (0.51, vertical),
                    }
                    for t in (10.1, 13.1, 14.1)
                ],
            }
        )
    result = diagnose_records(records)
    target = result["by_target"]["T-2-2"]
    assert target["median_signed_x_bias"] == pytest.approx(0.01)
    assert target["median_signed_y_bias"] == pytest.approx(0.15)
    assert target["late_median_signed_y_bias"] == pytest.approx(0.15)
    assert result["repeated_target_y_difference_median"] == pytest.approx(0.1)
    assert target["median_within_trial_y_p95_p05"] == 0
    assert target["median_late_within_trial_y_p95_p05"] == 0


def synthetic_session(session):
    trials, target_samples = [], []
    for item in schedule():
        onset = 0.75
        state = DwellState(onset, item.target.x, item.target.y, 0.1, 0.1, 1.0, 5.0)
        rows = []
        for timestamp in (0.85, 1.85):
            inside, dwell = state.observe(timestamp, (item.target.x, item.target.y))
            rows.append(
                {
                    **item.identity(),
                    "status": "usable",
                    "raw_predicted_x": item.target.x,
                    "raw_predicted_y": item.target.y,
                    "horizontal_feature": item.target.x,
                    "vertical_feature": item.target.y,
                    "inside_target": inside,
                    "active_dwell_seconds": dwell,
                    "monotonic_seconds": timestamp,
                }
            )
        target_samples.extend(rows)
        trials.append(
            {
                **item.identity(),
                "cue_onset_monotonic_seconds": 0.0,
                "cue_end_monotonic_seconds": 0.75,
                "target_onset_monotonic_seconds": onset,
                "target_end_monotonic_seconds": 1.85,
                "target_summary": summarize_target(item, state, rows),
            }
        )
    return {
        "participant": "cagri",
        "session": session,
        "protocol_name": "intentional_gaze_targeting",
        "protocol_version": 2,
        "order_seed": 20261006,
        "target_half_width": 0.1,
        "target_half_height": 0.1,
        "target_dwell_seconds": 1.0,
        "target_timeout_seconds": 5.0,
        "fixation_cue_seconds": 0.75,
        "cue_assignment": CUE_ASSIGNMENT,
        "calibration_presentations": [
            {
                "target_id": point.name,
                "target_x": point.x,
                "target_y": point.y,
                "usable_samples": 5,
                "median_horizontal_feature": point.x,
                "median_vertical_feature": point.y,
            }
            for point in CALIBRATION_TARGETS
        ],
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 1.0,
            "y_intercept": 0.0,
        },
        "trials": trials,
        "target_samples": target_samples,
        "failed_camera_reads_including_calibration": 0,
        "no_face_observations_including_calibration": 0,
    }


def test_full_baseline_replay_is_exact_and_deterministic_without_target_fit():
    reports = [synthetic_session(session) for session in ("live-1", "live-2")]
    first = evaluate(reports, "M0", "T0")
    assert first == evaluate(reports, "M0", "T0")
    assert first["pooled"]["successes"] == 54
    assert first["pooled"]["x_mae"] == pytest.approx(0)
    assert first["pooled"]["y_mae"] == pytest.approx(0)
    assert first["baseline_max_prediction_error"] == 0
    assert first["baseline_timing_mismatches"] == 0
    reports[0]["target_samples"][0]["horizontal_feature"] += 1
    changed = evaluate(reports, "M1", "T0")
    assert (
        changed["calibration"]["live-1"]["coefficients"]
        == first["calibration"]["live-1"]["coefficients"]
    )


def test_report_validation_rejects_old_reset_pilot_and_missing_features():
    report = synthetic_session("live-1")
    report["reset_samples"] = []
    with pytest.raises(ValueError, match="pilot"):
        validate_report(report)
    del report["reset_samples"]
    report["target_samples"][0]["horizontal_feature"] = None
    with pytest.raises(ValueError, match="feature"):
        validate_report(report)
