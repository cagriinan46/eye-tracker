"""Hardware-free, calibration/held-out-separated comparison of two y mappings."""

from collections import defaultdict
from math import isclose, isfinite
from statistics import fmean

from experiments.vertical_error_decomposition.analysis import (
    calibration_from_rows,
    verify_recorded_mapping,
)
from experiments.vertical_mapping_evaluation.mapping import CombinedMapping, fit_row_anchor_mapping
from eye_tracker.gaze.calibration import CalibrationSample, GazeMapping
from eye_tracker.gaze.estimator import GazeEstimate, estimate_gaze
from validation.real_calibration import (
    MIN_USABLE_SAMPLES,
    VALIDATION_TARGETS,
    TrialEstimate,
    summarize_held_out,
)


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def summarize_calibration(samples: tuple[CalibrationSample, ...], mapping: GazeMapping) -> dict:
    """Signed residual is predicted minus target, matching held-out signed bias."""
    if not samples:
        raise ValueError("calibration samples are required")
    targets = []
    grouped: dict[float, list[dict]] = defaultdict(list)
    for sample in samples:
        if not isinstance(sample, CalibrationSample):
            raise ValueError("expected CalibrationSample")
        predicted_x, predicted_y = mapping.predict(
            sample.horizontal_feature, sample.vertical_feature
        )
        if not (isfinite(predicted_x) and isfinite(predicted_y)):
            raise ValueError("calibration prediction must be finite")
        record = {
            "target_x": sample.target_x,
            "target_y": sample.target_y,
            "vertical_feature": sample.vertical_feature,
            "predicted_y": predicted_y,
            "signed_residual": predicted_y - sample.target_y,
        }
        targets.append(record)
        grouped[sample.target_y].append(record)
    centers = [item for item in targets if (item["target_x"], item["target_y"]) == (0.5, 0.5)]
    if len(centers) != 1:
        raise ValueError("exactly one calibration CENTER target is required")
    rows = [
        {
            "target_y": y,
            "predicted_y_mean": fmean(item["predicted_y"] for item in group),
            "signed_residual_mean": fmean(item["signed_residual"] for item in group),
            "mae": fmean(abs(item["signed_residual"]) for item in group),
        }
        for y, group in sorted(grouped.items())
    ]
    return {
        "targets": targets,
        "rows": rows,
        "mae": fmean(abs(item["signed_residual"]) for item in targets),
        "center_signed_residual": centers[0]["signed_residual"],
    }


def evaluate_held_out(
    rows: list[dict], mapping: GazeMapping, window_width: int, window_height: int
) -> dict:
    """Replay untouched validation features through one fitted candidate."""
    by_id = {target.name: target for target in VALIDATION_TARGETS}
    expected = {(name, trial) for name in by_id for trial in (1, 2)}
    groups: dict[tuple[str, int], list[GazeEstimate]] = defaultdict(list)
    outside_frames = 0
    outside_trials: set[tuple[str, int]] = set()
    for row in rows:
        if row.get("phase") != "validation":
            continue
        target = by_id.get(row.get("target_id"))
        trial = row.get("trial_number")
        key = (row.get("target_id"), trial)
        if (
            target is None
            or isinstance(trial, bool)
            or key not in expected
            or (_number(row.get("target_x"), "target x"), _number(row.get("target_y"), "target y"))
            != (target.x, target.y)
        ):
            raise ValueError("unknown or inconsistent validation target/trial")
        status = row.get("status")
        if status != "usable":
            if not isinstance(status, str) or not status.startswith("unavailable_"):
                raise ValueError("unrecognized validation availability status")
            continue
        horizontal = _number(row.get("horizontal"), "horizontal feature")
        vertical = _number(row.get("vertical"), "vertical feature")
        estimate = estimate_gaze(mapping, horizontal, vertical)
        if not isinstance(estimate, GazeEstimate):
            raise ValueError("usable validation row produced unavailable gaze estimate")
        groups[key].append(estimate)
        if isinstance(mapping, CombinedMapping) and mapping.vertical.outside_anchor_range(vertical):
            outside_frames += 1
            outside_trials.add(key)
    if set(groups) != expected or any(len(group) < MIN_USABLE_SAMPLES for group in groups.values()):
        raise ValueError("all 16 held-out trials need sufficient usable samples")
    trial_estimates = [
        TrialEstimate(target, trial, tuple(groups[target.name, trial]))
        for target in VALIDATION_TARGETS
        for trial in (1, 2)
    ]
    result = summarize_held_out(trial_estimates, window_width, window_height)
    predictions = [item["predicted_y"] for item in result["trials"]]
    return {
        **result,
        "prediction_range_y": (min(predictions), max(predictions)),
        "outside_anchor_frame_count": outside_frames
        if isinstance(mapping, CombinedMapping)
        else None,
        "outside_anchor_trial_count": len(outside_trials)
        if isinstance(mapping, CombinedMapping)
        else None,
    }


def analyze_session(report: dict) -> dict:
    """Fit on calibration rows only, then evaluate both on the same held-out rows."""
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("session rows are required")
    baseline, samples = calibration_from_rows(rows)
    verify_recorded_mapping(baseline, report.get("mapping_coefficients", {}))
    piecewise = fit_row_anchor_mapping(samples)
    alternative = CombinedMapping(baseline, piecewise)
    dimensions = report.get("window_image_area")
    if not isinstance(dimensions, list) or len(dimensions) != 2:
        raise ValueError("window image area is required")
    width, height = dimensions
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in dimensions
    ):
        raise ValueError("window dimensions must be positive integers")
    results = {}
    for name, mapping in (("independent_linear", baseline), ("piecewise_row_anchor", alternative)):
        results[name] = {
            "calibration": summarize_calibration(samples, mapping),
            "held_out": evaluate_held_out(rows, mapping, width, height),
        }
    # Confirm that replaying untouched validation rows reproduces the stored
    # production baseline before comparing the new experimental candidate.
    recorded = report.get("held_out_validation", {})
    stored_trials = {
        (item["target_id"], item["trial_number"]): item for item in recorded.get("trials", [])
    }
    baseline_trials = results["independent_linear"]["held_out"]["trials"]
    if len(stored_trials) != len(baseline_trials):
        raise ValueError("stored held-out trial count does not match baseline replay")
    for trial in baseline_trials:
        stored = stored_trials.get((trial["target_id"], trial["trial_number"]))
        if stored is None or any(
            not isclose(trial[key], _number(stored.get(key), key), rel_tol=1e-9, abs_tol=1e-10)
            for key in ("predicted_x", "predicted_y")
        ):
            raise ValueError("baseline replay disagrees with stored held-out prediction")
    return {
        "participant": report.get("participant"),
        "session": report.get("session"),
        "anchor_features_and_y": piecewise.anchors,
        "baseline_coefficients": {
            key: getattr(baseline, key) for key in baseline.__dataclass_fields__
        },
        "candidates": results,
    }
