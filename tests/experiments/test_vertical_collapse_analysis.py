"""Hardware-free checks for Issue #44's numerical diagnostics."""

import math

import pytest


def _analysis():
    from experiments.vertical_collapse_diagnostics import analysis

    return analysis


def _calibration_rows(offset: float = 0.0) -> tuple[list[dict], list[dict]]:
    rows = []
    samples = []
    for row_index, target_y in enumerate((0.2, 0.5, 0.8)):
        for column_index, target_x in enumerate((0.2, 0.5, 0.8)):
            target_id = f"C-{row_index + 1}-{column_index + 1}"
            horizontal = target_x + 0.01 * row_index
            vertical = target_y + offset
            for deviation in (-0.01, 0.0, 0.01):
                rows.append(
                    {
                        "phase": "calibration",
                        "target_id": target_id,
                        "target_x": target_x,
                        "target_y": target_y,
                        "trial_number": 1,
                        "status": "usable",
                        "horizontal": horizontal + deviation,
                        "vertical": vertical + deviation,
                    }
                )
            samples.append(
                {
                    "target_id": target_id,
                    "target_x": target_x,
                    "target_y": target_y,
                    "horizontal_feature": horizontal,
                    "vertical_feature": vertical,
                }
            )
    return rows, samples


def _report(participant: str, session: str, offset: float = 0.0) -> dict:
    rows, samples = _calibration_rows(offset)
    rows.append(
        {
            "phase": "validation",
            "target_id": "V-1",
            "target_x": 0.35,
            "target_y": 0.35,
            "trial_number": 1,
            "status": "unavailable_no_face",
            "horizontal": None,
            "vertical": None,
        }
    )
    return {
        "participant": participant,
        "session": session,
        "rows": rows,
        "calibration_samples": samples,
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 1.0,
            "y_intercept": -offset,
        },
        "held_out_validation": {
            "trials": [
                {"predicted_x": 0.34, "predicted_y": 0.36},
                {"predicted_x": 0.66, "predicted_y": 0.64},
            ],
            "summary": {
                "mean_horizontal_absolute_error": 0.01,
                "mean_vertical_absolute_error": 0.01,
                "mean_signed_x_bias": 0.0,
                "mean_signed_y_bias": 0.0,
            },
            "spatial_ordering": {
                "x": {"consistent_pairs": 1, "total_pairs": 1},
                "y": {"consistent_pairs": 1, "total_pairs": 1},
            },
        },
    }


def test_describe_values_reports_median_range_and_iqr() -> None:
    summary = _analysis().describe_values([0.0, 1.0, 2.0, 3.0, 4.0])

    assert summary == {
        "count": 5,
        "median": 2.0,
        "minimum": 0.0,
        "maximum": 4.0,
        "range": 4.0,
        "iqr": 2.0,
    }


def test_row_grouping_separates_raw_frames_from_target_medians() -> None:
    rows, samples = _calibration_rows()
    result = _analysis().calibration_axis_summary(rows, samples, "vertical", "target_y")

    assert [row["target_coordinate"] for row in result["rows"]] == [0.2, 0.5, 0.8]
    assert [row["raw"]["count"] for row in result["rows"]] == [9, 9, 9]
    assert [row["raw"]["median"] for row in result["rows"]] == pytest.approx([0.2, 0.5, 0.8])
    assert [row["aggregated"]["count"] for row in result["rows"]] == [3, 3, 3]
    assert result["raw_ordering"] == "increasing"
    assert result["aggregated_ordering"] == "increasing"
    assert result["raw_range_overlap"] == [False, False]


def test_mixed_ordering_and_overlapping_ranges_are_not_hidden() -> None:
    rows, samples = _calibration_rows()
    for item in rows:
        if item["target_y"] == 0.5:
            item["vertical"] = 0.2
    result = _analysis().calibration_axis_summary(rows, samples, "vertical", "target_y")

    assert result["raw_ordering"] == "mixed"
    assert result["aggregated_ordering"] == "increasing"
    assert result["raw_range_overlap"] == [True, False]


def test_prediction_range_reports_near_flat_values_without_a_threshold() -> None:
    trials = [{"predicted_y": 0.500}, {"predicted_y": 0.518}]

    assert _analysis().prediction_range(trials, "predicted_y") == {
        "minimum": 0.5,
        "maximum": 0.518,
        "span": pytest.approx(0.018),
    }


def test_session_summary_preserves_pre_and_post_mapping_evidence() -> None:
    summary = _analysis().summarize_session(_report("cagri", "A", offset=0.04))

    assert (summary["participant"], summary["session"]) == ("cagri", "A")
    assert summary["statuses"] == {"usable": 27, "unavailable_no_face": 1}
    assert summary["vertical"]["rows"][1]["raw"]["median"] == pytest.approx(0.54)
    assert summary["vertical"]["rows"][1]["aggregated"]["median"] == pytest.approx(0.54)
    assert summary["mapping_coefficients"]["y_intercept"] == pytest.approx(-0.04)
    assert summary["held_out"]["y_prediction_range"]["span"] == pytest.approx(0.28)
    assert summary["held_out"]["y_ordering"] == {"consistent_pairs": 1, "total_pairs": 1}


def test_mapping_failure_keeps_valid_pre_mapping_features() -> None:
    report = _report("cagri", "A")
    report["rows"][-1].update(status="mapping_failed", horizontal=0.48, vertical=-0.04)

    summary = _analysis().summarize_session(report)

    assert summary["statuses"]["mapping_failed"] == 1


def test_comparison_keeps_people_and_sessions_separate() -> None:
    summaries = [
        _analysis().summarize_session(_report("cagri", "A")),
        _analysis().summarize_session(_report("cagri", "B", offset=0.1)),
        _analysis().summarize_session(_report("fatih", "A", offset=-0.2)),
    ]

    comparison = _analysis().compare_sessions(summaries)

    assert comparison["same_user"]["cagri"]["center_vertical_delta_B_minus_A"] == pytest.approx(0.1)
    assert comparison["same_user"]["cagri"]["vertical_row_deltas_B_minus_A"] == {
        "0.2": pytest.approx(0.1),
        "0.5": pytest.approx(0.1),
        "0.8": pytest.approx(0.1),
    }
    assert "fatih" not in comparison["same_user"]
    assert comparison["by_session"] == {
        "cagri/A": pytest.approx(0.5),
        "cagri/B": pytest.approx(0.6),
        "fatih/A": pytest.approx(0.3),
    }


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, "0.2", True])
def test_non_finite_or_non_numeric_features_are_rejected(bad_value: object) -> None:
    report = _report("cagri", "A")
    report["rows"][0]["vertical"] = bad_value

    with pytest.raises(ValueError, match="finite numerical"):
        _analysis().summarize_session(report)


def test_missing_session_identity_is_rejected() -> None:
    report = _report("cagri", "A")
    report["session"] = ""

    with pytest.raises(ValueError, match="participant and session"):
        _analysis().summarize_session(report)
