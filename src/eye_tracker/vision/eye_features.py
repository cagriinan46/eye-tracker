"""Vendor-neutral eye geometry to directional numerical features.

This preserves the horizontal contour and vertical local-axis formulas from
Phase 0 experiments 003/004. Feature values are not screen coordinates.
"""

from dataclasses import dataclass
from math import dist, hypot
from statistics import fmean

from eye_tracker.vision.contracts import NormalizedPoint

_MIN_PIXEL_SPAN = 1e-6  # Phase 0 degenerate-geometry guard, not a gaze threshold.


@dataclass(frozen=True, slots=True)
class EyeGeometry:
    """Named image-normalized geometry supplied by a future landmark adapter.

    ``iris_ring`` contains the points used to calculate the iris center;
    ``contour`` contains the eye outline. Corner ordering is arbitrary: eyelid
    direction orients the local vertical axis consistently toward image-down.
    """

    contour: tuple[NormalizedPoint, ...]
    iris_ring: tuple[NormalizedPoint, ...]
    corner_a: NormalizedPoint
    corner_b: NormalizedPoint
    upper_lid: NormalizedPoint
    lower_lid: NormalizedPoint


@dataclass(frozen=True, slots=True)
class EyeFeatures:
    """Uncalibrated horizontal and local-axis vertical directional features."""

    horizontal: float
    vertical: float


def _pixel(point: NormalizedPoint, width: int, height: int) -> tuple[float, float]:
    return point.x * width, point.y * height


def _dot(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def extract_eye_features(
    geometry: EyeGeometry, frame_width: int, frame_height: int
) -> EyeFeatures | None:
    """Measure one eye, returning ``None`` for unavailable/degenerate geometry.

    Use pixel-scaled coordinates for the local axis so image aspect ratio does
    not alter its direction. No clipping, calibration, or temporal filtering.
    """
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")
    if not geometry.contour or not geometry.iris_ring:
        return None

    contour = [_pixel(point, frame_width, frame_height) for point in geometry.contour]
    iris_ring = [_pixel(point, frame_width, frame_height) for point in geometry.iris_ring]
    iris = (fmean(point[0] for point in iris_ring), fmean(point[1] for point in iris_ring))
    corner_a = _pixel(geometry.corner_a, frame_width, frame_height)
    corner_b = _pixel(geometry.corner_b, frame_width, frame_height)
    upper = _pixel(geometry.upper_lid, frame_width, frame_height)
    lower = _pixel(geometry.lower_lid, frame_width, frame_height)

    x_min = min(point[0] for point in contour)
    x_max = max(point[0] for point in contour)
    y_min = min(point[1] for point in contour)
    y_max = max(point[1] for point in contour)
    axis = (corner_b[0] - corner_a[0], corner_b[1] - corner_a[1])
    eye_width = hypot(*axis)
    if (
        eye_width <= _MIN_PIXEL_SPAN
        or x_max - x_min <= _MIN_PIXEL_SPAN
        or y_max - y_min <= _MIN_PIXEL_SPAN
    ):
        return None

    normal = (-axis[1] / eye_width, axis[0] / eye_width)
    lid_gap = _dot((lower[0] - upper[0], lower[1] - upper[1]), normal)
    if lid_gap < 0:
        normal = (-normal[0], -normal[1])
        lid_gap = -lid_gap
    if lid_gap <= _MIN_PIXEL_SPAN or dist(iris, upper) + dist(iris, lower) <= _MIN_PIXEL_SPAN:
        return None

    midpoint = ((corner_a[0] + corner_b[0]) / 2, (corner_a[1] + corner_b[1]) / 2)
    displacement = (iris[0] - midpoint[0], iris[1] - midpoint[1])
    return EyeFeatures(
        horizontal=(iris[0] - x_min) / (x_max - x_min),
        vertical=_dot(displacement, normal) / eye_width,
    )


def extract_binocular_features(
    left: EyeGeometry | None,
    right: EyeGeometry | None,
    frame_width: int,
    frame_height: int,
) -> EyeFeatures | None:
    """Average two eyes as in Phase 0; return ``None`` if either is unavailable."""
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")
    if left is None or right is None:
        return None
    left_features = extract_eye_features(left, frame_width, frame_height)
    right_features = extract_eye_features(right, frame_width, frame_height)
    if left_features is None or right_features is None:
        return None
    return EyeFeatures(
        horizontal=(left_features.horizontal + right_features.horizontal) / 2,
        vertical=(left_features.vertical + right_features.vertical) / 2,
    )
