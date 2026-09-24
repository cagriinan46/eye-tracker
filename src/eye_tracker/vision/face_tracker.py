"""MediaPipe Face Landmarker adapter; raw detector types stay in Vision."""

from pathlib import Path

from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint


def _load_cv2():
    import cv2

    return cv2


def _load_mediapipe():
    import mediapipe

    return mediapipe


class MediaPipeFaceLandmarkExtractor:
    """Convert one local Face Landmarker result to normalized project points.

    The caller owns this native resource and must call ``close`` or use a
    context manager. The model bundle is a local file, never a runtime network
    dependency. This is a Phase 1 adapter choice, not a permanent framework.
    """

    def __init__(self, model_path: str | Path) -> None:
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"Face Landmarker model not found: {model_path}")
        self._cv2 = _load_cv2()
        self._mp = _load_mediapipe()
        options = self._mp.tasks.vision.FaceLandmarkerOptions(
            base_options=self._mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=self._mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
        )
        self._landmarker = self._mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def extract(self, frame: CameraFrame) -> LandmarkObservation:
        if self._landmarker is None:
            raise RuntimeError("Face Landmarker is closed")
        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=self._cv2.cvtColor(frame.payload, self._cv2.COLOR_BGR2RGB),
        )
        timestamp_ms = max(self._last_timestamp_ms + 1, frame.timestamp_ns // 1_000_000)
        self._last_timestamp_ms = timestamp_ms
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.face_landmarks or not result.face_landmarks[0]:
            return LandmarkObservation(timestamp_ns=frame.timestamp_ns, landmarks=None)
        try:
            points = tuple(
                NormalizedPoint(x=float(point.x), y=float(point.y))
                for point in result.face_landmarks[0]
            )
        except (TypeError, ValueError):
            return LandmarkObservation(timestamp_ns=frame.timestamp_ns, landmarks=None)
        return LandmarkObservation(timestamp_ns=frame.timestamp_ns, landmarks=points)

    def close(self) -> None:
        landmarker = self._landmarker
        self._landmarker = None
        if landmarker is not None:
            landmarker.close()

    def __enter__(self) -> "MediaPipeFaceLandmarkExtractor":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()
