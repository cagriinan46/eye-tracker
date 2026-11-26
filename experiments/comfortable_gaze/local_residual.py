"""Fit a smooth personal residual from the thirteen calibration anchors."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from experiments.unigaze.mapping import Ridge
from experiments.unigaze.smoothing import StreamFilter

from .replay import calibration_rows, features, metrics, pose_reference, small_motion


class PersonalCorrection:
    """Smooth residual of the baseline at the median of each calibration target."""

    def __init__(self, model, x, y):
        labels = np.asarray(list(dict.fromkeys(map(tuple, y))))
        anchors = [np.median(x[np.all(y == target, axis=1)], axis=0) for target in labels]
        self.locations = np.array([model.predict(a) for a in anchors])
        distances = np.linalg.norm(self.locations[:, None] - self.locations, axis=2)
        np.fill_diagonal(distances, np.inf)
        self.width = np.median(distances.min(axis=1))
        if not np.isfinite(self.width) or self.width <= 0:
            raise ValueError("Kalibrasyon noktaları birbirinden ayrılamadı.")
        kernel = self.weights(self.locations[:, None])
        self.coeff = np.linalg.solve(kernel + 0.25 * np.eye(len(labels)), labels - self.locations)

    def weights(self, point):
        return np.exp(-np.sum((point - self.locations) ** 2, axis=-1) / (2 * self.width**2))

    def correct(self, predicted):
        return predicted + self.weights(predicted) @ self.coeff


def replay(folder):
    training = calibration_rows(folder)
    center, rotation = pose_reference(training)
    size = np.asarray(json.loads((folder / "session.json").read_text())["screen_size"])
    y = np.array([r["target"] for r in training])
    labels = {tuple(target) for target in y}
    fits = {}
    # Freeze all settings before scoring. Camera angles and the estimated
    # ray-plane intersection are alternative two-dimensional inputs.
    for signal in ("angles", "plane"):
        x = np.array([features(r, signal) for r in training])
        model = Ridge(standardize=True)
        model.fit(x, y)
        fits[signal] = model, PersonalCorrection(model, x, y)

    filters = {key: StreamFilter() for key in fits}
    errors = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for line in (folder / "filter-stream.jsonl").read_text().splitlines():
        row = json.loads(line)
        if not row["joint_valid"]:
            for stream in filters.values():
                stream.reset()
            continue
        target = tuple(row["target"])
        condition = row.get("condition", "normal")
        groups = [condition]
        if condition == "normal" and small_motion(row, center, rotation):
            groups.append("small_motion")
        for signal, (model, correction) in fits.items():
            predicted = model.predict(features(row, signal))
            point, _ = filters[signal].update(correction.correct(predicted), row["timestamp_ns"])
            if row["scored"] and target not in labels:
                for group in groups:
                    errors[group][signal][target].append((point - np.asarray(target)) * size)
    return {group: {s: metrics(t) for s, t in signals.items()} for group, signals in errors.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    paths = parser.parse_args().sessions
    print(json.dumps({p.name: replay(p) for p in paths}, indent=2, allow_nan=False))
