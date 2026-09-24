"""Deterministic checks for reducing repeated observations to one calibration sample."""

from itertools import permutations
from math import inf, nan

import pytest

from eye_tracker.gaze.calibration import (
    CalibrationSample,
    aggregate_calibration_observations,
    fit_independent_linear,
)


def test_odd_count_uses_the_middle_value_of_each_axis() -> None:
    sample = aggregate_calibration_observations(
        [(0.30, -0.02), (0.10, -0.05), (0.20, -0.04)], target_x=0.2, target_y=0.8
    )

    assert sample == CalibrationSample(0.20, -0.04, 0.2, 0.8)


def test_even_count_averages_the_two_middle_values_of_each_axis() -> None:
    sample = aggregate_calibration_observations(
        [(0.1, 0.4), (0.4, 0.1), (0.2, 0.3), (0.3, 0.2)], target_x=0.5, target_y=0.5
    )

    assert sample.horizontal_feature == pytest.approx(0.25)
    assert sample.vertical_feature == pytest.approx(0.25)


def test_axes_are_summarized_independently_not_as_an_observed_pair() -> None:
    observations = [(0.1, 0.9), (0.5, 0.1), (0.9, 0.5)]

    sample = aggregate_calibration_observations(observations, target_x=0.5, target_y=0.5)

    assert (sample.horizontal_feature, sample.vertical_feature) == (0.5, 0.5)
    assert (0.5, 0.5) not in observations


def test_input_order_does_not_change_the_result() -> None:
    observations = [(0.31, -0.02), (0.12, -0.05), (0.27, -0.04), (0.18, -0.01)]

    results = {
        aggregate_calibration_observations(order, target_x=0.8, target_y=0.2)
        for order in permutations(observations)
    }

    assert len(results) == 1


def test_target_coordinates_are_preserved() -> None:
    sample = aggregate_calibration_observations([(0.2, 0.1)], target_x=0.35, target_y=0.65)

    assert (sample.target_x, sample.target_y) == (0.35, 0.65)


def test_single_observation_is_accepted_without_a_minimum_frame_count() -> None:
    sample = aggregate_calibration_observations([(0.2, -0.03)], target_x=0.0, target_y=1.0)

    assert sample == CalibrationSample(0.2, -0.03, 0.0, 1.0)


def test_generator_and_list_observations_are_accepted() -> None:
    generated = aggregate_calibration_observations(
        ((0.1 * i, 0.2 * i) for i in range(1, 4)), target_x=0.5, target_y=0.5
    )
    listed = aggregate_calibration_observations([[0.1, 0.2], [0.2, 0.4], [0.3, 0.6]], 0.5, 0.5)

    assert generated.horizontal_feature == pytest.approx(listed.horizontal_feature)
    assert generated.vertical_feature == pytest.approx(listed.vertical_feature)


def test_aggregated_samples_feed_the_existing_fitter() -> None:
    offsets = (-0.01, 0.0, 0.02)
    samples = [
        aggregate_calibration_observations(
            [((x - 0.1) / 2 + d, (0.8 - y) / 2 - d) for d in offsets], target_x=x, target_y=y
        )
        for x in (0.2, 0.5, 0.8)
        for y in (0.2, 0.5, 0.8)
    ]

    mapping = fit_independent_linear(samples)

    assert mapping.predict(0.2, 0.15) == pytest.approx((0.5, 0.5))


def test_empty_observations_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        aggregate_calibration_observations([], target_x=0.5, target_y=0.5)


@pytest.mark.parametrize("value", [nan, inf, -inf, True, "0.2", None])
def test_non_finite_or_non_numeric_values_are_rejected(value: object) -> None:
    for observation in ((value, 0.1), (0.1, value)):
        with pytest.raises(ValueError, match="finite numbers"):
            aggregate_calibration_observations(
                [(0.2, 0.1), observation], target_x=0.5, target_y=0.5
            )


@pytest.mark.parametrize("observation", [(0.2,), (0.2, 0.1, 0.0), "ab", 0.2, None])
def test_malformed_observations_are_rejected(observation: object) -> None:
    with pytest.raises(ValueError, match="pairs"):
        aggregate_calibration_observations([observation], target_x=0.5, target_y=0.5)  # type: ignore[list-item]


@pytest.mark.parametrize(("target_x", "target_y"), [(1.1, 0.5), (0.5, -0.1), (nan, 0.5)])
def test_invalid_targets_are_rejected(target_x: float, target_y: float) -> None:
    with pytest.raises(ValueError):
        aggregate_calibration_observations([(0.2, 0.1)], target_x=target_x, target_y=target_y)
