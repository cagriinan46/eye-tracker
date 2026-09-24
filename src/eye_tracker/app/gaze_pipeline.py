"""One-step orchestration of the existing Vision and Gaze stages."""

from eye_tracker.gaze.calibration import GazeMapping
from eye_tracker.gaze.estimator import (
    GazeEstimate,
    GazeUnavailable,
    UnavailableReason,
    estimate_gaze,
)
from eye_tracker.vision.contracts import FrameSource, LandmarkExtractor
from eye_tracker.vision.eye_features import extract_binocular_features
from eye_tracker.vision.eye_topology import eye_geometry_from_observation


def process_gaze_frame(
    source: FrameSource, extractor: LandmarkExtractor, mapping: GazeMapping | None
) -> GazeEstimate | GazeUnavailable:
    """Process one frame from an open source; the caller manages resource lifecycles."""
    frame = source.read()
    if frame is None:
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    observation = extractor.extract(frame)
    try:
        geometry = eye_geometry_from_observation(observation)
    except ValueError:
        return GazeUnavailable(UnavailableReason.INVALID_FEATURES)
    if geometry is None:
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    left, right = geometry
    features = extract_binocular_features(left, right, frame.width, frame.height)
    if features is None:
        return GazeUnavailable(UnavailableReason.INVALID_FEATURES)
    return estimate_gaze(mapping, features.horizontal, features.vertical)
