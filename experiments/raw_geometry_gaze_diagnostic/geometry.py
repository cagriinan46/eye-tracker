"""Copy selected numerical primitives from the SAME production detector result.

No detector options, project contracts, or production feature behavior change.
The private native call is wrapped only by this experiment-owned subclass.
"""

from math import atan2, hypot, isfinite
from statistics import fmean

from eye_tracker.vision.contracts import NormalizedPoint
from eye_tracker.vision.eye_features import (
    EyeGeometry,
    extract_binocular_features,
    extract_eye_features,
)
from eye_tracker.vision.face_tracker import MediaPipeFaceLandmarkExtractor

# Exact production eye_topology.py contours/rings/references; no guessed roles.
EYES = {
    "left": {
        "contour": (249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466),
        "iris_ring": (474, 475, 476, 477),
        "detector_iris_center": 473,
        "corner_a": 263,
        "corner_b": 362,
        "upper_lid": 386,
        "lower_lid": 374,
    },
    "right": {
        "contour": (7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246),
        "iris_ring": (469, 470, 471, 472),
        "detector_iris_center": 468,
        "corner_a": 33,
        "corner_b": 133,
        "upper_lid": 159,
        "lower_lid": 145,
    },
}
# Existing six NOSE + four bilateral FACE_OVAL anchors, plus superior/inferior
# FACE_OVAL 10/152 for offline orientation support. Exclude eyes/iris/brows/lips.
FACE_ANCHOR_INDICES = (6, 197, 195, 5, 4, 1, 127, 234, 454, 356, 10, 152)
REQUIRED_INDICES = tuple(
    sorted(
        set(FACE_ANCHOR_INDICES).union(*(set(e["contour"] + e["iris_ring"]) for e in EYES.values()))
    )
)
SELECTED_INDICES = tuple(
    sorted(set(REQUIRED_INDICES).union(e["detector_iris_center"] for e in EYES.values()))
)


def _number(value):
    try:
        return (
            float(value)
            if value is not None and not isinstance(value, bool) and isfinite(float(value))
            else None
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _copy_point(point):
    x, y = _number(getattr(point, "x", None)), _number(getattr(point, "y", None))
    if x is None or y is None:
        return None
    return {"x": x, "y": y, "z": _number(getattr(point, "z", None))}


def _center(points):
    if any(p is None for p in points):
        return None
    return {
        axis: fmean(p[axis] for p in points) if all(p[axis] is not None for p in points) else None
        for axis in ("x", "y", "z")
    }


def _eye_geometry(landmarks, eye):
    def point(index):
        p = landmarks[str(index)]
        if p is None:
            raise ValueError("missing production eye point")
        return NormalizedPoint(p["x"], p["y"])

    return EyeGeometry(
        contour=tuple(point(i) for i in eye["contour"]),
        iris_ring=tuple(point(i) for i in eye["iris_ring"]),
        corner_a=point(eye["corner_a"]),
        corner_b=point(eye["corner_b"]),
        upper_lid=point(eye["upper_lid"]),
        lower_lid=point(eye["lower_lid"]),
    )


def reconstruct_r0(record):
    """Exact baseline through production formulas, from saved primitives only."""
    width, height = record["camera_resolution"]
    return extract_binocular_features(
        *(_eye_geometry(record["landmarks"], EYES[side]) for side in ("left", "right")),
        width,
        height,
    )


def eye_records(landmarks, width, height):
    result = {}
    for side, eye in EYES.items():

        def get(name):
            return landmarks[str(eye[name])]

        a, b, upper, lower = (
            get(name) for name in ("corner_a", "corner_b", "upper_lid", "lower_lid")
        )
        iris = _center([landmarks[str(i)] for i in eye["iris_ring"]])
        midpoint = _center([a, b])
        values = {
            "iris_center": iris,
            "detector_iris_center": get("detector_iris_center"),
            "outer_corner": a,
            "inner_corner": b,
            "corner_midpoint": midpoint,
            "upper_lid": upper,
            "lower_lid": lower,
            "lid_midpoint": _center([upper, lower]),
            "corner_span_px": None,
            "corner_angle_rad": None,
            "lid_distance_px": None,
            "eye_opening": None,
            "local_vertical_basis": None,
            "production_horizontal": None,
            "production_vertical": None,
        }
        if a is not None and b is not None:
            dx, dy = (b["x"] - a["x"]) * width, (b["y"] - a["y"]) * height
            span = hypot(dx, dy)
            values.update(corner_span_px=span, corner_angle_rad=atan2(dy, dx))
            if upper is not None and lower is not None and span > 1e-6:
                nx, ny = -dy / span, dx / span
                ux, uy = (lower["x"] - upper["x"]) * width, (lower["y"] - upper["y"]) * height
                if ux * nx + uy * ny < 0:
                    nx, ny = -nx, -ny
                values.update(
                    lid_distance_px=hypot(ux, uy),
                    eye_opening=hypot(ux, uy) / span,
                    local_vertical_basis=[nx, ny],
                )
        try:
            feature = extract_eye_features(_eye_geometry(landmarks, eye), width, height)
            if feature is not None:
                values.update(
                    production_horizontal=feature.horizontal, production_vertical=feature.vertical
                )
        except ValueError:
            pass  # Preserve partial geometry; never change production availability.
        result[side] = values
    return result


def _matrix(result):
    matrices = getattr(result, "facial_transformation_matrixes", None)
    if matrices is None or len(matrices) == 0:
        return None, "not_exposed"
    value = matrices[0]
    if hasattr(value, "tolist"):
        value = value.tolist()
    try:
        if len(value) != 4 or any(len(row) != 4 for row in value):
            return None, "malformed"
        output = [[_number(v) for v in row] for row in value]
        if any(v is None for row in output for v in row):
            return None, "malformed"
        return output, "available"
    except TypeError:
        return None, "malformed"


def interocular_distance(eyes, width, height):
    centers = [eyes[side]["corner_midpoint"] for side in ("left", "right")]
    return (
        hypot(
            (centers[0]["x"] - centers[1]["x"]) * width,
            (centers[0]["y"] - centers[1]["y"]) * height,
        )
        if all(centers)
        else None
    )


def geometry_record(result, width, height, frame_timestamp_ns, detector_timestamp_ms):
    """Detached numerical whitelist; never retain native objects or pixels."""
    if not result.face_landmarks or not result.face_landmarks[0]:
        return None
    if width <= 0 or height <= 0:
        raise ValueError("positive frame dimensions required")
    points = result.face_landmarks[0]
    landmarks = {
        str(i): _copy_point(points[i]) if i < len(points) else None for i in SELECTED_INDICES
    }
    eyes = eye_records(landmarks, width, height)
    matrix, status = _matrix(result)
    return {
        "schema_version": 1,
        "frame_timestamp_ns": frame_timestamp_ns,
        "detector_timestamp_ms": detector_timestamp_ms,
        "camera_resolution": [width, height],
        "landmarks": landmarks,
        "face_anchors": {str(i): landmarks[str(i)] for i in FACE_ANCHOR_INDICES},
        "eyes": eyes,
        "interocular_distance_px": interocular_distance(eyes, width, height),
        "missing_required_indices": [i for i in REQUIRED_INDICES if landmarks[str(i)] is None],
        "missing_optional_indices": [
            i for i in SELECTED_INDICES if i not in REQUIRED_INDICES and landmarks[str(i)] is None
        ],
        "missing_z_indices": [
            i
            for i in SELECTED_INDICES
            if landmarks[str(i)] is None or landmarks[str(i)]["z"] is None
        ],
        "facial_transformation_matrix": matrix,
        "pose_transform_status": status,
    }


class _ResultObserver:
    """Return the original detector result unchanged after a read-only copy."""

    def __init__(self, native, observe):
        self.native, self.observe = native, observe

    def detect_for_video(self, image, timestamp_ms):
        result = self.native.detect_for_video(image, timestamp_ms)
        self.observe(result, timestamp_ms)
        return result

    def close(self):
        self.native.close()


class GeometryExtractor(MediaPipeFaceLandmarkExtractor):
    """Same options, image conversion, native call, timestamps and XY conversion.

    Isolated dependency on the adapter's private native member is covered by a
    same-result equivalence test. No public production accessor is necessary.
    """

    def __init__(self, model_path):
        super().__init__(model_path)
        self.last_geometry = None
        self.geometry_error = None
        self._geometry_frame = None
        self._landmarker = _ResultObserver(self._landmarker, self._observe)

    def _observe(self, result, timestamp_ms):
        frame = self._geometry_frame
        try:
            self.last_geometry = geometry_record(
                result, frame.width, frame.height, frame.timestamp_ns, timestamp_ms
            )
        except (ValueError, TypeError, AttributeError, OverflowError) as error:
            self.geometry_error = str(error)
            # Logging failure must not modify production's conversion/result.

    def extract(self, frame):
        self.last_geometry = None
        self.geometry_error = None
        self._geometry_frame = frame
        try:
            return super().extract(frame)
        finally:
            self._geometry_frame = None  # Never retain camera payloads in the sidecar.
