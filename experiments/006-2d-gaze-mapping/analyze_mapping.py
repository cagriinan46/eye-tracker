"""Fit session-local experimental mappings and evaluate held-out target summaries.

The calibration and validation phases must come from one capture session. Only
calibration targets are used to fit models; validation targets stay held out.
"""

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

MIN_SAMPLES_PER_TARGET = 5
NUMERIC_FIELDS = (
    "timestamp_s",
    "presentation_index",
    "trial_number",
    "target_x",
    "target_y",
    "face_detected",
    "geometry_valid",
    "horizontal_feature",
    "vertical_feature",
    "left_horizontal",
    "right_horizontal",
    "left_vertical_local_axis",
    "right_vertical_local_axis",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "binocular_eye_opening",
    "head_center_y",
    "camera_width",
    "camera_height",
    "window_width",
    "window_height",
)
REQUIRED_FIELDS = (*NUMERIC_FIELDS, "phase", "target_id")


def _finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = set(REQUIRED_FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        rows = []
        for line_number, raw in enumerate(reader, start=2):
            row = {name: float(raw[name]) if raw[name] else None for name in NUMERIC_FIELDS}
            row.update(phase=raw["phase"], target_id=raw["target_id"])
            if row["phase"] not in ("calibration", "validation"):
                raise ValueError(f"{path}:{line_number}: invalid phase")
            if not all(
                _finite(row[name])
                for name in ("timestamp_s", "presentation_index", "target_x", "target_y")
            ):
                raise ValueError(f"{path}:{line_number}: invalid timestamp, target, or index")
            if not (0 <= row["target_x"] <= 1 and 0 <= row["target_y"] <= 1):
                raise ValueError(f"{path}:{line_number}: target outside normalized window")
            if rows and row["timestamp_s"] <= rows[-1]["timestamp_s"]:
                raise ValueError(f"{path}:{line_number}: timestamps must increase")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no sampling rows")
    return rows


def quality_flags(rows):
    """Experimental blink/near-closure rule from Experiment 005, without smoothing."""
    accepted_openings = []
    previous_index = None
    flags = []
    for row in rows:
        index = row["presentation_index"]
        if index != previous_index:
            accepted_openings.clear()
        previous_index = index
        timestamp = row["timestamp_s"]
        accepted_openings = [
            (time, opening) for time, opening in accepted_openings if timestamp - time <= 0.25
        ]
        valid = (
            row.get("face_detected") == 1
            and row.get("geometry_valid") == 1
            and _finite(row.get("horizontal_feature"))
            and _finite(row.get("vertical_feature"))
        )
        if not valid:
            flags.append(False)
            continue
        opening = row.get("binocular_eye_opening")
        left, right = row.get("eyeBlinkLeft"), row.get("eyeBlinkRight")
        obvious_blink = (
            len(accepted_openings) >= 3
            and _finite(opening)
            and _finite(left)
            and _finite(right)
            and max(left, right) >= 0.65
            and opening <= 0.70 * statistics.median(value for _, value in accepted_openings)
        )
        flags.append(not obvious_blink)
        if not obvious_blink and _finite(opening):
            accepted_openings.append((timestamp, opening))
    return flags


def target_summaries(rows, flags):
    grouped = defaultdict(list)
    for row, accepted in zip(rows, flags):
        grouped[int(row["presentation_index"])].append((row, accepted))
    targets = []
    for index, samples in sorted(grouped.items()):
        first = samples[0][0]
        if any(
            (row["phase"], row["target_id"], row["target_x"], row["target_y"])
            != (first["phase"], first["target_id"], first["target_x"], first["target_y"])
            for row, _ in samples
        ):
            raise ValueError(f"presentation {index}: inconsistent target metadata")
        usable = [row for row, accepted in samples if accepted]
        if len(usable) < MIN_SAMPLES_PER_TARGET:
            raise ValueError(
                f"presentation {index} ({first['target_id']}): only {len(usable)} usable "
                f"samples; need {MIN_SAMPLES_PER_TARGET}"
            )
        horizontal = statistics.median(row["horizontal_feature"] for row in usable)
        vertical = statistics.median(row["vertical_feature"] for row in usable)
        targets.append(
            {
                "phase": first["phase"],
                "target_id": first["target_id"],
                "trial_number": int(first["trial_number"]),
                "presentation_index": index,
                "target_x": first["target_x"],
                "target_y": first["target_y"],
                "horizontal_feature": horizontal,
                "vertical_feature": vertical,
                "horizontal_mad": statistics.median(
                    abs(row["horizontal_feature"] - horizontal) for row in usable
                ),
                "vertical_mad": statistics.median(
                    abs(row["vertical_feature"] - vertical) for row in usable
                ),
                "sample_count": len(usable),
                "left_right_horizontal_gap": statistics.median(
                    abs(row["left_horizontal"] - row["right_horizontal"])
                    for row in usable
                    if _finite(row.get("left_horizontal")) and _finite(row.get("right_horizontal"))
                ),
                "left_right_vertical_gap": statistics.median(
                    abs(row["left_vertical_local_axis"] - row["right_vertical_local_axis"])
                    for row in usable
                    if _finite(row.get("left_vertical_local_axis"))
                    and _finite(row.get("right_vertical_local_axis"))
                ),
                "head_center_y_median": statistics.median(
                    row["head_center_y"] for row in usable if _finite(row.get("head_center_y"))
                ),
            }
        )
    return targets


def fit_models(calibration):
    """Fit two intentionally small least-squares candidates from calibration only."""
    if len(calibration) < 3:
        raise ValueError("calibration needs at least three target summaries")
    h = np.asarray([point["horizontal_feature"] for point in calibration], dtype=float)
    v = np.asarray([point["vertical_feature"] for point in calibration], dtype=float)
    x = np.asarray([point["target_x"] for point in calibration], dtype=float)
    y = np.asarray([point["target_y"] for point in calibration], dtype=float)
    independent_x = np.column_stack((h, np.ones(len(h))))
    independent_y = np.column_stack((v, np.ones(len(v))))
    affine = np.column_stack((h, v, np.ones(len(h))))
    if (
        min(
            np.linalg.matrix_rank(independent_x),
            np.linalg.matrix_rank(independent_y),
            np.linalg.matrix_rank(affine),
        )
        < 2
        or np.linalg.matrix_rank(affine) < 3
    ):
        raise ValueError("calibration feature geometry has insufficient rank")
    return {
        "independent_linear": {
            "x": np.linalg.lstsq(independent_x, x, rcond=None)[0].tolist(),
            "y": np.linalg.lstsq(independent_y, y, rcond=None)[0].tolist(),
        },
        "affine_2d": {
            "x": np.linalg.lstsq(affine, x, rcond=None)[0].tolist(),
            "y": np.linalg.lstsq(affine, y, rcond=None)[0].tolist(),
        },
    }


def predict(model, horizontal, vertical):
    x_coefficients, y_coefficients = model["x"], model["y"]
    if len(x_coefficients) == 2:
        return (
            x_coefficients[0] * horizontal + x_coefficients[1],
            y_coefficients[0] * vertical + y_coefficients[1],
        )
    return (
        x_coefficients[0] * horizontal + x_coefficients[1] * vertical + x_coefficients[2],
        y_coefficients[0] * horizontal + y_coefficients[1] * vertical + y_coefficients[2],
    )


def _error_summary(predictions):
    result = {}
    for name in (
        "horizontal_absolute_error",
        "vertical_absolute_error",
        "normalized_error",
        "pixel_equivalent_error",
    ):
        values = [item[name] for item in predictions]
        result[f"mean_{name}"] = statistics.fmean(values)
        result[f"median_{name}"] = statistics.median(values)
        result[f"p95_{name}"] = float(np.percentile(values, 95))
    result["mean_signed_x_bias"] = statistics.fmean(
        item["predicted_x"] - item["target_x"] for item in predictions
    )
    result["mean_signed_y_bias"] = statistics.fmean(
        item["predicted_y"] - item["target_y"] for item in predictions
    )
    return result


def _spatial_ordering(predictions):
    """Descriptive ordering of distinct target IDs, averaged over repeats."""
    grouped = defaultdict(list)
    for index, item in enumerate(predictions):
        grouped[item.get("target_id", str(index))].append(item)
    centers = [
        {
            "x": values[0]["target_x"],
            "y": values[0]["target_y"],
            "pred_x": statistics.median(item["predicted_x"] for item in values),
            "pred_y": statistics.median(item["predicted_y"] for item in values),
        }
        for values in grouped.values()
    ]
    result = {}
    for coordinate, predicted in (("x", "pred_x"), ("y", "pred_y")):
        consistent = total = 0
        for index, left in enumerate(centers):
            for right in centers[index + 1 :]:
                actual_delta = right[coordinate] - left[coordinate]
                if abs(actual_delta) < 0.05:
                    continue
                total += 1
                consistent += (right[predicted] - left[predicted]) * actual_delta > 0
        result[coordinate] = {"consistent_pairs": consistent, "total_pairs": total}
    return result


def evaluate_targets(model, targets, window_width, window_height):
    if not targets:
        raise ValueError("no target summaries to evaluate")
    predictions = []
    for point in targets:
        x, y = predict(model, point["horizontal_feature"], point["vertical_feature"])
        dx, dy = x - point["target_x"], y - point["target_y"]
        predictions.append(
            {
                **point,
                "predicted_x": x,
                "predicted_y": y,
                "horizontal_absolute_error": abs(dx),
                "vertical_absolute_error": abs(dy),
                "normalized_error": math.hypot(dx, dy),
                "pixel_equivalent_error": math.hypot(dx * window_width, dy * window_height),
            }
        )
    return {
        "targets": predictions,
        "summary": _error_summary(predictions),
        "spatial_ordering": _spatial_ordering(predictions),
    }


def analyze_rows(rows):
    seen_validation = False
    for row in rows:
        if row["phase"] == "validation":
            seen_validation = True
        elif seen_validation:
            raise ValueError("validation must occur after calibration in the same session")
    flags = quality_flags(rows)
    targets = target_summaries(rows, flags)
    calibration = [item for item in targets if item["phase"] == "calibration"]
    validation = [item for item in targets if item["phase"] == "validation"]
    if not calibration or not validation:
        raise ValueError("one session must contain calibration and held-out validation targets")
    calibration_positions = {(item["target_x"], item["target_y"]) for item in calibration}
    if any((item["target_x"], item["target_y"]) in calibration_positions for item in validation):
        raise ValueError("validation coordinates must differ from calibration coordinates")
    widths = {item["window_width"] for item in rows}
    heights = {item["window_height"] for item in rows}
    if len(widths) != 1 or len(heights) != 1:
        raise ValueError("window dimensions changed within the session")
    width, height = widths.pop(), heights.pop()
    if not _finite(width) or not _finite(height) or width <= 0 or height <= 0:
        raise ValueError("invalid window dimensions")
    models = fit_models(calibration)
    invalid = sum(
        row.get("face_detected") != 1
        or row.get("geometry_valid") != 1
        or not _finite(row.get("horizontal_feature"))
        or not _finite(row.get("vertical_feature"))
        for row in rows
    )
    return {
        "sampling_frames": len(rows),
        "unusable_tracking_or_geometry": invalid,
        "experimental_blink_rejected": len(rows) - invalid - sum(flags),
        "usable_frames": sum(flags),
        "window_width": width,
        "window_height": height,
        "calibration_targets": len(calibration),
        "validation_trials": len(validation),
        "models": {
            name: {
                "coefficients": model,
                "calibration_fit": evaluate_targets(model, calibration, width, height),
                "held_out_validation": evaluate_targets(model, validation, width, height),
            }
            for name, model in models.items()
        },
    }


def print_report(result):
    print(
        f"Frames={result['sampling_frames']}, usable={result['usable_frames']}, "
        f"tracking/geometry invalid={result['unusable_tracking_or_geometry']}, "
        f"experimental blink rejected={result['experimental_blink_rejected']}"
    )
    print(
        f"Window image area={result['window_width']} x {result['window_height']}; "
        f"calibration targets={result['calibration_targets']}; "
        f"held-out trials={result['validation_trials']}"
    )
    for name, model in result["models"].items():
        print(f"\n{name} coefficients: {model['coefficients']}")
        for phase in ("calibration_fit", "held_out_validation"):
            evaluated = model[phase]
            print(f"  {phase}: {evaluated['summary']}")
            print(f"  spatial ordering: {evaluated['spatial_ordering']}")
            if phase == "held_out_validation":
                for item in evaluated["targets"]:
                    print(
                        f"    {item['target_id']} trial {item['trial_number']}: "
                        f"actual=({item['target_x']:.3f},{item['target_y']:.3f}), "
                        f"predicted=({item['predicted_x']:.3f},{item['predicted_y']:.3f}), "
                        f"|dx|={item['horizontal_absolute_error']:.3f}, "
                        f"|dy|={item['vertical_absolute_error']:.3f}, "
                        f"2D={item['normalized_error']:.3f}, "
                        f"window-px-equiv={item['pixel_equivalent_error']:.1f}"
                    )
    print("Held-out validation is separate; this is not a production gaze tracker.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="One session's derived numerical CSV")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    args = parser.parse_args()
    try:
        result = analyze_rows(read_rows(args.input))
    except (OSError, ValueError) as error:
        print(f"Analysis failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
