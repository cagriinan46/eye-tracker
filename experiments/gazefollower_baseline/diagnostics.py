"""Opt-in numerical diagnostics; never retain images or full facial landmarks."""

import json

import numpy as np


def finite_values(value, length):
    if value is None:
        return None
    values = np.asarray(value, dtype=float)
    return values.tolist() if values.shape == (length,) and np.isfinite(values).all() else None


def eye_metrics(rgb, rectangle):
    rect = finite_values(rectangle, 4)
    if rect is None or rect[2] <= 0 or rect[3] <= 0:
        return None
    x, y, width, height = rect
    h, w = rgb.shape[:2]
    left, top = max(0, int(x)), max(0, int(y))
    right, bottom = min(w, int(x + width)), min(h, int(y + height))
    if right - left < 2 or bottom - top < 2:
        return None
    gray = rgb[top:bottom, left:right].astype(float).mean(axis=2)
    gradient = np.concatenate((np.diff(gray, axis=0).ravel(), np.diff(gray, axis=1).ravel()))
    return dict(
        crop_size=[right - left, bottom - top],
        mean_rgb_intensity=float(gray.mean()),
        intensity_std=float(gray.std()),
        bright_fraction=float(np.mean(gray >= 245)),
        gradient_rms=float(np.sqrt(np.mean(gradient**2))),
    )


def diagnostic_row(rgb, face, gaze, *, usable, captured_at, phase, trial):
    features = finite_values(getattr(gaze, "features", None), 258) if usable else None
    openness = [
        finite_values([getattr(face, key, float("nan"))], 1)
        for key in ("left_eye_openness", "right_eye_openness")
    ]
    return dict(
        captured_monotonic_s=captured_at,
        phase=phase,
        trial=trial,
        usable=bool(usable and features is not None),
        features=features,
        face_rect=finite_values(getattr(face, "face_rect", None), 4),
        eye_openness=[value[0] if value else None for value in openness],
        eyes={
            side: eye_metrics(rgb, getattr(face, side + "_rect", None))
            for side in ("left", "right")
        },
    )


class DiagnosticRecorder:
    """Exclusive, bounded local sidecar. Partial records survive cancellation."""

    def __init__(self, path, *, max_rows=10000):
        self.stream = path.open("x", encoding="utf-8")
        self.max_rows = max_rows
        self.rows = 0

    def write(self, row):
        if self.rows >= self.max_rows:
            raise RuntimeError("Diagnostic frame limit reached")
        self.stream.write(json.dumps(row, allow_nan=False) + "\n")
        self.stream.flush()
        self.rows += 1

    def close(self):
        self.stream.close()
