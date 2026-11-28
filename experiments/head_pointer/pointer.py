"""Hardware-free calibration fit, One Euro filter and dwell trial for Issue #156."""

from dataclasses import dataclass, field
from math import hypot, isfinite, pi, sqrt
from statistics import fmean, median

from experiments.head_pointer.protocol import (
    DWELL_SECONDS,
    GAP_RESET_SECONDS,
    MIN_FRAMES_PER_POINT,
    MIN_POINTS,
    ONE_EURO_BETA,
    ONE_EURO_D_CUTOFF,
    ONE_EURO_MIN_CUTOFF,
    TIMEOUT_SECONDS,
)


@dataclass(frozen=True, slots=True)
class Line:
    intercept: float
    slope: float

    def __call__(self, value: float) -> float:
        return self.intercept + self.slope * value


@dataclass(frozen=True, slots=True)
class Mapping:
    """Per-axis lines from a candidate's raw signal to normalized screen coordinates."""

    x: Line
    y: Line

    def __call__(self, signal: tuple[float, float]) -> tuple[float, float]:
        return (self.x(signal[0]), self.y(signal[1]))


def fit_line(pairs: list[tuple[float, float]]) -> Line | None:
    """OLS of screen coordinate on signal value; ``pairs`` are (signal, screen)."""
    if len(pairs) < 2:
        return None
    mean_s = fmean(s for s, _ in pairs)
    mean_t = fmean(t for _, t in pairs)
    variance = sum((s - mean_s) ** 2 for s, _ in pairs)
    if variance <= 1e-12:
        return None
    slope = sum((s - mean_s) * (t - mean_t) for s, t in pairs) / variance
    return Line(mean_t - slope * mean_s, slope)


def fit_mapping(rows: list[dict], candidate: str) -> Mapping | None:
    """Fit one candidate from calibration rows sharing the same frames.

    Each row: ``point`` (presentation index), ``target_x``, ``target_y`` and
    ``signals`` {candidate: [a, b] | None}. Uses the per-presentation median.
    """
    grouped: dict[int, list[tuple[float, float]]] = {}
    targets: dict[int, tuple[float, float]] = {}
    for row in rows:
        value = (row.get("signals") or {}).get(candidate)
        if value is None or len(value) != 2 or not all(isfinite(v) for v in value):
            continue
        grouped.setdefault(row["point"], []).append((value[0], value[1]))
        targets[row["point"]] = (row["target_x"], row["target_y"])
    medians = {
        point: (median(v[0] for v in values), median(v[1] for v in values))
        for point, values in grouped.items()
        if len(values) >= MIN_FRAMES_PER_POINT
    }
    if len(medians) < MIN_POINTS:
        return None
    x = fit_line([(medians[p][0], targets[p][0]) for p in medians])
    y = fit_line([(medians[p][1], targets[p][1]) for p in medians])
    return Mapping(x, y) if x is not None and y is not None else None


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2 * pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter2D:
    """Casiez et al. 2012 One Euro filter on a 2D point (low jitter, low lag)."""

    def __init__(
        self,
        min_cutoff: float = ONE_EURO_MIN_CUTOFF,
        beta: float = ONE_EURO_BETA,
        d_cutoff: float = ONE_EURO_D_CUTOFF,
        gap: float = GAP_RESET_SECONDS,
    ) -> None:
        self.min_cutoff, self.beta, self.d_cutoff, self.gap = min_cutoff, beta, d_cutoff, gap
        self.reset()

    def reset(self) -> None:
        self.time: float | None = None
        self.value: tuple[float, float] | None = None
        self.speed = (0.0, 0.0)

    def update(self, now: float, point: tuple[float, float]) -> tuple[float, float]:
        if self.time is not None and now <= self.time:
            return self.value
        if self.time is None or now - self.time > self.gap:
            self.time, self.value, self.speed = now, point, (0.0, 0.0)
            return point
        dt = now - self.time
        a_d = _alpha(self.d_cutoff, dt)
        raw_speed = tuple((p - v) / dt for p, v in zip(point, self.value, strict=True))
        self.speed = tuple(
            a_d * r + (1 - a_d) * s for r, s in zip(raw_speed, self.speed, strict=True)
        )
        cutoff = self.min_cutoff + self.beta * hypot(*self.speed)
        a = _alpha(cutoff, dt)
        self.value = tuple(a * p + (1 - a) * v for p, v in zip(point, self.value, strict=True))
        self.time = now
        return self.value


@dataclass
class DwellTrial:
    """One target: contiguous dwell inside the circle selects; timeout otherwise.

    Times are seconds from the trial start. ``update`` takes the filtered cursor in
    pixels (or None when the face is lost, which leaves the cursor where it was but
    does not add dwell time).
    """

    center: tuple[float, float]
    radius: float
    dwell: float = DWELL_SECONDS
    timeout: float = TIMEOUT_SECONDS
    entries: int = 0
    first_entry: float | None = None
    outcome: str | None = None
    elapsed: float | None = None
    _inside_since: float | None = None
    _dwell_points: list[tuple[float, float, float]] = field(default_factory=list)

    def inside(self, cursor: tuple[float, float]) -> bool:
        return hypot(cursor[0] - self.center[0], cursor[1] - self.center[1]) <= self.radius

    def update(self, t: float, cursor: tuple[float, float] | None) -> str | None:
        if self.outcome is not None:
            return self.outcome
        if cursor is not None and self.inside(cursor):
            if self._inside_since is None:
                self._inside_since = t
                self._dwell_points = []
                self.entries += 1
                if self.first_entry is None:
                    self.first_entry = t
            self._dwell_points.append((t, *cursor))
            if t - self._inside_since >= self.dwell - 1e-9:
                self.outcome, self.elapsed = "selected", t
                return self.outcome
        else:
            self._inside_since = None
        if t >= self.timeout:
            self.outcome, self.elapsed = "timeout", t
        return self.outcome

    def progress(self, t: float) -> float:
        if self._inside_since is None:
            return 0.0
        return min(1.0, (t - self._inside_since) / self.dwell)

    def hold_jitter(self) -> float | None:
        """RMS distance (px) of the dwell's cursor points from their mean; selected only."""
        if self.outcome != "selected" or len(self._dwell_points) < 2:
            return None
        mx = fmean(p[1] for p in self._dwell_points)
        my = fmean(p[2] for p in self._dwell_points)
        return sqrt(fmean((p[1] - mx) ** 2 + (p[2] - my) ** 2 for p in self._dwell_points))
