"""Synthetic tests for the final fixed lid-feature round and holdout rule."""

from copy import deepcopy

import pytest

from experiments.lid_reference_vertical_feature_benchmark.analysis import (
    _validated_report,
    eligibility,
    evaluate_split,
    feature_presentations,
    ratio,
)
from experiments.lid_reference_vertical_feature_benchmark.candidates import (
    APERTURE_EPSILON_PX,
    BASELINE,
    CANDIDATES,
    LID_FRACTION,
    LID_MIDPOINT_FIXED_SCALE,
    InvalidAperture,
    binocular,
    calibration_references,
    feature,
)


def eye(corner_span=4.0, upper=-1.0, lower=1.0, iris=0.5, reverse=False):
    a, b = ([corner_span / 100, 0], [0, 0]) if reverse else ([0, 0], [corner_span / 100, 0])
    return {
        "corner_a": a,
        "corner_b": b,
        "upper_lid": [corner_span / 200, upper / 100],
        "lower_lid": [corner_span / 200, lower / 100],
        "iris_center": [corner_span / 200, iris / 100],
    }


def row(phase="calibration", corner_span=4.0, reverse=False, upper=-1.0, lower=1.0, iris=0.5):
    geometry = eye(corner_span, upper, lower, iris, reverse)
    return {
        "phase": phase,
        "status": "usable",
        "geometry": {"left": geometry, "right": deepcopy(geometry)},
        "left_vertical": iris / corner_span,
        "right_vertical": iris / corner_span,
    }


def test_exact_candidate_set_and_calibration_only_axis_scale():
    assert CANDIDATES == (BASELINE, LID_MIDPOINT_FIXED_SCALE, LID_FRACTION)
    calibration = [row(corner_span=4), row(corner_span=6)]
    reference = calibration_references(calibration, 100, 100)
    assert reference["left"].span_px == 5
    assert reference["left"].normal_y == 1
    calibration.append(row(phase="diagnostic", corner_span=100, reverse=True))
    assert calibration_references(calibration, 100, 100) == reference


def test_lid_midpoint_and_fraction_formulas_and_no_clipping():
    reference = calibration_references([row()], 100, 100)
    current = row(phase="diagnostic")
    assert feature(current, BASELINE, "left", reference["left"], 100, 100) == pytest.approx(0.125)
    assert feature(
        current, LID_MIDPOINT_FIXED_SCALE, "left", reference["left"], 100, 100
    ) == pytest.approx(0.125)
    assert feature(current, LID_FRACTION, "left", reference["left"], 100, 100) == pytest.approx(
        0.25
    )
    assert binocular(current, LID_FRACTION, reference, 100, 100) == pytest.approx(0.25)
    far = row(phase="diagnostic", iris=4)
    assert feature(far, LID_FRACTION, "left", reference["left"], 100, 100) == pytest.approx(2)


def test_axis_sign_is_calibration_fixed_and_reversed_lid_gap_rejected():
    reference = calibration_references([row(reverse=True)], 100, 100)
    assert reference["left"].normal_y == 1
    flipped = row(phase="diagnostic", upper=1, lower=-1)
    with pytest.raises(InvalidAperture):
        feature(flipped, LID_FRACTION, "left", reference["left"], 100, 100)
    near_zero = row(phase="diagnostic", upper=-1, lower=-1 + 0.5 * APERTURE_EPSILON_PX)
    with pytest.raises(InvalidAperture):
        feature(near_zero, LID_FRACTION, "left", reference["left"], 100, 100)


def test_candidate_presentation_aggregation_and_calibration_noise_are_deterministic():
    report = {
        "camera_resolution": [100, 100],
        "minimum_usable_samples_per_presentation": 1,
        "presentations": [],
        "rows": [],
    }
    reference = calibration_references([row()], 100, 100)
    for order in range(1, 10):
        report["presentations"].append(
            {
                "order": order,
                "phase": "calibration",
                "target_id": str(order),
                "target_y": 0.2,
                "condition": "natural",
                "block": 0,
                "usable_count": 2,
            }
        )
        for iris in (0.25, 0.75):
            sample = row(iris=iris)
            sample["presentation_order"] = order
            report["rows"].append(sample)
    first = feature_presentations(report, LID_MIDPOINT_FIXED_SCALE, reference)
    assert first == feature_presentations(deepcopy(report), LID_MIDPOINT_FIXED_SCALE, reference)
    presentations, noise, skipped = first
    assert len(presentations) == 9 and skipped == 0
    assert presentations[0]["binocular"] == pytest.approx(0.125)
    assert noise["binocular"] == pytest.approx(0.0625)


def record(mae=1.0, narrow=1.0, wide=1.0, repeated=1.0, noise=1.0, ordered=True):
    return {
        "natural": {"mae": mae, "ordered": ordered},
        "conditions": {
            "comfortably_narrow": {"mapped_absolute": {"median": narrow}},
            "comfortably_wide": {"mapped_absolute": {"median": wide}},
        },
        "repeated": {"mapped_absolute": {"median": repeated}},
        "calibration_mapped_noise": noise,
    }


def holdout(candidate):
    return {
        "tier": "primary",
        "session": "live-3",
        "candidates": {
            BASELINE: {"fields": {"binocular": record()}},
            LID_MIDPOINT_FIXED_SCALE: {"fields": {"binocular": candidate}},
            LID_FRACTION: {"fields": {"binocular": record(narrow=1.2)}},
        },
    }


def test_holdout_rule_passes_exact_boundaries_and_fails_each_constraint():
    passing = record(mae=1.15, narrow=0.85, wide=1.15, repeated=1.15, noise=1.15)
    result = eligibility(holdout(passing))
    assert result[LID_MIDPOINT_FIXED_SCALE]["eligible"]
    assert not result[LID_FRACTION]["eligible"]
    failures = (
        ("ordered", False, "row_ordering"),
        ("mae", 1.151, "natural_mae"),
        ("narrow", 0.851, "one_opening_improves"),
        ("wide", 1.151, "other_opening_not_worse"),
        ("repeated", 1.151, "repeated_target"),
        ("noise", 1.151, "calibration_amplification"),
    )
    for field, value, criterion in failures:
        changed = deepcopy(passing)
        if field == "ordered":
            changed["natural"]["ordered"] = value
        elif field == "mae":
            changed["natural"]["mae"] = value
        elif field == "narrow":
            changed["conditions"]["comfortably_narrow"]["mapped_absolute"]["median"] = value
        elif field == "wide":
            changed["conditions"]["comfortably_wide"]["mapped_absolute"]["median"] = value
        elif field == "repeated":
            changed["repeated"]["mapped_absolute"]["median"] = value
        else:
            changed["calibration_mapped_noise"] = value
        assert not eligibility(holdout(changed))[LID_MIDPOINT_FIXED_SCALE]["checks"][criterion]
    assert ratio(0, 0) == 1
    assert ratio(1, 0) == float("inf")


def test_holdout_separation_and_incompatible_protocol_rejection():
    with pytest.raises(ValueError, match="development must"):
        evaluate_split([{"session": "live-2"}, {"session": "live-1"}], {"session": "live-3"})
    with pytest.raises(ValueError, match="primary split"):
        evaluate_split(
            [
                {"session": "live-1", "protocol_name": "eye_geometry_decomposition"},
                {"session": "live-2", "protocol_name": "face_reference_corner_stability"},
            ],
            {"session": "live-3", "protocol_name": "face_reference_corner_stability"},
        )
    with pytest.raises(ValueError, match="incompatible study protocol"):
        _validated_report({"protocol_name": "eye_opening_controlled", "protocol_version": 2})
    with pytest.raises(ValueError, match="eligibility requires"):
        eligibility({"tier": "secondary", "session": "live-3"})
