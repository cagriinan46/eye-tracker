"""Classify each session's vertical failure with the rule frozen in README.md (Issue #75).

Inputs are Issue #44 collector reports. Only derived numerical rows are read; the
classification thresholds below are preregistered and must not be changed after
the Fatih A/B sessions are collected.
"""

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from statistics import fmean, median

from experiments.vertical_collapse_diagnostics.analysis import summarize_session
from validation.real_calibration import MIN_USABLE_SAMPLES

# Preregistered on 2026-10-08 before the Fatih A/B sessions; do not tune.
CALIBRATION_R2_MIN = 0.80
CALIBRATION_COLUMN_PAIRS_MIN = 8  # of 9 same-column pairs
HELD_OUT_PAIRS_MIN = 17  # of 21 distinct-row target pairs
DRIFT_SHIFT_MIN = 0.10  # normalized screen-y units
ORDERING_MIN_DELTA = 0.05  # same distinct-target rule as the validation harness

SIGNAL = "SIGNAL"
INSTABILITY = "INSTABILITY"
DRIFT = "DRIFT"
NOT_REPRODUCED = "NOT_REPRODUCED"
MIXED = "MIXED"


def fit_line(points: list[tuple[float, float]]) -> dict:
    """Ordinary least squares of feature on target coordinate, with R²."""
    if len(points) < 3:
        raise ValueError("at least three points are required for a line fit")
    coordinates = [point[0] for point in points]
    values = [point[1] for point in points]
    mean_coordinate, mean_value = fmean(coordinates), fmean(values)
    spread = sum((item - mean_coordinate) ** 2 for item in coordinates)
    if spread == 0:
        raise ValueError("target coordinates must vary")
    slope = (
        sum((coordinate - mean_coordinate) * (value - mean_value) for coordinate, value in points)
        / spread
    )
    intercept = mean_value - slope * mean_coordinate
    total = sum((value - mean_value) ** 2 for value in values)
    residual = sum((value - intercept - slope * coordinate) ** 2 for coordinate, value in points)
    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": 1 - residual / total if total > 0 else 0.0,
    }


def _ordered(sign: float, first: tuple[float, float], second: tuple[float, float]) -> bool:
    return sign * (second[1] - first[1]) * (second[0] - first[0]) > 0


def column_ordering(targets: list[dict], sign: float) -> dict:
    """Count same-column calibration pairs ordered in the fitted feature direction."""
    columns: dict[float, list[tuple[float, float]]] = defaultdict(list)
    for target in targets:
        columns[target["target_x"]].append((target["target_y"], target["value"]))
    consistent = total = 0
    for points in columns.values():
        for first, second in combinations(points, 2):
            if first[0] == second[0]:
                continue
            total += 1
            consistent += _ordered(sign, first, second)
    return {"consistent_pairs": consistent, "total_pairs": total}


def _calibration_targets(rows: list[dict], key: str) -> list[dict] | None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["phase"] == "calibration" and row["status"] == "usable":
            groups[row["target_id"]].append(row)
    targets = []
    for target_rows in groups.values():
        values = [row[key] for row in target_rows if row.get(key) is not None]
        if len(values) < MIN_USABLE_SAMPLES:
            return None
        first = target_rows[0]
        targets.append(
            {"target_x": first["target_x"], "target_y": first["target_y"], "value": median(values)}
        )
    return targets


def _feature_summary(targets: list[dict] | None) -> dict | None:
    if targets is None:
        return None
    fit = fit_line([(item["target_y"], item["value"]) for item in targets])
    sign = 1.0 if fit["slope"] > 0 else -1.0
    return {**fit, "column_ordering": column_ordering(targets, sign)}


def _held_out_trials(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        if row["phase"] == "validation" and row["status"] == "usable":
            groups[(row["target_id"], row["trial_number"])].append(row)
    trials = []
    for (target_id, trial_number), trial_rows in sorted(groups.items()):
        if len(trial_rows) < MIN_USABLE_SAMPLES:
            raise ValueError(f"{target_id}/{trial_number}: need five usable held-out rows")
        trials.append(
            {
                "target_id": target_id,
                "trial_number": trial_number,
                "target_y": trial_rows[0]["target_y"],
                "vertical": median(row["vertical"] for row in trial_rows),
            }
        )
    if not trials:
        raise ValueError("held-out rows are required")
    return trials


def _held_out_ordering(trials: list[dict], sign: float) -> dict:
    by_target: dict[str, list[dict]] = defaultdict(list)
    for trial in trials:
        by_target[trial["target_id"]].append(trial)
    points = [
        (items[0]["target_y"], median(item["vertical"] for item in items))
        for items in by_target.values()
    ]
    consistent = total = 0
    for first, second in combinations(points, 2):
        if abs(second[0] - first[0]) < ORDERING_MIN_DELTA:
            continue
        total += 1
        consistent += _ordered(sign, first, second)
    return {"consistent_pairs": consistent, "total_pairs": total}


def _median_of(rows: list[dict], phase: str, key: str) -> float | None:
    values = [
        row[key]
        for row in rows
        if row["phase"] == phase and row["status"] == "usable" and row.get(key) is not None
    ]
    return median(values) if values else None


def classify(calibration: dict, held_out_ordering: dict, shift_y: float) -> str:
    """Apply the preregistered rule in its fixed precedence order."""
    if (
        calibration["slope"] == 0
        or calibration["r_squared"] < CALIBRATION_R2_MIN
        or calibration["column_ordering"]["consistent_pairs"] < CALIBRATION_COLUMN_PAIRS_MIN
    ):
        return SIGNAL
    if held_out_ordering["consistent_pairs"] < HELD_OUT_PAIRS_MIN:
        return INSTABILITY
    if abs(shift_y) > DRIFT_SHIFT_MIN:
        return DRIFT
    return NOT_REPRODUCED


def analyze_session(report: dict) -> dict:
    """Classify one participant/session; never pools sessions or people."""
    summary = summarize_session(report)
    rows = report["rows"]
    calibration_targets = [
        {
            "target_x": sample["target_x"],
            "target_y": sample["target_y"],
            "value": sample["vertical_feature"],
        }
        for sample in report["calibration_samples"]
    ]
    calibration = _feature_summary(calibration_targets)
    sign = 1.0 if calibration["slope"] > 0 else -1.0
    trials = _held_out_trials(rows)
    ordering = _held_out_ordering(trials, sign)
    shift_y = (
        fmean(
            (
                trial["vertical"]
                - calibration["intercept"]
                - calibration["slope"] * trial["target_y"]
            )
            / calibration["slope"]
            for trial in trials
        )
        if calibration["slope"] != 0
        else None
    )
    category = SIGNAL if shift_y is None else classify(calibration, ordering, shift_y)
    head_calibration = _median_of(rows, "calibration", "head_center_y")
    head_validation = _median_of(rows, "validation", "head_center_y")
    return {
        "participant": summary["participant"],
        "session": summary["session"],
        "category": category,
        "calibration_vertical": calibration,
        "held_out_feature_ordering": ordering,
        "held_out_shift_y": shift_y,
        "held_out_prediction_metrics": summary["held_out"],
        "descriptive": {
            "left_vertical": _feature_summary(_calibration_targets(rows, "left_vertical")),
            "right_vertical": _feature_summary(_calibration_targets(rows, "right_vertical")),
            "eye_opening": _feature_summary(_calibration_targets(rows, "binocular_eye_opening")),
            "head_center_y_validation_minus_calibration": (
                None
                if head_calibration is None or head_validation is None
                else head_validation - head_calibration
            ),
            "within_target_associations": summary["within_target_associations"],
        },
    }


def combine(sessions: list[dict]) -> dict:
    """A category is conclusive only when every session of one participant agrees."""
    keys = [(item["participant"], item["session"]) for item in sessions]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate participant/session")
    if len({item["participant"] for item in sessions}) != 1:
        raise ValueError("combine one participant at a time")
    categories = [item["category"] for item in sessions]
    overall = categories[0] if len(sessions) >= 2 and len(set(categories)) == 1 else MIXED
    return {"participant": sessions[0]["participant"], "categories": categories, "overall": overall}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=Path, help="Issue #44 collector JSON")
    args = parser.parse_args(argv)
    try:
        sessions = [
            analyze_session(json.loads(path.read_text(encoding="utf-8"))) for path in args.datasets
        ]
        print(json.dumps({"sessions": sessions, "combined": combine(sessions)}, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cannot classify diagnostic dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
