"""Validate and summarize raw numerical geometry for later descriptive analysis."""

import argparse
import json
from itertools import combinations
from math import atan2, hypot, isclose, isfinite
from pathlib import Path
from statistics import median

from experiments.eye_geometry_decomposition_study.geometry import geometry_metrics
from experiments.eye_geometry_decomposition_study.protocol import (
    CONDITIONS,
    CUE_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGETS,
    schedule,
)
from eye_tracker.gaze.estimator import UnavailableReason
from validation.real_calibration import SAMPLE_SECONDS, SETTLE_SECONDS

UNAVAILABLE = {"unavailable_frame", "unavailable_no_face", "unavailable_geometry"} | {
    reason.value for reason in UnavailableReason
}
METRIC_NAMES = (
    "iris_x",
    "iris_y",
    "upper_x",
    "upper_y",
    "lower_x",
    "lower_y",
    "lid_mid_x",
    "lid_mid_y",
    "corner_a_x",
    "corner_a_y",
    "corner_b_x",
    "corner_b_y",
    "corner_mid_x",
    "corner_mid_y",
    "eye_width_px",
    "axis_angle_rad",
    "normal_x",
    "normal_y",
    "orientation_polarity",
    "iris_local_parallel",
    "iris_local_vertical",
    "upper_local_vertical",
    "lower_local_vertical",
    "lid_mid_local_vertical",
    "iris_vs_lid_mid_vertical",
    "aperture",
    "lid_gap_projected_px",
    "horizontal",
    "vertical",
)
BINOCULAR_NAMES = (
    "vertical",
    "horizontal",
    "binocular_eye_opening",
    "head_center_x",
    "head_center_y",
    "inter_eye_scale_px",
    "eye_line_angle_rad",
)
OTHER_CONDITIONS = tuple(c for c in CONDITIONS if c != "natural")
COMPARISONS = tuple(("natural", c) for c in OTHER_CONDITIONS) + tuple(
    combinations(OTHER_CONDITIONS, 2)
)
REFERENCE_POINTS = ("corner_a", "corner_b", "upper_lid", "lower_lid")


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _equal(actual: object, expected: float, label: str) -> None:
    if not isclose(_finite(actual, label), expected, rel_tol=0, abs_tol=1e-10):
        raise ValueError(f"{label} disagrees with reconstructed geometry")


def _capture_metadata(report: dict) -> tuple[int, int, int]:
    if (
        report.get("protocol_name") != PROTOCOL_NAME
        or report.get("protocol_version") != PROTOCOL_VERSION
        or report.get("order_seed") != ORDER_SEED
        or report.get("ready_screen_used") is not True
        or report.get("cue_seconds") != CUE_SECONDS
        or report.get("settle_seconds") != SETTLE_SECONDS
        or report.get("sample_seconds") != SAMPLE_SECONDS
    ):
        raise ValueError("incompatible protocol metadata; pilot/older studies are excluded")
    if report.get("participant") != "cagri" or report.get("session") not in (
        "live-1",
        "live-2",
        "live-3",
    ):
        raise ValueError("unexpected participant or session")
    resolution = report.get("camera_resolution")
    if (
        not isinstance(resolution, (list, tuple))
        or len(resolution) != 2
        or any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in resolution)
    ):
        raise ValueError("valid camera resolution is required")
    camera_index = report.get("camera_index")
    if isinstance(camera_index, bool) or not isinstance(camera_index, int) or camera_index < 0:
        raise ValueError("valid camera index is required")
    minimum = report.get("minimum_usable_samples_per_presentation")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("valid minimum usable sample count is required")
    mapping = report.get("mapping_coefficients")
    if not isinstance(mapping, dict):
        raise ValueError("mapping coefficients are required")
    _finite(mapping.get("y_slope"), "mapping y slope")
    _finite(mapping.get("y_intercept"), "mapping y intercept")
    return resolution[0], resolution[1], minimum


def _validated_metrics(row: dict, width: int, height: int) -> dict[str, dict[str, float]]:
    if row.get("frame_width") != width or row.get("frame_height") != height:
        raise ValueError("sample frame dimensions disagree with capture metadata")
    geometry = row.get("geometry")
    if not isinstance(geometry, dict) or set(geometry) != {"left", "right"}:
        raise ValueError("both eyes' primitive geometry is required")
    metrics = {side: geometry_metrics(geometry[side], width, height) for side in ("left", "right")}
    for side in ("left", "right"):
        _equal(row.get(f"{side}_vertical"), metrics[side]["vertical"], f"{side} vertical")
        _equal(row.get(f"{side}_horizontal"), metrics[side]["horizontal"], f"{side} horizontal")
        _equal(row.get(f"{side}_eye_opening"), metrics[side]["aperture"], f"{side} opening")
    for field in ("vertical", "horizontal"):
        _equal(
            row.get(field),
            (metrics["left"][field] + metrics["right"][field]) / 2,
            f"binocular {field}",
        )
    _equal(
        row.get("binocular_eye_opening"),
        (metrics["left"]["aperture"] + metrics["right"]["aperture"]) / 2,
        "binocular opening",
    )
    left, right = metrics["left"], metrics["right"]
    _equal(
        row.get("head_center_x"),
        (left["corner_mid_x"] + right["corner_mid_x"]) / 2,
        "head center x",
    )
    _equal(
        row.get("head_center_y"),
        (left["corner_mid_y"] + right["corner_mid_y"]) / 2,
        "head center y",
    )
    _equal(
        row.get("inter_eye_scale_px"),
        hypot(
            (right["corner_mid_x"] - left["corner_mid_x"]) * width,
            (right["corner_mid_y"] - left["corner_mid_y"]) * height,
        ),
        "inter-eye scale",
    )
    _equal(
        row.get("eye_line_angle_rad"),
        atan2(
            (right["corner_mid_y"] - left["corner_mid_y"]) * height,
            (right["corner_mid_x"] - left["corner_mid_x"]) * width,
        ),
        "eye line angle",
    )
    _finite(row.get("monotonic_seconds"), "monotonic seconds")
    timestamp = row.get("timestamp_ns")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError("sample timestamp must be nonnegative integer")
    return metrics


def aggregate(report: dict) -> list[dict]:
    """Take independent presentation medians from validated raw numerical rows."""
    width, height, minimum = _capture_metadata(report)
    plan = schedule()
    saved, rows = report.get("presentations"), report.get("rows")
    if not isinstance(saved, list) or len(saved) != len(plan) or not isinstance(rows, list):
        raise ValueError("all 54 presentations and raw rows are required")
    groups: dict[int, list[dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("raw row must be an object")
        order = row.get("presentation_order")
        if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= len(plan):
            raise ValueError("invalid presentation order")
        item = plan[order - 1]
        if (
            row.get("participant") != report.get("participant")
            or row.get("session") != report.get("session")
            or any(row.get(key) != value for key, value in item.identity().items())
            or row.get("status") not in ({"usable"} | UNAVAILABLE)
        ):
            raise ValueError("raw row disagrees with protocol identity or status")
        groups.setdefault(order, []).append(row)
    result = []
    for item, recorded in zip(plan, saved, strict=True):
        group = groups.get(item.order, [])
        usable = [row for row in group if row["status"] == "usable"]
        if len(usable) < minimum:
            raise ValueError(f"presentation {item.order} has insufficient usable samples")
        if (
            not isinstance(recorded, dict)
            or recorded.get("order") != item.order
            or any(recorded.get(key) != value for key, value in item.identity().items())
            or recorded.get("usable_count") != len(usable)
            or recorded.get("unavailable_count") != len(group) - len(usable)
            or recorded.get("sampling_attempts") != len(group)
        ):
            raise ValueError("saved presentation disagrees with raw rows or protocol")
        sample_metrics = [_validated_metrics(row, width, height) for row in usable]
        summary = {
            "order": item.order,
            **item.identity(),
            "usable_count": len(usable),
            "unavailable_count": len(group) - len(usable),
            "first_monotonic_seconds": usable[0]["monotonic_seconds"],
            "last_monotonic_seconds": usable[-1]["monotonic_seconds"],
        }
        for field in BINOCULAR_NAMES:
            summary[field] = median(_finite(row.get(field), field) for row in usable)
        for side in ("left", "right"):
            summary[side] = {
                field: median(metrics[side][field] for metrics in sample_metrics)
                for field in METRIC_NAMES
            }
        _equal(recorded.get("vertical_feature"), summary["vertical"], "saved vertical median")
        result.append(summary)
    return result


def manipulation_check(presentations: list[dict]) -> dict:
    """Report measured openings for every matched five-condition set."""
    by_key = {
        (p["block"], p["target_id"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    triples = []
    for block in range(1, 4):
        for target in TARGETS:
            opening = {
                condition: by_key[(block, target.name, condition)]["binocular_eye_opening"]
                for condition in CONDITIONS
            }
            values = [opening[condition] for condition in CONDITIONS]
            triples.append(
                {
                    "block": block,
                    "target_id": target.name,
                    "target_y": target.y,
                    "opening": opening,
                    "strictly_ordered": all(a < b for a, b in zip(values, values[1:])),
                }
            )
    return {
        "triples": triples,
        "ordered_five_level_count": sum(t["strictly_ordered"] for t in triples),
    }


def _vertical_with_components(iris: list[float], reference: dict, width: int, height: int) -> float:
    """Production vertical formula with a separately substitutable iris and frame."""
    ax, ay = _point_xy(reference["corner_a"], width, height)
    bx, by = _point_xy(reference["corner_b"], width, height)
    ux, uy = _point_xy(reference["upper_lid"], width, height)
    lx, ly = _point_xy(reference["lower_lid"], width, height)
    ix, iy = _point_xy(iris, width, height)
    axis_x, axis_y = bx - ax, by - ay
    eye_width = hypot(axis_x, axis_y)
    if eye_width <= 1e-6:
        raise ValueError("representative corner width is degenerate")
    normal_x, normal_y = -axis_y / eye_width, axis_x / eye_width
    if (lx - ux) * normal_x + (ly - uy) * normal_y < 0:
        normal_x, normal_y = -normal_x, -normal_y
    return ((ix - (ax + bx) / 2) * normal_x + (iy - (ay + by) / 2) * normal_y) / eye_width


def _point_xy(point: list[float], width: int, height: int) -> tuple[float, float]:
    if not isinstance(point, list) or len(point) != 2:
        raise ValueError("representative point needs x/y coordinates")
    return _finite(point[0], "point x") * width, _finite(point[1], "point y") * height


def decompose_vertical(
    natural: dict, changed: dict, width: int, height: int, observed_delta: float
) -> dict[str, float]:
    """Symmetric two-factor attribution plus median-aggregation residual.

    f(I,R) uses the production iris/corner/lid geometry. The iris and reference
    contributions are the mean of the two substitution orders (Shapley form).
    The interaction is split equally between them; the remaining difference
    to the actual median-feature contrast is reported, never silently dropped.
    """
    i0, i1 = natural["iris_center"], changed["iris_center"]
    f00 = _vertical_with_components(i0, natural, width, height)
    f10 = _vertical_with_components(i1, natural, width, height)
    f01 = _vertical_with_components(i0, changed, width, height)
    f11 = _vertical_with_components(i1, changed, width, height)
    interaction = f11 - f10 - f01 + f00
    iris = (f10 - f00 + f11 - f01) / 2
    reference = (f01 - f00 + f11 - f10) / 2
    return {
        "iris_position_contribution": iris,
        "reference_frame_contribution": reference,
        "interaction_split_between_components": interaction,
        "median_aggregation_residual": observed_delta - (iris + reference),
        "representative_first_vertical": f00,
        "representative_second_vertical": f11,
    }


def representative_geometry(report: dict) -> dict[int, dict[str, dict]]:
    """Per-presentation medians of primitive coordinates, not synthetic frames."""
    groups: dict[int, list[dict]] = {}
    for row in report["rows"]:
        if row["status"] == "usable":
            groups.setdefault(row["presentation_order"], []).append(row)
    result = {}
    for order, rows in groups.items():
        result[order] = {}
        for side in ("left", "right"):
            result[order][side] = {
                name: [
                    median(row["geometry"][side][name][coordinate] for row in rows)
                    for coordinate in (0, 1)
                ]
                for name in ("iris_center", *REFERENCE_POINTS)
            }
    return result


def compare_conditions(
    presentations: list[dict],
    y_slope: float,
    representatives: dict[int, dict[str, dict]] | None = None,
    width: int | None = None,
    height: int | None = None,
) -> list[dict]:
    """All ten predeclared condition pairs at the same target and block."""
    by_key = {
        (p["block"], p["target_id"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    pairs = []
    for block in range(1, 4):
        for target in TARGETS:
            for first_name, second_name in COMPARISONS:
                first = by_key[(block, target.name, first_name)]
                second = by_key[(block, target.name, second_name)]
                result = {
                    "block": block,
                    "target_id": target.name,
                    "target_x": target.x,
                    "target_y": target.y,
                    "comparison": f"{second_name}_minus_{first_name}",
                    "first_order": first["order"],
                    "second_order": second["order"],
                    "first_monotonic_seconds": first["first_monotonic_seconds"],
                    "second_monotonic_seconds": second["first_monotonic_seconds"],
                }
                for field in BINOCULAR_NAMES:
                    result[f"delta_{field}"] = second[field] - first[field]
                result["delta_binocular_opening"] = result["delta_binocular_eye_opening"]
                result["mapped_y_delta"] = y_slope * result["delta_vertical"]
                for side in ("left", "right"):
                    result[f"delta_{side}"] = {
                        field: second[side][field] - first[side][field] for field in METRIC_NAMES
                    }
                    if representatives is not None:
                        if width is None or height is None:
                            raise ValueError("frame dimensions are required for decomposition")
                        result[f"decomposition_{side}"] = decompose_vertical(
                            representatives[first["order"]][side],
                            representatives[second["order"]][side],
                            width,
                            height,
                            result[f"delta_{side}"]["vertical"],
                        )
                pairs.append(result)
    return pairs


def analyze(report: dict) -> dict:
    presentations = aggregate(report)
    slope = _finite(report["mapping_coefficients"]["y_slope"], "mapping y slope")
    width, height = report["camera_resolution"]
    return {
        "participant": report["participant"],
        "session": report["session"],
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "y_slope": slope,
        "presentations": presentations,
        "manipulation_check": manipulation_check(presentations),
        "condition_pairs": compare_conditions(
            presentations, slope, representative_geometry(report), width, height
        ),
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
