"""Session-local calibration: RBF-kernel SVR and the historical linear baseline.

Calibration pairs numerical gaze features with known target positions observed in
one session. Fitted coefficients are never persisted or shared between sessions:
Phase 0 measured between-session feature offsets (Experiments 004 and 006), so a
mapping is valid only for the session whose samples produced it.

Coordinates are normalized to the calibration area: ``x`` increases to the right,
``y`` increases downward, and targets lie in ``[0, 1]``. Predictions are not
clipped, so extrapolation error stays visible instead of being hidden at the edge.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from statistics import linear_regression, median
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from sklearn.pipeline import Pipeline

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


def aggregate_calibration_observations(
    observations: Iterable[Sequence[float]], target_x: float, target_y: float
) -> CalibrationSample:
    """Reduce repeated ``(horizontal, vertical)`` observations at one target to one sample.

    Each axis is summarized by its own median, as in Experiment 006's per-target
    summaries, so the result is independent of input order and need not equal any
    single observed pair. No quality gate, smoothing, or minimum observation count
    is applied; Experiment 006's five-frame rule was experimental protocol.

    Raises ``ValueError`` when there are no observations, an observation is not a
    ``(horizontal, vertical)`` pair of finite numbers, or the target is invalid.
    """
    pairs = tuple(observations)
    if not pairs:
        raise ValueError("at least one feature observation is required")
    for pair in pairs:
        if not (
            isinstance(pair, Sequence) and not isinstance(pair, (str, bytes)) and len(pair) == 2
        ):
            raise ValueError("feature observations must be (horizontal, vertical) pairs")
        if not all(_is_finite_number(value) for value in pair):
            raise ValueError("feature observations must be finite numbers")
    return CalibrationSample(
        horizontal_feature=median(pair[0] for pair in pairs),
        vertical_feature=median(pair[1] for pair in pairs),
        target_x=target_x,
        target_y=target_y,
    )


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


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


@dataclass(frozen=True, slots=True)
class SVRCalibrationSample(CalibrationSample):
    """Per-target medians; pose angles are in degrees in pitch/yaw/roll order."""

    pitch: float
    yaw: float
    roll: float

    def __post_init__(self) -> None:
        CalibrationSample.__post_init__(self)
        if not all(_is_finite_number(v) for v in (self.pitch, self.yaw, self.roll)):
            raise ValueError("head pose angles must be finite numbers")


@dataclass(frozen=True, slots=True)
class SVRMapping:
    """Two fitted RBF-kernel SVR regressors with pixel and normalized outputs, requiring five inputs.

    Each model consumes horizontal, vertical, pitch, yaw, roll (degrees).
    The live app supplies all five inputs; the legacy two-input pipeline stays separate.
    Scalers are fitted only on calibration data and never updated in predict. No clipping or temporal smoothing occurs.
    Screen dimensions describe the calibrated drawable area, not camera resolution.
    """

    svr_x: Pipeline
    svr_y: Pipeline
    screen_width: int
    screen_height: int

    def predict_pixels(
        self,
        horizontal_feature: float,
        vertical_feature: float,
        pitch: float,
        yaw: float,
        roll: float,
    ) -> tuple[float, float]:
        if not all(
            _is_finite_number(v) for v in (horizontal_feature, vertical_feature, pitch, yaw, roll)
        ):
            raise ValueError("gaze features must be finite numbers")
        features = [[horizontal_feature, vertical_feature, pitch, yaw, roll]]
        point = (float(self.svr_x.predict(features)[0]), float(self.svr_y.predict(features)[0]))
        if not all(isfinite(value) for value in point):
            raise ValueError("SVR prediction must be finite")
        return point

    def predict(
        self,
        horizontal_feature: float,
        vertical_feature: float,
        pitch: float,
        yaw: float,
        roll: float,
    ) -> tuple[float, float]:
        """Return normalized coordinates for the five-input live SVR application."""
        x, y = self.predict_pixels(horizontal_feature, vertical_feature, pitch, yaw, roll)
        return x / self.screen_width, y / self.screen_height


def fit_svr(
    samples: Iterable[SVRCalibrationSample],
    *,
    screen_width: int,
    screen_height: int,
) -> SVRMapping:
    """Fit two RBF-kernel SVRs to per-target medians and actual drawable-area pixel targets.

    Discard blink/invalid frames, then median all five features per target.
    This low-level fitter requires >=3 distinct feature vectors with variation in
    both eye features and both target axes; collection owns the protocol's target-count gate.
    Only input features are standardized; targets remain in drawable-area pixels.
    RBF kernel, gamma=0.1, C=1000 and epsilon=1.0 pixels are experimental settings, not
    validated accuracy thresholds. Fixed pixel-unit settings are resolution dependent.

    The historical fit_independent_linear remains available for frozen experiments.
    """
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVR

    if any(type(size) is not int or size <= 0 for size in (screen_width, screen_height)):
        raise ValueError("screen dimensions must be positive integers")
    samples = tuple(samples)
    if not all(isinstance(sample, SVRCalibrationSample) for sample in samples):
        raise TypeError("calibration samples must be SVRCalibrationSample instances")
    if len(samples) < MIN_CALIBRATION_SAMPLES:
        raise ValueError("at least three calibration samples are required")
    features = [(s.horizontal_feature, s.vertical_feature, s.pitch, s.yaw, s.roll) for s in samples]
    if len(set(features)) < MIN_CALIBRATION_SAMPLES:
        raise ValueError("at least three distinct calibration feature vectors are required")
    for field in ("horizontal_feature", "vertical_feature", "target_x", "target_y"):
        if len({getattr(sample, field) for sample in samples}) < 2:
            raise ValueError(f"{field} does not vary across calibration samples")

    def fit_axis(targets):
        regressor = SVR(kernel="rbf", C=1000.0, epsilon=1.0, gamma=0.1)
        # Alternatives for a NEW calibration; no accuracy/stability guarantee:
        # regressor = SVR(kernel="linear", C=1000.0, epsilon=1.0)
        # regressor = SVR(kernel="poly", degree=2, C=1000.0, epsilon=1.0,
        #                 gamma=0.1, coef0=1.0)
        model = make_pipeline(StandardScaler(), regressor)
        model.fit(features, targets)
        return model

    return SVRMapping(
        svr_x=fit_axis([sample.target_x * screen_width for sample in samples]),
        svr_y=fit_axis([sample.target_y * screen_height for sample in samples]),
        screen_width=screen_width,
        screen_height=screen_height,
    )
