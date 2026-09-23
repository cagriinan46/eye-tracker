"""Compare causal stabilization of Experiment 004's binocular local-axis signal.

Only derived numerical CSV data is read. Target labels are used for evaluation,
never to filter, smooth, normalize, or select a frame.
"""

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

LABELS = ("UP", "CENTER", "DOWN")
METHODS = ("raw", "median_120", "median_240", "mean_120", "ewma_045", "blink_median_120")
DEFAULT_INPUTS = tuple(Path(f".venv/vertical-gaze-stable{suffix}.csv") for suffix in ("", "2", "3"))
REQUIRED = (
    "timestamp_s",
    "target_label",
    "trial_number",
    "face_detected",
    "geometry_valid",
    "binocular_vertical_local_axis",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "binocular_eye_opening",
)


def number(value):
    if value is None or value == "":
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        missing = set(REQUIRED) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        rows = []
        for line_number, raw in enumerate(reader, start=2):
            row = {key: number(raw[key]) for key in REQUIRED if key != "target_label"}
            row["target_label"] = raw["target_label"]
            if row["timestamp_s"] is None or row["target_label"] not in LABELS:
                raise ValueError(f"{path}:{line_number}: invalid timestamp or label")
            if row["trial_number"] is None or row["trial_number"] < 1:
                raise ValueError(f"{path}:{line_number}: invalid trial number")
            if rows and row["timestamp_s"] <= rows[-1]["timestamp_s"]:
                raise ValueError(f"{path}:{line_number}: timestamps must increase")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no samples")
    return rows


def sampling_interval(rows):
    """Median observed sample interval, excluding unsampled trial transitions."""
    intervals = [
        current["timestamp_s"] - previous["timestamp_s"]
        for previous, current in zip(rows, rows[1:])
        if 0 < current["timestamp_s"] - previous["timestamp_s"] <= 0.5
    ]
    if not intervals:
        raise ValueError("not enough within-trial timestamps to estimate sample rate")
    return statistics.median(intervals)


def stabilize(rows, method):
    """Emit one causal result per row; None denotes unavailable or rejected data."""
    if method not in METHODS:
        raise ValueError(f"unknown method: {method}")
    window_s = 0.24 if method == "median_240" else 0.12
    values = []
    openings = []
    output = []
    previous_time = None
    ewma = None
    for row in rows:
        timestamp = row["timestamp_s"]
        if previous_time is not None and timestamp - previous_time > 0.5:
            values.clear()
            openings.clear()
            ewma = None
        previous_time = timestamp
        values = [(t, value) for t, value in values if timestamp - t <= window_s]
        openings = [(t, value) for t, value in openings if timestamp - t <= 0.25]
        value = row.get("binocular_vertical_local_axis")
        valid = row.get("face_detected") == 1 and row.get("geometry_valid") == 1
        if not valid or value is None or not math.isfinite(value):
            output.append(None)
            continue
        if method == "raw":
            output.append(value)
            continue

        opening = row.get("binocular_eye_opening")
        blink_left = row.get("eyeBlinkLeft")
        blink_right = row.get("eyeBlinkRight")
        if method == "blink_median_120" and len(openings) >= 3:
            prior_opening = statistics.median(item for _, item in openings)
            obvious_blink = (
                opening is not None
                and blink_left is not None
                and blink_right is not None
                and max(blink_left, blink_right) >= 0.65
                and opening <= 0.70 * prior_opening
            )
            if obvious_blink:
                output.append(None)
                continue

        values.append((timestamp, value))
        if opening is not None:
            openings.append((timestamp, opening))
        recent = [item for _, item in values]
        if method.startswith("median") or method.startswith("blink_median"):
            result = statistics.median(recent)
        elif method.startswith("mean"):
            result = statistics.fmean(recent)
        else:
            ewma = value if ewma is None else 0.45 * value + 0.55 * ewma
            result = ewma
        output.append(result)
    return output


def describe(values):
    if not values:
        return None
    median = statistics.median(values)
    ordered = sorted(values)
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "median": median,
        "mad": statistics.median(abs(value - median) for value in values),
        "min": ordered[0],
        "max": ordered[-1],
        "p10": ordered[int(0.10 * (len(ordered) - 1))],
        "p90": ordered[int(0.90 * (len(ordered) - 1))],
    }


def successive_deltas(rows, output):
    return [
        abs(current_value - previous_value)
        for previous_row, current_row, previous_value, current_value in zip(
            rows, rows[1:], output, output[1:]
        )
        if current_row["timestamp_s"] - previous_row["timestamp_s"] <= 0.5
        and previous_value is not None
        and current_value is not None
    ]


def count_jumps(rows, output, cutoff):
    """Count large adjacent changes within sampled segments (evaluation only)."""
    return sum(delta > cutoff for delta in successive_deltas(rows, output))


def summarize(rows, output):
    by_label = {}
    by_trial = {}
    for label in LABELS:
        values = [
            value
            for row, value in zip(rows, output)
            if row["target_label"] == label and value is not None
        ]
        by_label[label] = describe(values)
        by_trial[label] = {}
        for trial in sorted(
            {int(row["trial_number"]) for row in rows if row["target_label"] == label}
        ):
            trial_values = [
                value
                for row, value in zip(rows, output)
                if row["target_label"] == label
                and row["trial_number"] == trial
                and value is not None
            ]
            by_trial[label][trial] = describe(trial_values)
    comparisons = {}
    for first, second in (("UP", "CENTER"), ("CENTER", "DOWN"), ("UP", "DOWN")):
        a, b = by_label[first], by_label[second]
        comparisons[f"{first}-{second}"] = (
            {
                "mean_delta": a["mean"] - b["mean"],
                "raw_range_overlap": a["min"] <= b["max"] and b["min"] <= a["max"],
                "p10_p90_overlap": a["p10"] <= b["p90"] and b["p10"] <= a["p90"],
            }
            if a and b
            else None
        )
    trial_spans = {
        label: {
            "mean_span": max(item["mean"] for item in trials.values() if item)
            - min(item["mean"] for item in trials.values() if item),
            "median_span": max(item["median"] for item in trials.values() if item)
            - min(item["median"] for item in trials.values() if item),
        }
        for label, trials in by_trial.items()
        if any(trials.values())
    }
    return {
        "available": sum(value is not None for value in output),
        "excluded": sum(value is None for value in output),
        "labels": by_label,
        "trials": by_trial,
        "trial_spans": trial_spans,
        "comparisons": comparisons,
    }


def analyze(path):
    rows = read_csv(path)
    interval = sampling_interval(rows)
    summaries = {method: summarize(rows, stabilize(rows, method)) for method in METHODS}
    raw = stabilize(rows, "raw")
    blink = stabilize(rows, "blink_median_120")
    raw_deltas = sorted(successive_deltas(rows, raw))
    jump_cutoff = raw_deltas[int(0.95 * (len(raw_deltas) - 1))] if raw_deltas else None
    if jump_cutoff is not None:
        for method, summary in summaries.items():
            summary["jumps_above_raw_p95"] = count_jumps(rows, stabilize(rows, method), jump_cutoff)
    rejected = [
        index
        for index, (before, after) in enumerate(zip(raw, blink))
        if before is not None and after is None
    ]
    return {
        "input": str(path),
        "rows": len(rows),
        "interval_ms": interval * 1000,
        "observed_fps": 1 / interval,
        "window_frames_120": max(1, round(0.12 / interval)),
        "window_frames_240": max(1, round(0.24 / interval)),
        "face_or_geometry_unavailable": len(rows) - summaries["raw"]["available"],
        "blink_rejected": len(rejected),
        "raw_jump_p95": jump_cutoff,
        "blink_rejected_by_label": {
            label: sum(rows[index]["target_label"] == label for index in rejected)
            for label in LABELS
        },
        "methods": summaries,
    }


def print_report(runs):
    for run in runs:
        print(f"\n{run['input']}: {run['rows']} rows, {run['observed_fps']:.2f} FPS")
        print(
            f"  120/240 ms ~ {run['window_frames_120']}/{run['window_frames_240']} frames; "
            f"invalid={run['face_or_geometry_unavailable']}; blink-rejected={run['blink_rejected']}"
        )
        for method, result in run["methods"].items():
            print(
                f"  {method}: available={result['available']}, excluded={result['excluded']}, "
                f"jumps above raw p95={result.get('jumps_above_raw_p95', 'N/A')}"
            )
            for label in LABELS:
                item = result["labels"][label]
                if item:
                    print(
                        f"    {label}: n={item['count']} mean={item['mean']:+.5f} "
                        f"std={item['std']:.5f} median={item['median']:+.5f} "
                        f"MAD={item['mad']:.5f}"
                    )
                    print(
                        "      trial means/medians: "
                        + ", ".join(
                            f"{trial}:{stats['mean']:+.5f}/{stats['median']:+.5f}"
                            for trial, stats in result["trials"][label].items()
                            if stats
                        )
                    )
                    spans = result["trial_spans"][label]
                    print(
                        f"      trial mean span={spans['mean_span']:.5f}; "
                        f"median span={spans['median_span']:.5f}"
                    )
            for pair, comparison in result["comparisons"].items():
                if comparison:
                    print(
                        f"    {pair}: delta={comparison['mean_delta']:+.5f}, "
                        f"range_overlap={comparison['raw_range_overlap']}, "
                        f"p10-p90_overlap={comparison['p10_p90_overlap']}"
                    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary")
    args = parser.parse_args()
    try:
        runs = [analyze(path) for path in args.inputs]
    except (OSError, ValueError) as error:
        print(f"Analysis failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(runs, indent=2))
    else:
        print_report(runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
