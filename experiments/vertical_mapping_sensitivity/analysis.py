"""Describe calibration feature geometry and linear y sensitivity."""

from collections import defaultdict
from math import isclose, isfinite
from statistics import median

from experiments.vertical_error_decomposition.analysis import (
    calibration_from_rows,
    verify_recorded_mapping,
)
from eye_tracker.gaze.calibration import CalibrationSample, fit_independent_linear
from validation.real_calibration import CALIBRATION_TARGETS, _evaluate_predictions


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return float(value)


def reconstruct_feature(prediction: float, slope: float, intercept: float) -> float:
    """Invert the exact independent-linear identity y = slope * feature + intercept."""
    prediction = _finite(prediction, "prediction")
    slope = _finite(slope, "slope")
    intercept = _finite(intercept, "intercept")
    if slope == 0:
        raise ValueError("feature reconstruction requires a nonzero slope")
    return (prediction - intercept) / slope


def calibration_geometry(samples: list[dict]) -> dict:
    """Describe the nine per-target features used by the existing 3x3 fitter."""
    expected = {target.name: target for target in CALIBRATION_TARGETS}
    if len(samples) != 9 or {sample.get("target_id") for sample in samples} != set(expected):
        raise ValueError("calibration geometry requires the nine distinct grid targets")
    targets = []
    rows: dict[str, list[float]] = defaultdict(list)
    names = {0.2: "top", 0.5: "center", 0.8: "bottom"}
    for sample in samples:
        target = expected[sample["target_id"]]
        if (sample.get("target_x"), sample.get("target_y")) != (target.x, target.y):
            raise ValueError("calibration target coordinates disagree with grid")
        feature = _finite(sample.get("vertical_feature"), "vertical feature")
        targets.append(
            {
                "target_id": target.name,
                "target_x": target.x,
                "target_y": target.y,
                "vertical_feature": feature,
            }
        )
        rows[names[target.y]].append(feature)
    targets.sort(key=lambda item: (item["target_y"], item["target_x"]))
    row_summary = {
        name: {
            "median": median(values),
            "minimum": min(values),
            "maximum": max(values),
            "spread": max(values) - min(values),
        }
        for name, values in rows.items()
    }
    top_to_center = row_summary["center"]["median"] - row_summary["top"]["median"]
    center_to_bottom = row_summary["bottom"]["median"] - row_summary["center"]["median"]
    features = [item["vertical_feature"] for item in targets]
    return {
        "targets": targets,
        "rows": row_summary,
        "full_span": max(features) - min(features),
        "top_to_center": top_to_center,
        "center_to_bottom": center_to_bottom,
        "minimum_adjacent_row_separation": min(top_to_center, center_to_bottom),
    }


def amplification(slope: float, feature_delta: float) -> float:
    """Account for the output change from a feature change at a fixed slope."""
    return _finite(slope, "slope") * _finite(feature_delta, "feature delta")


def repeated_target_differences(presentations: list[dict], slope: float) -> list[dict]:
    """Compare first and last presentations of each identical phase/target."""
    slope = _finite(slope, "slope")
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in presentations:
        groups[item["phase"], item["target_id"]].append(item)
    result = []
    for (phase, target_id), group in sorted(groups.items()):
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda item: item["order"])
        first, last = ordered[0], ordered[-1]
        feature_values = [item.get("vertical_feature") for item in ordered]
        feature_delta = (
            _finite(last["vertical_feature"], "vertical feature")
            - _finite(first["vertical_feature"], "vertical feature")
            if all(value is not None for value in feature_values)
            else None
        )
        predictions = [item.get("predicted_y") for item in ordered]
        prediction_delta = (
            _finite(last["predicted_y"], "predicted y")
            - _finite(first["predicted_y"], "predicted y")
            if all(value is not None for value in predictions)
            else None
        )
        result.append(
            {
                "phase": phase,
                "target_id": target_id,
                "presentation_count": len(group),
                "feature_delta": feature_delta,
                "feature_span": max(feature_values) - min(feature_values)
                if feature_delta is not None
                else None,
                "mapped_y_delta": amplification(slope, feature_delta)
                if feature_delta is not None
                else None,
                "prediction_delta": prediction_delta,
            }
        )
    return result


def analyze_session(report: dict) -> dict:
    """Analyze one recorded session; absent optional observations stay absent."""
    participant, session = report.get("participant"), report.get("session")
    if not all(isinstance(value, str) and value.strip() for value in (participant, session)):
        raise ValueError("participant and session are required")
    coefficients = report.get("mapping_coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("mapping coefficients are required")
    slope = _finite(coefficients.get("y_slope"), "y slope")
    intercept = _finite(coefficients.get("y_intercept"), "y intercept")
    if slope == 0:
        raise ValueError("zero y slope cannot support feature reconstruction")

    rows = report.get("rows")
    original_samples = report.get("calibration_samples")
    if isinstance(original_samples, list):
        samples = [
            {
                "target_id": item["target_id"],
                "target_x": item["target_x"],
                "target_y": item["target_y"],
                "vertical_feature": item["vertical_feature"],
            }
            for item in original_samples
        ]
        mapped_samples = tuple(
            CalibrationSample(
                item["horizontal_feature"],
                item["vertical_feature"],
                item["target_x"],
                item["target_y"],
            )
            for item in original_samples
        )
        fitted = fit_independent_linear(mapped_samples)
        verify_recorded_mapping(fitted, coefficients)
        source = "recorded_calibration_features"
    elif isinstance(rows, list):
        fitted, aggregated = calibration_from_rows(rows)
        mapped_samples = aggregated
        verify_recorded_mapping(fitted, coefficients)
        samples = [
            {
                "target_id": target.name,
                "target_x": sample.target_x,
                "target_y": sample.target_y,
                "vertical_feature": sample.vertical_feature,
            }
            for target, sample in zip(CALIBRATION_TARGETS, aggregated, strict=True)
        ]
        source = "recorded_frame_features_aggregated_by_production_median"
    else:
        fit = report.get("calibration_fit")
        if not isinstance(fit, dict) or not isinstance(fit.get("trials"), list):
            raise ValueError("calibration features or linear predictions are required")
        samples = [
            {
                "target_id": trial["target_id"],
                "target_x": trial["target_x"],
                "target_y": trial["target_y"],
                "vertical_feature": reconstruct_feature(trial["predicted_y"], slope, intercept),
            }
            for trial in fit["trials"]
        ]
        center = next(item for item in samples if item["target_id"] == "C-2-2")
        if not isclose(
            center["vertical_feature"],
            _finite(report.get("calibration_center_vertical_feature"), "CENTER feature"),
            rel_tol=1e-9,
            abs_tol=1e-10,
        ):
            raise ValueError("reconstructed CENTER feature disagrees with recorded value")
        source = "reconstructed_from_linear_predictions"

    geometry = calibration_geometry(samples)
    calibration_fit = report.get("calibration_fit")
    if calibration_fit is None:
        by_id = {target.name: target for target in CALIBRATION_TARGETS}
        x_slope = _finite(coefficients.get("x_slope"), "x slope")
        x_intercept = _finite(coefficients.get("x_intercept"), "x intercept")
        horizontal_by_id = {
            item["target_id"]: sample.horizontal_feature
            for item, sample in zip(samples, mapped_samples, strict=True)
        }
        calibration_fit = _evaluate_predictions(
            [
                (
                    by_id[item["target_id"]],
                    1,
                    x_slope * horizontal_by_id[item["target_id"]] + x_intercept,
                    amplification(slope, item["vertical_feature"]) + intercept,
                )
                for item in geometry["targets"]
            ],
            *report["window_image_area"],
        )

    held = report.get("baseline", report.get("held_out_validation"))
    presentations = (
        _presentations_from_rows(rows, slope, intercept)
        if isinstance(rows, list)
        else _presentations_from_live(held)
    )
    repeats = repeated_target_differences(presentations, slope)
    return {
        "participant": participant,
        "session": session,
        "calibration_feature_source": source,
        "y_slope": slope,
        "y_intercept": intercept,
        "calibration": geometry,
        "calibration_fit": _vertical_metrics(calibration_fit),
        "held_out": _vertical_metrics(held) if held is not None else None,
        "amplification": {
            str(change): amplification(slope, change) for change in (0.001, 0.003, 0.005)
        },
        "repeats": repeats,
        "repeat_summary": _repeat_summary(repeats),
    }


def _vertical_metrics(result: dict) -> dict:
    summary, ordering = result["summary"], result["spatial_ordering"]["y"]
    return {
        "trial_count": len(result["trials"]),
        "y_mae": _finite(summary["mean_vertical_absolute_error"], "y MAE"),
        "median_absolute_y_error": _finite(
            summary["median_vertical_absolute_error"], "median y error"
        ),
        "p95_absolute_y_error": _finite(summary["p95_vertical_absolute_error"], "p95 y error"),
        "y_ordering": ordering,
    }


def _presentations_from_live(held: dict | None) -> list[dict]:
    if held is None:
        return []
    return [
        {
            "phase": "validation",
            "target_id": trial["target_id"],
            "order": index,
            "vertical_feature": None,
            "predicted_y": trial["predicted_y"],
        }
        for index, trial in enumerate(held["trials"])
    ]


def _presentations_from_rows(rows: list[dict], slope: float, intercept: float) -> list[dict]:
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for row in rows:
        if (
            row.get("phase") in ("validation", "checkpoint", "diagnostic")
            and row.get("status") == "usable"
        ):
            groups[row["phase"], row["target_id"], row["trial_number"]].append(row)
    presentations = []
    for (phase, target_id, _), group in groups.items():
        feature = median(_finite(item["vertical"], "vertical") for item in group)
        presentations.append(
            {
                "phase": phase,
                "target_id": target_id,
                "order": min(_finite(item["monotonic_seconds"], "timestamp") for item in group),
                "vertical_feature": feature,
                "predicted_y": amplification(slope, feature) + intercept,
            }
        )
    return presentations


def _repeat_summary(repeats: list[dict]) -> dict:
    by_phase: dict[str, list[dict]] = defaultdict(list)
    for item in repeats:
        by_phase[item["phase"]].append(item)
    return {
        phase: {
            "target_count": len(group),
            "median_absolute_feature_delta": median(abs(item["feature_delta"]) for item in group)
            if all(item["feature_delta"] is not None for item in group)
            else None,
            "max_absolute_feature_delta": max(abs(item["feature_delta"]) for item in group)
            if all(item["feature_delta"] is not None for item in group)
            else None,
            "median_absolute_prediction_delta": median(
                abs(item["prediction_delta"]) for item in group
            )
            if all(item["prediction_delta"] is not None for item in group)
            else None,
            "max_absolute_prediction_delta": max(abs(item["prediction_delta"]) for item in group)
            if all(item["prediction_delta"] is not None for item in group)
            else None,
        }
        for phase, group in by_phase.items()
    }
