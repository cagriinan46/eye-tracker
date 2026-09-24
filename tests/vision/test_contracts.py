"""Behavioral checks for the vendor-neutral Vision contracts."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from eye_tracker.vision.contracts import (
    CameraFrame,
    FrameSource,
    LandmarkExtractor,
    LandmarkObservation,
    NormalizedPoint,
)


def test_camera_frame_preserves_payload_and_immutable_capture_metadata() -> None:
    payload = object()
    frame = CameraFrame(payload=payload, width=1920, height=1080, timestamp_ns=123)

    assert frame.payload is payload
    assert (frame.width, frame.height, frame.timestamp_ns) == (1920, 1080, 123)
    with pytest.raises(FrozenInstanceError):
        frame.width = 640  # type: ignore[misc]


@pytest.mark.parametrize(
    ("width", "height", "timestamp_ns"),
    [(0, 480, 1), (640, -1, 1), (640, 480, -1)],
)
def test_camera_frame_rejects_invalid_metadata(width: int, height: int, timestamp_ns: int) -> None:
    with pytest.raises(ValueError):
        CameraFrame(payload=object(), width=width, height=height, timestamp_ns=timestamp_ns)


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_normalized_point_rejects_non_finite_coordinates(value: float) -> None:
    with pytest.raises(ValueError):
        NormalizedPoint(x=value, y=0.5)
    with pytest.raises(ValueError):
        NormalizedPoint(x=0.5, y=value)


def test_normalized_point_preserves_out_of_frame_geometry() -> None:
    point = NormalizedPoint(x=1.05, y=-0.02)

    assert (point.x, point.y) == (1.05, -0.02)


def test_landmark_observation_distinguishes_unavailable_from_geometry() -> None:
    unavailable = LandmarkObservation(timestamp_ns=123, landmarks=None)
    point = NormalizedPoint(x=0.4, y=0.6)
    available = LandmarkObservation(timestamp_ns=123, landmarks=(point,))

    assert unavailable.landmarks is None
    assert available.landmarks == (point,)
    with pytest.raises(ValueError):
        LandmarkObservation(timestamp_ns=123, landmarks=())


def test_landmark_observation_rejects_mutable_landmark_collections() -> None:
    point = NormalizedPoint(x=0.4, y=0.6)

    with pytest.raises(TypeError):
        LandmarkObservation(timestamp_ns=123, landmarks=[point])  # type: ignore[arg-type]


def test_protocols_accept_a_source_with_explicit_lifecycle_and_an_extractor() -> None:
    frame = CameraFrame(payload=object(), width=640, height=480, timestamp_ns=123)

    class FakeSource:
        def __init__(self) -> None:
            self.opened = False

        def open(self) -> None:
            self.opened = True

        def read(self) -> CameraFrame | None:
            return frame if self.opened else None

        def close(self) -> None:
            self.opened = False

    class FakeExtractor:
        def extract(self, source_frame: CameraFrame) -> LandmarkObservation:
            return LandmarkObservation(timestamp_ns=source_frame.timestamp_ns, landmarks=None)

    source: FrameSource = FakeSource()
    extractor: LandmarkExtractor = FakeExtractor()
    source.open()
    try:
        captured = source.read()
        assert captured is frame
        assert extractor.extract(captured).landmarks is None
    finally:
        source.close()

    assert not source.opened
