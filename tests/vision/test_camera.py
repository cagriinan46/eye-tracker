"""Hardware-free behavior checks for the concrete camera source."""

from types import SimpleNamespace

import pytest

from eye_tracker.vision import camera
from eye_tracker.vision.contracts import CameraFrame


class FakeCapture:
    def __init__(self, opened: bool = True) -> None:
        self.opened = opened
        self.reads: list[tuple[bool, object | None]] = []
        self.releases = 0

    def isOpened(self) -> bool:
        return self.opened

    def read(self) -> tuple[bool, object | None]:
        return self.reads.pop(0)

    def release(self) -> None:
        self.releases += 1


def test_explicit_index_capture_converts_a_successful_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = FakeCapture()
    image = SimpleNamespace(shape=(480, 640, 3))
    capture.reads.append((True, image))
    selected: list[int] = []

    def make_capture(index: int) -> FakeCapture:
        selected.append(index)
        return capture

    monkeypatch.setattr(camera, "_load_cv2", lambda: SimpleNamespace(VideoCapture=make_capture))
    monkeypatch.setattr(camera, "monotonic_ns", lambda: 123_000_000)
    source = camera.OpenCVCameraSource(camera_index=1)

    source.open()
    try:
        frame = source.read()
    finally:
        source.close()

    assert selected == [1]
    assert isinstance(frame, CameraFrame)
    assert frame.payload is image
    assert (frame.width, frame.height, frame.timestamp_ns) == (640, 480, 123_000_000)
    assert capture.releases == 1


def test_failed_read_returns_unavailable_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = FakeCapture()
    capture.reads.extend(((False, None), (True, None)))
    monkeypatch.setattr(
        camera, "_load_cv2", lambda: SimpleNamespace(VideoCapture=lambda _: capture)
    )
    source = camera.OpenCVCameraSource(camera_index=0)

    source.open()
    try:
        assert source.read() is None
        assert source.read() is None
    finally:
        source.close()
    assert capture.releases == 1


def test_open_failure_releases_capture_and_reports_camera_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = FakeCapture(opened=False)
    monkeypatch.setattr(
        camera, "_load_cv2", lambda: SimpleNamespace(VideoCapture=lambda _: capture)
    )
    source = camera.OpenCVCameraSource(camera_index=7)

    with pytest.raises(RuntimeError, match="camera index 7"):
        source.open()
    assert capture.releases == 1
    with pytest.raises(RuntimeError, match="not open"):
        source.read()
    source.close()
    assert capture.releases == 1


def test_close_is_safe_after_a_read_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = FakeCapture()
    monkeypatch.setattr(
        camera, "_load_cv2", lambda: SimpleNamespace(VideoCapture=lambda _: capture)
    )
    source = camera.OpenCVCameraSource(camera_index=1)
    source.open()

    with pytest.raises(IndexError):
        try:
            source.read()
        finally:
            source.close()

    assert capture.releases == 1


def test_invalid_camera_index_is_rejected() -> None:
    with pytest.raises(ValueError, match="camera index"):
        camera.OpenCVCameraSource(camera_index=-1)
