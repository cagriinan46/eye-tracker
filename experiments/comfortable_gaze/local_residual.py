"""Fit a smooth personal residual from the thirteen calibration anchors."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from experiments.unigaze.mapping import Ridge
from experiments.unigaze.smoothing import StreamFilter

from .replay import calibration_rows, features, metrics, pose_reference, small_motion


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
        anchors = np.median(x.reshape(13, 20, 2), axis=1)
        locations = np.array([model.predict(a) for a in anchors])
        residual = y[::20] - locations
        distances = np.linalg.norm(locations[:, None] - locations, axis=2)
        np.fill_diagonal(distances, np.inf)
        width = np.median(distances.min(axis=1))
        kernel = np.exp(-np.sum((locations[:, None] - locations) ** 2, axis=2) / (2 * width**2))
        coeff = np.linalg.solve(kernel + 0.25 * np.eye(len(kernel)), residual)
        fits[signal] = model, locations, width, coeff

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
        for signal, (model, locations, width, coeff) in fits.items():
            predicted = model.predict(features(row, signal))
            weights = np.exp(-np.sum((predicted - locations) ** 2, axis=1) / (2 * width**2))
            point, _ = filters[signal].update(predicted + weights @ coeff, row["timestamp_ns"])
            if row["scored"] and target not in labels:
                for group in groups:
                    errors[group][signal][target].append((point - np.asarray(target)) * size)
    return {group: {s: metrics(t) for s, t in signals.items()} for group, signals in errors.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    paths = parser.parse_args().sessions
    print(json.dumps({p.name: replay(p) for p in paths}, indent=2, allow_nan=False))
