"""Hardware-free checks for Issue #52's position/time diagnostic."""

import math

import pytest

from experiments.vertical_position_variability.analysis import analyze_session
from experiments.vertical_position_variability.protocol import build_schedule


def _row(
    phase: str,
    target: str,
    trial: int,
    x: float,
    y: float,
    time: float,
    vertical: float,
    *,
    status: str = "usable",
) -> dict:
    return {
        "participant": "tester",
        "session": "A",
        "phase": phase,
        "target_id": target,
        "trial_number": trial,
        "checkpoint": trial if phase == "checkpoint" else None,
        "target_x": x,
        "target_y": y,
        "monotonic_seconds": time,
        "status": status,
        "vertical": vertical if status == "usable" else None,
        "horizontal": 1 - x if status == "usable" else None,
        "left_vertical": vertical - 0.01 if status == "usable" else None,
        "right_vertical": vertical + 0.01 if status == "usable" else None,
        "left_horizontal": 1 - x if status == "usable" else None,
        "right_horizontal": 1 - x if status == "usable" else None,
        "left_eye_opening": 0.3 if status == "usable" else None,
        "right_eye_opening": 0.3 if status == "usable" else None,
        "binocular_eye_opening": 0.3 if status == "usable" else None,
        "head_center_y": 0.4 if status == "usable" else None,
    }


def _report(rows: list[dict]) -> dict:
    return {
        "participant": "tester",
        "session": "A",
        "rows": rows,
        "mapping_coefficients": {"y_slope": 10.0},
    }


def test_fixed_y_position_summary_preserves_order_and_within_target_spread() -> None:
    rows = [
        _row("calibration", "left", 1, 0.2, 0.5, 1, 0.1),
        _row("calibration", "left", 1, 0.2, 0.5, 1.1, 0.2),
        _row("calibration", "center", 1, 0.5, 0.5, 2, 0.3),
        _row("calibration", "center", 1, 0.5, 0.5, 2.1, 0.3),
        _row("calibration", "right", 1, 0.8, 0.5, 3, 0.5),
        _row("calibration", "right", 1, 0.8, 0.5, 3.1, 0.6),
    ]

    result = analyze_session(_report(rows))
    comparison = result["position_comparisons"][0]

    assert (comparison["phase"], comparison["target_y"]) == ("calibration", 0.5)
    assert [item["target_x"] for item in comparison["positions"]] == [0.2, 0.5, 0.8]
    assert [item["vertical_median"] for item in comparison["positions"]] == pytest.approx(
        [0.15, 0.3, 0.55]
    )
    assert comparison["vertical_median_span"] == pytest.approx(0.4)
    assert comparison["mapped_y_span"] == pytest.approx(4.0)
    assert comparison["max_within_presentation_iqr"] == pytest.approx(0.05)
    assert comparison["x_time_order_confounded"] is True


def test_identical_target_repeats_remain_separate_from_cross_target_comparison() -> None:
    rows = [
        _row("validation", "left", 1, 0.2, 0.5, 1, 0.1),
        _row("validation", "right", 1, 0.8, 0.5, 2, 0.4),
        _row("validation", "right", 2, 0.8, 0.5, 3, 0.5),
        _row("validation", "left", 2, 0.2, 0.5, 4, 0.2),
        _row("checkpoint", "CENTER", 0, 0.5, 0.5, 5, 0.2),
        _row("checkpoint", "CENTER", 1, 0.5, 0.5, 6, 0.4),
    ]

    result = analyze_session(_report(rows))
    repeats = {(item["phase"], item["target_id"]): item for item in result["repeats"]}

    assert repeats["validation", "left"]["vertical_median_delta"] == pytest.approx(0.1)
    assert repeats["validation", "left"]["elapsed_seconds"] == pytest.approx(3)
    assert repeats["validation", "left"]["mapped_y_delta"] == pytest.approx(1)
    assert repeats["checkpoint", "CENTER"]["vertical_median_delta"] == pytest.approx(0.2)
    assert result["position_comparisons"][0]["x_time_order_confounded"] is False


def test_unavailable_rows_are_counted_but_not_used_as_features() -> None:
    rows = [
        _row("validation", "one", 1, 0.2, 0.5, 1, 0.2),
        _row("validation", "one", 1, 0.2, 0.5, 1.1, 0, status="unavailable_no_face"),
        _row("validation", "two", 1, 0.8, 0.5, 2, 0.4),
    ]

    result = analyze_session(_report(rows))

    assert result["availability"] == {"usable": 2, "unavailable_no_face": 1}
    assert result["position_comparisons"][0]["positions"][0]["vertical_median"] == 0.2


@pytest.mark.parametrize(
    "change",
    [
        {"vertical": math.nan},
        {"target_x": math.inf},
        {"monotonic_seconds": float("nan")},
        {"status": "usable", "left_vertical": None},
    ],
)
def test_malformed_or_nonfinite_diagnostics_are_rejected(change: dict) -> None:
    row = _row("validation", "one", 1, 0.2, 0.5, 1, 0.2)
    row.update(change)

    with pytest.raises(ValueError):
        analyze_session(_report([row]))


def test_mismatched_target_coordinates_and_nonfinite_slope_are_rejected() -> None:
    first = _row("validation", "one", 1, 0.2, 0.5, 1, 0.2)
    second = _row("validation", "one", 2, 0.8, 0.5, 2, 0.3)

    with pytest.raises(ValueError):
        analyze_session(_report([first, second]))

    with pytest.raises(ValueError):
        analyze_session({**_report([first]), "mapping_coefficients": {"y_slope": math.inf}})


def test_rows_from_another_session_are_rejected_instead_of_pooled() -> None:
    first = _row("diagnostic", "one", 1, 0.2, 0.5, 1, 0.2)
    second = _row("diagnostic", "one", 2, 0.2, 0.5, 2, 0.3)
    second["session"] = "B"

    with pytest.raises(ValueError):
        analyze_session(_report([first, second]))


def test_controlled_schedule_repeats_every_position_with_reversed_order() -> None:
    schedule = build_schedule()
    calibration = schedule[:9]
    first = schedule[9:18]
    second = schedule[18:]

    assert len(schedule) == 27
    assert all(item.phase == "calibration" for item in calibration)
    assert all(item.phase == "diagnostic" for item in (*first, *second))
    assert {(item.target.x, item.target.y) for item in first} == {
        (x, y) for x in (0.2, 0.5, 0.8) for y in (0.2, 0.5, 0.8)
    }
    assert [(item.target.name, item.trial) for item in first] == [
        (item.target.name, 1) for item in reversed(second)
    ]


def test_diagnostic_repeats_are_analyzed_like_validation_repeats() -> None:
    rows = [
        _row("diagnostic", "same", 1, 0.2, 0.5, 1, 0.1),
        _row("diagnostic", "same", 2, 0.2, 0.5, 5, 0.3),
        _row("diagnostic", "other", 1, 0.8, 0.5, 2, 0.4),
        _row("diagnostic", "other", 2, 0.8, 0.5, 4, 0.5),
    ]

    result = analyze_session(_report(rows))

    assert result["position_comparisons"][0]["vertical_median_span"] == pytest.approx(0.25)
    assert result["repeats"][0]["phase"] == "diagnostic"


def test_overlapping_repeat_time_ranges_are_not_marked_order_confounded() -> None:
    rows = [
        _row("diagnostic", "left", 1, 0.2, 0.5, 1, 0.1),
        _row("diagnostic", "left", 2, 0.2, 0.5, 4, 0.1),
        _row("diagnostic", "center", 1, 0.5, 0.5, 2, 0.2),
        _row("diagnostic", "center", 2, 0.5, 0.5, 4, 0.2),
        _row("diagnostic", "right", 1, 0.8, 0.5, 2.5, 0.3),
        _row("diagnostic", "right", 2, 0.8, 0.5, 4.5, 0.3),
    ]

    result = analyze_session(_report(rows))

    assert result["position_comparisons"][0]["x_time_order_confounded"] is False


def test_diagnostic_pass_summaries_preserve_reversed_x_order_and_distinct_spans() -> None:
    rows = [
        _row("diagnostic", "left", 1, 0.2, 0.5, 1, 0.1),
        _row("diagnostic", "center", 1, 0.5, 0.5, 2, 0.2),
        _row("diagnostic", "right", 1, 0.8, 0.5, 3, 0.4),
        _row("diagnostic", "right", 2, 0.8, 0.5, 4, 0.5),
        _row("diagnostic", "center", 2, 0.5, 0.5, 5, 0.2),
        _row("diagnostic", "left", 2, 0.2, 0.5, 6, 0.1),
    ]

    result = analyze_session(_report(rows))

    assert [
        (item["trial"], item["vertical_median_span"]) for item in result["pass_comparisons"]
    ] == [
        (1, pytest.approx(0.3)),
        (2, pytest.approx(0.4)),
    ]
    assert [item["observed_x_order"] for item in result["pass_comparisons"]] == [
        [0.2, 0.5, 0.8],
        [0.8, 0.5, 0.2],
    ]
