"""Describe where directional information changes within each recorded session."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import combinations
from math import isfinite
from statistics import StatisticsError, correlation, median

from validation.real_calibration import percentile


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite numerical value")
    return float(value)


def describe_values(values: Iterable[float]) -> dict:
    """Return descriptive spread only; no gaze-success threshold is imposed."""
    numbers = [_number(value, "feature") for value in values]
    if not numbers:
        raise ValueError("at least one finite numerical value is required")
    minimum, maximum = min(numbers), max(numbers)
    return {
        "count": len(numbers),
        "median": median(numbers),
        "minimum": minimum,
        "maximum": maximum,
        "range": maximum - minimum,
        "iqr": percentile(numbers, 75) - percentile(numbers, 25),
    }


def _ordering(values: list[float]) -> str:
    if all(right > left for left, right in zip(values, values[1:])):
        return "increasing"
    if all(right < left for left, right in zip(values, values[1:])):
        return "decreasing"
    return "mixed"


def calibration_axis_summary(
    rows: list[dict], samples: list[dict], feature_key: str, target_key: str
) -> dict:
    """Keep frame distributions distinct from the medians supplied to the fitter."""
    if (feature_key, target_key) not in {
        ("horizontal", "target_x"),
        ("vertical", "target_y"),
    }:
        raise ValueError("feature and target axis must match")
    sample_feature = f"{feature_key}_feature"
    raw_groups: dict[float, list[float]] = defaultdict(list)
    aggregated_groups: dict[float, list[float]] = defaultdict(list)
    per_target = []
    for row in rows:
        if row["phase"] == "calibration" and row["status"] == "usable":
            coordinate = _number(row[target_key], target_key)
            raw_groups[coordinate].append(_number(row[feature_key], feature_key))
    for sample in samples:
        coordinate = _number(sample[target_key], target_key)
        value = _number(sample[sample_feature], sample_feature)
        aggregated_groups[coordinate].append(value)
        per_target.append(
            {
                "target_id": sample["target_id"],
                "target_coordinate": coordinate,
                "median_feature": value,
            }
        )
    if not raw_groups or set(raw_groups) != set(aggregated_groups):
        raise ValueError("calibration frame and aggregated target groups must match")
    grouped = [
        {
            "target_coordinate": coordinate,
            "raw": describe_values(raw_groups[coordinate]),
            "aggregated": describe_values(aggregated_groups[coordinate]),
        }
        for coordinate in sorted(raw_groups)
    ]
    overlaps = [
        left["raw"]["maximum"] >= right["raw"]["minimum"]
        and right["raw"]["maximum"] >= left["raw"]["minimum"]
        for left, right in zip(grouped, grouped[1:])
    ]
    return {
        "rows": grouped,
        "per_target": per_target,
        "raw_ordering": _ordering([item["raw"]["median"] for item in grouped]),
        "aggregated_ordering": _ordering([item["aggregated"]["median"] for item in grouped]),
        "raw_range_overlap": overlaps,
    }


def prediction_range(trials: list[dict], key: str) -> dict:
    """Expose span rather than declaring collapse using an invented cutoff."""
    values = [_number(item[key], key) for item in trials]
    if not values:
        raise ValueError("at least one held-out prediction is required")
    minimum, maximum = min(values), max(values)
    return {"minimum": minimum, "maximum": maximum, "span": maximum - minimum}


def _validate_rows(rows: object) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("at least one diagnostic row is required")
    for row in rows:
        if not isinstance(row, dict) or row.get("phase") not in {"calibration", "validation"}:
            raise ValueError("diagnostic rows need a valid phase")
        if not isinstance(row.get("target_id"), str) or not row["target_id"]:
            raise ValueError("diagnostic rows need a target identifier")
        for key in ("target_x", "target_y"):
            coordinate = _number(row.get(key), key)
            if not 0 <= coordinate <= 1:
                raise ValueError("target coordinates must lie in [0, 1]")
        if not isinstance(row.get("trial_number"), int) or row["trial_number"] < 1:
            raise ValueError("trial number must be positive")
        if not isinstance(row.get("status"), str) or not row["status"]:
            raise ValueError("diagnostic rows need availability status")
        if row["status"] == "usable":
            for key in ("horizontal", "vertical"):
                _number(row.get(key), key)
        elif row.get("horizontal") is None and row.get("vertical") is None:
            pass
        elif row.get("horizontal") is not None and row.get("vertical") is not None:
            # A mapping failure can occur after valid features were observed.
            _number(row["horizontal"], "horizontal")
            _number(row["vertical"], "vertical")
        else:
            raise ValueError("horizontal and vertical features must be present together")
        for key in (
            "left_horizontal",
            "right_horizontal",
            "left_vertical",
            "right_vertical",
            "left_eye_opening",
            "right_eye_opening",
            "binocular_eye_opening",
            "head_center_y",
            "predicted_x",
            "predicted_y",
        ):
            if row.get(key) is not None:
                _number(row[key], key)
    return rows


def _within_target_correlation(rows: list[dict], diagnostic_key: str) -> float | None:
    """Demean by calibration target so target direction does not create the association."""
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        if row["phase"] == "calibration" and row["status"] == "usable":
            value = row.get(diagnostic_key)
            if value is not None:
                groups[row["target_id"]].append((row["vertical"], value))
    feature_deviations, diagnostic_deviations = [], []
    for values in groups.values():
        if len(values) < 2:
            continue
        feature_center = sum(item[0] for item in values) / len(values)
        diagnostic_center = sum(item[1] for item in values) / len(values)
        feature_deviations.extend(item[0] - feature_center for item in values)
        diagnostic_deviations.extend(item[1] - diagnostic_center for item in values)
    if len(feature_deviations) < 2:
        return None
    try:
        return correlation(feature_deviations, diagnostic_deviations)
    except StatisticsError:
        return None


def summarize_session(report: dict) -> dict:
    """Summarize one person/session without pooling observations across runs."""
    participant, session = report.get("participant"), report.get("session")
    if not all(isinstance(value, str) and value.strip() for value in (participant, session)):
        raise ValueError("participant and session are required")
    rows = _validate_rows(report.get("rows"))
    samples = report.get("calibration_samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("calibration samples are required")
    coefficients = report.get("mapping_coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("mapping coefficients are required")
    coefficients = {
        name: _number(coefficients.get(name), name)
        for name in ("x_slope", "x_intercept", "y_slope", "y_intercept")
    }
    held_out = report.get("held_out_validation")
    if not isinstance(held_out, dict) or not isinstance(held_out.get("trials"), list):
        raise ValueError("held-out validation trials are required")
    trials = held_out["trials"]
    horizontal = calibration_axis_summary(rows, samples, "horizontal", "target_x")
    vertical = calibration_axis_summary(rows, samples, "vertical", "target_y")
    return {
        "participant": participant,
        "session": session,
        "statuses": dict(Counter(row["status"] for row in rows)),
        "horizontal": horizontal,
        "vertical": vertical,
        "mapping_coefficients": coefficients,
        "held_out": {
            "x_prediction_range": prediction_range(trials, "predicted_x"),
            "y_prediction_range": prediction_range(trials, "predicted_y"),
            "x_ordering": held_out["spatial_ordering"]["x"],
            "y_ordering": held_out["spatial_ordering"]["y"],
            "horizontal_mae": _number(
                held_out["summary"]["mean_horizontal_absolute_error"], "horizontal MAE"
            ),
            "vertical_mae": _number(
                held_out["summary"]["mean_vertical_absolute_error"], "vertical MAE"
            ),
            "signed_x_bias": _number(held_out["summary"]["mean_signed_x_bias"], "x bias"),
            "signed_y_bias": _number(held_out["summary"]["mean_signed_y_bias"], "y bias"),
        },
        "within_target_associations": {
            key: _within_target_correlation(rows, key)
            for key in ("binocular_eye_opening", "head_center_y")
        },
    }


def compare_sessions(summaries: list[dict]) -> dict:
    """Describe offsets only; never average participants into a pooled result."""
    by_person: dict[str, dict[str, dict]] = defaultdict(dict)
    by_session: dict[str, float] = {}

    def row_medians(summary: dict) -> dict[float, float]:
        return {
            row["target_coordinate"]: row["aggregated"]["median"]
            for row in summary["vertical"]["rows"]
        }

    def row_deltas(first: dict, second: dict) -> dict[str, float]:
        first_rows, second_rows = row_medians(first), row_medians(second)
        if first_rows.keys() != second_rows.keys():
            raise ValueError("sessions use different vertical calibration rows")
        return {str(y): second_rows[y] - first_rows[y] for y in sorted(first_rows)}

    for summary in summaries:
        participant, session = summary["participant"], summary["session"]
        if session in by_person[participant]:
            raise ValueError(f"duplicate participant/session: {participant}/{session}")
        by_person[participant][session] = summary
        centers = row_medians(summary)
        if 0.5 not in centers:
            raise ValueError("center calibration row is required for session comparison")
        by_session[f"{participant}/{session}"] = centers[0.5]
    same_user = {
        participant: {
            "center_vertical_delta_B_minus_A": by_session[f"{participant}/B"]
            - by_session[f"{participant}/A"],
            "vertical_row_deltas_B_minus_A": row_deltas(sessions["A"], sessions["B"]),
            "vertical_slope_delta_B_minus_A": sessions["B"]["mapping_coefficients"]["y_slope"]
            - sessions["A"]["mapping_coefficients"]["y_slope"],
        }
        for participant, sessions in by_person.items()
        if "A" in sessions and "B" in sessions
    }
    between_users = []
    for left, right in combinations(sorted(by_person), 2):
        for session in sorted(set(by_person[left]) & set(by_person[right])):
            between_users.append(
                {
                    "participant_a": left,
                    "participant_b": right,
                    "session": session,
                    "center_vertical_delta_b_minus_a": by_session[f"{right}/{session}"]
                    - by_session[f"{left}/{session}"],
                    "vertical_row_deltas_b_minus_a": row_deltas(
                        by_person[left][session], by_person[right][session]
                    ),
                }
            )
    return {"by_session": by_session, "same_user": same_user, "between_users": between_users}
