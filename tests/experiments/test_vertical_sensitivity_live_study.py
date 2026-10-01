"""Hardware-free checks for the predeclared live sensitivity study."""

import json
from argparse import Namespace
from copy import deepcopy

import pytest

from experiments.vertical_sensitivity_live_study import run as capture
from experiments.vertical_sensitivity_live_study.analysis import analyze_session, prepare_report
from experiments.vertical_sensitivity_live_study.protocol import pass_name, schedule


def sample_report(*, slope=60.0):
    presentations = []
    for order, item in enumerate(schedule(), start=1):
        block = pass_name(item.phase, item.trial)
        feature = item.target.y / slope
        if block == "pass_a":
            feature += 0.001
        elif block == "pass_b":
            feature += 0.003
        presentations.append(
            {
                "order": order,
                "pass": block,
                "target_id": item.target.name,
                "target_x": item.target.x,
                "target_y": item.target.y,
                "horizontal_feature": item.target.x,
                "vertical_feature": feature,
                "predicted_x": item.target.x,
                "predicted_y": slope * feature,
                "usable_count": 5,
                "unavailable_count": 0,
                "sampling_attempts": 5,
            }
        )
    return {
        "participant": "cagri",
        "session": "live-1",
        "window_image_area": [1200, 700],
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": slope,
            "y_intercept": 0.0,
        },
        "presentations": presentations,
    }


def test_forward_reverse_schedule():
    planned = schedule()
    assert len(planned) == 27
    assert [item.target for item in planned[9:18]] == [
        item.target for item in reversed(planned[18:])
    ]
    assert [pass_name(item.phase, item.trial) for item in planned] == [
        *["calibration"] * 9,
        *["pass_a"] * 9,
        *["pass_b"] * 9,
    ]


def test_geometry_repeats_and_amplification():
    result = analyze_session(sample_report())
    geometry = result["calibration"]
    assert geometry["full_span"] == pytest.approx(0.6 / 60)
    assert geometry["rows"]["top"]["median"] == pytest.approx(0.2 / 60)
    assert geometry["top_to_center"] == pytest.approx(0.3 / 60)
    assert geometry["center_to_bottom"] == pytest.approx(0.3 / 60)
    assert geometry["minimum_adjacent_row_separation"] == pytest.approx(0.3 / 60)
    assert all(row["spread"] == 0 for row in geometry["rows"].values())
    assert result["calibration_fit"]["y_mae"] == pytest.approx(0)
    assert result["calibration_fit"]["y_ordering"] == {"consistent_pairs": 27, "total_pairs": 27}
    assert result["sensitivity_examples"]["0.003"] == pytest.approx(0.18)
    assert len(result["repeated_targets"]) == 27
    center = [
        item
        for item in result["repeated_targets"]
        if (item["target_x"], item["target_y"]) == (0.5, 0.5)
    ]
    assert [(item["comparison"], item["signed_feature_change"]) for item in center] == [
        ("calibration_to_a", pytest.approx(0.001)),
        ("calibration_to_b", pytest.approx(0.003)),
        ("a_to_b", pytest.approx(0.002)),
    ]
    assert center[2]["signed_mapped_y_change"] == pytest.approx(0.12)
    assert result["repeat_summary"]["maximum_absolute_feature_change"] == pytest.approx(0.003)
    assert result["repeat_summary"]["maximum_absolute_mapped_y_change"] == pytest.approx(0.18)


def test_exact_coordinate_matching_and_saved_features_are_required():
    report = sample_report()
    report["presentations"][10]["target_x"] = 0.21
    with pytest.raises(ValueError, match="target coordinates"):
        analyze_session(report)
    report = sample_report()
    report["presentations"][0]["vertical_feature"] = None
    with pytest.raises(ValueError, match="vertical feature"):
        analyze_session(report)


def test_invalid_observations_and_changed_predictions_are_rejected():
    report = sample_report()
    report["presentations"][0]["usable_count"] = 4
    with pytest.raises(ValueError, match="usable"):
        analyze_session(report)
    report = sample_report()
    report["presentations"][0]["predicted_y"] = 0.5
    with pytest.raises(ValueError, match="prediction"):
        analyze_session(report)
    report = sample_report()
    report["presentations"][0]["predicted_x"] = 0.9
    with pytest.raises(ValueError, match="prediction"):
        analyze_session(report)


def test_unclipped_predictions_and_actual_recorded_medians():
    report = sample_report(slope=60.0)
    report["mapping_coefficients"]["y_intercept"] = 1.0
    for item in report["presentations"]:
        item["predicted_y"] += 1.0
    result = analyze_session(report)
    assert max(item["predicted_y"] for item in report["presentations"]) > 1
    assert result["calibration_fit"]["y_mae"] == pytest.approx(1.0)


def test_prepare_report_uses_recorded_usable_rows_and_counts():
    expected = sample_report()
    raw = deepcopy(expected)
    raw.pop("presentations")
    rows = []
    for presentation in expected["presentations"]:
        for sample in range(5):
            rows.append(
                {
                    "participant": "cagri",
                    "session": "live-1",
                    "phase": "calibration"
                    if presentation["pass"] == "calibration"
                    else "diagnostic",
                    "trial_number": 1 if presentation["pass"] != "pass_b" else 2,
                    "target_id": presentation["target_id"],
                    "target_x": presentation["target_x"],
                    "target_y": presentation["target_y"],
                    "monotonic_seconds": presentation["order"] + sample / 10,
                    "status": "usable",
                    "vertical": presentation["vertical_feature"],
                    "horizontal": presentation["horizontal_feature"],
                    **{
                        name: 0.1
                        for name in (
                            "left_vertical",
                            "right_vertical",
                            "left_horizontal",
                            "right_horizontal",
                            "left_eye_opening",
                            "right_eye_opening",
                            "binocular_eye_opening",
                            "head_center_y",
                        )
                    },
                }
            )
    raw["rows"] = rows
    prepared = prepare_report(raw)
    assert prepared["presentations"] == expected["presentations"]
    assert len(prepared["rows"]) == 135


def test_missing_presentation_cannot_be_silently_analyzed():
    report = sample_report()
    report["presentations"].pop()
    with pytest.raises(ValueError, match="27"):
        analyze_session(report)


def test_invalid_run_preserves_reason_and_refuses_overwrite(tmp_path, monkeypatch):
    model = tmp_path / "model.task"
    model.write_bytes(b"test")
    args = Namespace(
        participant="cagri",
        session="live-1",
        camera_index=1,
        model=model,
        output=tmp_path / "attempt.json",
    )

    def fail(_args):
        raise ValueError("insufficient usable samples")

    monkeypatch.setattr(capture, "collect_session", fail)
    assert capture.run(args) == 1
    invalid = tmp_path / "attempt.invalid.json"
    marker = json.loads(invalid.read_text())
    assert marker["reason"] == "insufficient usable samples"
    assert marker["partial_measurements_available"] is False
    assert capture.run(args) == 1
