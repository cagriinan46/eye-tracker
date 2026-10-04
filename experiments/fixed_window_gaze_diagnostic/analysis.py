"""Raw-feature diagnostics and calibration-only mapping residuals; no outcome gate."""

import argparse
import json
from itertools import combinations
from math import hypot, isclose, isfinite
from pathlib import Path
from statistics import fmean, median

from eye_tracker.gaze.calibration import IndependentLinearMapping
from validation.real_calibration import fit_session_calibration, percentile

from .protocol import (
    CALIBRATION_TARGETS,
    MIN_USABLE_SAMPLES,
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    TARGET_SECONDS,
    configuration,
    schedule,
)

AXES = ("horizontal", "vertical")


def robust(values: list[float]) -> dict:
    if not values:
        return {
            "count": 0,
            "median": None,
            "mad": None,
            "iqr": None,
            "p95_p05": None,
            "p05": None,
            "p25": None,
            "p75": None,
            "p95": None,
        }
    center = median(values)
    return {
        "count": len(values),
        "median": center,
        "mad": median(abs(x - center) for x in values),
        "iqr": percentile(values, 75) - percentile(values, 25),
        "p95_p05": percentile(values, 95) - percentile(values, 5),
        **{f"p{p:02}": percentile(values, p) for p in (5, 25, 75, 95)},
    }


def _delta(first, second):
    return None if first is None or second is None else second - first


def _mean(values):
    return fmean(values) if values else None


def _screen(rows: list[dict], x: float, y: float) -> dict:
    usable = [r for r in rows if r["gaze_status"] == "usable"]
    dx = [r["predicted_x"] - x for r in usable]
    dy = [r["predicted_y"] - y for r in usable]
    errors = [hypot(a, b) for a, b in zip(dx, dy, strict=True)]
    return {
        "usable_count": len(usable),
        "median_predicted_x": median([r["predicted_x"] for r in usable]) if usable else None,
        "median_predicted_y": median([r["predicted_y"] for r in usable]) if usable else None,
        "signed_x_error": median(dx) if dx else None,
        "signed_y_error": median(dy) if dy else None,
        "absolute_x_error": median([abs(d) for d in dx]) if dx else None,
        "absolute_y_error": median([abs(d) for d in dy]) if dy else None,
        "x_mae": _mean([abs(d) for d in dx]),
        "y_mae": _mean([abs(d) for d in dy]),
        "signed_x_bias": _mean(dx),
        "signed_y_bias": _mean(dy),
        "mean_euclidean_error": _mean(errors),
        "median_euclidean_error": median(errors) if errors else None,
        "p95_euclidean_error": percentile(errors, 95) if errors else None,
    }


def summarize_trial(rows: list[dict], target_x: float, target_y: float) -> dict:
    usable = [r for r in rows if r["feature_status"] == "usable"]
    features, temporal = {}, {}
    for axis in AXES:
        key = f"{axis}_feature"
        features[axis] = robust([r[key] for r in usable])
        first = robust([r[key] for r in usable if r["trial_relative_seconds"] < 1.5])
        second = robust([r[key] for r in usable if r["trial_relative_seconds"] >= 1.5])
        temporal[axis] = {
            "first_half": first,
            "second_half": second,
            "half_shift": _delta(first["median"], second["median"]),
        }
    reasons = {}
    for row in rows:
        if row["feature_status"] != "usable":
            reason = row["unavailable_reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "sample_count": len(rows),
        "usable_feature_count": len(usable),
        "unavailable_reasons": reasons,
        "features": features,
        "temporal": temporal,
        "screen": _screen(rows, target_x, target_y),
    }


def _validate_rows(rows, start, end, mapping=None, onset=0, identity=None):
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing sample attempts")
    previous = -1.0
    for row in rows:
        if identity and any(row[key] != value for key, value in identity.items()):
            raise ValueError("sample/presentation identity mismatch")
        t = row["trial_relative_seconds"]
        if not isfinite(t) or not start - 1e-9 <= t < end or t < previous:
            raise ValueError("unordered or out-of-window samples")
        previous = t
        stamp = row["monotonic_timestamp_seconds"]
        if not isfinite(stamp) or not isclose(stamp - onset, t, abs_tol=1e-8, rel_tol=0):
            raise ValueError("sample timestamp does not match presentation onset")
        if row["feature_status"] not in ("usable", "unavailable"):
            raise ValueError("invalid feature status")
        if row["gaze_status"] not in ("usable", "unavailable", "not_calibrated"):
            raise ValueError("invalid gaze status")
        if row["feature_status"] == "usable":
            if not all(
                isinstance(row[f"{a}_feature"], (int, float)) and isfinite(row[f"{a}_feature"])
                for a in AXES
            ):
                raise ValueError("missing or nonfinite production features")
        elif row["unavailable_reason"] is None or any(
            row[f"{a}_feature"] is not None for a in AXES
        ):
            raise ValueError("unavailable observation must have reason and no features")
        if row["gaze_status"] == "usable":
            if row["feature_status"] != "usable" or mapping is None:
                raise ValueError("gaze estimate without calibrated features")
            expected = mapping.predict(row["horizontal_feature"], row["vertical_feature"])
            if not all(
                isinstance(row[k], (int, float))
                and isfinite(row[k])
                and isclose(row[k], v, abs_tol=1e-10, rel_tol=1e-10)
                for k, v in zip(("predicted_x", "predicted_y"), expected, strict=True)
            ):
                raise ValueError("prediction does not match the production calibration")
        elif any(row[k] is not None for k in ("predicted_x", "predicted_y")):
            raise ValueError("unavailable prediction must not contain coordinates")


def validate_capture(report: dict) -> IndependentLinearMapping:
    """Reject protocol/order/window mismatches; never reject for poor gaze accuracy."""
    try:
        for key, value in configuration().items():
            if report[key] != value:
                raise ValueError(f"incompatible protocol field: {key}")
        if (
            report["status"] != "completed"
            or report["ready_screen_used"] is not True
            or not report["participant"]
            or not report["session"]
            or report["camera_index"] < 0
            or len(report["camera_resolution"]) != 2
            or min(report["camera_resolution"]) <= 0
        ):
            raise ValueError("incomplete capture metadata")
        for key in ("failed_camera_reads", "no_face_observations"):
            if not isinstance(report[key], int) or report[key] < 0:
                raise ValueError("missing capture counts")
        calibration = report["calibration_presentations"]
        if len(calibration) != 9 or len(report["trials"]) != 27:
            raise ValueError("incomplete presentation schedule")
        observations = []
        previous_end = -float("inf")
        for order, (item, target) in enumerate(
            zip(calibration, CALIBRATION_TARGETS, strict=True), 1
        ):
            if (item["order"], item["target_id"], item["target_x"], item["target_y"]) != (
                order,
                target.name,
                target.x,
                target.y,
            ):
                raise ValueError("calibration target/order mismatch")
            if (
                item["end_monotonic_seconds"] - item["onset_monotonic_seconds"]
                < SETTLE_SECONDS + SAMPLE_SECONDS
            ):
                raise ValueError("short calibration presentation")
            if (
                not isfinite(item["onset_monotonic_seconds"])
                or not isfinite(item["end_monotonic_seconds"])
                or item["onset_monotonic_seconds"] < previous_end
            ):
                raise ValueError("unordered/nonfinite calibration timestamps")
            previous_end = item["end_monotonic_seconds"]
            _validate_rows(
                item["samples"],
                SETTLE_SECONDS,
                SETTLE_SECONDS + SAMPLE_SECONDS,
                onset=item["onset_monotonic_seconds"],
                identity={
                    "target_id": target.name,
                    "target_x": target.x,
                    "target_y": target.y,
                    "block": 0,
                },
            )
            usable = [r for r in item["samples"] if r["feature_status"] == "usable"]
            if len(usable) < MIN_USABLE_SAMPLES:
                raise ValueError("insufficient usable calibration observations")
            observations.append(
                (target, [(r["horizontal_feature"], r["vertical_feature"]) for r in usable])
            )
        fitted, _ = fit_session_calibration(observations)
        coefficients = report["mapping_coefficients"]
        if not all(
            isfinite(coefficients[k])
            and isclose(coefficients[k], getattr(fitted, k), abs_tol=1e-10, rel_tol=1e-10)
            for k in ("x_slope", "x_intercept", "y_slope", "y_intercept")
        ):
            raise ValueError("mapping was not fitted from ordinary calibration only")
        for item, trial in zip(report["trials"], schedule(), strict=True):
            if any(item[k] != v for k, v in trial.identity().items()):
                raise ValueError("validation target/block/order/cue mismatch")
            onset, end = item["onset_monotonic_seconds"], item["end_monotonic_seconds"]
            if (
                end - onset < TARGET_SECONDS - 1e-9
                or onset - item["cue_onset_monotonic_seconds"]
                < configuration()["cue_seconds"] - 1e-9
            ):
                raise ValueError("short validation window or cue")
            cue = item["cue_onset_monotonic_seconds"]
            if not all(isfinite(v) for v in (cue, onset, end)) or cue < previous_end:
                raise ValueError("unordered/nonfinite validation timestamps")
            previous_end = end
            _validate_rows(item["samples"], 0, TARGET_SECONDS, fitted, onset, trial.identity())
        return fitted
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError(f"missing/malformed capture field: {error}") from error


def _feature_levels(calibration, trials, axis):
    coordinate = "target_x" if axis == "horizontal" else "target_y"
    key = f"{axis}_feature"
    cal_levels = [
        median(
            [
                median([r[key] for r in t["samples"] if r["feature_status"] == "usable"])
                for t in calibration
                if t[coordinate] == level
            ]
        )
        for level in (0.2, 0.5, 0.8)
    ]
    cal_steps = [cal_levels[i + 1] - cal_levels[i] for i in (0, 1)]
    direction = (
        1 if all(x > 0 for x in cal_steps) else -1 if all(x < 0 for x in cal_steps) else None
    )
    result = []
    for block in (1, 2, 3, "pooled"):
        subset = [t for t in trials if block == "pooled" or t["block"] == block]
        # Equal weight per presentation: each contributes its independently saved raw median.
        levels = [
            robust(
                [
                    v
                    for t in subset
                    if t[coordinate] == level
                    if (v := t["summary"]["features"][axis]["median"]) is not None
                ]
            )
            for level in (0.2, 0.5, 0.8)
        ]
        steps = [_delta(levels[i]["median"], levels[i + 1]["median"]) for i in (0, 1)]
        separation = min(abs(s) for s in steps) if all(s is not None for s in steps) else None
        ordered = (
            all(s * direction > 0 for s in steps)
            if direction is not None and all(s is not None for s in steps)
            else None
        )
        spreads = [t["summary"]["features"][axis]["iqr"] for t in subset]
        result.append(
            {
                "block": block,
                "levels": levels,
                "sample_distributions": [
                    robust(
                        [
                            r[key]
                            for t in subset
                            if t[coordinate] == level
                            for r in t["samples"]
                            if r["feature_status"] == "usable"
                        ]
                    )
                    for level in (0.2, 0.5, 0.8)
                ],
                "signed_adjacent_separations": steps,
                "minimum_absolute_separation": separation,
                "ordered": ordered,
                "target_spread_ratios": [
                    {
                        "target_id": t["target_id"],
                        "block": t["block"],
                        "iqr_over_minimum_separation": spread / separation
                        if separation and spread is not None
                        else None,
                    }
                    for t, spread in zip(subset, spreads, strict=True)
                ],
            }
        )
    return {
        "level_coordinates": [0.2, 0.5, 0.8],
        "calibration_level_medians": cal_levels,
        "calibration_direction": direction,
        "calibration_ordered": direction is not None,
        "validation": result,
    }


def _residual_group(trials):
    # Sample-weighted errors; report per-trial medians separately to expose weighting.
    rows = [
        {
            **r,
            "predicted_x": r["predicted_x"] - t["target_x"],
            "predicted_y": r["predicted_y"] - t["target_y"],
        }
        for t in trials
        for r in t["samples"]
        if r["gaze_status"] == "usable"
    ]
    result = _screen(rows, 0, 0)
    # These coordinates are residuals, not actual predicted screen positions.
    result.pop("median_predicted_x")
    result.pop("median_predicted_y")
    return result


def _group(trials, key, summary):
    return {
        str(value): summary([t for t in trials if t[key] == value])
        for value in sorted({t[key] for t in trials})
    }


def analyze_session(report: dict) -> dict:
    mapping = validate_capture(report)
    trials = [
        {**t, "summary": summarize_trial(t["samples"], t["target_x"], t["target_y"])}
        for t in report["trials"]
    ]
    # Secondary predeclared settled interval, leaving the complete primary window intact.
    settled = [
        {**t, "samples": [r for r in t["samples"] if r["trial_relative_seconds"] >= 0.8]}
        for t in trials
    ]
    settled = [
        {**t, "summary": summarize_trial(t["samples"], t["target_x"], t["target_y"])}
        for t in settled
    ]
    transfer, repeatability = [], []
    for cal in report["calibration_presentations"]:
        subset = [
            t
            for t in trials
            if (t["target_x"], t["target_y"]) == (cal["target_x"], cal["target_y"])
        ]
        cal_summary = summarize_trial(cal["samples"], cal["target_x"], cal["target_y"])
        shift = {
            "target_id": subset[0]["target_id"],
            "target_x": cal["target_x"],
            "target_y": cal["target_y"],
        }
        repeated = {
            "target_id": subset[0]["target_id"],
            "target_x": cal["target_x"],
            "target_y": cal["target_y"],
        }
        for axis in AXES:
            reference = cal_summary["features"][axis]["median"]
            medians = [t["summary"]["features"][axis]["median"] for t in subset]
            center = (
                median([v for v in medians if v is not None])
                if any(v is not None for v in medians)
                else None
            )
            signed = _delta(reference, center)
            shift[axis] = {
                "calibration_median": reference,
                "validation_median": center,
                "signed_shift": signed,
                "absolute_shift": abs(signed) if signed is not None else None,
                "by_block": [
                    {"block": t["block"], "median": value, "signed_shift": _delta(reference, value)}
                    for t, value in zip(subset, medians, strict=True)
                ],
            }
            deltas = [_delta(a, b) for a, b in combinations(medians, 2)]
            valid = [d for d in deltas if d is not None]
            adjacent = [_delta(medians[i], medians[i + 1]) for i in (0, 1)]
            slope = mapping.x_slope if axis == "horizontal" else mapping.y_slope
            repeated[axis] = {
                "block_medians": medians,
                "pairwise_signed_shifts": deltas,
                "maximum_shift": max(abs(d) for d in valid) if valid else None,
                "block_3_minus_1": _delta(medians[0], medians[2]),
                "directional": all(d > 0 for d in adjacent) or all(d < 0 for d in adjacent)
                if all(d is not None for d in adjacent)
                else None,
                "mapped_pairwise_shifts": [d * slope if d is not None else None for d in deltas],
            }
        transfer.append(shift)
        repeatability.append(repeated)

    def shift_summary(items):
        return {
            axis: {
                "signed_shift": robust(
                    [t[axis]["signed_shift"] for t in items if t[axis]["signed_shift"] is not None]
                ),
                "absolute_shift": robust(
                    [
                        t[axis]["absolute_shift"]
                        for t in items
                        if t[axis]["absolute_shift"] is not None
                    ]
                ),
            }
            for axis in AXES
        }

    calibration_predictions = []
    for item in report["calibration_presentations"]:
        rows = []
        for row in item["samples"]:
            if row["feature_status"] == "usable":
                x, y = mapping.predict(row["horizontal_feature"], row["vertical_feature"])
                rows.append({**row, "gaze_status": "usable", "predicted_x": x, "predicted_y": y})
        calibration_predictions.append(
            {
                **item,
                "samples": rows,
                "summary": summarize_trial(rows, item["target_x"], item["target_y"]),
            }
        )
    all_rows = [r for t in trials for r in t["samples"]]
    usable = sum(r["gaze_status"] == "usable" for r in all_rows)
    return {
        "participant": report["participant"],
        "session": report["session"],
        "mapping_coefficients": report["mapping_coefficients"],
        "trials": [{k: v for k, v in t.items() if k != "samples"} for t in trials],
        "calibration": {
            "presentations": [
                {k: v for k, v in item.items() if k != "samples"}
                for item in calibration_predictions
            ],
            "mapping_residuals": _residual_group(calibration_predictions),
        },
        "feature_levels": {
            a: _feature_levels(report["calibration_presentations"], trials, a) for a in AXES
        },
        "transfer": transfer,
        "transfer_summary": shift_summary(transfer),
        "transfer_by_row": _group(transfer, "target_y", shift_summary),
        "transfer_by_column": _group(transfer, "target_x", shift_summary),
        "repeatability": repeatability,
        "mapping_residuals": {
            "all": _residual_group(trials),
            "by_row": _group(trials, "target_y", _residual_group),
            "by_column": _group(trials, "target_x", _residual_group),
            "by_target": _group(trials, "target_id", _residual_group),
            "by_block": _group(trials, "block", _residual_group),
        },
        "secondary_settled_interval": {
            "start_seconds": 0.8,
            "end_seconds": 3.0,
            "feature_levels": {
                a: _feature_levels(report["calibration_presentations"], settled, a) for a in AXES
            },
            "mapping_residuals": _residual_group(settled),
        },
        "availability": {
            "attempts": len(all_rows),
            "usable": usable,
            "unavailable": len(all_rows) - usable,
            "usable_fraction": usable / len(all_rows),
            "failed_camera_reads": report["failed_camera_reads"],
            "no_face_observations": report["no_face_observations"],
        },
        "signal_limitations": [
            t["trial_order"] for t in trials if t["summary"]["usable_feature_count"] < 2
        ],
    }


def compare_sessions(reports: list[dict]) -> dict:
    if (
        len(reports) != 2
        or reports[0]["participant"] != reports[1]["participant"]
        or reports[0]["session"] == reports[1]["session"]
    ):
        raise ValueError("comparison requires two distinct sessions of the same participant")
    sessions = [analyze_session(r) for r in reports]
    differences = []
    for first, second in zip(sessions[0]["transfer"], sessions[1]["transfer"], strict=True):
        differences.append(
            {
                "target_id": first["target_id"],
                **{
                    f"{axis}_median_delta": _delta(
                        first[axis]["validation_median"], second[axis]["validation_median"]
                    )
                    for axis in AXES
                },
            }
        )
    return {
        "sessions": sessions,
        "target_differences": differences,
        "note": "Raw session feature differences are descriptive; session geometry/scaling may differ.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if len(args.captures) not in (1, 2):
        parser.error("supply one capture or two sessions to compare")
    reports = [json.loads(path.read_text()) for path in args.captures]
    result = analyze_session(reports[0]) if len(reports) == 1 else compare_sessions(reports)
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
            parser.error("analysis output must stay inside ignored .venv")
        with args.output.open("x") as destination:
            destination.write(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
