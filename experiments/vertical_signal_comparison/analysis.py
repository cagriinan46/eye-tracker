"""Compare preregistered vertical-signal candidates (Issue #77); see README.md.

Every candidate is fitted on the same session's calibration presentations only
and scored on the same validation presentations and common frames. Thresholds
and candidate definitions are frozen before the Fatih A/B sessions.
"""

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from statistics import fmean, median

import numpy as np

from validation.real_calibration import MIN_USABLE_SAMPLES, percentile

# Preregistered on 2026-10-08 before any Issue #77 session; do not tune.
BLINK_MAX = 0.5
MIN_CALIBRATION_PRESENTATIONS = 20  # of 25
MIN_VALIDATION_PRESENTATIONS = 14  # of 16
PASS_Y_MAE = 0.08
PASS_ORDERING = 19 / 21
PASS_ABS_BIAS = 0.05
ORDERING_MIN_DELTA = 0.05

BASE_FEATURES = ("horizontal", "vertical", "opening", "blend", "pitch")
CANDIDATES = {
    "R0": ("vertical",),
    "OPEN": ("opening",),
    "OPEN_Q": ("opening", "opening_squared"),
    "BLEND": ("blend",),
    "COMBO": ("vertical", "opening", "blend", "pitch"),
}
REQUIRED_ROW_FIELDS = (
    "horizontal",
    "vertical",
    "binocular_eye_opening",
    "look_up_left",
    "look_up_right",
    "look_down_left",
    "look_down_right",
    "blink_left",
    "blink_right",
    "head_pitch_deg",
)


def frame_features(row: dict) -> dict | None:
    """Common-frame rule: every input present and no blink; otherwise excluded."""
    if row.get("status") != "usable" or any(row.get(k) is None for k in REQUIRED_ROW_FIELDS):
        return None
    if max(row["blink_left"], row["blink_right"]) > BLINK_MAX:
        return None
    return {
        "horizontal": float(row["horizontal"]),
        "vertical": float(row["vertical"]),
        "opening": float(row["binocular_eye_opening"]),
        "blend": (row["look_down_left"] + row["look_down_right"]) / 2
        - (row["look_up_left"] + row["look_up_right"]) / 2,
        "pitch": float(row["head_pitch_deg"]),
    }


def presentation_medians(rows: list[dict]) -> list[dict]:
    """One record per presentation with per-feature medians over its common frames."""
    groups: dict[int, list[dict]] = defaultdict(list)
    info: dict[int, dict] = {}
    for row in rows:
        key = row["presentation"]
        info.setdefault(key, row)
        features = frame_features(row)
        if features is not None:
            groups[key].append(features)
    records = []
    for key in sorted(info):
        first, frames = info[key], groups.get(key, [])
        record = {
            "presentation": key,
            "phase": first["phase"],
            "target_id": first["target_id"],
            "target_x": first["target_x"],
            "target_y": first["target_y"],
            "trial_number": first["trial_number"],
            "frames": len(frames),
            "available": len(frames) >= MIN_USABLE_SAMPLES,
        }
        if record["available"]:
            for name in BASE_FEATURES:
                record[name] = median(frame[name] for frame in frames)
            record["opening_squared"] = record["opening"] ** 2
        records.append(record)
    return records


def fit(records: list[dict], features: tuple[str, ...], target: str) -> list[float] | None:
    """Ordinary least squares with intercept; None when the design is rank deficient."""
    design = np.array([[1.0, *(r[name] for name in features)] for r in records])
    values = np.array([r[target] for r in records])
    coefficients, _, rank, _ = np.linalg.lstsq(design, values, rcond=None)
    if rank < design.shape[1]:
        return None
    return [float(value) for value in coefficients]


def predict(coefficients: list[float], record: dict, features: tuple[str, ...]) -> float:
    return coefficients[0] + sum(c * record[n] for c, n in zip(coefficients[1:], features))


def ordering(points: list[tuple[float, float]]) -> dict:
    """Distinct-target pairs at least 0.05 apart whose predicted order matches."""
    consistent = total = 0
    for (target_a, predicted_a), (target_b, predicted_b) in combinations(points, 2):
        if abs(target_b - target_a) < ORDERING_MIN_DELTA:
            continue
        total += 1
        consistent += (predicted_b - predicted_a) * (target_b - target_a) > 0
    return {
        "consistent_pairs": consistent,
        "total_pairs": total,
        "proportion": consistent / total if total else 0.0,
    }


def score(predictions: list[tuple[dict, float]], axis: str) -> dict:
    errors = [predicted - record[axis] for record, predicted in predictions]
    return {
        "mae": fmean(abs(error) for error in errors),
        "bias": fmean(errors),
        "ordering": ordering([(record[axis], predicted) for record, predicted in predictions]),
    }


def passes(metrics: dict) -> bool:
    return (
        metrics["mae"] <= PASS_Y_MAE
        and metrics["ordering"]["proportion"] >= PASS_ORDERING
        and abs(metrics["bias"]) <= PASS_ABS_BIAS
    )


def _r_squared(records: list[dict], coefficients: list[float], features: tuple[str, ...]) -> float:
    values = [r["target_y"] for r in records]
    mean_value = fmean(values)
    total = sum((value - mean_value) ** 2 for value in values)
    residual = sum((r["target_y"] - predict(coefficients, r, features)) ** 2 for r in records)
    return 1 - residual / total if total > 0 else 0.0


def _checkpoint_drift(checkpoints: list[dict], coefficients, features) -> dict:
    by_target: dict[str, dict[int, float]] = defaultdict(dict)
    for record in checkpoints:
        by_target[record["target_id"]][record["trial_number"]] = predict(
            coefficients, record, features
        )
    per_target = {
        target: {
            "blocks": {str(block): value for block, value in sorted(blocks.items())},
            "last_minus_first": (blocks[3] - blocks[1] if 1 in blocks and 3 in blocks else None),
        }
        for target, blocks in sorted(by_target.items())
    }
    deltas = [
        abs(v["last_minus_first"]) for v in per_target.values() if v["last_minus_first"] is not None
    ]
    return {
        "per_target": per_target,
        "mean_abs_last_minus_first": fmean(deltas) if deltas else None,
    }


def analyze_session(report: dict) -> dict:
    """Score every candidate for one participant/session; never pools sessions."""
    rows = report["rows"]
    records = presentation_medians(rows)
    calibration = [r for r in records if r["phase"] == "calibration" and r["available"]]
    validation = [r for r in records if r["phase"] == "validation" and r["available"]]
    checkpoints = [r for r in records if r["phase"] == "checkpoint" and r["available"]]
    extract_ms = [row["extract_ms"] for row in rows if row.get("extract_ms") is not None]
    usable_rows = [row for row in rows if row.get("status") == "usable"]
    summary = {
        "participant": report["participant"],
        "session": report["session"],
        "window_image_area": report.get("window_image_area"),
        "rows": len(rows),
        "usable_rows": len(usable_rows),
        "common_frames": sum(r["frames"] for r in records),
        "calibration_presentations": len(calibration),
        "validation_presentations": len(validation),
        "extract_ms": (
            {"median": median(extract_ms), "p95": percentile(extract_ms, 95)}
            if extract_ms
            else None
        ),
    }
    if (
        len(calibration) < MIN_CALIBRATION_PRESENTATIONS
        or len(validation) < MIN_VALIDATION_PRESENTATIONS
    ):
        return {**summary, "valid": False, "candidates": {}}
    x_coefficients = fit(calibration, ("horizontal",), "target_x")
    summary["x"] = (
        None
        if x_coefficients is None
        else score(
            [(r, predict(x_coefficients, r, ("horizontal",))) for r in validation], "target_x"
        )
    )
    candidates = {}
    for name, features in CANDIDATES.items():
        coefficients = fit(calibration, features, "target_y")
        if coefficients is None:
            candidates[name] = {"available": False, "passes": False}
            continue
        metrics = score([(r, predict(coefficients, r, features)) for r in validation], "target_y")
        candidates[name] = {
            "available": True,
            "coefficients": coefficients,
            "calibration_r_squared": _r_squared(calibration, coefficients, features),
            **metrics,
            "passes": passes(metrics),
            "checkpoint_drift": _checkpoint_drift(checkpoints, coefficients, features),
        }
    return {**summary, "valid": True, "candidates": candidates}


def combine(sessions: list[dict]) -> dict:
    """Winner must pass in every session; ties go to the lowest mean y MAE."""
    keys = [(s["participant"], s["session"]) for s in sessions]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate participant/session")
    if len({s["participant"] for s in sessions}) != 1:
        raise ValueError("combine one participant at a time")
    ranking = []
    for name in CANDIDATES:
        results = [s["candidates"].get(name, {}) for s in sessions]
        if all(s["valid"] and r.get("available") for s, r in zip(sessions, results)):
            ranking.append(
                {
                    "candidate": name,
                    "mean_y_mae": fmean(r["mae"] for r in results),
                    "passes_all_sessions": all(r["passes"] for r in results),
                }
            )
    ranking.sort(key=lambda item: item["mean_y_mae"])
    passing = [item for item in ranking if item["passes_all_sessions"]]
    enough = len(sessions) >= 2 and all(s["valid"] for s in sessions)
    return {
        "participant": sessions[0]["participant"],
        "sessions": [s["session"] for s in sessions],
        "winner": passing[0]["candidate"] if enough and passing else None,
        "ranking": ranking,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=argparse.FileType("r", encoding="utf-8"))
    args = parser.parse_args(argv)
    try:
        sessions = [analyze_session(json.load(handle)) for handle in args.datasets]
        output = {"sessions": sessions, "combined": combine(sessions)}
        print(json.dumps(output, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError) as error:
        print(f"Cannot analyze dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
