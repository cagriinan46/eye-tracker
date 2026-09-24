"""Translate the Phase 0 Face Landmarker topology inside the Vision boundary.

Indices match Experiments 003/004. The returned geometry and its consumers
contain only project-level points, never MediaPipe objects or index meanings.
"""

from eye_tracker.vision.contracts import LandmarkObservation, NormalizedPoint
from eye_tracker.vision.eye_features import EyeGeometry

_LEFT_CONTOUR = (249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466)
_RIGHT_CONTOUR = (7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246)
_LEFT_IRIS = (474, 475, 476, 477)
_RIGHT_IRIS = (469, 470, 471, 472)
_REQUIRED_COUNT = max(*_LEFT_CONTOUR, *_RIGHT_CONTOUR, *_LEFT_IRIS, *_RIGHT_IRIS) + 1


def eye_geometry_from_observation(
    observation: LandmarkObservation,
) -> tuple[EyeGeometry, EyeGeometry] | None:
    """Return MediaPipe-left/right named geometry or ``None`` for no face.

    A present but incomplete observation is invalid, not an unavailable face.
    Only referenced landmarks are required to be valid project-level points.
    """
    landmarks = observation.landmarks
    if landmarks is None:
        return None
    if len(landmarks) < _REQUIRED_COUNT:
        raise ValueError(f"eye geometry requires {_REQUIRED_COUNT} landmarks; got {len(landmarks)}")

    def point(index: int) -> NormalizedPoint:
        value = landmarks[index]
        if not isinstance(value, NormalizedPoint):
            raise ValueError(f"required landmark {index} is missing or invalid")
        return value

    left = EyeGeometry(
        contour=tuple(point(index) for index in _LEFT_CONTOUR),
        iris_ring=tuple(point(index) for index in _LEFT_IRIS),
        corner_a=point(263),
        corner_b=point(362),
        upper_lid=point(386),
        lower_lid=point(374),
    )
    right = EyeGeometry(
        contour=tuple(point(index) for index in _RIGHT_CONTOUR),
        iris_ring=tuple(point(index) for index in _RIGHT_IRIS),
        corner_a=point(33),
        corner_b=point(133),
        upper_lid=point(159),
        lower_lid=point(145),
    )
    return left, right
