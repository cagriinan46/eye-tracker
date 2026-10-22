"""Camera-free paired replay of three fixed ridge settings; no model selection."""

import argparse
import hashlib
import io
import json
from pathlib import Path
from uuid import uuid4

import numpy as np

from experiments.gazefollower_baseline.run import summarize

RESULTS = Path(__file__).resolve().parent / "results"
FILES = (
    "session.json",
    "completion.json",
    "calibration.npz",
    "ridge_weights.npy",
    "evaluation-plan.json",
    "evaluation.jsonl",
    "diagnostic-frames.jsonl",
)
ALPHAS = (0.1, 1.0, 10.0)


def array(value, shape):
    result = np.asarray(value, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError("Invalid numerical array")
    return result


def timestamp(row):
    value = row.get("captured_monotonic_s")
    if type(value) not in (int, float) or not np.isfinite(value) or value < 0:
        raise ValueError("Invalid capture timestamp")
    return value


def fit(features, labels, alpha):
    design = np.c_[np.ones(len(features)), features]
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0
    weights = np.linalg.solve(design.T @ design + penalty, design.T @ labels)
    if not np.isfinite(weights).all():
        raise ValueError("Model fit produced nonfinite weights")
    return weights


def validate_plan(plan, labels, expected):
    trained = labels[:, 0, :]

    def close(a, b):
        return np.allclose(a, b, rtol=0, atol=1e-7)

    if any(close(point, old) for i, point in enumerate(trained) for old in trained[:i]):
        raise ValueError("Calibration plan contains duplicate locations")
    seen_ids, seen_points = set(), []
    for item in plan:
        point = array(item["target"], (2,))
        group, index = item["target_set"], item["target_id"]
        if (
            group not in expected
            or type(index) is not int
            or not 1 <= index <= expected[group]
            or (point < 0).any()
            or (point > 1).any()
        ):
            raise ValueError("Invalid evaluation plan location or identity")
        if (group, index) in seen_ids or any(close(point, old) for old in seen_points):
            raise ValueError("Duplicate evaluation plan identity or location")
        if group == "repeated" and not close(point, trained[index - 1]):
            raise ValueError("Repeated plan target differs from calibration")
        if group == "unseen" and any(close(point, old) for old in trained):
            raise ValueError("Unseen plan target was present in calibration")
        seen_ids.add((group, index))
        seen_points.append(point)


def analyze(session, *, results_root=RESULTS):
    session = Path(session)
    if session.is_symlink() or session.resolve().parent != Path(results_root).resolve():
        raise ValueError("Select one non-symlink session directly under validation/results")
    payload = {}
    for name in FILES:
        path = session / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing or symlink input: {name}; diagnostic capture required")
        if path.stat().st_size > 128 * 1024 * 1024:
            raise ValueError("Input exceeds diagnostic size bound")
        payload[name] = path.read_bytes()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
    metadata = json.loads(payload["session.json"])
    if metadata.get("diagnostic_features_enabled") is not True:
        raise ValueError("Session did not enable diagnostic features")
    if json.loads(payload["completion.json"]).get("status") != "completed":
        raise ValueError("Session did not complete")
    size = array(metadata["screen_size"], (2,))
    if (size <= 0).any():
        raise ValueError("Invalid screen size")
    with np.load(io.BytesIO(payload["calibration.npz"]), allow_pickle=False) as calibration:
        features = array(calibration["features"], (13, 45, 258))
        labels = array(calibration["labels"], (13, 45, 2))
    if not np.all(labels == labels[:, :1, :]) or (labels < 0).any() or (labels > 1).any():
        raise ValueError("Invalid calibration labels")
    saved = array(np.load(io.BytesIO(payload["ridge_weights.npy"]), allow_pickle=False), (259, 2))
    # Only calibration inputs reach the fit. Held-out labels are used solely for metrics.
    models = {
        str(alpha): fit(features.reshape(-1, 258), labels.reshape(-1, 2), alpha) for alpha in ALPHAS
    }
    design = np.c_[np.ones(585), features.reshape(-1, 258)]
    if np.max(np.abs((design @ models["0.1"] - design @ saved) * size)) > 0.001:
        raise ValueError("Saved model does not reproduce the declared baseline")
    plan = json.loads(payload["evaluation-plan.json"])["targets"]
    repeat = metadata.get("repeat_calibration_targets") is True
    expected = {"repeated": 13, "unseen": 6} if repeat else {"unseen": 6}
    if len(plan) != sum(expected.values()) or any(
        sum(item["target_set"] == group for item in plan) != count
        for group, count in expected.items()
    ):
        raise ValueError("Evaluation plan differs from supported protocol")
    validate_plan(plan, labels, expected)
    diagnostics = [json.loads(line) for line in payload["diagnostic-frames.jsonl"].splitlines()]
    if len(diagnostics) > 10000:
        raise ValueError("Too many diagnostic records")
    joined = {}
    for row in diagnostics:
        stamp = timestamp(row)
        if stamp in joined:
            raise ValueError("Duplicate diagnostic timestamp")
        joined[stamp] = row
    evaluation = [json.loads(line) for line in payload["evaluation.jsonl"].splitlines()]
    if not evaluation or len(evaluation) > 10000:
        raise ValueError("Empty or oversized evaluation")
    outputs = {key: [] for key in models}
    previous = -1
    maximum = 0.0
    for row in evaluation:
        stamp = timestamp(row)
        if stamp <= previous:
            raise ValueError("Evaluation timestamps must increase uniquely")
        previous = stamp
        trial = row["trial"]
        if type(trial) is not int or not 1 <= trial <= len(plan):
            raise ValueError("Invalid evaluation trial")
        item = plan[trial - 1]
        target = array(row["target_px"], (2,))
        if (
            row["target_set"] != item["target_set"]
            or row["target_id"] != item["target_id"]
            or not np.allclose(target, array(item["target"], (2,)) * size, rtol=0, atol=1e-6)
        ):
            raise ValueError("Evaluation target differs from plan")
        sample = joined.get(stamp)
        if sample is None or sample["phase"] != "evaluation" or sample["trial"] != trial:
            raise ValueError("Missing or mismatched diagnostic sample")
        if type(sample["usable"]) is not bool:
            raise ValueError("Invalid diagnostic usability")
        vector = None
        if sample["usable"]:
            vector = np.r_[1.0, array(sample["features"], (258,))]
            recorded = array(row["raw_px"], (2,))
            baseline = vector @ models["0.1"] * size
            maximum = max(maximum, float(np.abs(baseline - recorded).max()))
            if maximum > 0.001 or np.max(np.abs((vector @ saved) * size - recorded)) > 0.001:
                raise ValueError("Recorded predictions do not match replay baseline")
        elif sample["features"] is not None or row["raw_px"] is not None:
            raise ValueError("Rejected sample has features or predictions")
        for key, weights in models.items():
            point = (vector @ weights * size).tolist() if vector is not None else None
            outputs[key].append(
                dict(
                    trial=trial,
                    target_set=row["target_set"],
                    target_px=target.tolist(),
                    raw_px=point,
                    filtered_px=None,
                )
            )
    reports = {}
    for key, rows in outputs.items():
        reports[key] = {}
        for group, count in expected.items():
            summary = summarize(
                [row for row in rows if row["target_set"] == group], expected_trials=count
            )
            reports[key][group] = dict(
                sufficient_data=summary["sufficient_data"],
                mean_error_px_equal_target_weight=summary["mean_error_px_equal_target_weight"][
                    "raw"
                ],
                trials=[
                    dict(trial=t["trial"], target_px=t["target_px"], **t["raw"])
                    for t in summary["trials"]
                ],
            )
    if any(
        hashlib.sha256((session / name).read_bytes()).hexdigest() != digest
        for name, digest in hashes.items()
    ):
        raise ValueError("Source changed during analysis")
    return dict(
        session=session.name,
        source_sha256=hashes,
        models=reports,
        baseline_max_difference_px=maximum,
        attempts=len(evaluation),
        limitations="Fixed ridge comparisons only, raw/unclipped predictions. No filtering, "
        "automatic selection or deployed-model changes. Repeated locations are not unseen "
        "accuracy. No independently verified fixation or causal attribution. Missing "
        "attempts remain in hit-rate denominators; insufficient groups have no mean.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.session, results_root=RESULTS)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f"Cannot replay session: {error}\n")
    folder = RESULTS / ("gaze-model-replay-" + uuid4().hex)
    folder.mkdir()
    report["analyzer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with (folder / "report.json").open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(folder)


if __name__ == "__main__":
    main()
