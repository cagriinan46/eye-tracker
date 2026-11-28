"""Head-cursor pieces for the desktop demo worker (Issue #160).

The worker owns the camera; this module turns one BGR frame into the RAY signal
(Issue #156 winner) plus eye landmarks for blink detection, and provides the
#158 point filter and a recentrable mapping. No GUI or OS dependency.
"""

from pathlib import Path

import numpy as np

from experiments.head_pointer.pointer import OneEuroFilter2D
from experiments.head_pointer.signals import ray_signal
from experiments.head_pointer_tuning.protocol import BY_NAME

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = ROOT / ".venv/models/face_landmarker.task"
# MediaPipe Face Mesh points in the dlib 36-47 order used by the existing eye
# closure code: corner, upper outer, upper inner, corner, lower inner, lower outer.
EYE_INDICES = ((33, 160, 158, 133, 153, 144), (362, 385, 387, 263, 373, 380))
FILTER = BY_NAME["STEADY"]  # Issue #158 frozen-rule outcome
NOMINAL_PIXELS = 1500.0  # One Euro constants are in pixels; normalized points are scaled


def eye_opening(eyes) -> list[float] | None:
    """Per-eye opening ratio (mean lid gap / width), as in the MPIIFaceGaze engine."""
    points = np.asarray(eyes, float)
    if points.shape != (2, 6, 2) or not np.isfinite(points).all():
        return None
    widths = np.linalg.norm(points[:, 0] - points[:, 3], axis=1)
    gaps = np.linalg.norm(points[:, 1] - points[:, 5], axis=1) + np.linalg.norm(
        points[:, 2] - points[:, 4], axis=1
    )
    return (gaps / (2 * np.maximum(widths, 1e-8))).tolist()


class HeadLandmarks:
    """MediaPipe Face Landmarker (VIDEO mode) with the transformation matrix."""

    def __init__(self, model_path: Path = DEFAULT_MODEL) -> None:
        import cv2
        import mediapipe

        if not Path(model_path).is_file():
            raise RuntimeError(f"Face Landmarker modeli bulunamadı: {model_path}")
        self.cv2, self.mp = cv2, mediapipe
        vision = mediapipe.tasks.vision
        options = vision.FaceLandmarkerOptions(
            base_options=mediapipe.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_facial_transformation_matrixes=True,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)
        self.last_ms = -1
        self.provenance = dict(
            signal="RAY (Issue #156)",
            mediapipe=mediapipe.__version__,
            face_model=str(Path(model_path).name),
        )

    def observe(self, frame, captured_ns):
        rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        stamp = max(self.last_ms + 1, captured_ns // 1_000_000)
        self.last_ms = stamp
        result = self.detector.detect_for_video(
            self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb), stamp
        )
        if not result.face_landmarks:
            return None, None, "no_face"
        landmarks = result.face_landmarks[0]
        height, width = frame.shape[:2]
        eyes = [[[landmarks[i].x * width, landmarks[i].y * height] for i in e] for e in EYE_INDICES]
        matrices = result.facial_transformation_matrixes or []
        ray = ray_signal(matrices[0]) if len(matrices) else None
        if ray is None:
            return None, eyes, "invalid_head_pose"
        return [float(ray[0]), float(ray[1])], eyes, "valid"

    def close(self) -> None:
        if self.detector is not None:
            self.detector.close()
            self.detector = None


class RecentredMapping:
    """A fitted mapping plus an offset; ``recentre`` puts the last input on the centre."""

    def __init__(self, mapping) -> None:
        self.mapping = mapping
        self.offset = np.zeros(2)
        self.last = None

    @property
    def weights(self):
        return self.mapping.weights

    def fit(self, x, y):
        self.mapping.fit(x, y)
        self.offset = np.zeros(2)
        self.last = None
        return self

    def predict(self, x):
        mapped = np.asarray(self.mapping.predict(x), float)
        self.last = mapped
        return mapped + self.offset

    def recentre(self) -> bool:
        if self.weights is None or self.last is None:
            return False
        self.offset = np.array([0.5, 0.5]) - self.last
        return True


class HeadFilter:
    """The #158 One Euro filter with the StreamFilter interface (value, lag)."""

    def __init__(self) -> None:
        self.filter = OneEuroFilter2D(FILTER.min_cutoff, FILTER.beta)

    def reset(self) -> None:
        self.filter.reset()

    def update(self, value, timestamp_ns):
        if value is None or np.asarray(value).shape != (2,) or not np.isfinite(value).all():
            self.reset()
            return None, None
        scaled = (value[0] * NOMINAL_PIXELS, value[1] * NOMINAL_PIXELS)
        x, y = self.filter.update(timestamp_ns / 1e9, scaled)
        return [x / NOMINAL_PIXELS, y / NOMINAL_PIXELS], None
