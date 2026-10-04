"""Validate face-reference captures and prepare matched geometry contrasts."""

import argparse
import json
from math import atan2, cos, isclose, isfinite, sin
from pathlib import Path
from statistics import median

from experiments.eye_geometry_decomposition_study.analysis import UNAVAILABLE, _validated_metrics
from experiments.face_reference_corner_stability_study.face_reference import (
    EYE_POINTS,
    FACE_ANCHOR_INDICES,
    FACE_REFERENCE_METHOD,
    apply_similarity,
    calibration_template,
    eye_summary,
    fit_similarity,
)
from experiments.face_reference_corner_stability_study.protocol import (
    CONDITIONS,
    CUE_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGETS,
    schedule,
)
from validation.real_calibration import SAMPLE_SECONDS, SETTLE_SECONDS

POINT_FIELDS = (*EYE_POINTS, "corner_midpoint", "lid_midpoint")
SCALAR_FIELDS = (
    "corner_span_px",
    "corner_angle_rad",
    "eye_opening",
    "vertical",
    "iris_local_parallel",
    "iris_local_vertical",
)
ALIGN_FIELDS = ("scale", "rotation_rad", "translation_x_px", "translation_y_px", "rms_px")


def wrapped_angle_delta(first: float, second: float) -> float:
    """Signed second-minus-first angle without artificial ±π jumps."""
    difference = second - first
    return atan2(sin(difference), cos(difference))


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _equal(actual: object, expected: float, name: str) -> None:
    if not isclose(_finite(actual, name), expected, rel_tol=0, abs_tol=1e-9):
        raise ValueError(f"{name} disagrees with reconstructed geometry")


def _metadata(report: dict) -> tuple[int, int, int]:
    if (
        report.get("protocol_name") != PROTOCOL_NAME
        or report.get("protocol_version") != PROTOCOL_VERSION
        or report.get("order_seed") != ORDER_SEED
        or report.get("ready_screen_used") is not True
        or report.get("cue_seconds") != CUE_SECONDS
        or report.get("settle_seconds") != SETTLE_SECONDS
        or report.get("sample_seconds") != SAMPLE_SECONDS
        or report.get("face_reference_method") != FACE_REFERENCE_METHOD
        or report.get("face_landmark_indices") != list(FACE_ANCHOR_INDICES)
    ):
        raise ValueError("incompatible protocol or face-reference metadata")
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
        raise ValueError("camera resolution required")
    index = report.get("camera_index")
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("camera index required")
    minimum = report.get("minimum_usable_samples_per_presentation")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("minimum usable sample count required")
    mapping = report.get("mapping_coefficients")
    if not isinstance(mapping, dict):
        raise ValueError("mapping coefficients required")
    _finite(mapping.get("y_slope"), "y slope")
    _finite(mapping.get("y_intercept"), "y intercept")
    return resolution[0], resolution[1], minimum


def _validate_eye_record(saved: dict, expected: dict, name: str) -> None:
    if not isinstance(saved, dict) or set(saved) != set(expected):
        raise ValueError(f"{name} fields disagree with required geometry")
    for key in POINT_FIELDS:
        point = saved[key]
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError(f"{name} {key} point required")
        for actual, value in zip(point, expected[key], strict=True):
            _equal(actual, value, f"{name} {key}")
    for key in SCALAR_FIELDS:
        _equal(saved[key], expected[key], f"{name} {key}")


def _validate_usable(row: dict, template: list, width: int, height: int) -> None:
    _validated_metrics(row, width, height)
    anchors = row.get("face_anchors")
    if not isinstance(anchors, list) or len(anchors) != len(FACE_ANCHOR_INDICES):
        raise ValueError("all non-eye face anchors required")
    fitted = fit_similarity(anchors, template, width, height)
    saved_alignment = row.get("face_alignment")
    if not isinstance(saved_alignment, dict) or set(saved_alignment) != set(fitted):
        raise ValueError("face alignment fields required")
    for field in ALIGN_FIELDS:
        _equal(saved_alignment[field], fitted[field], f"face alignment {field}")
    for coordinate_frame in ("image_eye_geometry", "face_normalized_geometry"):
        saved = row.get(coordinate_frame)
        if not isinstance(saved, dict) or set(saved) != {"left", "right"}:
            raise ValueError(f"{coordinate_frame} needs both eyes")
        for side in ("left", "right"):
            raw = row["geometry"][side]
            points = (
                raw
                if coordinate_frame == "image_eye_geometry"
                else {
                    name: apply_similarity(raw[name], fitted, width, height) for name in EYE_POINTS
                }
            )
            _validate_eye_record(saved[side], eye_summary(points, width, height), coordinate_frame)
            _equal(saved[side]["vertical"], row[f"{side}_vertical"], f"{side} vertical")
            _equal(saved[side]["eye_opening"], row[f"{side}_eye_opening"], f"{side} opening")


def aggregate(report: dict) -> list[dict]:
    """Strict protocol validation and independent per-field presentation medians."""
    width, height, minimum = _metadata(report)
    plan = schedule()
    saved, rows = report.get("presentations"), report.get("rows")
    if not isinstance(saved, list) or len(saved) != len(plan) or not isinstance(rows, list):
        raise ValueError("all 36 presentations and numerical rows required")
    template = calibration_template(rows, width, height)
    saved_template = report.get("face_reference_template_px")
    if not isinstance(saved_template, list) or len(saved_template) != len(template):
        raise ValueError("calibration-only face reference template required")
    for a, b in zip(saved_template, template, strict=True):
        if not isinstance(a, list) or len(a) != 2:
            raise ValueError("face template point required")
        for x, y in zip(a, b, strict=True):
            _equal(x, y, "calibration face template")
    groups: dict[int, list[dict]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("raw row must be an object")
        order = row.get("presentation_order")
        if isinstance(order, bool) or not isinstance(order, int) or not 1 <= order <= len(plan):
            raise ValueError("invalid presentation order")
        item = plan[order - 1]
        if (
            row.get("participant") != report["participant"]
            or row.get("session") != report["session"]
            or any(row.get(key) != value for key, value in item.identity().items())
            or row.get("status") not in ({"usable"} | UNAVAILABLE)
        ):
            raise ValueError("raw row disagrees with protocol")
        groups.setdefault(order, []).append(row)
    output = []
    for item, recorded in zip(plan, saved, strict=True):
        group = groups.get(item.order, [])
        usable = [r for r in group if r["status"] == "usable"]
        if len(usable) < minimum:
            raise ValueError(f"presentation {item.order} lacks usable samples")
        if (
            not isinstance(recorded, dict)
            or recorded.get("order") != item.order
            or any(recorded.get(k) != v for k, v in item.identity().items())
            or recorded.get("usable_count") != len(usable)
            or recorded.get("unavailable_count") != len(group) - len(usable)
            or recorded.get("sampling_attempts") != len(group)
        ):
            raise ValueError("saved presentation disagrees with raw rows or schedule")
        for row in usable:
            _validate_usable(row, template, width, height)
        summary = {
            "order": item.order,
            **item.identity(),
            "usable_count": len(usable),
            "unavailable_count": len(group) - len(usable),
            "first_monotonic_seconds": usable[0]["monotonic_seconds"],
            "last_monotonic_seconds": usable[-1]["monotonic_seconds"],
            "vertical": median(row["vertical"] for row in usable),
            "binocular_eye_opening": median(row["binocular_eye_opening"] for row in usable),
            "face_alignment": {
                field: median(row["face_alignment"][field] for row in usable)
                for field in ALIGN_FIELDS
            },
        }
        for coordinate_frame in ("image_eye_geometry", "face_normalized_geometry"):
            summary[coordinate_frame] = {}
            for side in ("left", "right"):
                summary[coordinate_frame][side] = {
                    **{
                        name: [
                            median(row[coordinate_frame][side][name][axis] for row in usable)
                            for axis in (0, 1)
                        ]
                        for name in POINT_FIELDS
                    },
                    **{
                        name: median(row[coordinate_frame][side][name] for row in usable)
                        for name in SCALAR_FIELDS
                    },
                }
        _equal(recorded.get("vertical_feature"), summary["vertical"], "presentation vertical")
        _equal(
            recorded.get("binocular_eye_opening"),
            summary["binocular_eye_opening"],
            "presentation opening",
        )
        output.append(summary)
    return output


def manipulation_check(presentations: list[dict]) -> list[dict]:
    by_key = {
        (p["block"], p["target_id"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    result = []
    for block in (1, 2, 3):
        for target in TARGETS:
            opening = {
                condition: by_key[(block, target.name, condition)]["binocular_eye_opening"]
                for condition in CONDITIONS
            }
            result.append(
                {
                    "block": block,
                    "target_id": target.name,
                    "opening": opening,
                    "strictly_ordered": (
                        opening["comfortably_narrow"]
                        < opening["natural"]
                        < opening["comfortably_wide"]
                    ),
                }
            )
    return result


def compare_conditions(presentations: list[dict], slope: float) -> list[dict]:
    by_key = {
        (p["block"], p["target_id"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    result = []
    for block in (1, 2, 3):
        for target in TARGETS:
            natural = by_key[(block, target.name, "natural")]
            for condition in ("comfortably_narrow", "comfortably_wide"):
                changed = by_key[(block, target.name, condition)]
                pair = {
                    "block": block,
                    "target_id": target.name,
                    "target_x": target.x,
                    "target_y": target.y,
                    "condition_minus_natural": condition,
                    "natural_order": natural["order"],
                    "condition_order": changed["order"],
                    "natural_time": natural["first_monotonic_seconds"],
                    "condition_time": changed["first_monotonic_seconds"],
                    "delta_vertical": changed["vertical"] - natural["vertical"],
                    "delta_binocular_eye_opening": (
                        changed["binocular_eye_opening"] - natural["binocular_eye_opening"]
                    ),
                    "delta_face_alignment": {
                        k: (
                            wrapped_angle_delta(
                                natural["face_alignment"][k], changed["face_alignment"][k]
                            )
                            if k == "rotation_rad"
                            else changed["face_alignment"][k] - natural["face_alignment"][k]
                        )
                        for k in ALIGN_FIELDS
                    },
                    "eyes": {},
                }
                pair["mapped_y_delta"] = slope * pair["delta_vertical"]
                for side in ("left", "right"):
                    pair["eyes"][side] = {}
                    for frame in ("image_eye_geometry", "face_normalized_geometry"):
                        a, b = natural[frame][side], changed[frame][side]
                        pair["eyes"][side][frame] = {
                            **{
                                name: [b[name][axis] - a[name][axis] for axis in (0, 1)]
                                for name in POINT_FIELDS
                            },
                            **{
                                name: (
                                    wrapped_angle_delta(a[name], b[name])
                                    if name == "corner_angle_rad"
                                    else b[name] - a[name]
                                )
                                for name in SCALAR_FIELDS
                            },
                        }
                result.append(pair)
    return result


def _natural_corner_reference(natural: list[dict]) -> dict[str, list[float]]:
    if not natural:
        raise ValueError("natural rows required for stabilized reference")
    return {
        name: [median(row[name][axis] for row in natural) for axis in (0, 1)]
        for name in ("corner_a", "corner_b", "upper_lid", "lower_lid")
    }


def _fixed_vertical(eye: dict, reference: dict, width: int, height: int) -> float:
    return eye_summary({**reference, "iris_center": eye["iris_center"]}, width, height)["vertical"]


def stabilized_reference_contrast(
    natural: list[dict], changed: list[dict], width: int, height: int
) -> dict[str, float]:
    """Hold the matched natural face-local corner frame fixed for both visits."""
    if not changed:
        raise ValueError("condition rows required for stabilized reference")
    reference = _natural_corner_reference(natural)
    baseline = median(_fixed_vertical(row, reference, width, height) for row in natural)
    condition = median(_fixed_vertical(row, reference, width, height) for row in changed)
    return {
        "natural_fixed_feature": baseline,
        "condition_fixed_feature": condition,
        "stabilized_delta": condition - baseline,
    }


def stabilized_reference_pairs(report: dict, presentations: list[dict]) -> list[dict]:
    """Diagnostic matched-target oracle using each natural presentation's frame."""
    width, height = report["camera_resolution"]
    by_key = {
        (p["block"], p["target_id"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    rows_by_order: dict[int, list[dict]] = {}
    for row in report["rows"]:
        if row["status"] == "usable":
            rows_by_order.setdefault(row["presentation_order"], []).append(row)
    output = []
    for block in (1, 2, 3):
        for target in TARGETS:
            natural = by_key[(block, target.name, "natural")]
            natural_rows = rows_by_order[natural["order"]]
            for condition in ("comfortably_narrow", "comfortably_wide"):
                changed = by_key[(block, target.name, condition)]
                changed_rows = rows_by_order[changed["order"]]
                result = {
                    "block": block,
                    "target_id": target.name,
                    "condition_minus_natural": condition,
                    "natural_order": natural["order"],
                    "condition_order": changed["order"],
                    "actual_binocular_delta": changed["vertical"] - natural["vertical"],
                    "eyes": {},
                }
                references = {}
                for side in ("left", "right"):
                    natural_eye = [row["face_normalized_geometry"][side] for row in natural_rows]
                    changed_eye = [row["face_normalized_geometry"][side] for row in changed_rows]
                    references[side] = _natural_corner_reference(natural_eye)
                    result["eyes"][side] = {
                        **stabilized_reference_contrast(natural_eye, changed_eye, width, height),
                        "actual_delta": (
                            changed["face_normalized_geometry"][side]["vertical"]
                            - natural["face_normalized_geometry"][side]["vertical"]
                        ),
                    }

                def fixed_binocular(row: dict) -> float:
                    return (
                        sum(
                            _fixed_vertical(
                                row["face_normalized_geometry"][side],
                                references[side],
                                width,
                                height,
                            )
                            for side in ("left", "right")
                        )
                        / 2
                    )

                result["stabilized_binocular_delta"] = median(
                    fixed_binocular(row) for row in changed_rows
                ) - median(fixed_binocular(row) for row in natural_rows)
                output.append(result)
    return output


def analyze(report: dict) -> dict:
    presentations = aggregate(report)
    slope = _finite(report["mapping_coefficients"]["y_slope"], "y slope")
    triples = manipulation_check(presentations)
    return {
        "participant": report["participant"],
        "session": report["session"],
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "y_slope": slope,
        "presentations": presentations,
        "manipulation_check": {
            "triples": triples,
            "strict_order_count": sum(t["strictly_ordered"] for t in triples),
        },
        "condition_pairs": compare_conditions(presentations, slope),
        "stabilized_reference_pairs": stabilized_reference_pairs(report, presentations),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps([analyze(json.loads(path.read_text())) for path in args.reports], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
