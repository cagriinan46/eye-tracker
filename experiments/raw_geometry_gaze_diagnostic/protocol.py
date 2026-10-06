"""Fixed-window collection and frozen representation/holdout identities."""

from experiments.fixed_window_gaze_diagnostic.protocol import (
    CALIBRATION_TARGETS,
    CUE_SECONDS,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    TARGET_SECONDS,
    TRANSITION_SECONDS,
    Trial,
    schedule,
    screen_content,
)
from experiments.fixed_window_gaze_diagnostic.protocol import (
    configuration as base_configuration,
)

from .geometry import EYES, FACE_ANCHOR_INDICES, REQUIRED_INDICES, SELECTED_INDICES

PROTOCOL_NAME = "raw_geometry_gaze_diagnostic"
PROTOCOL_VERSION = 1
REPRESENTATIONS = ("R0", "R1", "R2")
SESSION_ROLES = {"geometry-1": "development", "geometry-2": "holdout"}
__all__ = [
    "CALIBRATION_TARGETS",
    "CUE_SECONDS",
    "SAMPLE_SECONDS",
    "SETTLE_SECONDS",
    "TARGET_SECONDS",
    "TRANSITION_SECONDS",
    "Trial",
    "schedule",
    "screen_content",
]


def configuration():
    return {
        **base_configuration(),
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "geometry_schema_version": 1,
        "geometry_coordinates": "mediapipe_normalized_xyz_optional_z",
        "selected_landmark_indices": list(SELECTED_INDICES),
        "required_landmark_indices": list(REQUIRED_INDICES),
        "face_anchor_indices": list(FACE_ANCHOR_INDICES),
        "eye_landmark_indices": {
            side: {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in eye.items()
            }
            for side, eye in EYES.items()
        },
        "detector_options_policy": "production_defaults_unchanged",
        "representation_families": list(REPRESENTATIONS),
        "session_roles": SESSION_ROLES.copy(),
    }
