"""Deterministic checks for the offline repeated-target covariate analysis."""

from copy import deepcopy

import pytest

from experiments.vertical_feature_covariates.analysis import analyze_session, spearman
from experiments.vertical_sensitivity_live_study.protocol import pass_name, schedule


def sample_report():
    rows = []
    presentations = []
    for order, planned in enumerate(schedule(), start=1):
        phase = pass_name(planned.phase, planned.trial)
        shift = {"calibration": 0.0, "pass_a": 0.01, "pass_b": 0.03}[phase]
        if (planned.target.x, planned.target.y) == (0.5, 0.5):
            shift *= 2
        left = planned.target.y / 10 + shift
        right = planned.target.y / 10 + shift / 2
        for sample, jitter in enumerate((-0.001, 0, 0, 0, 0.001), start=1):
            rows.append(
                {
                    "participant": "cagri",
                    "session": "live-1",
                    "phase": planned.phase,
                    "trial_number": planned.trial,
                    "target_id": planned.target.name,
                    "target_x": planned.target.x,
                    "target_y": planned.target.y,
                    "sample_sequence": len(rows) + 1,
                    "monotonic_seconds": order + sample / 100,
                    "status": "usable",
                    "vertical": (left + right) / 2 + jitter,
                    "left_vertical": left + jitter,
                    "right_vertical": right + jitter,
                    "left_eye_opening": 0.2 + shift + jitter,
                    "right_eye_opening": 0.3 + shift / 2 + jitter,
                    "binocular_eye_opening": 0.25 + 0.75 * shift + jitter,
                    "head_center_y": 0.4 + shift * 2 + jitter,
                }
            )
        presentations.append(
            {
                "order": order,
                "pass": phase,
                "target_id": planned.target.name,
                "target_x": planned.target.x,
                "target_y": planned.target.y,
                "vertical_feature": (left + right) / 2,
                "usable_count": 5,
                "unavailable_count": 0,
                "sampling_attempts": 5,
            }
        )
    return {
        "participant": "cagri",
        "session": "live-1",
        "mapping_coefficients": {"y_slope": 10.0},
        "rows": rows,
        "presentations": presentations,
    }


def test_presentation_medians_and_exact_coordinate_matching():
    result = analyze_session(sample_report())
    assert len(result["presentations"]) == 27
    assert len(result["pairs"]) == 27
    center = [
        item
        for item in result["pairs"]
        if item["target_x"] == item["target_y"] == 0.5 and item["comparison"] == "calibration_to_a"
    ][0]
    assert center["delta_vertical"] == pytest.approx(0.015)
    assert center["abs_delta_vertical"] == pytest.approx(0.015)
    assert center["delta_left_vertical"] == pytest.approx(0.02)
    assert center["delta_right_vertical"] == pytest.approx(0.01)
    assert center["common_mode_vertical_delta"] == pytest.approx(0.015)
    assert center["differential_vertical_delta"] == pytest.approx(0.01)
    assert center["same_direction"] is True
    assert center["delta_head_center_y"] == pytest.approx(0.04)
    assert center["abs_delta_head_center_y"] == pytest.approx(0.04)
    assert center["delta_binocular_eye_opening"] == pytest.approx(0.015)
    assert center["abs_delta_binocular_eye_opening"] == pytest.approx(0.015)
    assert center["delta_left_eye_opening"] == pytest.approx(0.02)
    assert center["delta_right_eye_opening"] == pytest.approx(0.01)
    assert center["mapped_y_delta"] == pytest.approx(0.15)
    assert result["presentations"][0]["vertical"] == pytest.approx(0.02)
    assert result["presentations"][0]["phase"] == "calibration"
    assert result["presentations"][0]["pass"] == "calibration"
    assert result["presentations"][0]["vertical_p95_p05"] == pytest.approx(0.0016)
    assert result["frame_binocular_identity"]["max_abs_residual"] == pytest.approx(0)
    assert result["frame_binocular_identity"]["checked_count"] == 135
    assert result["summary"]["same_direction_count"] == 27
    assert result["summary"]["same_direction_proportion"] == pytest.approx(1)
    assert result["summary"]["median_abs_delta_left_vertical"] == pytest.approx(0.02)
    assert result["summary"]["median_abs_delta_right_vertical"] == pytest.approx(0.01)
    assert result["summary"]["median_abs_common_mode_vertical_delta"] == pytest.approx(0.015)
    assert result["summary"]["median_abs_differential_vertical_delta"] == pytest.approx(0.01)
    assert result["summary"]["p95_abs_differential_vertical_delta"] == pytest.approx(0.0185)
    assert result["summary"]["max_abs_differential_vertical_delta"] == pytest.approx(0.03)
    assert result["top_outliers"][0]["target_x"] == 0.5
    assert result["top_outliers"][0]["target_y"] == 0.5
    assert result["top_outliers"][0]["comparison"] == "calibration_to_b"


def test_wrong_coordinate_or_saved_median_is_rejected():
    report = sample_report()
    report["rows"][0]["target_x"] = 0.21
    with pytest.raises(ValueError, match="protocol|coordinate"):
        analyze_session(report)
    report = sample_report()
    report["presentations"][0]["vertical_feature"] = 99
    with pytest.raises(ValueError, match="saved vertical median"):
        analyze_session(report)


def test_opposite_direction_and_zero_are_distinct():
    report = sample_report()
    for row in report["rows"]:
        if row["target_x"] == row["target_y"] == 0.5 and row["phase"] == "diagnostic":
            row["right_vertical"] -= 0.04
            row["vertical"] = (row["left_vertical"] + row["right_vertical"]) / 2
    for item in report["presentations"]:
        if item["target_x"] == item["target_y"] == 0.5 and item["pass"] != "calibration":
            item["vertical_feature"] -= 0.02
    result = analyze_session(report)
    center_a = next(
        item
        for item in result["pairs"]
        if item["target_x"] == item["target_y"] == 0.5 and item["comparison"] == "calibration_to_a"
    )
    assert center_a["same_direction"] is False
    assert center_a["differential_vertical_delta"] == pytest.approx(0.05)


def test_missing_optional_covariate_stays_missing():
    report = deepcopy(sample_report())
    for row in report["rows"]:
        row.pop("head_center_y")
    result = analyze_session(report)
    assert result["presentations"][0]["head_center_y"] is None
    assert result["pairs"][0]["delta_head_center_y"] is None
    assert result["associations"]["vertical_vs_head_center_y"] is None
    assert result["availability"]["head_center_y_presentations"] == 0


def test_missing_monocular_fields_do_not_create_a_direction_classification():
    report = deepcopy(sample_report())
    for row in report["rows"]:
        row.pop("right_vertical")
    result = analyze_session(report)
    assert result["summary"]["zero_or_missing_direction_count"] == 27
    assert result["summary"]["same_direction_proportion"] is None
    assert result["summary"]["median_abs_differential_vertical_delta"] is None
    assert result["frame_binocular_identity"]["checked_count"] == 0


def test_spearman_midrank_and_degenerate_inputs():
    assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1)
    assert spearman([1, 1, 3], [2, 2, 5]) == pytest.approx(1)
    assert spearman([1, 1, 1], [1, 2, 3]) is None
    assert spearman([1], [1]) is None
