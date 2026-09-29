"""Hardware-free checks for fixed-center feature drift summaries."""

import math

import pytest

from experiments.vertical_drift_diagnostics.analysis import compare_sessions, summarize_checkpoints


def _row(checkpoint: int, vertical: float | None, *, status: str = "usable", **changes):
    row = {
        "phase": "checkpoint",
        "checkpoint": checkpoint,
        "target_x": 0.5,
        "target_y": 0.5,
        "monotonic_seconds": float(checkpoint + 1),
        "status": status,
        "horizontal": 0.5 if vertical is not None else None,
        "vertical": vertical,
        "left_vertical": vertical - 0.01 if vertical is not None else None,
        "right_vertical": vertical + 0.01 if vertical is not None else None,
        "left_eye_opening": 0.3 if vertical is not None else None,
        "right_eye_opening": 0.4 if vertical is not None else None,
        "binocular_eye_opening": 0.35 if vertical is not None else None,
        "head_center_y": 0.5 if vertical is not None else None,
    }
    row.update(changes)
    return row


def test_checkpoint_grouping_baselines_and_per_eye_summaries() -> None:
    rows = [
        _row(0, -0.04),
        _row(0, -0.05),
        _row(0, -0.06),
        _row(1, -0.07, left_vertical=-0.08, right_vertical=-0.06),
        _row(1, -0.08, left_vertical=-0.09, right_vertical=-0.07),
        _row(1, -0.09, left_vertical=-0.10, right_vertical=-0.08),
        _row(1, None, status="unavailable_no_face"),
    ]
    summary = summarize_checkpoints(rows, calibration_center_vertical=-0.045)

    assert [item["checkpoint"] for item in summary["checkpoints"]] == [0, 1]
    first, second = summary["checkpoints"]
    assert first["vertical"]["median"] == pytest.approx(-0.05)
    assert first["vertical"]["iqr"] == pytest.approx(0.01)
    assert first["delta_from_calibration_center"] == pytest.approx(-0.005)
    assert first["delta_from_checkpoint_0"] == 0
    assert second["vertical"]["median"] == pytest.approx(-0.08)
    assert second["delta_from_calibration_center"] == pytest.approx(-0.035)
    assert second["delta_from_checkpoint_0"] == pytest.approx(-0.03)
    assert second["left_vertical"]["median"] == pytest.approx(-0.09)
    assert second["right_vertical"]["median"] == pytest.approx(-0.07)
    assert second["availability"] == {"usable": 3, "unavailable_no_face": 1}
    assert summary["first_to_last_vertical_delta"] == pytest.approx(-0.03)
    assert second["diagnostic_deltas_from_checkpoint_0"]["left_vertical"] == pytest.approx(-0.03)
    assert second["diagnostic_deltas_from_checkpoint_0"]["right_vertical"] == pytest.approx(-0.03)


def test_checkpoint_median_association_is_descriptive_and_handles_constant_proxy() -> None:
    rows = [
        _row(0, -0.03, binocular_eye_opening=0.30, head_center_y=0.5),
        _row(1, -0.02, binocular_eye_opening=0.32, head_center_y=0.5),
        _row(2, -0.01, binocular_eye_opening=0.34, head_center_y=0.5),
    ]

    result = summarize_checkpoints(rows, calibration_center_vertical=-0.03)

    assert result["checkpoint_median_associations"]["binocular_eye_opening"] == pytest.approx(1)
    assert result["checkpoint_median_associations"]["head_center_y"] is None


def test_invalid_or_missing_checkpoint_data_is_rejected() -> None:
    for rows in (
        [_row(1, -0.04)],
        [_row(0, math.nan)],
        [_row(0, -0.04, target_x=0.4)],
        [_row(0, None, status="unavailable_no_face")],
    ):
        with pytest.raises(ValueError):
            summarize_checkpoints(rows, calibration_center_vertical=-0.045)
    with pytest.raises(ValueError):
        summarize_checkpoints([_row(0, -0.04)], calibration_center_vertical=math.inf)


def test_session_comparison_preserves_identity_and_reports_per_checkpoint_offsets() -> None:
    first = {
        "participant": "cagri",
        "session": "A",
        "calibration_center_vertical": -0.04,
        "rows": [_row(0, -0.04), _row(1, -0.05)],
    }
    second = {
        "participant": "cagri",
        "session": "B",
        "calibration_center_vertical": -0.03,
        "rows": [_row(0, -0.035), _row(1, -0.06)],
    }

    comparison = compare_sessions([first, second])

    assert comparison["participant"] == "cagri"
    assert comparison["sessions"]["A"]["first_to_last_vertical_delta"] == pytest.approx(-0.01)
    assert comparison["sessions"]["B"]["first_to_last_vertical_delta"] == pytest.approx(-0.025)
    assert comparison["B_minus_A"]["checkpoint_vertical_medians"] == pytest.approx([0.005, -0.01])
    with pytest.raises(ValueError):
        compare_sessions([first, {**second, "participant": "fatih"}])
