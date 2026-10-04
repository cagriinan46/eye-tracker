"""Two fixed lid-referenced candidates and the unmodified production baseline."""

from experiments.alternative_vertical_feature_benchmark.candidates import (
    BASELINE,
    EYES,
    EyeReference,
    calibration_references,
)
from experiments.alternative_vertical_feature_benchmark.candidates import (
    feature as production_feature,
)

LID_MIDPOINT_FIXED_SCALE = "lid_midpoint_fixed_scale"
LID_FRACTION = "lid_fraction"
CANDIDATES = (BASELINE, LID_MIDPOINT_FIXED_SCALE, LID_FRACTION)
APERTURE_EPSILON_PX = 1e-6


class InvalidAperture(ValueError):
    """A lid fraction cannot be formed from a near-zero/reversed projected gap."""


def _pixel(point: list[float], width: int, height: int) -> tuple[float, float]:
    return point[0] * width, point[1] * height


def feature(
    row: dict,
    candidate: str,
    eye: str,
    reference: EyeReference,
    width: int,
    height: int,
) -> float:
    """Evaluate one eye from current geometry and its calibration-only axis/scale."""
    if candidate not in CANDIDATES or eye not in EYES:
        raise ValueError("unsupported candidate or eye")
    if candidate == BASELINE:
        return production_feature(row, BASELINE, eye, reference, width, height)
    geometry = row["geometry"][eye]
    ix, iy = _pixel(geometry["iris_center"], width, height)
    ux, uy = _pixel(geometry["upper_lid"], width, height)
    lx, ly = _pixel(geometry["lower_lid"], width, height)
    nx, ny = reference.normal_x, reference.normal_y
    iris_from_mid = (ix - (ux + lx) / 2) * nx + (iy - (uy + ly) / 2) * ny
    if candidate == LID_MIDPOINT_FIXED_SCALE:
        return iris_from_mid / reference.span_px
    gap = (lx - ux) * nx + (ly - uy) * ny
    if gap <= APERTURE_EPSILON_PX:
        raise InvalidAperture("invalid projected lid aperture")
    return iris_from_mid / gap


def binocular(
    row: dict, candidate: str, references: dict[str, EyeReference], width: int, height: int
) -> float:
    """Match production's simultaneous two-eye arithmetic mean."""
    return sum(feature(row, candidate, eye, references[eye], width, height) for eye in EYES) / 2


__all__ = (
    "APERTURE_EPSILON_PX",
    "BASELINE",
    "CANDIDATES",
    "EYES",
    "InvalidAperture",
    "LID_FRACTION",
    "LID_MIDPOINT_FIXED_SCALE",
    "binocular",
    "calibration_references",
    "feature",
)
