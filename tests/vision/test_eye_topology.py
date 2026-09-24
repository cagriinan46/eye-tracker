"""Phase 0 topology translation into existing vendor-neutral eye geometry."""

import pytest

from eye_tracker.vision.contracts import LandmarkObservation, NormalizedPoint
from eye_tracker.vision.eye_features import extract_binocular_features
from eye_tracker.vision.eye_topology import eye_geometry_from_observation

LEFT_CONTOUR = (249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466)
RIGHT_CONTOUR = (7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246)


def test_phase_0_topology_maps_both_eyes_without_swapping() -> None:
    landmarks = tuple(NormalizedPoint(index / 1000, index / 2000) for index in range(478))

    left, right = eye_geometry_from_observation(LandmarkObservation(123, landmarks))

    assert left.contour == tuple(landmarks[index] for index in LEFT_CONTOUR)
    assert left.iris_ring == tuple(landmarks[index] for index in (474, 475, 476, 477))
    assert (left.corner_a, left.corner_b) == (landmarks[263], landmarks[362])
    assert (left.upper_lid, left.lower_lid) == (landmarks[386], landmarks[374])
    assert right.contour == tuple(landmarks[index] for index in RIGHT_CONTOUR)
    assert right.iris_ring == tuple(landmarks[index] for index in (469, 470, 471, 472))
    assert (right.corner_a, right.corner_b) == (landmarks[33], landmarks[133])
    assert (right.upper_lid, right.lower_lid) == (landmarks[159], landmarks[145])


def test_missing_face_stays_unavailable() -> None:
    assert eye_geometry_from_observation(LandmarkObservation(123, None)) is None


def test_incomplete_landmark_tuple_fails_explicitly() -> None:
    landmarks = (NormalizedPoint(0.5, 0.5),) * 477

    with pytest.raises(ValueError, match="478"):
        eye_geometry_from_observation(LandmarkObservation(123, landmarks))


def test_missing_required_point_fails_explicitly() -> None:
    landmarks = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    landmarks[474] = None  # type: ignore[assignment]

    with pytest.raises(ValueError, match="474"):
        eye_geometry_from_observation(LandmarkObservation(123, tuple(landmarks)))


def test_translated_geometry_is_usable_by_existing_feature_extractor() -> None:
    points = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    for contour, center_x, corners, upper, lower, iris in (
        (LEFT_CONTOUR, 0.3, (263, 362), 386, 374, (474, 475, 476, 477)),
        (RIGHT_CONTOUR, 0.7, (33, 133), 159, 145, (469, 470, 471, 472)),
    ):
        for index in contour:
            points[index] = NormalizedPoint(center_x, 0.3)
        points[corners[0]] = NormalizedPoint(center_x - 0.1, 0.3)
        points[corners[1]] = NormalizedPoint(center_x + 0.1, 0.3)
        points[upper] = NormalizedPoint(center_x, 0.28)
        points[lower] = NormalizedPoint(center_x, 0.32)
        for index in iris:
            points[index] = NormalizedPoint(center_x, 0.3)

    geometry = eye_geometry_from_observation(LandmarkObservation(123, tuple(points)))

    assert geometry is not None
    features = extract_binocular_features(*geometry, 1000, 500)
    assert features is not None
    assert features.horizontal == pytest.approx(0.5)
    assert features.vertical == pytest.approx(0.0)
