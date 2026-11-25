"""Replay paired research sessions. Inputs and outputs contain no camera images."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from experiments.unigaze.mapping import Ridge
from experiments.unigaze.smoothing import StreamFilter

FITTED = (
    "angles",
    "plane",
    "plane_quadratic",
    "plane_iris",
    "angles_quadratic",
    "angles_quadratic_median",
    "plane_quadratic_median",
)
MODELS = (*FITTED, "mgaze", "plane_mgaze_blend")


def features(row, model):
    if model == "angles":
        return row["unigaze_angles"]
    if model.startswith("angles_quadratic"):
        x, y = row["unigaze_angles"]
        return [x, y, x * x, x * y, y * y]
    origin = np.asarray(row["unigaze_face_center"])
    direction = np.asarray(row["unigaze_vector"])
    x, y = origin[:2] - origin[2] * direction[:2] / direction[2]
    if model.startswith("plane_quadratic"):
        return [x, y, x * x, x * y, y * y]
    if model == "plane_iris":
        eyes = row["diagnostics"]["corrected_eyes"]
        return [
            x,
            y,
            *(eyes[side][axis] for side in ("left", "right") for axis in ("iris_u", "iris_v")),
        ]
    return [x, y]


def rotation_vector_quaternion(vector):
    angle = np.linalg.norm(vector)
    return np.r_[np.cos(angle / 2), np.asarray(vector) * (0.5 * np.sinc(angle / (2 * np.pi)))]


def metrics(targets):
    vectors = [np.asarray(values) for values in targets.values()]
    errors = [np.linalg.norm(v, axis=1) for v in vectors]

    def mean(values):
        return float(np.mean(values))

    return {
        "targets": len(errors),
        "frames": sum(map(len, errors)),
        "mean_px": mean([e.mean() for e in errors]),
        "mean_target_bias_px": mean([np.linalg.norm(v.mean(0)) for v in vectors]),
        "within_20": mean([(e <= 20).mean() for e in errors]),
        "mean_target_p90_px": mean([np.percentile(e, 90) for e in errors]),
    }


def calibration_rows(folder):
    def read(name):
        return json.loads((folder / name).read_text())

    calibration = defaultdict(list)
    selected = read("training-selection.json")["successful_attempts"]
    for line in (folder / "samples.jsonl").read_text().splitlines():
        row = json.loads(line)
        if (
            row["phase"] == "calibration"
            and row["joint_valid"]
            and row["attempt"] == selected[str(row["trial"])]
        ):
            calibration[row["trial"]].append(row)
    if len(calibration) != 13 or min(map(len, calibration.values())) < 20:
        raise ValueError(f"Incomplete calibration in {folder}")
    return [
        rows[i]
        for _, rows in sorted(calibration.items())
        for i in np.linspace(0, len(rows) - 1, 20, dtype=int)
    ]


def pose_reference(training):
    center = np.median([r["unigaze_face_center"] for r in training], axis=0)
    rotation = rotation_vector_quaternion(
        np.median([r["unigaze_head_rotation"] for r in training], axis=0)
    )
    return center, rotation


def small_motion(row, center, rotation):
    distance = np.linalg.norm(np.asarray(row["unigaze_face_center"]) - center) / center[2]
    q = rotation_vector_quaternion(row["unigaze_head_rotation"])
    degrees = np.rad2deg(2 * np.arccos(np.clip(abs(q @ rotation), 0, 1)))
    return distance <= 0.04 and degrees <= 7 and (distance >= 0.005 or degrees >= 1)


def replay(folder):
    training = calibration_rows(folder)
    center, rotation = pose_reference(training)
    size = np.asarray(json.loads((folder / "session.json").read_text())["screen_size"])
    fits = {}
    for name in FITTED:
        x = np.asarray([features(r, name) for r in training])
        y = np.asarray([r["target"] for r in training])
        if name.endswith("_median"):
            x = np.median(x.reshape(13, 20, -1), axis=1)
            y = y[::20]
        fits[name] = Ridge(standardize=True)
        fits[name].fit(x, y)

    filters = {name: StreamFilter() for name in MODELS}
    errors = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    eligible = defaultdict(int)
    total = defaultdict(int)
    labels = {tuple(r["target"]) for r in training}
    for line in (folder / "filter-stream.jsonl").read_text().splitlines():
        row = json.loads(line)
        target = tuple(row["target"])
        condition = row.get("condition", "normal")
        score = row["scored"] and target not in labels
        if score:
            total[condition] += 1
        if not row["joint_valid"]:
            for stream in filters.values():
                stream.reset()
            continue
        predictions = {name: fit.predict(features(row, name)) for name, fit in fits.items()}
        predictions["mgaze"] = np.asarray(row["mgaze_prediction"])
        predictions["plane_mgaze_blend"] = (predictions["plane"] + predictions["mgaze"]) / 2
        groups = [condition]
        if score:
            eligible[condition] += 1
            if condition == "normal" and small_motion(row, center, rotation):
                groups.append("small_motion")
        for name, prediction in predictions.items():
            filtered, _ = filters[name].update(prediction, row["timestamp_ns"])
            if score:
                for group in groups:
                    for stage, value in (("raw", prediction), ("filtered", filtered)):
                        errors[group][name, stage][target].append(
                            (value - np.asarray(target)) * size
                        )
    result = {
        g: {n: {s: metrics(data[n, s]) for s in ("raw", "filtered")} for n in MODELS}
        for g, data in errors.items()
    }
    return {"groups": result, "eligible": dict(eligible), "total": dict(total)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    args = parser.parse_args()
    results = {p.name: replay(p) for p in args.sessions}
    if len(results) < 2:
        parser.error("Pass at least two distinct sessions for held-out selection.")
    # Only compare full eight-target movement blocks. Each training session
    # receives equal weight regardless of its duration.
    folds = {}
    for held in results:

        def selection_score(model):
            scores = []
            for session, result in results.items():
                if session == held:
                    continue
                groups = result["groups"]
                means = [groups["normal"][model]["filtered"]["mean_px"]]
                small = groups.get("small_motion", {}).get(model, {}).get("filtered")
                if small and small["targets"] == 8:
                    means.append(small["mean_px"])
                scores.append(np.mean(means))
            return np.mean(scores)

        folds[held] = min(MODELS, key=selection_score)
    print(json.dumps({"sessions": results, "held_out_choices": folds}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
