"""Calibration fits, per-frame pointing, smoothing and dwell for Issue #84."""

from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import fmean, median

from validation.real_calibration import MIN_USABLE_SAMPLES

# Preregistered on 2026-10-08 before any Issue #84 session; do not tune.
BLINK_MAX = 0.5
MIN_BLOCK_PRESENTATIONS = 4  # of 5 per calibration block
SMOOTHING_FRAMES = 7
SMOOTHING_MAX_AGE_SECONDS = 0.5
DWELL_SECONDS = 1.0
TIMEOUT_SECONDS = 5.0
CUE_SECONDS = 0.75
FEEDBACK_SECONDS = 0.5

# Calibration block -> (per-frame feature field, screen axis it calibrates).
BLOCK_FEATURES = {
    "eye_x": ("horizontal", "target_x"),
    "head_y": ("head_pitch_deg", "target_y"),
    "head_x": ("head_yaw_deg", "target_x"),
}
CONDITION_AXES = {"HYBRID": ("eye_x", "head_y"), "HEAD": ("head_x", "head_y")}


@dataclass(frozen=True, slots=True)
class Line:
    intercept: float
    slope: float

    def __call__(self, value: float) -> float:
        return self.intercept + self.slope * value


def frame_value(row: dict, field: str) -> float | None:
    """Usable frame value; eye features additionally require no blink."""
    if row.get("status") != "usable" or row.get(field) is None:
        return None
    if field == "horizontal":
        blinks = (row.get("blink_left"), row.get("blink_right"))
        if None in blinks or max(blinks) > BLINK_MAX:
            return None
    return float(row[field])


def fit_axis(points: list[tuple[float, float]]) -> Line | None:
    """OLS of screen coordinate on feature; None if the feature does not vary."""
    features = [p[0] for p in points]
    targets = [p[1] for p in points]
    mean_feature, mean_target = fmean(features), fmean(targets)
    spread = sum((f - mean_feature) ** 2 for f in features)
    if spread == 0:
        return None
    slope = sum((f - mean_feature) * (t - mean_target) for f, t in points) / spread
    return Line(mean_target - slope * mean_feature, slope)


def fit_calibration(rows: list[dict]) -> dict[str, Line] | None:
    """One line per block from presentation medians; None if any block is insufficient."""
    lines = {}
    for block, (field, axis) in BLOCK_FEATURES.items():
        groups: dict[int, list[float]] = defaultdict(list)
        coordinates: dict[int, float] = {}
        for row in rows:
            if row["phase"] != block:
                continue
            coordinates[row["presentation"]] = row[axis]
            value = frame_value(row, field)
            if value is not None:
                groups[row["presentation"]].append(value)
        points = [
            (median(values), coordinates[key])
            for key, values in groups.items()
            if len(values) >= MIN_USABLE_SAMPLES
        ]
        if len(points) < MIN_BLOCK_PRESENTATIONS:
            return None
        line = fit_axis(points)
        if line is None:
            return None
        lines[block] = line
    return lines


def frame_point(row: dict, lines: dict[str, Line], condition: str) -> tuple[float, float] | None:
    x_block, y_block = CONDITION_AXES[condition]
    x_value = frame_value(row, BLOCK_FEATURES[x_block][0])
    y_value = frame_value(row, BLOCK_FEATURES[y_block][0])
    if x_value is None or y_value is None:
        return None
    return lines[x_block](x_value), lines[y_block](y_value)


class Smoother:
    """Median of the last valid estimates that are at most 0.5 s old (as in Issue #81)."""

    def __init__(self) -> None:
        self._points: deque[tuple[float, tuple[float, float]]] = deque(maxlen=SMOOTHING_FRAMES)

    def reset(self) -> None:
        self._points.clear()

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
    return min(rows - 1, max(0, int(y * rows))), min(columns - 1, max(0, int(x * columns)))


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
