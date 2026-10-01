"""Compare recorded per-eye and face covariates at repeated identical targets."""

import argparse
import json
from math import isclose, isfinite, sqrt
from pathlib import Path
from statistics import median

from experiments.vertical_sensitivity_live_study.protocol import pass_name, schedule
from validation.real_calibration import percentile

MEASURES = (
    "vertical",
    "left_vertical",
    "right_vertical",
    "left_eye_opening",
    "right_eye_opening",
    "binocular_eye_opening",
    "head_center_y",
)


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _median_or_none(values: list[float]) -> float | None:
    return median(values) if values else None


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + end + 1) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def spearman(left: list[float], right: list[float]) -> float | None:
    """Pearson correlation of midranks; undefined for short or constant lists."""
    if len(left) != len(right):
        raise ValueError("Spearman inputs must have equal length")
    if len(left) < 2:
        return None
    x, y = _ranks(left), _ranks(right)
    x_mean, y_mean = sum(x) / len(x), sum(y) / len(y)
    cross = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
    x_square = sum((a - x_mean) ** 2 for a in x)
    y_square = sum((b - y_mean) ** 2 for b in y)
    if not x_square or not y_square:
        return None
    return cross / sqrt(x_square * y_square)


def _aggregate(report: dict) -> list[dict]:
    rows, saved = report.get("rows"), report.get("presentations")
    planned = schedule()
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty raw rows are required")
    if not isinstance(saved, list) or len(saved) != len(planned):
        raise ValueError("exactly 27 saved presentations are required")
    groups = {}
    expected = {
        (item.phase, item.trial, item.target.name, item.target.x, item.target.y) for item in planned
    }
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("raw row must be an object")
        if row.get("participant") != report.get("participant") or row.get("session") != report.get(
            "session"
        ):
            raise ValueError("raw row participant/session disagrees with report")
        key = tuple(
            row.get(name) for name in ("phase", "trial_number", "target_id", "target_x", "target_y")
        )
        if key not in expected:
            raise ValueError("raw row target or coordinate disagrees with protocol")
        if row.get("status") not in ("usable", "unavailable"):
            raise ValueError("raw row status is invalid")
        groups.setdefault(key, []).append(row)
    presentations = []
    minimum = report.get("minimum_usable_samples_per_presentation", 5)
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("minimum usable count is invalid")
    for order, (item, stored) in enumerate(zip(planned, saved, strict=True), start=1):
        key = (item.phase, item.trial, item.target.name, item.target.x, item.target.y)
        group = groups.get(key, [])
        usable = [row for row in group if row["status"] == "usable"]
        if len(usable) < minimum:
            raise ValueError("presentation has insufficient usable observations")
        phase = pass_name(item.phase, item.trial)
        if (
            not isinstance(stored, dict)
            or stored.get("order") != order
            or stored.get("pass") != phase
            or stored.get("target_id") != item.target.name
            or (stored.get("target_x"), stored.get("target_y")) != (item.target.x, item.target.y)
            or stored.get("usable_count") != len(usable)
            or stored.get("unavailable_count") != len(group) - len(usable)
        ):
            raise ValueError("saved presentation disagrees with raw rows or protocol")
        result = {
            "order": order,
            "phase": item.phase,
            "pass": phase,
            "trial": item.trial,
            "target_id": item.target.name,
            "target_x": item.target.x,
            "target_y": item.target.y,
            "usable_count": len(usable),
            "unavailable_count": len(group) - len(usable),
        }
        for name in MEASURES:
            values = [_finite(row[name], name) for row in usable if row.get(name) is not None]
            result[name] = _median_or_none(values)
            result[f"{name}_count"] = len(values)
            if name in ("vertical", "binocular_eye_opening", "head_center_y"):
                result[f"{name}_p95_p05"] = (
                    percentile(values, 95) - percentile(values, 5) if values else None
                )
        if result["vertical_count"] != len(usable):
            raise ValueError("usable row needs vertical feature")
        if not isclose(
            result["vertical"],
            _finite(stored.get("vertical_feature"), "saved vertical median"),
            abs_tol=1e-12,
        ):
            raise ValueError("saved vertical median disagrees with raw rows")
        left, right = result["left_vertical"], result["right_vertical"]
        result["binocular_minus_mean_monocular_medians"] = (
            result["vertical"] - (left + right) / 2
            if left is not None and right is not None
            else None
        )
        presentations.append(result)
    return presentations


def _difference(first: float | None, second: float | None) -> float | None:
    return second - first if first is not None and second is not None else None


def _pairs(presentations: list[dict], slope: float) -> list[dict]:
    by_pass = {
        name: {(p["target_x"], p["target_y"]): p for p in presentations if p["pass"] == name}
        for name in ("calibration", "pass_a", "pass_b")
    }
    pairs = []
    for coordinate in by_pass["calibration"]:
        for label, first_name, second_name in (
            ("calibration_to_a", "calibration", "pass_a"),
            ("calibration_to_b", "calibration", "pass_b"),
            ("a_to_b", "pass_a", "pass_b"),
        ):
            first, second = by_pass[first_name][coordinate], by_pass[second_name][coordinate]
            result = {"target_x": coordinate[0], "target_y": coordinate[1], "comparison": label}
            for name in MEASURES:
                change = _difference(first[name], second[name])
                result[f"delta_{name}"] = change
                result[f"abs_delta_{name}"] = abs(change) if change is not None else None
            left, right = result["delta_left_vertical"], result["delta_right_vertical"]
            result["common_mode_vertical_delta"] = (
                (left + right) / 2 if left is not None and right is not None else None
            )
            result["differential_vertical_delta"] = (
                left - right if left is not None and right is not None else None
            )
            result["same_direction"] = (
                left * right > 0
                if left is not None and right is not None and left * right != 0
                else None
            )
            result["larger_abs_eye"] = (
                (
                    "left"
                    if abs(left) > abs(right)
                    else "right"
                    if abs(right) > abs(left)
                    else "equal"
                )
                if left is not None and right is not None
                else None
            )
            result["mapped_y_delta"] = slope * result["delta_vertical"]
            result["abs_mapped_y_delta"] = abs(result["mapped_y_delta"])
            pairs.append(result)
    return pairs


def _summary(pairs: list[dict]) -> dict:
    def absolute_values(name: str) -> list[float]:
        return [abs(p[name]) for p in pairs if p[name] is not None]

    result = {"pair_count": len(pairs)}
    for source in (
        "delta_vertical",
        "delta_left_vertical",
        "delta_right_vertical",
        "common_mode_vertical_delta",
        "differential_vertical_delta",
        "delta_head_center_y",
        "delta_binocular_eye_opening",
    ):
        values = absolute_values(source)
        result[f"median_abs_{source}"] = _median_or_none(values)
        if source == "differential_vertical_delta":
            result["p95_abs_differential_vertical_delta"] = (
                percentile(values, 95) if values else None
            )
            result["max_abs_differential_vertical_delta"] = max(values) if values else None
    result["same_direction_count"] = sum(p["same_direction"] is True for p in pairs)
    result["opposite_direction_count"] = sum(p["same_direction"] is False for p in pairs)
    result["zero_or_missing_direction_count"] = sum(p["same_direction"] is None for p in pairs)
    decisive = result["same_direction_count"] + result["opposite_direction_count"]
    result["same_direction_proportion"] = (
        result["same_direction_count"] / decisive if decisive else None
    )
    return result


def _association(pairs: list[dict], x_name: str, y_name: str) -> dict | None:
    observed = [
        (p[x_name], p[y_name]) for p in pairs if p[x_name] is not None and p[y_name] is not None
    ]
    if not observed:
        return None
    x, y = zip(*observed, strict=True)
    return {"pair_count": len(observed), "spearman": spearman(list(x), list(y))}


def _frame_binocular_identity(rows: list[dict]) -> dict:
    residuals = [
        abs(
            _finite(row["vertical"], "vertical")
            - (
                _finite(row["left_vertical"], "left vertical")
                + _finite(row["right_vertical"], "right vertical")
            )
            / 2
        )
        for row in rows
        if row["status"] == "usable"
        and all(
            row.get(name) is not None for name in ("vertical", "left_vertical", "right_vertical")
        )
    ]
    return {"checked_count": len(residuals), "max_abs_residual": max(residuals, default=None)}


def analyze_session(report: dict) -> dict:
    """Aggregate one saved session and return all 27 paired descriptive comparisons."""
    if not isinstance(report, dict) or not report.get("participant") or not report.get("session"):
        raise ValueError("participant and session are required")
    coefficients = report.get("mapping_coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("mapping coefficients are required")
    slope = _finite(coefficients.get("y_slope"), "y slope")
    presentations = _aggregate(report)
    pairs = _pairs(presentations, slope)
    associations = {}
    for label, x, y in (
        ("vertical_vs_head_center_y", "delta_vertical", "delta_head_center_y"),
        ("abs_vertical_vs_abs_head_center_y", "abs_delta_vertical", "abs_delta_head_center_y"),
        ("vertical_vs_binocular_eye_opening", "delta_vertical", "delta_binocular_eye_opening"),
        (
            "abs_vertical_vs_abs_binocular_eye_opening",
            "abs_delta_vertical",
            "abs_delta_binocular_eye_opening",
        ),
        ("left_vertical_vs_left_eye_opening", "delta_left_vertical", "delta_left_eye_opening"),
        ("right_vertical_vs_right_eye_opening", "delta_right_vertical", "delta_right_eye_opening"),
    ):
        associations[label] = _association(pairs, x, y)
    return {
        "participant": report["participant"],
        "session": report["session"],
        "y_slope": slope,
        "presentations": presentations,
        "pairs": pairs,
        "summary": _summary(pairs),
        "associations": associations,
        "availability": {
            f"{name}_presentations": sum(p[name] is not None for p in presentations)
            for name in MEASURES
        },
        "frame_binocular_identity": _frame_binocular_identity(report["rows"]),
        "max_abs_binocular_minus_mean_monocular_medians": max(
            (
                abs(p["binocular_minus_mean_monocular_medians"])
                for p in presentations
                if p["binocular_minus_mean_monocular_medians"] is not None
            ),
            default=None,
        ),
        "top_outliers": sorted(pairs, key=lambda p: -p["abs_delta_vertical"])[:5],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            [analyze_session(json.loads(path.read_text())) for path in args.reports], indent=2
        )
    )


if __name__ == "__main__":
    main()
