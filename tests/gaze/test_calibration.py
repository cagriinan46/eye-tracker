"""Deterministic checks for session-local gaze calibration with synthetic features."""

from dataclasses import FrozenInstanceError
from math import inf, nan

import pytest

from eye_tracker.gaze.calibration import (
    MIN_CALIBRATION_SAMPLES,
    CalibrationSample,
    GazeMapping,
    IndependentLinearMapping,
    fit_independent_linear,
)

GRID = (0.1, 0.2, 0.3)


def grid_samples(x_of, y_of, horizontal=GRID, vertical=GRID) -> list[CalibrationSample]:
    return [CalibrationSample(h, v, x_of(h), y_of(v)) for h in horizontal for v in vertical]


def test_calibration_recovers_known_axis_relationships() -> None:
    mapping = fit_independent_linear(grid_samples(lambda h: 2 * h + 0.1, lambda v: -2 * v + 0.8))

    assert mapping.x_slope == pytest.approx(2.0)
    assert mapping.x_intercept == pytest.approx(0.1)
    assert mapping.y_slope == pytest.approx(-2.0)
    assert mapping.y_intercept == pytest.approx(0.8)


def test_unseen_feature_pair_is_predicted_from_calibration_only() -> None:
    mapping = fit_independent_linear(grid_samples(lambda h: 2 * h + 0.1, lambda v: -2 * v + 0.8))

    assert mapping.predict(0.15, 0.25) == pytest.approx((0.4, 0.3))


def test_noisy_calibration_uses_ordinary_least_squares() -> None:
    samples = [
        CalibrationSample(0.1, 0.1, 0.2, 0.3),
        CalibrationSample(0.2, 0.2, 0.5, 0.4),
        CalibrationSample(0.3, 0.3, 0.6, 0.8),
    ]
    mapping = fit_independent_linear(samples)

    # Hand-computed least-squares lines: x = 2h + 1/30, y = 2.5v + 0.
    assert (mapping.x_slope, mapping.x_intercept) == pytest.approx((2.0, 1 / 30))
    assert mapping.y_slope == pytest.approx(2.5)
    assert mapping.y_intercept == pytest.approx(0.0, abs=1e-12)


def test_feature_sign_is_learned_rather_than_assumed() -> None:
    mapping = fit_independent_linear(grid_samples(lambda h: 1.0 - 2 * h, lambda v: 0.2 + 2 * v))

    left, _ = mapping.predict(0.3, 0.2)
    right, _ = mapping.predict(0.1, 0.2)
    assert left < right


def test_each_axis_depends_only_on_its_own_feature() -> None:
    mapping = fit_independent_linear(grid_samples(lambda h: 2 * h + 0.1, lambda v: -2 * v + 0.8))

    x_first, y_first = mapping.predict(0.2, 0.1)
    x_moved_vertical, y_moved_vertical = mapping.predict(0.2, 0.3)
    x_moved_horizontal, y_moved_horizontal = mapping.predict(0.3, 0.1)

    assert x_moved_vertical == x_first
    assert y_moved_vertical != y_first
    assert y_moved_horizontal == y_first
    assert x_moved_horizontal != x_first


def test_sessions_are_calibrated_independently() -> None:
    first = fit_independent_linear(grid_samples(lambda h: 2 * h + 0.1, lambda v: -2 * v + 0.8))
    first_before = IndependentLinearMapping(
        first.x_slope, first.x_intercept, first.y_slope, first.y_intercept
    )
    # A synthetic between-session feature offset: same targets, shifted features.
    second = fit_independent_linear(
        grid_samples(
            lambda h: 2 * (h - 0.05) + 0.1,
            lambda v: -2 * (v - 0.02) + 0.8,
            horizontal=tuple(h + 0.05 for h in GRID),
            vertical=tuple(v + 0.02 for v in GRID),
        )
    )

    assert first == first_before
    assert first.predict(0.2, 0.2) == pytest.approx((0.5, 0.4))
    assert second.predict(0.25, 0.22) == pytest.approx((0.5, 0.4))
    assert second.predict(0.2, 0.2) != pytest.approx(first.predict(0.2, 0.2))


def test_predictions_are_continuous_and_unclipped_without_direction_thresholds() -> None:
    mapping = fit_independent_linear(grid_samples(lambda h: 2 * h + 0.1, lambda v: -2 * v + 0.8))
    features = [0.1 + step * 0.001 for step in range(201)]
    xs = [mapping.predict(h, 0.2)[0] for h in features]

    steps = [after - before for before, after in zip(xs, xs[1:])]
    assert all(step == pytest.approx(0.002) for step in steps)
    assert len(set(xs)) == len(xs)
    assert mapping.predict(-0.2, 0.5)[0] == pytest.approx(-0.3)
    assert mapping.predict(0.8, -0.2)[1] == pytest.approx(1.2)


def test_fitted_mapping_is_immutable_and_satisfies_the_mapping_boundary() -> None:
    mapping: GazeMapping = fit_independent_linear(grid_samples(lambda h: h, lambda v: v))

    with pytest.raises(FrozenInstanceError):
        mapping.x_slope = 0.0  # type: ignore[attr-defined]


def test_generator_input_is_accepted() -> None:
    samples = (sample for sample in grid_samples(lambda h: h, lambda v: v))

    assert fit_independent_linear(samples).predict(0.2, 0.2) == pytest.approx((0.2, 0.2))


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_calibration_sample_rejects_non_finite_values(value: float) -> None:
    for fields in (
        (value, 0.1, 0.5, 0.5),
        (0.1, value, 0.5, 0.5),
        (0.1, 0.1, value, 0.5),
        (0.1, 0.1, 0.5, value),
    ):
        with pytest.raises(ValueError, match="finite"):
            CalibrationSample(*fields)


@pytest.mark.parametrize(("target_x", "target_y"), [(-0.01, 0.5), (1.01, 0.5), (0.5, -0.01)])
def test_calibration_sample_rejects_targets_outside_normalized_area(
    target_x: float, target_y: float
) -> None:
    with pytest.raises(ValueError, match="normalized"):
        CalibrationSample(0.1, 0.1, target_x, target_y)


def test_too_few_samples_are_rejected() -> None:
    samples = [CalibrationSample(0.1, 0.1, 0.2, 0.2), CalibrationSample(0.3, 0.3, 0.8, 0.8)]

    assert len(samples) < MIN_CALIBRATION_SAMPLES
    with pytest.raises(ValueError, match="at least"):
        fit_independent_linear(samples)


def test_constant_horizontal_feature_is_rejected() -> None:
    samples = [CalibrationSample(0.2, v, x, v) for v, x in zip(GRID, (0.2, 0.5, 0.8))]

    with pytest.raises(ValueError, match="horizontal feature does not vary"):
        fit_independent_linear(samples)


def test_constant_vertical_feature_is_rejected() -> None:
    samples = [CalibrationSample(h, 0.2, h, y) for h, y in zip(GRID, (0.2, 0.5, 0.8))]

    with pytest.raises(ValueError, match="vertical feature does not vary"):
        fit_independent_linear(samples)


def test_constant_target_coordinate_is_rejected() -> None:
    samples = [CalibrationSample(h, h, 0.5, y) for h, y in zip(GRID, (0.2, 0.5, 0.8))]

    with pytest.raises(ValueError, match="target x does not vary"):
        fit_independent_linear(samples)


def test_identical_repeated_samples_are_rejected() -> None:
    with pytest.raises(ValueError, match="does not vary"):
        fit_independent_linear([CalibrationSample(0.2, 0.1, 0.2, 0.2)] * 9)


def test_non_sample_inputs_are_rejected() -> None:
    with pytest.raises(TypeError):
        fit_independent_linear([(0.1, 0.1, 0.2, 0.2)] * 3)  # type: ignore[list-item]


@pytest.mark.parametrize(("horizontal", "vertical"), [(nan, 0.2), (0.2, inf), (-inf, nan)])
def test_prediction_rejects_non_finite_features(horizontal: float, vertical: float) -> None:
    mapping = fit_independent_linear(grid_samples(lambda h: h, lambda v: v))

    with pytest.raises(ValueError, match="finite"):
        mapping.predict(horizontal, vertical)


def test_mapping_rejects_non_finite_coefficients() -> None:
    with pytest.raises(ValueError, match="finite"):
        IndependentLinearMapping(nan, 0.0, 1.0, 0.0)
