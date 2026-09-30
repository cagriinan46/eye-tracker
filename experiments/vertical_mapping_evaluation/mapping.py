"""Experiment-local monotonic row-anchor alternative; not a production mapping."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from statistics import median

from eye_tracker.gaze.calibration import CalibrationSample, IndependentLinearMapping


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


@dataclass(frozen=True, slots=True)
class PiecewiseVerticalMapping:
    """Three (vertical feature, normalized y) anchors ordered top to bottom.

    Use each adjacent linear segment for interpolation. Outside the outer
    anchors, extend the nearest segment; never clamp predictions.
    """

    anchors: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]

    def __post_init__(self) -> None:
        if len(self.anchors) != 3 or any(
            not isinstance(pair, tuple) or len(pair) != 2 or not all(map(_finite, pair))
            for pair in self.anchors
        ):
            raise ValueError("exactly three finite (feature, y) anchors are required")
        (top_feature, top_y), (center_feature, center_y), (bottom_feature, bottom_y) = self.anchors
        if not (0 <= top_y < center_y < bottom_y <= 1):
            raise ValueError("anchor y coordinates must increase within [0, 1]")
        if not (
            top_feature < center_feature < bottom_feature
            or top_feature > center_feature > bottom_feature
        ):
            raise ValueError("vertical features must be strictly monotonic across rows")

    def outside_anchor_range(self, feature: float) -> bool:
        if not _finite(feature):
            raise ValueError("vertical feature must be finite")
        outer = (self.anchors[0][0], self.anchors[2][0])
        return not min(outer) <= feature <= max(outer)

    def predict_vertical(self, feature: float) -> float:
        if not _finite(feature):
            raise ValueError("vertical feature must be finite")
        direction = 1 if self.anchors[2][0] > self.anchors[0][0] else -1
        first, second = (
            self.anchors[:2]
            if direction * (feature - self.anchors[1][0]) <= 0
            else self.anchors[1:]
        )
        first_feature, first_y = first
        second_feature, second_y = second
        prediction = first_y + (feature - first_feature) * (second_y - first_y) / (
            second_feature - first_feature
        )
        if not isfinite(prediction):
            raise ValueError("vertical prediction is not finite")
        return prediction


def fit_row_anchor_mapping(samples: Iterable[CalibrationSample]) -> PiecewiseVerticalMapping:
    """Fit three anchors from the median of three per-target medians per row."""
    groups: dict[float, list[CalibrationSample]] = defaultdict(list)
    for sample in samples:
        if not isinstance(sample, CalibrationSample):
            raise ValueError("row anchors require CalibrationSample values")
        groups[sample.target_y].append(sample)
    if len(groups) != 3 or any(
        len(row) != 3 or len({sample.target_x for sample in row}) != 3 for row in groups.values()
    ):
        raise ValueError("row-anchor experiment requires three distinct targets in each row")
    anchors = tuple(
        (median(sample.vertical_feature for sample in groups[y]), y) for y in sorted(groups)
    )
    return PiecewiseVerticalMapping(anchors)


@dataclass(frozen=True, slots=True)
class CombinedMapping:
    """Reuse baseline x unchanged; replace y only for this offline experiment."""

    baseline: IndependentLinearMapping
    vertical: PiecewiseVerticalMapping

    def predict(self, horizontal_feature: float, vertical_feature: float) -> tuple[float, float]:
        x, _ = self.baseline.predict(horizontal_feature, vertical_feature)
        return x, self.vertical.predict_vertical(vertical_feature)
