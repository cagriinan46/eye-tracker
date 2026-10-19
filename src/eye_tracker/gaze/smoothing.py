"""Output-coordinate EMA; independent of vision, fitting and OS pointer actions."""

from math import isfinite


class EMASmoother:
    """Fixed alpha per valid update, applied equally to both coordinate axes.

    Accepts either normalized or pixel coordinates (never mix units in a session).
    Missing/nonfinite input resets history and returns no point. The first valid
    estimate initializes state without drifting from an arbitrary origin.
    This reduces fast fluctuations but adds lag; it does not correct gaze bias.
    """

    def __init__(self, alpha: float = 0.2) -> None:
        if not isfinite(alpha) or not 0 < alpha <= 1:
            raise ValueError("alpha must be finite and in (0, 1]")
        self._alpha = alpha
        self._previous: tuple[float, float] | None = None

    def reset(self) -> None:
        self._previous = None

    def update(self, point: tuple[float, float] | None) -> tuple[float, float] | None:
        if point is None or not all(isfinite(value) for value in point):
            self.reset()
            return None
        x, y = point
        if self._previous is not None:
            old_x, old_y = self._previous
            x = self._alpha * x + (1 - self._alpha) * old_x
            y = self._alpha * y + (1 - self._alpha) * old_y
        self._previous = (x, y)
        return self._previous
