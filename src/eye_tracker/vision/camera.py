"""OpenCV-backed local camera source; OpenCV stays inside Vision."""

from time import monotonic_ns

from eye_tracker.vision.contracts import CameraFrame


def _load_cv2():
    import cv2

    return cv2


class OpenCVCameraSource:
    """Read a configured camera index through the ``FrameSource`` lifecycle.

    Camera indices identify devices only in the current environment; index 0
    must not be assumed to select a built-in camera.
    """

    def __init__(self, camera_index: int) -> None:
        if camera_index < 0:
            raise ValueError("camera index must be non-negative")
        self.camera_index = camera_index
        self._capture: object | None = None

    def open(self) -> None:
        if self._capture is not None:
            raise RuntimeError("camera source is already open")
        capture = _load_cv2().VideoCapture(self.camera_index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"could not open camera index {self.camera_index}")
        self._capture = capture

    def read(self) -> CameraFrame | None:
        if self._capture is None:
            raise RuntimeError("camera source is not open")
        ok, image = self._capture.read()
        if not ok or image is None:
            return None
        height, width = image.shape[:2]
        return CameraFrame(payload=image, width=width, height=height, timestamp_ns=monotonic_ns())

    def close(self) -> None:
        capture = self._capture
        self._capture = None
        if capture is not None:
            capture.release()
