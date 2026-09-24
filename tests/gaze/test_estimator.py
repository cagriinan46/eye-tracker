"""Deterministic checks for the gaze estimate and unavailable-state runtime."""

from dataclasses import FrozenInstanceError, fields
from math import inf, nan

import pytest

from eye_tracker.gaze.calibration import (
    CalibrationSample,
    GazeMapping,
    IndependentLinearMapping,
    fit_independent_linear,
)
from eye_tracker.gaze.estimator import (
    GazeEstimate,
    GazeUnavailable,
    UnavailableReason,
    estimate_gaze,
)

GRID = (0.1, 0.2, 0.3)


class RecordingMapping:
    """A stand-in ``GazeMapping`` that records calls and returns a fixed value."""

    def __init__(self, result: object = (0.25, 0.75), error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[float, float]] = []

    def predict(self, horizontal_feature: float, vertical_feature: float) -> tuple[float, float]:
        self.calls.append((horizontal_feature, vertical_feature))
        if self.error is not None:
            raise self.error
        return self.result  # type: ignore[return-value]


def fitted_mapping() -> IndependentLinearMapping:
    return fit_independent_linear(
        CalibrationSample(h, v, 2 * h + 0.1, -2 * v + 0.8) for h in GRID for v in GRID
    )


def test_valid_features_produce_expected_estimate_from_fitted_mapping() -> None:
    result = estimate_gaze(fitted_mapping(), 0.15, 0.25)

    assert isinstance(result, GazeEstimate)
    assert (result.x, result.y) == pytest.approx((0.4, 0.3))


def test_runtime_delegates_to_the_existing_mapping_boundary() -> None:
    mapping = RecordingMapping(result=(0.25, 0.75))
    boundary: GazeMapping = mapping

    result = estimate_gaze(boundary, 0.4, -0.03)

    assert mapping.calls == [(0.4, -0.03)]
    assert result == GazeEstimate(0.25, 0.75)


def test_extrapolated_predictions_are_not_clipped() -> None:
    result = estimate_gaze(fitted_mapping(), -0.2, 0.8)

    assert isinstance(result, GazeEstimate)
    assert (result.x, result.y) == pytest.approx((-0.3, -0.8))


def test_missing_mapping_is_explicitly_unavailable() -> None:
    assert estimate_gaze(None, 0.2, 0.2) == GazeUnavailable(
        UnavailableReason.CALIBRATION_UNAVAILABLE
    )


@pytest.mark.parametrize(("horizontal", "vertical"), [(None, 0.2), (0.2, None), (None, None)])
def test_missing_features_are_unavailable_without_calling_mapping(
    horizontal: float | None, vertical: float | None
) -> None:
    mapping = RecordingMapping()

    result = estimate_gaze(mapping, horizontal, vertical)

    assert result == GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    assert mapping.calls == []


@pytest.mark.parametrize(
    ("horizontal", "vertical"), [(nan, 0.2), (0.2, inf), (-inf, 0.2), (True, 0.2), ("0.2", 0.2)]
)
def test_invalid_features_are_unavailable_without_calling_mapping(
    horizontal: object, vertical: object
) -> None:
    mapping = RecordingMapping()

    result = estimate_gaze(mapping, horizontal, vertical)  # type: ignore[arg-type]

    assert result == GazeUnavailable(UnavailableReason.INVALID_FEATURES)
    assert mapping.calls == []


@pytest.mark.parametrize("error", [ValueError("bad features"), OverflowError("too large")])
def test_mapping_failure_is_explicitly_unavailable(error: Exception) -> None:
    result = estimate_gaze(RecordingMapping(error=error), 0.2, 0.2)

    assert result == GazeUnavailable(UnavailableReason.MAPPING_FAILED)


def test_unexpected_mapping_errors_are_not_hidden() -> None:
    with pytest.raises(RuntimeError):
        estimate_gaze(RecordingMapping(error=RuntimeError("bug")), 0.2, 0.2)


@pytest.mark.parametrize(
    "prediction",
    [(nan, 0.5), (0.5, inf), (0.5,), (0.5, 0.5, 0.5), [0.5, 0.5], ("0.5", 0.5), None],
)
def test_invalid_prediction_is_explicitly_unavailable(prediction: object) -> None:
    result = estimate_gaze(RecordingMapping(result=prediction), 0.2, 0.2)

    assert result == GazeUnavailable(UnavailableReason.INVALID_PREDICTION)


def test_unavailable_result_carries_no_coordinates() -> None:
    result = estimate_gaze(RecordingMapping(), None, 0.2)

    assert [field.name for field in fields(result)] == ["reason"]
    assert not hasattr(result, "x")
    assert not hasattr(result, "y")


@pytest.mark.parametrize(("x", "y"), [(nan, 0.5), (0.5, inf), (True, 0.5)])
def test_gaze_estimate_rejects_non_finite_coordinates(x: object, y: object) -> None:
    with pytest.raises(ValueError, match="finite"):
        GazeEstimate(x, y)  # type: ignore[arg-type]


def test_gaze_estimate_is_immutable() -> None:
    estimate = GazeEstimate(1.2, -0.1)

    with pytest.raises(FrozenInstanceError):
        estimate.x = 0.5  # type: ignore[misc]
