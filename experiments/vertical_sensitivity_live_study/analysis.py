"""Analyze recorded feature medians from a controlled 27-presentation session."""

from math import isclose, isfinite
from statistics import median

from experiments.vertical_mapping_sensitivity.analysis import calibration_geometry
from experiments.vertical_position_variability.analysis import (
    _presentation_summaries,
    _validated_rows,
)
from experiments.vertical_sensitivity_live_study.protocol import pass_name, schedule
from eye_tracker.gaze.calibration import IndependentLinearMapping
from validation.real_calibration import MIN_USABLE_SAMPLES, _evaluate_predictions, percentile


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _mapping(report: dict) -> IndependentLinearMapping:
    coefficients = report.get("mapping_coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("mapping coefficients are required")
    return IndependentLinearMapping(
        *(
            _number(coefficients.get(name), name)
            for name in ("x_slope", "x_intercept", "y_slope", "y_intercept")
        )
    )


def _validated_presentations(report: dict) -> list[dict]:
    presentations = report.get("presentations")
    planned = schedule()
    if not isinstance(presentations, list) or len(presentations) != len(planned):
        raise ValueError("exactly 27 recorded presentations are required")
    mapping = _mapping(report)
    for order, (item, expected) in enumerate(zip(presentations, planned, strict=True), start=1):
        if not isinstance(item, dict) or item.get("order") != order:
            raise ValueError("presentation order disagrees with protocol")
        if item.get("pass") != pass_name(expected.phase, expected.trial):
            raise ValueError("presentation pass disagrees with protocol")
        if item.get("target_id") != expected.target.name or (
            item.get("target_x"),
            item.get("target_y"),
        ) != (expected.target.x, expected.target.y):
            raise ValueError("presentation target coordinates disagree with protocol")
        usable = item.get("usable_count")
        unavailable = item.get("unavailable_count")
        attempts = item.get("sampling_attempts")
        if any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in (usable, unavailable, attempts)
        ):
            raise ValueError("sample counts must be integers")
        if usable < MIN_USABLE_SAMPLES or unavailable < 0 or attempts != usable + unavailable:
            raise ValueError("presentation needs sufficient usable samples and consistent counts")
        x, y = mapping.predict(
            _number(item.get("horizontal_feature"), "horizontal feature"),
            _number(item.get("vertical_feature"), "vertical feature"),
        )
        if not (
            isclose(_number(item.get("predicted_x"), "x prediction"), x, abs_tol=1e-12)
            and isclose(_number(item.get("predicted_y"), "y prediction"), y, abs_tol=1e-12)
        ):
            raise ValueError("saved prediction disagrees with uncorrected, unclipped mapping")
    return presentations


def prepare_report(raw: dict) -> dict:
    """Retain original derived rows and add actual per-presentation feature medians."""
    if not isinstance(raw, dict):
        raise ValueError("raw session must be an object")
    rows = _validated_rows(raw.get("rows"), raw.get("participant"), raw.get("session"))
    summaries = _presentation_summaries(rows)
    if len(summaries) != len(schedule()):
        raise ValueError("exactly 27 complete presentations are required")
    mapping = _mapping(raw)
    presentations = []
    for order, item in enumerate(summaries, start=1):
        horizontal = item["measures"]["horizontal"]["median"]
        vertical = item["measures"]["vertical"]["median"]
        predicted_x, predicted_y = mapping.predict(horizontal, vertical)
        presentations.append(
            {
                "order": order,
                "pass": pass_name(item["phase"], item["trial"]),
                "target_id": item["target_id"],
                "target_x": item["target_x"],
                "target_y": item["target_y"],
                "horizontal_feature": horizontal,
                "vertical_feature": vertical,
                "predicted_x": predicted_x,
                "predicted_y": predicted_y,
                "usable_count": item["usable_count"],
                "unavailable_count": item["unavailable_count"],
                "sampling_attempts": item["usable_count"] + item["unavailable_count"],
            }
        )
    report = {**raw, "presentations": presentations}
    analyze_session(report)
    return report


def _difference(first: dict, second: dict, comparison: str, slope: float) -> dict:
    feature_change = second["vertical_feature"] - first["vertical_feature"]
    mapped_change = slope * feature_change
    return {
        "target_x": first["target_x"],
        "target_y": first["target_y"],
        "comparison": comparison,
        "signed_feature_change": feature_change,
        "absolute_feature_change": abs(feature_change),
        "signed_mapped_y_change": mapped_change,
        "absolute_mapped_y_change": abs(mapped_change),
    }


def _repeat_summary(differences: list[dict]) -> dict:
    feature_values = [item["absolute_feature_change"] for item in differences]
    mapped_values = [item["absolute_mapped_y_change"] for item in differences]
    return {
        "comparison_count": len(differences),
        "median_absolute_feature_change": median(feature_values),
        "p95_absolute_feature_change": percentile(feature_values, 95),
        "maximum_absolute_feature_change": max(feature_values),
        "median_absolute_mapped_y_change": median(mapped_values),
        "p95_absolute_mapped_y_change": percentile(mapped_values, 95),
        "maximum_absolute_mapped_y_change": max(mapped_values),
    }


def analyze_session(report: dict) -> dict:
    """Compare calibration, A, and B at each exact coordinate without correction."""
    if not isinstance(report, dict) or not all(
        isinstance(report.get(key), str) and report[key].strip()
        for key in ("participant", "session")
    ):
        raise ValueError("participant and session are required")
    presentations = _validated_presentations(report)
    mapping = _mapping(report)
    calibration = presentations[:9]
    geometry = calibration_geometry(calibration)
    dimensions = report.get("window_image_area")
    if (
        not isinstance(dimensions, (list, tuple))
        or len(dimensions) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in dimensions
        )
    ):
        raise ValueError("positive window image dimensions are required")
    fit = _evaluate_predictions(
        [
            (expected.target, 1, item["predicted_x"], item["predicted_y"])
            for item, expected in zip(calibration, schedule()[:9], strict=True)
        ],
        *dimensions,
    )
    by_pass = {
        name: {
            (item["target_x"], item["target_y"]): item
            for item in presentations
            if item["pass"] == name
        }
        for name in ("calibration", "pass_a", "pass_b")
    }
    differences = []
    for coordinate in by_pass["calibration"]:
        calibration_item = by_pass["calibration"][coordinate]
        a_item = by_pass["pass_a"][coordinate]
        b_item = by_pass["pass_b"][coordinate]
        differences.extend(
            (
                _difference(calibration_item, a_item, "calibration_to_a", mapping.y_slope),
                _difference(calibration_item, b_item, "calibration_to_b", mapping.y_slope),
                _difference(a_item, b_item, "a_to_b", mapping.y_slope),
            )
        )
    return {
        "participant": report["participant"],
        "session": report["session"],
        "y_slope": mapping.y_slope,
        "y_intercept": mapping.y_intercept,
        "calibration": geometry,
        "calibration_fit": {
            "y_mae": fit["summary"]["mean_vertical_absolute_error"],
            "y_ordering": fit["spatial_ordering"]["y"],
        },
        "sensitivity_examples": {
            str(change): abs(mapping.y_slope * change) for change in (0.001, 0.003, 0.005)
        },
        "repeated_targets": differences,
        "repeat_summary": _repeat_summary(differences),
        "repeat_summary_by_comparison": {
            name: _repeat_summary([item for item in differences if item["comparison"] == name])
            for name in ("calibration_to_a", "calibration_to_b", "a_to_b")
        },
    }
