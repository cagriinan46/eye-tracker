"""Small serializable eye geometry and exact feature reconstruction offline."""

from math import atan2, hypot, isclose, isfinite
from statistics import fmean

from eye_tracker.vision.contracts import NormalizedPoint
from eye_tracker.vision.eye_features import EyeGeometry


def _xy(point: NormalizedPoint) -> list[float]:
    return [point.x, point.y]


def eye_record(eye: EyeGeometry) -> dict:
    """Keep only current feature's iris, corner, lid, and contour-bound inputs."""
    ring = [_xy(point) for point in eye.iris_ring]
    return {
        "iris_ring": ring,
        "iris_center": [fmean(p[0] for p in ring), fmean(p[1] for p in ring)],
        "corner_a": _xy(eye.corner_a),
        "corner_b": _xy(eye.corner_b),
        "upper_lid": _xy(eye.upper_lid),
        "lower_lid": _xy(eye.lower_lid),
        "contour_bounds": [
            min(p.x for p in eye.contour),
            max(p.x for p in eye.contour),
            min(p.y for p in eye.contour),
            max(p.y for p in eye.contour),
        ],
    }


def _point(record: dict, name: str) -> tuple[float, float]:
    value = record.get(name)
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(
            isinstance(x, bool) or not isinstance(x, (float, int)) or not isfinite(x) for x in value
        )
    ):
        raise ValueError(f"invalid {name} point")
    return float(value[0]), float(value[1])


def geometry_metrics(record: dict, width: int, height: int) -> dict[str, float]:
    """Reconstruct local-axis feature and expose distinct primitive movements.

    Point coordinates are image-normalized. Axis projections use pixel-scaled
    geometry, exactly as the production feature does, and are normalized by
    corner distance where dimensionless comparisons are useful.
    """
    if width <= 0 or height <= 0:
        raise ValueError("frame dimensions must be positive")
    ring = record.get("iris_ring")
    if not isinstance(ring, list) or len(ring) != 4:
        raise ValueError("four iris ring points are required")
    ring_points = [_point({"point": point}, "point") for point in ring]
    iris = _point(record, "iris_center")
    if any(not isclose(iris[i], fmean(p[i] for p in ring_points), abs_tol=1e-12) for i in (0, 1)):
        raise ValueError("iris center disagrees with four ring points")
    corner_a = _point(record, "corner_a")
    corner_b = _point(record, "corner_b")
    upper = _point(record, "upper_lid")
    lower = _point(record, "lower_lid")
    bounds = record.get("contour_bounds")
    if (
        not isinstance(bounds, list)
        or len(bounds) != 4
        or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
            for v in bounds
        )
    ):
        raise ValueError("four finite contour bounds are required")
    x_min, x_max, y_min, y_max = bounds
    ax, ay = (corner_a[0] * width, corner_a[1] * height)
    bx, by = (corner_b[0] * width, corner_b[1] * height)
    ux, uy = (upper[0] * width, upper[1] * height)
    lx, ly = (lower[0] * width, lower[1] * height)
    ix, iy = (iris[0] * width, iris[1] * height)
    axis_x, axis_y = bx - ax, by - ay
    eye_width = hypot(axis_x, axis_y)
    if eye_width <= 1e-6 or (x_max - x_min) * width <= 1e-6 or (y_max - y_min) * height <= 1e-6:
        raise ValueError("degenerate eye geometry")
    tangent_x, tangent_y = axis_x / eye_width, axis_y / eye_width
    normal_x, normal_y = -tangent_y, tangent_x
    lid_gap = (lx - ux) * normal_x + (ly - uy) * normal_y
    orientation_polarity = -1 if lid_gap < 0 else 1
    if lid_gap < 0:
        normal_x, normal_y, lid_gap = -normal_x, -normal_y, -lid_gap
    if lid_gap <= 1e-6 or hypot(ix - ux, iy - uy) + hypot(ix - lx, iy - ly) <= 1e-6:
        raise ValueError("degenerate lid geometry")
    mid_x, mid_y = (ax + bx) / 2, (ay + by) / 2
    lid_mid_x, lid_mid_y = (ux + lx) / 2, (uy + ly) / 2

    def projected(x: float, y: float) -> float:
        return ((x - mid_x) * normal_x + (y - mid_y) * normal_y) / eye_width

    return {
        "iris_x": iris[0],
        "iris_y": iris[1],
        "upper_x": upper[0],
        "upper_y": upper[1],
        "lower_x": lower[0],
        "lower_y": lower[1],
        "lid_mid_x": lid_mid_x / width,
        "lid_mid_y": lid_mid_y / height,
        "corner_a_x": corner_a[0],
        "corner_a_y": corner_a[1],
        "corner_b_x": corner_b[0],
        "corner_b_y": corner_b[1],
        "corner_mid_x": mid_x / width,
        "corner_mid_y": mid_y / height,
        "eye_width_px": eye_width,
        "axis_angle_rad": atan2(axis_y, axis_x),
        "normal_x": normal_x,
        "normal_y": normal_y,
        "orientation_polarity": orientation_polarity,
        "iris_local_parallel": ((ix - mid_x) * tangent_x + (iy - mid_y) * tangent_y) / eye_width,
        "iris_local_vertical": projected(ix, iy),
        "upper_local_vertical": projected(ux, uy),
        "lower_local_vertical": projected(lx, ly),
        "lid_mid_local_vertical": projected(lid_mid_x, lid_mid_y),
        "iris_vs_lid_mid_vertical": ((ix - lid_mid_x) * normal_x + (iy - lid_mid_y) * normal_y)
        / eye_width,
        "aperture": hypot(lx - ux, ly - uy) / eye_width,
        "lid_gap_projected_px": lid_gap,
        "horizontal": (iris[0] - x_min) / (x_max - x_min),
        "vertical": projected(ix, iy),
    }
