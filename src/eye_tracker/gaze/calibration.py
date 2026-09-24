"""Session-local gaze calibration with a small, replaceable mapping baseline.

Calibration pairs numerical gaze features with known target positions observed in
one session. Fitted coefficients are never persisted or shared between sessions:
Phase 0 measured between-session feature offsets (Experiments 004 and 006), so a
mapping is valid only for the session whose samples produced it.

Coordinates are normalized to the calibration area: ``x`` increases to the right,
``y`` increases downward, and targets lie in ``[0, 1]``. Predictions are not
clipped, so extrapolation error stays visible instead of being hidden at the edge.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from statistics import linear_regression
from typing import Protocol

# Lower bound carried over from Experiment 006's fit; it is not a chosen
# calibration layout or point count, which remain undecided.
MIN_CALIBRATION_SAMPLES = 3


@dataclass(frozen=True, slots=True)
class CalibrationSample:
    """Numerical features observed while the user looked at a known target.

    Feature values are opaque numbers from the upstream feature extractor. Their
    sign and scale are learned by calibration rather than assumed here.
    """

    horizontal_feature: float
    vertical_feature: float
    target_x: float
    target_y: float

    def __post_init__(self) -> None:
        values = (self.horizontal_feature, self.vertical_feature, self.target_x, self.target_y)
        if not all(isfinite(value) for value in values):
            raise ValueError("calibration sample values must be finite")
        if not (0 <= self.target_x <= 1 and 0 <= self.target_y <= 1):
            raise ValueError("calibration targets must lie within the normalized [0, 1] area")


class GazeMapping(Protocol):
    """A fitted, session-local mapping from gaze features to normalized coordinates."""

    def predict(self, horizontal_feature: float, vertical_feature: float) -> tuple[float, float]:
        """Return the unclipped normalized ``(x, y)`` estimate for one feature pair."""
        ...


@dataclass(frozen=True, slots=True)
class IndependentLinearMapping:
    """Experiment 006's independent-linear mapping, kept as a baseline only.

    ``x = x_slope * horizontal + x_intercept`` and
    ``y = y_slope * vertical + y_intercept``. Each axis uses only its own feature.
    Phase 0 did not select a production mapping; this is not one.
    """

    x_slope: float
    x_intercept: float
    y_slope: float
    y_intercept: float

    def __post_init__(self) -> None:
        coefficients = (self.x_slope, self.x_intercept, self.y_slope, self.y_intercept)
        if not all(isfinite(value) for value in coefficients):
            raise ValueError("mapping coefficients must be finite")

    def predict(self, horizontal_feature: float, vertical_feature: float) -> tuple[float, float]:
        if not (isfinite(horizontal_feature) and isfinite(vertical_feature)):
            raise ValueError("gaze features must be finite")
        return (
            self.x_slope * horizontal_feature + self.x_intercept,
            self.y_slope * vertical_feature + self.y_intercept,
        )


def fit_independent_linear(samples: Iterable[CalibrationSample]) -> IndependentLinearMapping:
    """Fit the baseline by ordinary least squares on one session's calibration samples.

    Raises ``ValueError`` when fewer than ``MIN_CALIBRATION_SAMPLES`` samples are
    given, when a feature or target coordinate does not vary across samples, or
    when the fitted coefficients are not finite. Raises ``TypeError`` for inputs
    that are not ``CalibrationSample`` instances.
    """
    samples = tuple(samples)
    if not all(isinstance(sample, CalibrationSample) for sample in samples):
        raise TypeError("calibration samples must be CalibrationSample instances")
    if len(samples) < MIN_CALIBRATION_SAMPLES:
        raise ValueError(
            f"calibration needs at least {MIN_CALIBRATION_SAMPLES} samples; got {len(samples)}"
        )
    x_slope, x_intercept = _fit_axis(
        [sample.horizontal_feature for sample in samples],
        [sample.target_x for sample in samples],
        "horizontal feature",
        "target x",
    )
    y_slope, y_intercept = _fit_axis(
        [sample.vertical_feature for sample in samples],
        [sample.target_y for sample in samples],
        "vertical feature",
        "target y",
    )
    return IndependentLinearMapping(x_slope, x_intercept, y_slope, y_intercept)


def _fit_axis(
    features: Sequence[float], targets: Sequence[float], feature_name: str, target_name: str
) -> tuple[float, float]:
    if len(set(features)) < 2:
        raise ValueError(f"{feature_name} does not vary across calibration samples")
    if len(set(targets)) < 2:
        raise ValueError(f"{target_name} does not vary across calibration samples")
    slope, intercept = linear_regression(features, targets)
    if not (isfinite(slope) and isfinite(intercept)):
        raise ValueError(f"{feature_name} mapping is numerically degenerate")
    return slope, intercept
