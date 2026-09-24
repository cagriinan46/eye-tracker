"""Turn numerical gaze features into a normalized estimate or an explicit unavailable state.

The estimator only applies an already-fitted, session-local ``GazeMapping``; it
does not fit, smooth, filter, or threshold anything. An estimate is a normalized
``(x, y)`` in the calibration area (x right, y down). It is deliberately not
clipped, so extrapolation stays visible, and it makes no production-accuracy claim.
"""

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from eye_tracker.gaze.calibration import GazeMapping


class UnavailableReason(Enum):
    """Why no gaze estimate could be produced for one set of features."""

    CALIBRATION_UNAVAILABLE = "calibration_unavailable"
    MISSING_FEATURES = "missing_features"
    INVALID_FEATURES = "invalid_features"
    MAPPING_FAILED = "mapping_failed"
    INVALID_PREDICTION = "invalid_prediction"


@dataclass(frozen=True, slots=True)
class GazeEstimate:
    """Unclipped normalized gaze coordinates from one session's mapping."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not (_is_finite_number(self.x) and _is_finite_number(self.y)):
            raise ValueError("gaze estimate coordinates must be finite numbers")


@dataclass(frozen=True, slots=True)
class GazeUnavailable:
    """Explicit absence of an estimate; it carries no coordinates."""

    reason: UnavailableReason


def estimate_gaze(
    mapping: GazeMapping | None,
    horizontal_feature: float | None,
    vertical_feature: float | None,
) -> GazeEstimate | GazeUnavailable:
    """Apply ``mapping`` to one feature pair.

    Returns ``GazeUnavailable`` when there is no mapping, a feature is ``None``
    or not a finite number, ``mapping.predict`` raises ``ValueError`` or
    ``ArithmeticError`` (its documented failure modes), or the prediction is not
    two finite numbers. Other exceptions are programming errors and propagate.
    """
    if mapping is None:
        return GazeUnavailable(UnavailableReason.CALIBRATION_UNAVAILABLE)
    if horizontal_feature is None or vertical_feature is None:
        return GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    if not (_is_finite_number(horizontal_feature) and _is_finite_number(vertical_feature)):
        return GazeUnavailable(UnavailableReason.INVALID_FEATURES)
    try:
        prediction = mapping.predict(horizontal_feature, vertical_feature)
    except (ValueError, ArithmeticError):
        return GazeUnavailable(UnavailableReason.MAPPING_FAILED)
    if not (
        isinstance(prediction, tuple)
        and len(prediction) == 2
        and all(_is_finite_number(value) for value in prediction)
    ):
        return GazeUnavailable(UnavailableReason.INVALID_PREDICTION)
    return GazeEstimate(*prediction)


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
