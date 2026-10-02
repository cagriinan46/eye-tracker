"""Recompute preregistered feature-level contrasts from numerical capture rows."""

import argparse
import json
from math import isclose, isfinite
from pathlib import Path
from statistics import median

from experiments.eye_opening_controlled_study.protocol import CONDITIONS, TARGETS, schedule
from experiments.vertical_feature_covariates.analysis import spearman
from eye_tracker.gaze.estimator import UnavailableReason
from validation.real_calibration import percentile

FIELDS = (
    "vertical",
    "left_vertical",
    "right_vertical",
    "horizontal",
    "left_eye_opening",
    "right_eye_opening",
    "binocular_eye_opening",
    "head_center_y",
    "predicted_y",
)
COMPARISONS = (
    ("natural", "narrow"),
    ("natural", "wide"),
    ("narrow", "wide"),
)
UNAVAILABLE_STATUSES = {"unavailable_frame", "unavailable_no_face", "unavailable_geometry"} | {
    reason.value for reason in UnavailableReason
}


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _median_or_none(values: list[float]) -> float | None:
    return median(values) if values else None


def aggregate(report: dict) -> list[dict]:
    """Take independent field medians from all usable rows in each presentation."""
    plan = schedule()
    rows = report.get("rows")
    saved = report.get("presentations")
    if not isinstance(rows, list) or not isinstance(saved, list) or len(saved) != len(plan):
        raise ValueError("raw rows and all 36 saved presentations are required")
    minimum = report.get("minimum_usable_samples_per_presentation")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("invalid minimum usable sample count")
    groups: dict[int, list[dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("raw row must be an object")
        order = row.get("presentation_order")
        if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= len(plan):
            raise ValueError("invalid presentation order")
        item = plan[order - 1]
        expected = (
            report.get("participant"),
            report.get("session"),
            item.phase,
            item.target.name,
            item.target.x,
            item.target.y,
            item.condition,
            item.block,
        )
        observed = tuple(
            row.get(name)
            for name in (
                "participant",
                "session",
                "phase",
                "target_id",
                "target_x",
                "target_y",
                "condition",
                "block",
            )
        )
        if observed != expected or row.get("status") not in ({"usable"} | UNAVAILABLE_STATUSES):
            raise ValueError("raw row disagrees with protocol or has invalid status")
        groups.setdefault(order, []).append(row)
    result = []
    for item, stored in zip(plan, saved, strict=True):
        group = groups.get(item.order, [])
        usable = [row for row in group if row["status"] == "usable"]
        if len(usable) < minimum:
            raise ValueError(f"presentation {item.order} has insufficient usable samples")
        for row in usable:
            if row.get("left_vertical") is not None and row.get("right_vertical") is not None:
                monocular_mean = (
                    _number(row["left_vertical"], "left vertical")
                    + _number(row["right_vertical"], "right vertical")
                ) / 2
                if not isclose(
                    _number(row.get("vertical"), "binocular vertical"),
                    monocular_mean,
                    rel_tol=0,
                    abs_tol=1e-12,
                ):
                    raise ValueError("recorded binocular feature disagrees with per-eye mean")
        if not isinstance(stored, dict) or any(
            (
                stored.get("order") != item.order,
                stored.get("phase") != item.phase,
                stored.get("target_id") != item.target.name,
                stored.get("target_x") != item.target.x,
                stored.get("target_y") != item.target.y,
                stored.get("condition") != item.condition,
                stored.get("block") != item.block,
                stored.get("usable_count") != len(usable),
                stored.get("unavailable_count") != len(group) - len(usable),
                stored.get("sampling_attempts") != len(group),
            )
        ):
            raise ValueError("saved presentation disagrees with raw rows")
        summary = {
            "order": item.order,
            "phase": item.phase,
            "target_id": item.target.name,
            "target_x": item.target.x,
            "target_y": item.target.y,
            "condition": item.condition,
            "block": item.block,
            "usable_count": len(usable),
            "unavailable_count": len(group) - len(usable),
        }
        for field in FIELDS:
            values = [_number(row[field], field) for row in usable if row.get(field) is not None]
            summary[field] = _median_or_none(values)
            summary[f"{field}_count"] = len(values)
            summary[f"{field}_p95_p05"] = (
                percentile(values, 95) - percentile(values, 5) if values else None
            )
        if summary["vertical_count"] != len(usable):
            raise ValueError("every usable row needs binocular vertical")
        left, right = summary["left_vertical"], summary["right_vertical"]
        summary["binocular_minus_mean_monocular_medians"] = (
            summary["vertical"] - (left + right) / 2
            if left is not None and right is not None
            else None
        )
        if not isclose(
            summary["vertical"],
            _number(stored.get("vertical_feature"), "saved vertical"),
            rel_tol=0,
            abs_tol=1e-12,
        ):
            raise ValueError("saved and raw vertical medians disagree")
        result.append(summary)
    return result


def _delta(first: float | None, second: float | None) -> float | None:
    return second - first if first is not None and second is not None else None


def compare_conditions(presentations: list[dict], slope: float | None = None) -> list[dict]:
    """For each block and fixed target, compute second condition minus first."""
    by_key = {
        (p["block"], p["target_x"], p["target_y"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    pairs = []
    for block in range(1, 4):
        for target in TARGETS:
            for first_name, second_name in COMPARISONS:
                first = by_key.get((block, target.x, target.y, first_name))
                second = by_key.get((block, target.x, target.y, second_name))
                if first is None or second is None:
                    raise ValueError("missing fixed-target condition presentation")
                result = {
                    "block": block,
                    "target_id": target.name,
                    "target_x": target.x,
                    "target_y": target.y,
                    "comparison": f"{second_name}_minus_{first_name}",
                }
                for field in FIELDS:
                    change = _delta(first[field], second[field])
                    result[f"delta_{field}"] = change
                    result[f"abs_delta_{field}"] = abs(change) if change is not None else None
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
                result["mapped_y_delta"] = (
                    slope * result["delta_vertical"] if slope is not None else None
                )
                pairs.append(result)
    return pairs


def _median_field(records: list[dict], field: str) -> float | None:
    return _median_or_none([r[field] for r in records if r[field] is not None])


def _opening_vertical_spearman(pairs: list[dict]) -> float | None:
    complete = [
        pair
        for pair in pairs
        if pair["delta_binocular_eye_opening"] is not None and pair["delta_vertical"] is not None
    ]
    return spearman(
        [pair["delta_binocular_eye_opening"] for pair in complete],
        [pair["delta_vertical"] for pair in complete],
    )


def summarize(presentations: list[dict], pairs: list[dict]) -> dict:
    """Summarize measured manipulation, directional replication, and confounds."""
    result = []
    for target in TARGETS:
        row = [
            p for p in presentations if p["phase"] == "diagnostic" and p["target_id"] == target.name
        ]
        by_condition = {
            condition: [p for p in row if p["condition"] == condition] for condition in CONDITIONS
        }
        conditions = {}
        for condition, records in by_condition.items():
            opening_values = sorted(
                p["binocular_eye_opening"]
                for p in records
                if p["binocular_eye_opening"] is not None
            )
            conditions[condition] = {
                field: _median_field(records, field)
                for field in (
                    "vertical",
                    "left_vertical",
                    "right_vertical",
                    "binocular_eye_opening",
                    "head_center_y",
                )
            }
            conditions[condition]["opening_range"] = (
                [min(opening_values), max(opening_values)] if opening_values else None
            )
            conditions[condition]["opening_p95_p05_median"] = _median_field(
                records, "binocular_eye_opening_p95_p05"
            )
        row_pairs = [pair for pair in pairs if pair["target_id"] == target.name]
        comparisons = {}
        for first, second in COMPARISONS:
            label = f"{second}_minus_{first}"
            records = [pair for pair in row_pairs if pair["comparison"] == label]
            comparisons[label] = {
                field: _median_field(records, field)
                for field in (
                    "delta_vertical",
                    "abs_delta_vertical",
                    "delta_left_vertical",
                    "delta_right_vertical",
                    "delta_binocular_eye_opening",
                    "delta_head_center_y",
                    "abs_delta_head_center_y",
                    "common_mode_vertical_delta",
                    "differential_vertical_delta",
                    "mapped_y_delta",
                )
            }
            comparisons[label]["max_abs_delta_head_center_y"] = max(
                (
                    r["abs_delta_head_center_y"]
                    for r in records
                    if r["abs_delta_head_center_y"] is not None
                ),
                default=None,
            )
            comparisons[label]["same_direction_count"] = sum(
                r["same_direction"] is True for r in records
            )
            comparisons[label]["opposite_direction_count"] = sum(
                r["same_direction"] is False for r in records
            )
        wide_natural = [p for p in row_pairs if p["comparison"] == "wide_minus_natural"]
        with_opening_increase = [
            p
            for p in wide_natural
            if p["delta_binocular_eye_opening"] is not None and p["delta_binocular_eye_opening"] > 0
        ]
        direction = {
            "wide_greater_opening_blocks": len(with_opening_increase),
            "vertical_positive": sum(p["delta_vertical"] > 0 for p in with_opening_increase),
            "vertical_negative": sum(p["delta_vertical"] < 0 for p in with_opening_increase),
            "vertical_zero": sum(p["delta_vertical"] == 0 for p in with_opening_increase),
        }
        ordered_blocks = []
        for block in sorted({presentation["block"] for presentation in row}):
            by_label = {p["condition"]: p for p in row if p["block"] == block}
            values = [
                by_label[label]["binocular_eye_opening"] for label in ("narrow", "natural", "wide")
            ]
            opening_ordered = (
                all(v is not None for v in values) and values[0] < values[1] < values[2]
            )
            vertical = [by_label[label]["vertical"] for label in ("narrow", "natural", "wide")]
            ordered_blocks.append(
                {
                    "block": block,
                    "opening_ordered": opening_ordered,
                    "vertical_increasing": opening_ordered
                    and vertical[0] < vertical[1] < vertical[2],
                    "vertical_decreasing": opening_ordered
                    and vertical[0] > vertical[1] > vertical[2],
                }
            )
        opening_medians = [
            conditions[label]["binocular_eye_opening"] for label in ("narrow", "natural", "wide")
        ]
        opening_range_overlap = {}
        for first, second in COMPARISONS:
            first_range = conditions[first]["opening_range"]
            second_range = conditions[second]["opening_range"]
            opening_range_overlap[f"{second}_minus_{first}"] = (
                max(first_range[0], second_range[0]) <= min(first_range[1], second_range[1])
                if first_range is not None and second_range is not None
                else None
            )
        result.append(
            {
                "target_id": target.name,
                "target_y": target.y,
                "conditions": conditions,
                "opening_median_ordered": all(v is not None for v in opening_medians)
                and opening_medians[0] < opening_medians[1] < opening_medians[2],
                "opening_separations": {
                    f"{b}_minus_{a}": _delta(
                        conditions[a]["binocular_eye_opening"],
                        conditions[b]["binocular_eye_opening"],
                    )
                    for a, b in COMPARISONS
                },
                "opening_range_overlap": opening_range_overlap,
                "comparisons": comparisons,
                "wide_natural_direction": direction,
                "ordered_blocks": ordered_blocks,
            }
        )
    return {
        "rows": result,
        "opening_ordered_row_count": sum(r["opening_median_ordered"] for r in result),
        "opening_ordered_block_count": sum(
            b["opening_ordered"] for r in result for b in r["ordered_blocks"]
        ),
        "diagnostic_presentation_count": sum(p["phase"] == "diagnostic" for p in presentations),
        "fixed_target_comparison_count": len(pairs),
    }


def analyze(report: dict) -> dict:
    presentations = aggregate(report)
    slope = _number(report["mapping_coefficients"]["y_slope"], "y slope")
    pairs = compare_conditions(presentations, slope)
    result = {
        "participant": report["participant"],
        "session": report["session"],
        "capture": {
            key: report.get(key)
            for key in (
                "camera_index",
                "camera_resolution",
                "elapsed_seconds",
                "failed_camera_reads_including_settling",
                "no_face_observations_including_settling",
            )
        },
        "y_slope": slope,
        "presentations": presentations,
        "condition_pairs": pairs,
        "summary": summarize(presentations, pairs),
        "measured_opening_vertical_spearman": _opening_vertical_spearman(pairs),
    }
    if report["session"] == "live-3":
        result["notification_sensitivity"] = notification_sensitivity(presentations, pairs)
    return result


def notification_sensitivity(presentations: list[dict], pairs: list[dict]) -> dict:
    """Secondary analysis excluding exactly live-3's first diagnostic target trio."""
    affected = [
        p for p in presentations if p["phase"] == "diagnostic" and p["order"] in (10, 11, 12)
    ]
    if (
        len(affected) != 3
        or {(p["target_id"], p["block"]) for p in affected} != {("upper", 1)}
        or {p["condition"] for p in affected} != set(CONDITIONS)
    ):
        raise ValueError("first diagnostic trio does not match reported notification boundary")
    retained_presentations = [p for p in presentations if p not in affected]
    retained_pairs = [p for p in pairs if not (p["block"] == 1 and p["target_id"] == "upper")]
    return {
        "excluded_orders": [p["order"] for p in affected],
        "excluded_target": "upper",
        "excluded_block": 1,
        "summary": summarize(retained_presentations, retained_pairs),
        "measured_opening_vertical_spearman": _opening_vertical_spearman(retained_pairs),
        "condition_pairs": retained_pairs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            [analyze(json.loads(path.read_text(encoding="utf-8"))) for path in args.reports],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
