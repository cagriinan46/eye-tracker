"""Regression checks for the Phase 0 eye-feature geometry."""

from dataclasses import FrozenInstanceError
from math import hypot

import pytest

from eye_tracker.vision.contracts import NormalizedPoint
from eye_tracker.vision.eye_features import (
    EyeFeatures,
    EyeGeometry,
    extract_binocular_features,
    extract_eye_features,
)


def point(x: float, y: float) -> NormalizedPoint:
    return NormalizedPoint(x, y)


def eye(iris_x: float = 0.30, iris_y: float = 0.30) -> EyeGeometry:
    return EyeGeometry(
        contour=(point(0.20, 0.28), point(0.40, 0.28), point(0.20, 0.32), point(0.40, 0.32)),
        iris_ring=(
            point(iris_x - 0.01, iris_y),
            point(iris_x + 0.01, iris_y),
            point(iris_x, iris_y - 0.01),
            point(iris_x, iris_y + 0.01),
        ),
        corner_a=point(0.20, 0.30),
        corner_b=point(0.40, 0.30),
        upper_lid=point(0.30, 0.28),
        lower_lid=point(0.30, 0.32),
    )


def transformed(geometry: EyeGeometry, scale: float, dx: float, dy: float) -> EyeGeometry:
    def move(p: NormalizedPoint) -> NormalizedPoint:
        return point(scale * p.x + dx, scale * p.y + dy)

    return EyeGeometry(
        contour=tuple(map(move, geometry.contour)),
        iris_ring=tuple(map(move, geometry.iris_ring)),
        corner_a=move(geometry.corner_a),
        corner_b=move(geometry.corner_b),
        upper_lid=move(geometry.upper_lid),
        lower_lid=move(geometry.lower_lid),
    )


def assert_features_close(actual: EyeFeatures | None, expected: EyeFeatures) -> None:
    assert actual is not None
    assert actual.horizontal == pytest.approx(expected.horizontal)
    assert actual.vertical == pytest.approx(expected.vertical)


def test_horizontal_iris_movement_uses_contour_width_without_clipping() -> None:
    center = extract_eye_features(eye(), 1000, 500)
    image_right = extract_eye_features(eye(iris_x=0.32), 1000, 500)

    assert center is not None and image_right is not None
    assert center.horizontal == pytest.approx(0.5)
    assert image_right.horizontal == pytest.approx(0.6)
    assert image_right.vertical == pytest.approx(center.vertical)


def test_vertical_iris_movement_uses_pixel_scaled_local_axis_and_lid_orientation() -> None:
    center = extract_eye_features(eye(), 1000, 500)
    image_down = extract_eye_features(eye(iris_y=0.32), 1000, 500)

    assert center is not None and image_down is not None
    assert center.vertical == pytest.approx(0.0)
    assert image_down.vertical == pytest.approx(0.05)
    assert image_down.horizontal == pytest.approx(center.horizontal)


def test_translation_and_uniform_scale_preserve_normalized_features() -> None:
    geometry = eye(iris_x=0.32, iris_y=0.32)
    baseline = extract_eye_features(geometry, 1000, 500)

    assert baseline is not None
    assert_features_close(
        extract_eye_features(transformed(geometry, 1, 0.11, -0.07), 1000, 500), baseline
    )
    assert_features_close(
        extract_eye_features(transformed(geometry, 0.5, 0.1, 0.2), 1000, 500), baseline
    )
    assert_features_close(extract_eye_features(geometry, 2000, 1000), baseline)


def test_binocular_features_average_the_two_valid_eyes() -> None:
    result = extract_binocular_features(eye(0.32, 0.32), eye(0.28, 0.28), 1000, 500)

    assert result is not None
    assert result.horizontal == pytest.approx(0.5)
    assert result.vertical == pytest.approx(0.0)
    with pytest.raises(FrozenInstanceError):
        result.horizontal = 0.7  # type: ignore[misc]


def test_slanted_eye_preserves_phase_0_perpendicular_sign_and_width_normalization() -> None:
    # Pixel geometry: A=(200,150), B=(400,170), midpoint=(300,160).
    # A 10-pixel displacement along the oriented normal gives vertical=10/width.
    width = hypot(200, 20)
    nx, ny = -20 / width, 200 / width
    iris_x, iris_y = 300 + 10 * nx, 160 + 10 * ny
    geometry = EyeGeometry(
        contour=(point(0.2, 0.3), point(0.4, 0.34), point(0.2, 0.38)),
        iris_ring=(point(iris_x / 1000, iris_y / 500),) * 4,
        corner_a=point(0.2, 0.3),
        corner_b=point(0.4, 0.34),
        upper_lid=point((300 - 5 * nx) / 1000, (160 - 5 * ny) / 500),
        lower_lid=point((300 + 5 * nx) / 1000, (160 + 5 * ny) / 500),
    )

    result = extract_eye_features(geometry, 1000, 500)

    assert result is not None
    assert result.horizontal == pytest.approx((iris_x - 200) / 200)
    assert result.vertical == pytest.approx(10 / width)


def test_missing_or_degenerate_geometry_has_no_feature_result() -> None:
    valid = eye()
    assert extract_binocular_features(None, valid, 1000, 500) is None
    assert extract_binocular_features(valid, None, 1000, 500) is None
    assert (
        extract_eye_features(
            EyeGeometry(
                (),
                valid.iris_ring,
                valid.corner_a,
                valid.corner_b,
                valid.upper_lid,
                valid.lower_lid,
            ),
            1000,
            500,
        )
        is None
    )
    assert (
        extract_eye_features(
            EyeGeometry(
                valid.contour, (), valid.corner_a, valid.corner_b, valid.upper_lid, valid.lower_lid
            ),
            1000,
            500,
        )
        is None
    )
    assert (
        extract_eye_features(
            EyeGeometry(
                (point(0.2, 0.28), point(0.2, 0.32)),
                valid.iris_ring,
                valid.corner_a,
                valid.corner_b,
                valid.upper_lid,
                valid.lower_lid,
            ),
            1000,
            500,
        )
        is None
    )
    assert (
        extract_eye_features(
            EyeGeometry(
                valid.contour,
                valid.iris_ring,
                valid.corner_a,
                valid.corner_a,
                valid.upper_lid,
                valid.lower_lid,
            ),
            1000,
            500,
        )
        is None
    )
    assert (
        extract_eye_features(
            EyeGeometry(
                valid.contour,
                valid.iris_ring,
                valid.corner_a,
                valid.corner_b,
                valid.upper_lid,
                valid.upper_lid,
            ),
            1000,
            500,
        )
        is None
    )


@pytest.mark.parametrize("dimensions", [(0, 500), (1000, 0), (-1, 500)])
def test_invalid_frame_dimensions_are_rejected(dimensions: tuple[int, int]) -> None:
    with pytest.raises(ValueError, match="dimensions"):
        extract_eye_features(eye(), *dimensions)
