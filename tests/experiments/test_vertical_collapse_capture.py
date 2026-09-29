"""Hardware-free checks for Issue #44's per-frame diagnostic collection."""

import pytest

from eye_tracker.gaze.calibration import IndependentLinearMapping
from eye_tracker.gaze.estimator import GazeEstimate, GazeUnavailable, UnavailableReason
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint
from eye_tracker.vision.eye_features import EyeFeatures


def _capture():
    from experiments.vertical_collapse_diagnostics import capture

    return capture


def _observation() -> LandmarkObservation:
    from eye_tracker.vision.eye_topology import _LEFT_CONTOUR, _RIGHT_CONTOUR

    points = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    for contour, center_x, corners, upper, lower, iris in (
        (_LEFT_CONTOUR, 0.3, (263, 362), 386, 374, (474, 475, 476, 477)),
        (_RIGHT_CONTOUR, 0.7, (33, 133), 159, 145, (469, 470, 471, 472)),
    ):
        for index in contour:
            points[index] = NormalizedPoint(center_x, 0.3)
        points[corners[0]] = NormalizedPoint(center_x - 0.1, 0.3)
        points[corners[1]] = NormalizedPoint(center_x + 0.1, 0.3)
        points[upper] = NormalizedPoint(center_x, 0.28)
        points[lower] = NormalizedPoint(center_x, 0.32)
        for index in iris:
            points[index] = NormalizedPoint(center_x, 0.3)
    return LandmarkObservation(123, tuple(points))


class Source:
    def __init__(self, frame: CameraFrame | None):
        self.frame = frame

    def read(self) -> CameraFrame | None:
        return self.frame


class Extractor:
    def __init__(self, observation: LandmarkObservation):
        self.observation = observation

    def extract(self, frame: CameraFrame) -> LandmarkObservation:
        assert frame.timestamp_ns == 123
        return self.observation


def test_valid_frame_records_production_features_and_numerical_diagnostics() -> None:
    result, details = _capture().measure_once(
        Source(CameraFrame(object(), 1000, 500, 123)), Extractor(_observation()), None
    )

    assert isinstance(result, EyeFeatures)
    assert (result.horizontal, result.vertical) == pytest.approx((0.5, 0.0))
    assert details["status"] == "usable"
    assert details["horizontal"] == pytest.approx(0.5)
    assert details["vertical"] == 0.0
    assert details["left_vertical"] == 0.0
    assert details["right_vertical"] == 0.0
    assert details["binocular_eye_opening"] > 0
    assert details["head_center_y"] == 0.3
    assert "payload" not in details
    assert "landmarks" not in details


def test_fitted_mapping_uses_existing_estimator_without_changing_features() -> None:
    mapping = IndependentLinearMapping(2.0, -0.5, 3.0, 0.4)
    result, details = _capture().measure_once(
        Source(CameraFrame(object(), 1000, 500, 123)), Extractor(_observation()), mapping
    )

    assert isinstance(result, GazeEstimate)
    assert (result.x, result.y) == pytest.approx((0.5, 0.4))
    assert (details["horizontal"], details["vertical"]) == pytest.approx((0.5, 0.0))
    assert (details["predicted_x"], details["predicted_y"]) == pytest.approx((0.5, 0.4))


def test_unavailable_frame_and_no_face_remain_explicit() -> None:
    missing_frame, frame_details = _capture().measure_once(
        Source(None), Extractor(_observation()), None
    )
    no_face, face_details = _capture().measure_once(
        Source(CameraFrame(object(), 1000, 500, 123)),
        Extractor(LandmarkObservation(123, None)),
        None,
    )

    assert missing_frame == GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    assert frame_details["status"] == "unavailable_frame"
    assert frame_details["horizontal"] is None
    assert no_face == GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    assert face_details["status"] == "unavailable_no_face"
    assert face_details["vertical"] is None


def test_incomplete_geometry_is_recorded_without_a_fake_coordinate() -> None:
    result, details = _capture().measure_once(
        Source(CameraFrame(object(), 1000, 500, 123)),
        Extractor(LandmarkObservation(123, (NormalizedPoint(0.5, 0.5),))),
        None,
    )

    assert result == GazeUnavailable(UnavailableReason.INVALID_FEATURES)
    assert details["status"] == "unavailable_geometry"
    assert details["predicted_x"] is None
    assert details["predicted_y"] is None
