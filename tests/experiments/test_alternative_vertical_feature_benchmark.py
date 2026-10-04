"""Deterministic, camera-free checks of candidate geometry and evaluation."""

from copy import deepcopy
from math import isclose

import pytest

from experiments.alternative_vertical_feature_benchmark.analysis import (
    _condition_pairs,
    _natural,
    _repeated,
    analyze,
    fit_mapping,
    percentile,
)
from experiments.alternative_vertical_feature_benchmark.candidates import (
    BASELINE,
    CANDIDATES,
    FACE_IRIS_Y,
    STABLE_FRAME,
    STABLE_SPAN,
    binocular,
    calibration_references,
    feature,
)
from experiments.face_reference_corner_stability_study.face_reference import (
    apply_similarity,
    fit_similarity,
)


def _eye(span=4.0, tilt=0.0, iris_y=1.0):
    return {
        "corner_a": [0.0, 0.0],
        "corner_b": [span / 100, tilt / 100],
        "iris_center": [span / 200, iris_y / 100],
        "upper_lid": [span / 200, -1 / 100],
        "lower_lid": [span / 200, 2 / 100],
    }


def _row(phase="calibration", span=4.0, tilt=0.0, iris_y=1.0):
    return {
        "phase": phase,
        "status": "usable",
        "geometry": {"left": _eye(span, tilt, iris_y), "right": _eye(span, tilt, iris_y)},
        "left_vertical": iris_y / span,
        "right_vertical": iris_y / span,
    }


def test_bounded_candidate_set_and_calibration_only_reference():
    assert CANDIDATES == (BASELINE, FACE_IRIS_Y, STABLE_SPAN, STABLE_FRAME)
    calibration = [_row(span=4), _row(span=6)]
    reference = calibration_references(calibration, 100, 100)
    assert reference["left"].span_px == 5
    calibration.append(_row(phase="diagnostic", span=100))
    assert calibration_references(calibration, 100, 100) == reference


def test_stable_span_and_frame_have_known_synthetic_behavior():
    reference = calibration_references([_row(span=4)], 100, 100)
    current = _row(phase="diagnostic", span=8, iris_y=1)
    assert feature(current, BASELINE, "left", reference["left"], 100, 100) == 0.125
    assert isclose(feature(current, STABLE_SPAN, "left", reference["left"], 100, 100), 0.25)
    assert isclose(feature(current, STABLE_FRAME, "left", reference["left"], 100, 100), 0.25)
    tilted = _row(phase="diagnostic", span=4, tilt=4, iris_y=1)
    assert not isclose(
        feature(tilted, STABLE_SPAN, "left", reference["left"], 100, 100),
        feature(tilted, STABLE_FRAME, "left", reference["left"], 100, 100),
    )
    assert isclose(binocular(current, STABLE_SPAN, reference, 100, 100), 0.25)
    high_iris = _row(phase="diagnostic", span=4, iris_y=10)
    assert feature(high_iris, STABLE_FRAME, "left", reference["left"], 100, 100) == 2.5


def test_face_iris_y_uses_normalized_face_coordinate_and_requires_anchors():
    template = [[10.0, 20.0], [20.0, 20.0], [10.0, 30.0]]
    shifted = [[0.0, 10.0], [10.0, 10.0], [0.0, 20.0]]
    transform = fit_similarity([[x / 100, y / 100] for x, y in shifted], template, 100, 100)
    iris = apply_similarity([0.05, 0.15], transform, 100, 100)
    row = _row()
    row["face_normalized_geometry"] = {
        "left": {"iris_center": iris},
        "right": {"iris_center": iris},
    }
    assert isclose(feature(row, FACE_IRIS_Y, "left", None, 100, 100), 25.0)
    with pytest.raises(ValueError, match="face iris candidate"):
        feature(_row(), FACE_IRIS_Y, "left", None, 100, 100)


def test_mapping_uses_only_nine_calibration_presentations():
    calibration = [
        {"phase": "calibration", "target_y": y, "binocular": y * 2 + 1}
        for y in (0.2, 0.5, 0.8)
        for _ in range(3)
    ]
    calibration.append({"phase": "diagnostic", "target_y": 0.5, "binocular": 1000})
    assert fit_mapping(calibration) == pytest.approx((0.5, -0.5))
    with pytest.raises(ValueError, match="nine ordinary"):
        fit_mapping(calibration[1:])


def _presentations():
    result = []
    for y, target in ((0.25, "upper"), (0.5, "center"), (0.75, "lower")):
        for block in (1, 2, 3):
            for condition, offset in (
                ("natural", 0),
                ("comfortably_narrow", 0.1),
                ("comfortably_wide", -0.1),
            ):
                result.append(
                    {
                        "phase": "diagnostic",
                        "target_id": target,
                        "target_y": y,
                        "block": block,
                        "condition": condition,
                        "binocular": y + offset + block * 0.01,
                    }
                )
    return result


def test_natural_condition_and_repeated_metrics_are_deterministic():
    presentations = _presentations()
    natural = _natural(presentations, 1, 0, "binocular")
    assert natural["ordered"]
    assert natural["mae"] == pytest.approx(0.02)
    assert natural["upper_center_margin"] == pytest.approx(0.25)
    condition = _condition_pairs(presentations, 1, "binocular")
    assert condition["comfortably_narrow"]["mapped_absolute"]["median"] == pytest.approx(0.1)
    assert condition["comfortably_wide"]["negative"] == 9
    repeats = _repeated(presentations, 1, "binocular")
    assert len(repeats["pairs"]) == 27
    assert repeats["mapped_absolute"]["max"] == pytest.approx(0.02)
    assert repeats == _repeated(deepcopy(presentations), 1, "binocular")
    assert percentile([0, 10], 0.95) == pytest.approx(9.5)


def test_rejects_wrong_or_pilot_protocol_before_using_samples():
    for protocol in (
        "eye_opening_controlled",
        "face_reference_corner_stability",
        "eye_geometry_decomposition",
    ):
        report = {"protocol_name": protocol, "protocol_version": 2}
        with pytest.raises(ValueError, match="incompatible study protocol"):
            analyze(report)
