"""Per-frame head-frame numbers for the 3D eye-sphere feature (Issue #92).

Port of the head frame in Jason Orlosky's MIT-licensed prototype
(JEOresearch/EyeTracker, ``Webcam3DTracker/MonitorTracking.py``): PCA axes of
24 nose landmarks in (x·w, y·h, z·w) pixels, made right-handed, with axis signs
stabilized against the first frame. Only derived numbers are kept: the
rotation, the nose scale and each iris centre in scale-normalized head-local
coordinates; no landmark arrays or images.
"""

from math import isfinite

import numpy as np

from experiments.vertical_signal_comparison.capture import SignalExtractor

# Nose-region landmark indices used by the prototype for a stable head frame.
NOSE_INDICES = (
    4,
    45,
    275,
    220,
    440,
    1,
    5,
    51,
    281,
    44,
    274,
    241,
    461,
    125,
    354,
    218,
    438,
    195,
    167,
    393,
    165,
    391,
    3,
    248,
)
LEFT_IRIS, RIGHT_IRIS = 468, 473
ROTATION_FIELDS = tuple(f"head_r{row}{column}" for row in range(3) for column in range(3))
SPHERE_FIELDS = (
    *ROTATION_FIELDS,
    "nose_scale_px",
    *(f"{eye}_iris_local_{axis}" for eye in ("left", "right") for axis in "xyz"),
)


def nose_frame(points: np.ndarray, reference: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    """Centre and right-handed PCA rotation (columns = axes), signs aligned to reference."""
    center = points.mean(axis=0)
    eigenvalues, eigenvectors = np.linalg.eigh(np.cov((points - center).T))
    rotation = eigenvectors[:, np.argsort(-eigenvalues)]
    if np.linalg.det(rotation) < 0:
        rotation[:, 2] *= -1
    if reference is not None:
        for axis in range(3):
            if np.dot(rotation[:, axis], reference[:, axis]) < 0:
                rotation[:, axis] *= -1
    return center, rotation


def nose_scale(points: np.ndarray) -> float:
    """Mean pairwise distance, the prototype's head-size estimate."""
    differences = points[:, None, :] - points[None, :, :]
    distances = np.linalg.norm(differences, axis=-1)
    count = len(points)
    return float(distances.sum() / (count * (count - 1)))


def sphere_numbers(landmarks, width: int, height: int, reference) -> tuple[dict, np.ndarray] | None:
    """Head-frame numbers for one face, or None when landmarks are missing or invalid."""
    try:

        def pixel(index: int) -> np.ndarray:
            point = landmarks[index]
            return np.array([point.x * width, point.y * height, point.z * width], dtype=float)

        points = np.array([pixel(index) for index in NOSE_INDICES])
        irises = {"left": pixel(LEFT_IRIS), "right": pixel(RIGHT_IRIS)}
    except (IndexError, TypeError, AttributeError):
        return None
    if not np.all(np.isfinite(points)) or not all(np.all(np.isfinite(v)) for v in irises.values()):
        return None
    center, rotation = nose_frame(points, reference)
    scale = nose_scale(points)
    if not isfinite(scale) or scale <= 0:
        return None
    numbers = {name: float(rotation[i // 3, i % 3]) for i, name in enumerate(ROTATION_FIELDS)}
    numbers["nose_scale_px"] = scale
    for eye, iris in irises.items():
        local = rotation.T @ (iris - center) / scale
        for axis, value in zip("xyz", local):
            numbers[f"{eye}_iris_local_{axis}"] = float(value)
    return numbers, rotation


class SphereSignalExtractor(SignalExtractor):
    """Issue #77 side outputs plus the eye-sphere head-frame numbers from the same call."""

    def __init__(self, model_path) -> None:
        super().__init__(model_path)
        self._reference: np.ndarray | None = None
        self._frame_size: tuple[int, int] | None = None

    def extract(self, frame):
        self._frame_size = (frame.width, frame.height)
        return super().extract(frame)

    def _observe(self, result: object) -> None:
        super()._observe(result)
        self.last_signals.update(dict.fromkeys(SPHERE_FIELDS))
        faces = getattr(result, "face_landmarks", None)
        if not faces or self._frame_size is None:
            return
        computed = sphere_numbers(faces[0], *self._frame_size, self._reference)
        if computed is None:
            return
        numbers, rotation = computed
        if self._reference is None:
            self._reference = rotation.copy()
        self.last_signals.update(numbers)
