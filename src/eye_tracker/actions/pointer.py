"""Map calibrated-area coordinates to desktop pixels, then execute move/dwell."""

from math import isfinite

from eye_tracker.intent.dwell import DwellClick


class PointerController:
    def __init__(self, backend, region):
        self.backend = backend
        self.region = tuple(region)  # left, top, width, height in OS coordinates
        left, top, width, height = self.region
        sw, sh = backend.screen_size
        if not all(isfinite(v) for v in self.region) or not (
            width > 0
            and height > 0
            and left >= 0
            and top >= 0
            and left + width <= sw
            and top + height <= sh
        ):
            raise ValueError("calibration region must fit the primary display")
        self.dwell = DwellClick()

    def update(self, now, point):
        self.backend.check_stop()
        if point is None or not all(isfinite(v) and 0 <= v <= 1 for v in point):
            self.dwell.update(now, None)
            return {"pixel": None, "clicked": False}
        left, top, width, height = self.region
        sw, sh = self.backend.screen_size
        x = min(sw - 1, round(left + point[0] * width))
        y = min(sh - 1, round(top + point[1] * height))
        self.backend.move(x, y)
        clicked = self.dwell.update(now, (x, y))
        if clicked:
            self.backend.click()
        return {"pixel": [x, y], "clicked": clicked}
