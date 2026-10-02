"""Hardware-free tests for the predeclared eye-opening design and analysis."""

from collections import Counter

import pytest

from experiments.eye_opening_controlled_study.analysis import aggregate, analyze, compare_conditions
from experiments.eye_opening_controlled_study.protocol import (
    CONDITIONS,
    INSTRUCTIONS,
    TARGETS,
    schedule,
)


def synthetic_report():
    rows = []
    presentations = []
    for item in schedule():
        opening = {"narrow": 0.2, "natural": 0.3, "wide": 0.4}[item.condition]
        vertical = item.target.y / 10 + opening / 10 + item.block / 1000
        for sample in range(5):
            rows.append(
                {
                    "participant": "cagri",
                    "session": "live-1",
                    "phase": item.phase,
                    "target_id": item.target.name,
                    "target_x": item.target.x,
                    "target_y": item.target.y,
                    "condition": item.condition,
                    "block": item.block,
                    "presentation_order": item.order,
                    "status": "usable",
                    "vertical": vertical + (sample - 2) / 1000,
                    "left_vertical": vertical + 0.01 + (sample - 2) / 1000,
                    "right_vertical": vertical - 0.01 + (sample - 2) / 1000,
                    "horizontal": 0.5,
                    "left_eye_opening": opening - 0.01,
                    "right_eye_opening": opening + 0.01,
                    "binocular_eye_opening": opening,
                    "head_center_y": 0.5 + item.block / 100,
                    "predicted_y": vertical * 20,
                }
            )
        presentations.append(
            {
                "order": item.order,
                "phase": item.phase,
                "target_id": item.target.name,
                "target_x": item.target.x,
                "target_y": item.target.y,
                "condition": item.condition,
                "block": item.block,
                "usable_count": 5,
                "unavailable_count": 0,
                "sampling_attempts": 5,
                "vertical_feature": vertical,
            }
        )
    return {
        "participant": "cagri",
        "session": "live-1",
        "rows": rows,
        "presentations": presentations,
        "minimum_usable_samples_per_presentation": 5,
        "mapping_coefficients": {"y_slope": 20.0},
    }


def test_schedule_is_fixed_balanced_and_rotated():
    plan = schedule()
    assert plan == schedule()
    assert len(plan) == 36
    assert len([p for p in plan if p.phase == "calibration"]) == 9
    diagnostic = [p for p in plan if p.phase == "diagnostic"]
    assert len(diagnostic) == 27
    assert Counter((p.target.name, p.condition) for p in diagnostic) == {
        (target.name, condition): 3 for target in TARGETS for condition in CONDITIONS
    }
    assert all(
        Counter((p.target.name, p.condition) for p in diagnostic if p.block == block)
        == {(target.name, condition): 1 for target in TARGETS for condition in CONDITIONS}
        for block in (1, 2, 3)
    )
    assert {p.condition: INSTRUCTIONS[p.condition] for p in diagnostic} == {
        "narrow": "GENTLY NARROW",
        "natural": "NATURAL",
        "wide": "COMFORTABLY WIDE",
    }
    for target in TARGETS:
        first_positions = [
            next(
                index
                for index, p in enumerate(diagnostic)
                if p.block == block and p.target == target and p.condition == "narrow"
            )
            % 3
            for block in (1, 2, 3)
        ]
        assert sorted(first_positions) == [0, 1, 2]


def test_aggregation_and_fixed_target_signed_deltas_are_unclipped():
    report = synthetic_report()
    presentations = aggregate(report)
    assert len(presentations) == 36
    assert presentations[9]["vertical"] == report["presentations"][9]["vertical_feature"]
    assert presentations[9]["vertical_p95_p05"] == pytest.approx(0.0036)
    pairs = compare_conditions(presentations, 20.0)
    assert len(pairs) == 27
    pair = next(
        p
        for p in pairs
        if p["block"] == 1 and p["target_id"] == "upper" and p["comparison"] == "wide_minus_natural"
    )
    assert pair["delta_vertical"] == pytest.approx(0.01)
    assert pair["abs_delta_vertical"] == pytest.approx(0.01)
    assert pair["delta_left_vertical"] == pytest.approx(0.01)
    assert pair["delta_right_vertical"] == pytest.approx(0.01)
    assert pair["common_mode_vertical_delta"] == pytest.approx(0.01)
    assert pair["differential_vertical_delta"] == pytest.approx(0)
    assert pair["same_direction"] is True
    assert pair["delta_binocular_eye_opening"] == pytest.approx(0.1)
    assert pair["delta_head_center_y"] == pytest.approx(0)
    assert pair["mapped_y_delta"] == pytest.approx(0.2)
    assert next(p for p in pairs if p["comparison"] == "narrow_minus_natural")["delta_vertical"] < 0


def test_manipulation_order_direction_and_head_summary():
    result = analyze(synthetic_report())
    summary = result["summary"]
    assert summary["opening_ordered_row_count"] == 3
    assert summary["opening_ordered_block_count"] == 9
    assert summary["diagnostic_presentation_count"] == 27
    for row in summary["rows"]:
        assert row["opening_separations"]["wide_minus_narrow"] == pytest.approx(0.2)
        assert row["opening_range_overlap"]["wide_minus_narrow"] is False
        assert row["wide_natural_direction"]["vertical_positive"] == 3
        assert sum(block["vertical_increasing"] for block in row["ordered_blocks"]) == 3
        assert row["comparisons"]["wide_minus_natural"]["same_direction_count"] == 3
        assert row["comparisons"]["wide_minus_natural"][
            "max_abs_delta_head_center_y"
        ] == pytest.approx(0)


def test_missing_optional_and_invalid_observations():
    report = synthetic_report()
    first = next(row for row in report["rows"] if row["presentation_order"] == 10)
    first["head_center_y"] = None
    first["left_eye_opening"] = None
    assert aggregate(report)[9]["head_center_y_count"] == 4
    first["status"] = "unavailable_geometry"
    first["vertical"] = None
    report["presentations"][9]["usable_count"] = 4
    report["presentations"][9]["unavailable_count"] = 1
    with pytest.raises(ValueError, match="insufficient"):
        aggregate(report)
    report["minimum_usable_samples_per_presentation"] = 4
    report["presentations"][9]["vertical_feature"] = 999
    with pytest.raises(ValueError, match="saved and raw"):
        aggregate(report)


def test_monocular_disagreement_is_recorded_without_correcting_feature():
    presentations = aggregate(synthetic_report())
    wide = next(
        p
        for p in presentations
        if p["phase"] == "diagnostic"
        and p["block"] == 1
        and p["target_id"] == "upper"
        and p["condition"] == "wide"
    )
    wide["left_vertical"] -= 0.03
    pair = next(
        p
        for p in compare_conditions(presentations)
        if p["block"] == 1 and p["target_id"] == "upper" and p["comparison"] == "wide_minus_natural"
    )
    assert pair["same_direction"] is False
    assert pair["differential_vertical_delta"] == pytest.approx(-0.03)
    assert pair["delta_vertical"] == pytest.approx(0.01)
    assert pair["mapped_y_delta"] is None


def test_large_mapping_difference_is_not_clipped_and_wrong_target_rejected():
    report = synthetic_report()
    pair = next(
        p
        for p in compare_conditions(aggregate(report), 200.0)
        if p["block"] == 1 and p["target_id"] == "upper" and p["comparison"] == "wide_minus_natural"
    )
    assert pair["mapped_y_delta"] == pytest.approx(2.0)
    report["rows"][45]["target_y"] = 0.75
    with pytest.raises(ValueError, match="protocol"):
        aggregate(report)


def test_binocular_sample_identity_checked_without_reconstructing_median():
    report = synthetic_report()
    report["rows"][0]["left_vertical"] += 0.001
    with pytest.raises(ValueError, match="per-eye mean"):
        aggregate(report)


def test_secondary_notification_exclusion_is_only_first_diagnostic_trio():
    report = synthetic_report()
    report["session"] = "live-3"
    for row in report["rows"]:
        row["session"] = "live-3"
    result = analyze(report)
    sensitivity = result["notification_sensitivity"]
    assert result["summary"]["diagnostic_presentation_count"] == 27
    assert result["summary"]["fixed_target_comparison_count"] == 27
    assert sensitivity["excluded_orders"] == [10, 11, 12]
    assert sensitivity["summary"]["diagnostic_presentation_count"] == 24
    assert sensitivity["summary"]["fixed_target_comparison_count"] == 24
    assert sensitivity["summary"]["opening_ordered_block_count"] == 8
    assert sensitivity["measured_opening_vertical_spearman"] == pytest.approx(0.9665953493282832)


def test_missing_opening_measurements_remain_unavailable_in_association():
    report = synthetic_report()
    for row in report["rows"]:
        if row["phase"] == "diagnostic":
            row["binocular_eye_opening"] = None
    result = analyze(report)
    assert result["measured_opening_vertical_spearman"] is None
    assert result["summary"]["opening_ordered_block_count"] == 0
    assert all(pair["delta_binocular_eye_opening"] is None for pair in result["condition_pairs"])
