"""Test transfer of spatial bias and within-fixation pose sensitivity across sessions."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .replay import calibration_rows, metrics, pose_reference, small_motion


def blocks(folder):
    training = calibration_rows(folder)
    center, orientation = pose_reference(training)
    rotation = np.median([r["unigaze_head_rotation"] for r in training], axis=0)
    labels = {tuple(r["target"]) for r in training}
    size = np.asarray(json.loads((folder / "session.json").read_text())["screen_size"])
    groups = defaultdict(list)
    for line in (folder / "filter-stream.jsonl").read_text().splitlines():
        r = json.loads(line)
        target = tuple(r["target"])
        if (
            r.get("condition", "normal") != "normal"
            or not r["scored"]
            or not r["joint_valid"]
            or target in labels
        ):
            continue
        displacement = (np.asarray(r["unigaze_face_center"]) - center) / center[2]
        if not small_motion(r, center, orientation):
            continue
        pred = np.array(r["unigaze_filtered_prediction"])
        pose = np.r_[displacement, np.asarray(r["unigaze_head_rotation"]) - rotation]
        groups[target].append((pred, pose, (pred - target) * size))
    return {
        k: tuple(np.stack(col) for col in zip(*rows, strict=True)) for k, rows in groups.items()
    }


def pose_slopes(donors):
    # Center within each fixation so a location's constant error cannot explain
    # head sensitivity. Give each donor fixation the same total weight.
    poses, errors = [], []
    for _, pose, error in donors:
        weight = 1 / np.sqrt(len(pose))
        poses.append((pose - pose.mean(0)) * weight)
        errors.append((error - error.mean(0)) * weight)
    x, y = np.vstack(poses), np.vstack(errors)
    scale = np.maximum(np.sqrt(np.sum(x * x, axis=0) / len(donors)), 1e-8)
    z = x / scale
    return np.linalg.solve(z.T @ z + np.eye(6) * len(donors), z.T @ y) / scale[:, None]


def evaluate(sessions):
    scores = {}
    agreement = []
    movement = []
    for name, held in sessions.items():
        other = [data for session, data in sessions.items() if session != name]
        residuals = defaultdict(dict)
        for target, (prediction, pose, error) in held.items():
            # Same-location donor errors are used only in the diagnostic.
            at_target = np.mean([data[target][2].mean(0) for data in other], axis=0)
            observed = error.mean(0)
            agreement.append(float(at_target @ observed) > 0)
            donors = [block for data in other for key, block in data.items() if key != target]
            locations = np.array([p.mean(0) for p, _, _ in donors])
            biases = np.array([e.mean(0) for _, _, e in donors])
            delta = prediction[:, None, :] - locations
            # Fixed local averaging width in normalized screen coordinates.
            weights = np.exp(-np.sum(delta**2, axis=2) / (2 * 0.25**2))
            spatial = weights @ biases / weights.sum(axis=1, keepdims=True)
            head = pose @ pose_slopes(donors)
            for method, correction in (
                ("baseline", 0),
                ("spatial", spatial),
                ("pose", head),
                ("both", spatial + head),
            ):
                residuals[method][target] = error - correction
            # Remove each held fixation's mean only for this diagnostic. This
            # asks whether the donor pose response predicts within-target drift.
            centered = error - observed
            corrected = centered - (head - head.mean(0))
            movement.append(
                (np.mean(np.sum(centered**2, axis=1)), np.mean(np.sum(corrected**2, axis=1)))
            )
        scores[name] = {method: metrics(groups) for method, groups in residuals.items()}
    return {
        "sessions": scores,
        "same_direction": int(sum(agreement)),
        "comparisons": len(agreement),
        "within_target_rms_before_after_px": np.sqrt(np.mean(movement, axis=0)).tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    args = parser.parse_args()
    sessions = {p.name: blocks(p) for p in args.sessions}
    targets = set(next(iter(sessions.values())))
    if len(sessions) < 2 or len(targets) != 8 or any(set(s) != targets for s in sessions.values()):
        parser.error("Need distinct sessions with matching eight-target small-motion coverage.")
    print(json.dumps(evaluate(sessions), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
