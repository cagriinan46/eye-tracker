"""Move-only mapping for a bounded desktop demonstration; never emits a click."""

from math import isfinite


def window_point(point, region):
    if point is None or len(point) != 2 or not all(isfinite(v) and 0 <= v <= 1 for v in point):
        return None
    x, y, w, h = region
    if not all(isfinite(v) for v in region) or w < 1 or h < 1:
        return None
    return (x + min(w - 1, point[0] * w), y + min(h - 1, point[1] * h))
