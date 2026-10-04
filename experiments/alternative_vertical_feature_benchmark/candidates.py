"""Small, calibration-derived vertical feature candidates; no target labels used."""

from dataclasses import dataclass
from math import hypot
from statistics import median

BASELINE = "production"
FACE_IRIS_Y = "face_iris_y"
STABLE_SPAN = "stable_span"
STABLE_FRAME = "stable_frame"
CANDIDATES = (BASELINE, FACE_IRIS_Y, STABLE_SPAN, STABLE_FRAME)
EYES = ("left", "right")


@dataclass(frozen=True)
class EyeReference:
    """One eye's calibration-only median span and oriented unit normal."""

    span_px: float
    normal_x: float
    normal_y: float


def _pixel(point: list[float], width: int, height: int) -> tuple[float, float]:
    return point[0] * width, point[1] * height


def eye_axis(geometry: dict, width: int, height: int) -> tuple[float, float, float]:
    """The production corner normal, oriented by the upper-to-lower lid vector."""
    ax, ay = _pixel(geometry["corner_a"], width, height)
    bx, by = _pixel(geometry["corner_b"], width, height)
    ux, uy = _pixel(geometry["upper_lid"], width, height)
    lx, ly = _pixel(geometry["lower_lid"], width, height)
    dx, dy = bx - ax, by - ay
    span = hypot(dx, dy)
    if span <= 1e-6:
        raise ValueError("degenerate corner span")
    nx, ny = -dy / span, dx / span
    if (lx - ux) * nx + (ly - uy) * ny < 0:
        nx, ny = -nx, -ny
    if (lx - ux) * nx + (ly - uy) * ny <= 1e-6:
        raise ValueError("degenerate lid projection")
    return span, nx, ny


def calibration_references(rows: list[dict], width: int, height: int) -> dict[str, EyeReference]:
    """Construct per-eye references solely from usable ordinary calibration rows."""
    calibration = [
        row for row in rows if row["phase"] == "calibration" and row["status"] == "usable"
    ]
    if not calibration:
        raise ValueError("usable calibration geometry is required")
    result = {}
    for eye in EYES:
        axes = [eye_axis(row["geometry"][eye], width, height) for row in calibration]
        span, nx, ny = (median(axis[i] for axis in axes) for i in range(3))
        norm = hypot(nx, ny)
        if norm <= 1e-6:
            raise ValueError("degenerate calibration orientation")
        result[eye] = EyeReference(span, nx / norm, ny / norm)
    return result


def feature(
    row: dict, candidate: str, eye: str, reference: EyeReference | None, width: int, height: int
) -> float:
    """Evaluate one eye with only current geometry and calibration state."""
    if candidate not in CANDIDATES or eye not in EYES:
        raise ValueError("unsupported candidate or eye")
    if candidate == BASELINE:
        return row[f"{eye}_vertical"]
    if candidate == FACE_IRIS_Y:
        face = row.get("face_normalized_geometry")
        if face is None:
            raise ValueError("face iris candidate needs saved non-eye face anchors/alignment")
        return face[eye]["iris_center"][1] * height
    if reference is None:
        raise ValueError("calibration eye reference is required")
    geometry = row["geometry"][eye]
    _, nx, ny = eye_axis(geometry, width, height)
    if candidate == STABLE_FRAME:
        nx, ny = reference.normal_x, reference.normal_y
    iris_x, iris_y = _pixel(geometry["iris_center"], width, height)
    ax, ay = _pixel(geometry["corner_a"], width, height)
    bx, by = _pixel(geometry["corner_b"], width, height)
    return ((iris_x - (ax + bx) / 2) * nx + (iris_y - (ay + by) / 2) * ny) / reference.span_px


def binocular(
    row: dict, candidate: str, references: dict[str, EyeReference], width: int, height: int
) -> float:
    """Average simultaneous monocular values, matching the production policy."""
    return sum(feature(row, candidate, eye, references.get(eye), width, height) for eye in EYES) / 2
