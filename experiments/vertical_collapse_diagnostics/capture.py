"""Read-only numerical diagnostics around the existing Vision/Gaze path."""

from math import hypot

from eye_tracker.gaze.calibration import IndependentLinearMapping
from eye_tracker.gaze.estimator import (
    GazeEstimate,
    GazeUnavailable,
    UnavailableReason,
    estimate_gaze,
)
from eye_tracker.vision.contracts import FrameSource, LandmarkExtractor
from eye_tracker.vision.eye_features import (
    EyeFeatures,
    EyeGeometry,
    extract_binocular_features,
    extract_eye_features,
)
from eye_tracker.vision.eye_topology import eye_geometry_from_observation


def _eye_opening(geometry: EyeGeometry, width: int, height: int) -> float:
    """Diagnostic lid-point distance divided by corner distance in pixels."""
    lid = hypot(
        (geometry.lower_lid.x - geometry.upper_lid.x) * width,
        (geometry.lower_lid.y - geometry.upper_lid.y) * height,
    )
    corners = hypot(
        (geometry.corner_b.x - geometry.corner_a.x) * width,
        (geometry.corner_b.y - geometry.corner_a.y) * height,
    )
    return lid / corners


def measure_once(
    source: FrameSource,
    extractor: LandmarkExtractor,
    mapping: IndependentLinearMapping | None,
) -> tuple[EyeFeatures | GazeEstimate | GazeUnavailable, dict]:
    """Reuse production math while exposing only derived numerical diagnostics."""
    details = {
        "status": "unavailable_frame",
        "timestamp_ns": None,
        "horizontal": None,
        "vertical": None,
        "left_horizontal": None,
        "right_horizontal": None,
        "left_vertical": None,
        "right_vertical": None,
        "left_eye_opening": None,
        "right_eye_opening": None,
        "binocular_eye_opening": None,
        "head_center_y": None,
        "predicted_x": None,
        "predicted_y": None,
    }
    frame = source.read()
    if frame is None:
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES), details
    details["timestamp_ns"] = frame.timestamp_ns
    observation = extractor.extract(frame)
    try:
        geometry = eye_geometry_from_observation(observation)
    except ValueError:
        details["status"] = "unavailable_geometry"
        return GazeUnavailable(UnavailableReason.INVALID_FEATURES), details
    if geometry is None:
        details["status"] = "unavailable_no_face"
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES), details
    left, right = geometry
    left_features = extract_eye_features(left, frame.width, frame.height)
    right_features = extract_eye_features(right, frame.width, frame.height)
    features = extract_binocular_features(left, right, frame.width, frame.height)
    if left_features is None or right_features is None or features is None:
        details["status"] = "unavailable_geometry"
        return GazeUnavailable(UnavailableReason.INVALID_FEATURES), details
    details.update(
        status="usable",
        horizontal=features.horizontal,
        vertical=features.vertical,
        left_horizontal=left_features.horizontal,
        right_horizontal=right_features.horizontal,
        left_vertical=left_features.vertical,
        right_vertical=right_features.vertical,
        left_eye_opening=_eye_opening(left, frame.width, frame.height),
        right_eye_opening=_eye_opening(right, frame.width, frame.height),
        binocular_eye_opening=(
            _eye_opening(left, frame.width, frame.height)
            + _eye_opening(right, frame.width, frame.height)
        )
        / 2,
        head_center_y=(left.corner_a.y + left.corner_b.y + right.corner_a.y + right.corner_b.y) / 4,
    )
    if mapping is None:
        return features, details
    estimate = estimate_gaze(mapping, features.horizontal, features.vertical)
    if isinstance(estimate, GazeUnavailable):
        details["status"] = estimate.reason.value
        return estimate, details
    details["predicted_x"] = estimate.x
    details["predicted_y"] = estimate.y
    return estimate, details
