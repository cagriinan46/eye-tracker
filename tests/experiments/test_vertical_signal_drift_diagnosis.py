"""Hardware-free checks for Issue #75's preregistered vertical failure classification."""

import json

import pytest

from experiments.vertical_signal_drift_diagnosis import analysis

VALIDATION_TARGETS = (
    ("V-1", 0.35, 0.35),
    ("V-2", 0.65, 0.35),
    ("V-3", 0.35, 0.65),
    ("V-4", 0.65, 0.65),
    ("V-5", 0.50, 0.35),
    ("V-6", 0.65, 0.50),
    ("V-7", 0.50, 0.65),
    ("V-8", 0.35, 0.50),
)


def _row(phase, target_id, x, y, trial, vertical, **extra) -> dict:
    return {
        "phase": phase,
        "target_id": target_id,
        "target_x": x,
        "target_y": y,
        "trial_number": trial,
        "status": "usable",
        "horizontal": x,
        "vertical": vertical,
        "left_vertical": vertical - 0.001,
        "right_vertical": vertical + 0.001,
        "binocular_eye_opening": 0.3 - 0.1 * y,
        "head_center_y": 0.5,
        **extra,
    }


def _report(calibration_vertical, held_out_vertical, session: str = "A") -> dict:
    """Build a five-frame-per-presentation Issue #44-shaped report."""
    rows, samples = [], []
    for row_index, y in enumerate((0.2, 0.5, 0.8), start=1):
        for column_index, x in enumerate((0.2, 0.5, 0.8), start=1):
            target_id = f"C-{row_index}-{column_index}"
            value = calibration_vertical(x, y)
            for deviation in (-0.002, -0.001, 0.0, 0.001, 0.002):
                rows.append(_row("calibration", target_id, x, y, 1, value + deviation))
            samples.append(
                {
                    "target_id": target_id,
                    "target_x": x,
                    "target_y": y,
                    "horizontal_feature": x,
                    "vertical_feature": value,
                }
            )
    trials = []
    for trial in (1, 2):
        for target_id, x, y in VALIDATION_TARGETS:
            value = held_out_vertical(target_id, x, y, trial)
            for deviation in (-0.002, -0.001, 0.0, 0.001, 0.002):
                rows.append(_row("validation", target_id, x, y, trial, value + deviation))
            trials.append({"predicted_x": x, "predicted_y": y})
    return {
        "participant": "synthetic",
        "session": session,
        "rows": rows,
        "calibration_samples": samples,
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 1.0,
            "y_intercept": 0.0,
        },
        "held_out_validation": {
            "trials": trials,
            "summary": {
                "mean_horizontal_absolute_error": 0.0,
                "mean_vertical_absolute_error": 0.0,
                "mean_signed_x_bias": 0.0,
                "mean_signed_y_bias": 0.0,
            },
            "spatial_ordering": {
                "x": {"consistent_pairs": 21, "total_pairs": 21},
                "y": {"consistent_pairs": 21, "total_pairs": 21},
            },
        },
    }


def _linear(x, y):
    return 0.1 * y


def test_thresholds_are_the_preregistered_values() -> None:
    assert analysis.CALIBRATION_R2_MIN == 0.80
    assert analysis.CALIBRATION_COLUMN_PAIRS_MIN == 8
    assert analysis.HELD_OUT_PAIRS_MIN == 17
    assert analysis.DRIFT_SHIFT_MIN == 0.10
    assert analysis.ORDERING_MIN_DELTA == 0.05


def test_line_fit_reports_slope_intercept_and_r_squared() -> None:
    fit = analysis.fit_line([(0.2, 0.1), (0.5, 0.25), (0.8, 0.4)])
    assert fit["slope"] == pytest.approx(0.5)
    assert fit["intercept"] == pytest.approx(0.0)
    assert fit["r_squared"] == pytest.approx(1.0)
    assert analysis.fit_line([(0.2, 1.0), (0.5, 1.0), (0.8, 1.0)])["r_squared"] == 0.0
    with pytest.raises(ValueError):
        analysis.fit_line([(0.5, 0.1), (0.5, 0.2), (0.5, 0.3)])


def test_clean_session_is_not_reproduced() -> None:
    result = analysis.analyze_session(_report(_linear, lambda _id, x, y, _t: 0.1 * y))
    assert result["category"] == analysis.NOT_REPRODUCED
    assert result["calibration_vertical"]["column_ordering"] == {
        "consistent_pairs": 9,
        "total_pairs": 9,
    }
    assert result["held_out_feature_ordering"] == {"consistent_pairs": 21, "total_pairs": 21}
    assert result["held_out_shift_y"] == pytest.approx(0.0, abs=1e-12)


def test_saturated_lower_rows_are_a_signal_failure() -> None:
    result = analysis.analyze_session(
        _report(lambda x, y: 0.1 * min(y, 0.5), lambda _id, x, y, _t: 0.1 * y)
    )
    assert result["calibration_vertical"]["column_ordering"]["consistent_pairs"] == 6
    assert result["category"] == analysis.SIGNAL


def test_column_dependent_calibration_fails_r_squared() -> None:
    result = analysis.analyze_session(
        _report(lambda x, y: 0.1 * y + 0.2 * x, lambda _id, x, y, _t: 0.1 * y)
    )
    assert result["calibration_vertical"]["column_ordering"]["consistent_pairs"] == 9
    assert result["calibration_vertical"]["r_squared"] < analysis.CALIBRATION_R2_MIN
    assert result["category"] == analysis.SIGNAL


def test_constant_feature_is_a_signal_failure_without_division() -> None:
    result = analysis.analyze_session(_report(lambda x, y: 0.05, lambda _id, x, y, _t: 0.05))
    assert result["held_out_shift_y"] is None
    assert result["category"] == analysis.SIGNAL


def test_ordered_but_shifted_held_out_features_are_drift() -> None:
    result = analysis.analyze_session(_report(_linear, lambda _id, x, y, _t: 0.1 * (y + 0.25)))
    assert result["held_out_feature_ordering"]["consistent_pairs"] == 21
    assert result["held_out_shift_y"] == pytest.approx(0.25)
    assert result["category"] == analysis.DRIFT


def test_unordered_held_out_features_are_instability() -> None:
    reversed_rows = {0.35: 0.65, 0.5: 0.5, 0.65: 0.35}
    result = analysis.analyze_session(
        _report(_linear, lambda _id, x, y, _t: 0.1 * reversed_rows[y])
    )
    assert result["held_out_feature_ordering"]["consistent_pairs"] == 0
    assert result["category"] == analysis.INSTABILITY


def test_negative_feature_direction_is_respected() -> None:
    result = analysis.analyze_session(
        _report(lambda x, y: -0.1 * y, lambda _id, x, y, _t: -0.1 * y)
    )
    assert result["calibration_vertical"]["slope"] < 0
    assert result["held_out_feature_ordering"]["consistent_pairs"] == 21
    assert result["category"] == analysis.NOT_REPRODUCED


def test_held_out_trial_needs_five_usable_rows() -> None:
    report = _report(_linear, lambda _id, x, y, _t: 0.1 * y)
    victim = next(row for row in report["rows"] if row["phase"] == "validation")
    victim["status"] = "unavailable_no_face"
    victim["horizontal"] = victim["vertical"] = None
    with pytest.raises(ValueError, match="five usable"):
        analysis.analyze_session(report)


def test_descriptive_measures_and_json_output() -> None:
    result = analysis.analyze_session(_report(_linear, lambda _id, x, y, _t: 0.1 * y))
    descriptive = result["descriptive"]
    assert descriptive["left_vertical"]["r_squared"] == pytest.approx(1.0)
    assert descriptive["eye_opening"]["slope"] == pytest.approx(-0.1)
    assert descriptive["head_center_y_validation_minus_calibration"] == 0.0
    json.dumps(result, allow_nan=False)


def test_combine_requires_agreement_of_all_sessions() -> None:
    first = {"participant": "p", "session": "A", "category": analysis.DRIFT}
    second = {"participant": "p", "session": "B", "category": analysis.DRIFT}
    other = {"participant": "p", "session": "B", "category": analysis.SIGNAL}
    assert analysis.combine([first, second])["overall"] == analysis.DRIFT
    assert analysis.combine([first, other])["overall"] == analysis.MIXED
    assert analysis.combine([first])["overall"] == analysis.MIXED
    with pytest.raises(ValueError, match="duplicate"):
        analysis.combine([first, first])
    with pytest.raises(ValueError, match="one participant"):
        analysis.combine([first, {**second, "participant": "q"}])


def test_cli_prints_sessions_and_combined_result(tmp_path, capsys) -> None:
    paths = []
    for session in ("A", "B"):
        path = tmp_path / f"{session}.json"
        path.write_text(
            json.dumps(_report(_linear, lambda _id, x, y, _t: 0.1 * (y + 0.3), session)),
            encoding="utf-8",
        )
        paths.append(str(path))
    assert analysis.main(paths) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["combined"]["overall"] == analysis.DRIFT
    assert analysis.main([str(tmp_path / "missing.json")]) == 1


def test_issue_44_collector_accepts_full_screen_size_without_changing_default() -> None:
    from experiments.vertical_collapse_diagnostics.run import parse_args

    base = ["--participant", "fatih", "--session", "A", "--camera-index", "0"]
    output = ["--output", ".venv/vertical-collapse-fatih-A.json"]
    assert parse_args(base + output).screen_size is None
    assert parse_args(base + output + ["--screen-size", "1512x982"]).screen_size == (1512, 982)
    with pytest.raises(SystemExit):
        parse_args(base + output + ["--screen-size", "0x982"])
