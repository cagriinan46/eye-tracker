"""Live COMBO mapping, smoothing, zone lookup and dwell selection (Issue #81)."""

from collections import deque
from dataclasses import dataclass
from statistics import median

from experiments.vertical_signal_comparison.analysis import (
    CANDIDATES,
    fit,
    frame_features,
    predict,
    presentation_medians,
)

# Preregistered on 2026-10-08 before any Issue #81 session; do not tune.
MIN_CALIBRATION_PRESENTATIONS = 20  # of 25
SMOOTHING_FRAMES = 7
SMOOTHING_MAX_AGE_SECONDS = 0.5
DWELL_SECONDS = 1.0
TIMEOUT_SECONDS = 5.0
CUE_SECONDS = 0.75
FEEDBACK_SECONDS = 0.5

X_FEATURES = ("horizontal",)
Y_FEATURES = CANDIDATES["COMBO"]


@dataclass(frozen=True, slots=True)
class Mapping:
    x_coefficients: list[float]
    y_coefficients: list[float]
    calibration_presentations: int


def fit_mapping(calibration_rows: list[dict]) -> Mapping | None:
    """Calibration-only fit; None when too few presentations or a rank-deficient design."""
    records = [
        record
        for record in presentation_medians(calibration_rows)
        if record["phase"] == "calibration" and record["available"]
    ]
    if len(records) < MIN_CALIBRATION_PRESENTATIONS:
        return None
    x = fit(records, X_FEATURES, "target_x")
    y = fit(records, Y_FEATURES, "target_y")
    if x is None or y is None:
        return None
    return Mapping(x, y, len(records))


def frame_point(details: dict, mapping: Mapping) -> tuple[float, float] | None:
    """One frame's unclipped estimate, or None when unusable or blinking."""
    features = frame_features(details)
    if features is None:
        return None
    return (
        predict(mapping.x_coefficients, features, X_FEATURES),
        predict(mapping.y_coefficients, features, Y_FEATURES),
    )


class Smoother:
    """Median of the last valid estimates that are at most 0.5 s old."""

    def __init__(self) -> None:
        self._points: deque[tuple[float, tuple[float, float]]] = deque(maxlen=SMOOTHING_FRAMES)

    def update(self, now: float, point: tuple[float, float] | None) -> tuple[float, float] | None:
        if point is not None:
            self._points.append((now, point))
        while self._points and now - self._points[0][0] > SMOOTHING_MAX_AGE_SECONDS:
            self._points.popleft()
        if not self._points:
            return None
        return (
            median(item[1][0] for item in self._points),
            median(item[1][1] for item in self._points),
        )


def cell_of(point: tuple[float, float], rows: int, columns: int) -> tuple[int, int]:
    """Screen-filling zones; estimates beyond the screen clamp to the edge cell."""
    x, y = point
    row = min(rows - 1, max(0, int(y * rows)))
    column = min(columns - 1, max(0, int(x * columns)))
    return row, column


class DwellSelector:
    """Selects whichever cell stays continuously under the smoothed estimate for 1.0 s."""

    def __init__(self) -> None:
        self.cell: tuple[int, int] | None = None
        self.since: float | None = None

    def update(self, now: float, cell: tuple[int, int] | None) -> tuple[int, int] | None:
        if cell is None:
            self.cell = self.since = None
            return None
        if cell != self.cell:
            self.cell, self.since = cell, now
            return None
        if now - self.since >= DWELL_SECONDS:
            selected = self.cell
            self.cell = self.since = None
            return selected
        return None

    def progress(self, now: float) -> float:
        return 0.0 if self.since is None else min(1.0, (now - self.since) / DWELL_SECONDS)
