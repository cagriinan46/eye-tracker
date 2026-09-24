"""Hardware-free integration of the existing Vision and Gaze stages."""

import pytest

from eye_tracker.app.gaze_pipeline import process_gaze_frame
from eye_tracker.gaze.calibration import CalibrationSample, fit_independent_linear
from eye_tracker.gaze.estimator import GazeEstimate, GazeUnavailable, UnavailableReason
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint

LEFT_CONTOUR = (249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466)
RIGHT_CONTOUR = (7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246)


class FakeSource:
    def __init__(self, frame: CameraFrame | None) -> None:
        self.frame = frame
        self.reads = 0

    def read(self) -> CameraFrame | None:
        self.reads += 1
        return self.frame


class FakeExtractor:
    def __init__(self, observation: LandmarkObservation) -> None:
        self.observation = observation
        self.frames: list[CameraFrame] = []

    def extract(self, frame: CameraFrame) -> LandmarkObservation:
        self.frames.append(frame)
        return self.observation


def valid_frame() -> CameraFrame:
    return CameraFrame(payload=object(), width=1000, height=500, timestamp_ns=123)


def valid_observation() -> LandmarkObservation:
    points = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    for contour, center_x, corners, upper, lower, iris in (
        (LEFT_CONTOUR, 0.3, (263, 362), 386, 374, (474, 475, 476, 477)),
        (RIGHT_CONTOUR, 0.7, (33, 133), 159, 145, (469, 470, 471, 472)),
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


def fitted_mapping():
    samples = (
        CalibrationSample(h, v, x, y)
        for h, v, x, y in (
            (0.4, -0.1, 0.2, 0.2),
            (0.5, 0.0, 0.5, 0.5),
            (0.6, 0.1, 0.8, 0.8),
        )
    )
    return fit_independent_linear(samples)


def test_valid_vision_path_uses_existing_features_and_fitted_mapping() -> None:
    frame = valid_frame()
    source = FakeSource(frame)
    extractor = FakeExtractor(valid_observation())

    result = process_gaze_frame(source, extractor, fitted_mapping())

    assert isinstance(result, GazeEstimate)
    assert (result.x, result.y) == pytest.approx((0.5, 0.5))
    assert source.reads == 1
    assert extractor.frames == [frame]


def test_failed_camera_read_is_unavailable_without_running_extractor() -> None:
    source = FakeSource(None)
    extractor = FakeExtractor(valid_observation())

    result = process_gaze_frame(source, extractor, fitted_mapping())

    assert result == GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    assert source.reads == 1
    assert extractor.frames == []


def test_unavailable_landmarks_do_not_fabricate_coordinates() -> None:
    frame = valid_frame()
    extractor = FakeExtractor(LandmarkObservation(123, None))

    result = process_gaze_frame(FakeSource(frame), extractor, fitted_mapping())

    assert result == GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    assert extractor.frames == [frame]
    assert not hasattr(result, "x")


def test_incomplete_landmarks_report_invalid_features() -> None:
    truncated = LandmarkObservation(123, valid_observation().landmarks[:-1])

    result = process_gaze_frame(
        FakeSource(valid_frame()), FakeExtractor(truncated), fitted_mapping()
    )

    assert result == GazeUnavailable(UnavailableReason.INVALID_FEATURES)


def test_degenerate_eye_geometry_reports_invalid_features() -> None:
    collapsed = LandmarkObservation(123, (NormalizedPoint(0.5, 0.5),) * 478)

    result = process_gaze_frame(
        FakeSource(valid_frame()), FakeExtractor(collapsed), fitted_mapping()
    )

    assert result == GazeUnavailable(UnavailableReason.INVALID_FEATURES)


def test_valid_features_with_no_session_mapping_remain_calibration_unavailable() -> None:
    result = process_gaze_frame(FakeSource(valid_frame()), FakeExtractor(valid_observation()), None)

    assert result == GazeUnavailable(UnavailableReason.CALIBRATION_UNAVAILABLE)


def test_only_numerical_eye_features_cross_into_the_mapping() -> None:
    class RecordingMapping:
        def __init__(self) -> None:
            self.received: tuple[float, float] | None = None

        def predict(
            self, horizontal_feature: float, vertical_feature: float
        ) -> tuple[float, float]:
            self.received = horizontal_feature, vertical_feature
            return 0.25, 0.75

    mapping = RecordingMapping()
    result = process_gaze_frame(
        FakeSource(valid_frame()), FakeExtractor(valid_observation()), mapping
    )

    assert result == GazeEstimate(0.25, 0.75)
    assert mapping.received == pytest.approx((0.5, 0.0))
    assert all(type(value) is float for value in mapping.received)


def test_mapping_failure_reason_is_preserved() -> None:
    class FailingMapping:
        def predict(
            self, horizontal_feature: float, vertical_feature: float
        ) -> tuple[float, float]:
            raise ValueError("session mapping failed")

    result = process_gaze_frame(
        FakeSource(valid_frame()), FakeExtractor(valid_observation()), FailingMapping()
    )

    assert result == GazeUnavailable(UnavailableReason.MAPPING_FAILED)


def test_invalid_prediction_reason_is_preserved() -> None:
    class InvalidMapping:
        def predict(
            self, horizontal_feature: float, vertical_feature: float
        ) -> tuple[float, float]:
            return float("nan"), 0.5

    result = process_gaze_frame(
        FakeSource(valid_frame()), FakeExtractor(valid_observation()), InvalidMapping()
    )

    assert result == GazeUnavailable(UnavailableReason.INVALID_PREDICTION)


def test_unexpected_extractor_error_is_not_hidden() -> None:
    class BrokenExtractor:
        def extract(self, frame: CameraFrame) -> LandmarkObservation:
            raise RuntimeError("broken detector")

    with pytest.raises(RuntimeError, match="broken detector"):
        process_gaze_frame(FakeSource(valid_frame()), BrokenExtractor(), fitted_mapping())
