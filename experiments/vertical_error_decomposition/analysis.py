"""Compare calibration fit, fixed-target feature movement, and held-out error.

Only fixed-target CENTER checkpoints support exact additive model-output
accounting. Held-out targets differ from calibration targets, so their error
cannot be assigned causally to fit residual versus subsequent feature change.
"""

from collections import defaultdict
from math import isclose, isfinite
from statistics import fmean, median

from eye_tracker.gaze.calibration import (
    CalibrationSample,
    IndependentLinearMapping,
    aggregate_calibration_observations,
    fit_independent_linear,
)
from validation.real_calibration import CALIBRATION_TARGETS


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _axis_summary(errors: list[float]) -> dict:
    if not errors:
        raise ValueError("at least one error is required")
    return {"mae": fmean(abs(error) for error in errors), "signed_bias": fmean(errors)}


def calibration_from_rows(rows: list[dict]) -> tuple[IndependentLinearMapping, tuple]:
    """Reconstruct the nine median samples with the existing production routines."""
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    target_by_id = {target.name: target for target in CALIBRATION_TARGETS}
    for row in rows:
        if row.get("phase") != "calibration":
            continue
        target = target_by_id.get(row.get("target_id"))
        if target is None or (
            _number(row.get("target_x"), "target x"),
            _number(row.get("target_y"), "target y"),
        ) != (target.x, target.y):
            raise ValueError("unknown or mismatched calibration target")
        if row.get("status") == "usable":
            groups[target.name].append(
                (
                    _number(row.get("horizontal"), "horizontal"),
                    _number(row.get("vertical"), "vertical"),
                )
            )
    if set(groups) != set(target_by_id):
        raise ValueError("all nine calibration targets need usable observations")
    samples = tuple(
        aggregate_calibration_observations(groups[target.name], target.x, target.y)
        for target in CALIBRATION_TARGETS
    )
    return fit_independent_linear(samples), samples


def verify_recorded_mapping(mapping: IndependentLinearMapping, coefficients: dict) -> None:
    """Fail rather than analyze a dataset with a different stored mapping."""
    for name in ("x_slope", "x_intercept", "y_slope", "y_intercept"):
        recorded = _number(coefficients.get(name), name)
        if not isclose(getattr(mapping, name), recorded, rel_tol=1e-9, abs_tol=1e-10):
            raise ValueError(f"reconstructed mapping disagrees with recorded {name}")


def residual_summary(mapping: IndependentLinearMapping, samples: list | tuple) -> dict:
    """Calibration residual means target minus predicted; signed bias is its inverse."""
    if not samples:
        raise ValueError("calibration samples are required")
    targets = []
    for sample in samples:
        if not isinstance(sample, CalibrationSample):
            raise ValueError("expected CalibrationSample")
        predicted_x, predicted_y = mapping.predict(
            sample.horizontal_feature, sample.vertical_feature
        )
        targets.append(
            {
                "target_x": sample.target_x,
                "target_y": sample.target_y,
                "predicted_x": predicted_x,
                "predicted_y": predicted_y,
                "x_target_minus_predicted": sample.target_x - predicted_x,
                "y_target_minus_predicted": sample.target_y - predicted_y,
            }
        )
    result = {"targets": targets}
    for axis in ("x", "y"):
        residuals = [item[f"{axis}_target_minus_predicted"] for item in targets]
        result[axis] = {
            "mae": fmean(abs(value) for value in residuals),
            "mean_target_minus_predicted": fmean(residuals),
            "signed_bias_predicted_minus_target": -fmean(residuals),
        }
    return result


def center_accounting(
    mapping: IndependentLinearMapping,
    calibration_center: CalibrationSample,
    checkpoint_horizontal: float,
    checkpoint_vertical: float,
) -> dict:
    """Exact model-output identity at the identical CENTER target (0.5, 0.5)."""
    if (calibration_center.target_x, calibration_center.target_y) != (0.5, 0.5):
        raise ValueError("calibration sample must target CENTER")
    checkpoint_horizontal = _number(checkpoint_horizontal, "checkpoint horizontal")
    checkpoint_vertical = _number(checkpoint_vertical, "checkpoint vertical")
    before = mapping.predict(
        calibration_center.horizontal_feature, calibration_center.vertical_feature
    )
    after = mapping.predict(checkpoint_horizontal, checkpoint_vertical)
    return {
        axis: {
            "calibration_signed_error": before[index] - 0.5,
            "feature_output_change": after[index] - before[index],
            "total_signed_error": after[index] - 0.5,
            "accounting_remainder": (after[index] - 0.5)
            - (before[index] - 0.5)
            - (after[index] - before[index]),
        }
        for index, axis in enumerate(("x", "y"))
    }


def summarize_held_out(trials: list[dict]) -> dict:
    """Describe recorded held-out predictions, without inventing an attribution."""
    if not trials:
        raise ValueError("held-out trials are required")
    errors = {"x": [], "y": []}
    for trial in trials:
        for axis in ("x", "y"):
            target = _number(trial.get(f"target_{axis}"), f"target {axis}")
            predicted = _number(trial.get(f"predicted_{axis}"), f"predicted {axis}")
            if not 0 <= target <= 1:
                raise ValueError("target must be normalized")
            errors[axis].append(predicted - target)
    return {
        "trial_count": len(trials),
        "x": _axis_summary(errors["x"]),
        "y": _axis_summary(errors["y"]),
        "attributable_remainder": None,
    }


def analyze_session(report: dict) -> dict:
    """Keep each human session independent and verify its stored fit."""
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    mapping, samples = calibration_from_rows(rows)
    verify_recorded_mapping(mapping, report.get("mapping_coefficients", {}))
    center = next(sample for sample in samples if (sample.target_x, sample.target_y) == (0.5, 0.5))
    if not isclose(
        center.vertical_feature,
        _number(report.get("calibration_center_vertical"), "calibration center vertical"),
        rel_tol=1e-9,
        abs_tol=1e-10,
    ):
        raise ValueError("calibration-center vertical feature disagrees with recorded value")
    checkpoint_rows: dict[int, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("phase") != "checkpoint":
            continue
        if (row.get("target_x"), row.get("target_y")) != (0.5, 0.5):
            raise ValueError("checkpoint target must be CENTER")
        identifier = row.get("checkpoint")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 0:
            raise ValueError("checkpoint ID must be a nonnegative integer")
        if row.get("status") == "usable":
            checkpoint_rows[identifier].append(row)
    if not checkpoint_rows or sorted(checkpoint_rows) != list(range(max(checkpoint_rows) + 1)):
        raise ValueError("checkpoints must begin at zero without gaps")
    checkpoints = []
    for identifier, group in sorted(checkpoint_rows.items()):
        horizontal = median(_number(row.get("horizontal"), "horizontal") for row in group)
        vertical = median(_number(row.get("vertical"), "vertical") for row in group)
        checkpoints.append(
            {
                "checkpoint": identifier,
                "sample_count": len(group),
                "horizontal_feature": horizontal,
                "vertical_feature": vertical,
                "horizontal_feature_shift": horizontal - center.horizontal_feature,
                "vertical_feature_shift": vertical - center.vertical_feature,
                **center_accounting(mapping, center, horizontal, vertical),
            }
        )
    held_out = summarize_held_out(report.get("held_out_validation", {}).get("trials", []))
    stored = report["held_out_validation"]["summary"]
    for axis, prefix in (("x", "horizontal"), ("y", "vertical")):
        for key, recorded in (
            ("mae", stored[f"mean_{prefix}_absolute_error"]),
            ("signed_bias", stored[f"mean_signed_{axis}_bias"]),
        ):
            if not isclose(held_out[axis][key], _number(recorded, key), abs_tol=1e-9):
                raise ValueError("held-out summary disagrees with recorded trials")
    return {
        "participant": report.get("participant"),
        "session": report.get("session"),
        "mapping": {key: getattr(mapping, key) for key in mapping.__dataclass_fields__},
        "calibration_center_features": {
            "horizontal": center.horizontal_feature,
            "vertical": center.vertical_feature,
        },
        "calibration": residual_summary(mapping, samples),
        "checkpoints": checkpoints,
        "held_out": held_out,
    }
