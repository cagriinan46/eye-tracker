"""Experiment-only per-frame signals beside the unchanged production feature path.

The extractor reuses the production MediaPipe adapter's image conversion,
timestamps and landmark conversion, and only additionally requests blendshapes
and the facial transformation matrix from the same detector call. Only derived
numbers are kept: no landmarks, pixels or native objects.
"""

import time
from math import atan2, degrees, isfinite, sqrt

from experiments.vertical_collapse_diagnostics.capture import measure_once
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor

BLENDSHAPES = {
    "eyeLookUpLeft": "look_up_left",
    "eyeLookUpRight": "look_up_right",
    "eyeLookDownLeft": "look_down_left",
    "eyeLookDownRight": "look_down_right",
    "eyeBlinkLeft": "blink_left",
    "eyeBlinkRight": "blink_right",
}
SIGNAL_FIELDS = (*BLENDSHAPES.values(), "head_pitch_deg", "head_yaw_deg", "head_roll_deg")


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def blendshape_scores(result: object) -> dict[str, float | None]:
    scores = dict.fromkeys(BLENDSHAPES.values())
    faces = getattr(result, "face_blendshapes", None)
    if not faces:
        return scores
    for category in faces[0]:
        key = BLENDSHAPES.get(getattr(category, "category_name", None))
        if key is not None:
            scores[key] = _finite(getattr(category, "score", None))
    return scores


def head_pose_degrees(result: object) -> dict[str, float | None]:
    """Euler angles of the detector's facial transformation matrix (descriptive)."""
    pose = {"head_pitch_deg": None, "head_yaw_deg": None, "head_roll_deg": None}
    matrices = getattr(result, "facial_transformation_matrixes", None)
    if matrices is None or len(matrices) == 0:
        return pose
    matrix = matrices[0]
    try:
        r = [[_finite(matrix[row][column]) for column in range(3)] for row in range(3)]
    except (TypeError, IndexError):
        return pose
    if any(value is None for row in r for value in row):
        return pose
    pose["head_pitch_deg"] = degrees(atan2(r[2][1], r[2][2]))
    pose["head_yaw_deg"] = degrees(atan2(-r[2][0], sqrt(r[0][0] ** 2 + r[1][0] ** 2)))
    pose["head_roll_deg"] = degrees(atan2(r[1][0], r[0][0]))
    return pose


class _ResultObserver:
    """Return the detector result unchanged after a read-only numerical copy."""

    def __init__(self, native: object, observe) -> None:
        self.native, self.observe = native, observe

    def detect_for_video(self, image: object, timestamp_ms: int) -> object:
        result = self.native.detect_for_video(image, timestamp_ms)
        self.observe(result)
        return result

    def close(self) -> None:
        self.native.close()


class SignalExtractor(MediaPipeFaceLandmarkExtractor):
    """Production landmark conversion plus blendshape and head-pose side outputs."""

    def __init__(self, model_path) -> None:
        super().__init__(model_path)
        self._landmarker.close()
        options = self._mp.tasks.vision.FaceLandmarkerOptions(
            base_options=self._mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=self._mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
        )
        native = self._mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._landmarker = _ResultObserver(native, self._observe)
        self.last_signals: dict | None = None
        self.last_extract_ms: float | None = None

    def _observe(self, result: object) -> None:
        self.last_signals = {**blendshape_scores(result), **head_pose_degrees(result)}

    def extract(self, frame):
        self.last_signals = None
        started = time.perf_counter_ns()
        try:
            return super().extract(frame)
        finally:
            self.last_extract_ms = (time.perf_counter_ns() - started) / 1e6


def measure_signals(source, extractor, signals: SignalExtractor):
    """Production features via the Issue #44 path, then this frame's side signals."""
    signals.last_signals = None
    signals.last_extract_ms = None
    result, details = measure_once(source, extractor, None)
    details.update(dict.fromkeys(SIGNAL_FIELDS))
    details.update(signals.last_signals or {})
    details["extract_ms"] = signals.last_extract_ms
    return result, details
