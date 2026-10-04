"""Offline calibration-only fitting and matched evaluation of vertical candidates."""

import argparse
import json
from collections import defaultdict
from itertools import combinations
from math import isfinite
from pathlib import Path
from statistics import linear_regression, mean, median

from experiments.alternative_vertical_feature_benchmark.candidates import (
    BASELINE,
    CANDIDATES,
    EYES,
    FACE_IRIS_Y,
    binocular,
    calibration_references,
    feature,
)
from experiments.eye_geometry_decomposition_study import analysis as geometry_analysis
from experiments.face_reference_corner_stability_study import analysis as face_analysis

PROTOCOLS = {
    "face_reference_corner_stability": (1, "primary"),
    "eye_geometry_decomposition": (1, "secondary"),
}


def percentile(values: list[float], fraction: float) -> float:
    """Sorted linear-interpolation percentile, including both endpoints."""
    if not values or not 0 <= fraction <= 1:
        raise ValueError("nonempty values and fraction in [0, 1] required")
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def fit_mapping(calibration: list[dict], field: str = "binocular") -> tuple[float, float]:
    """OLS on exactly the ordinary nine calibration presentation medians."""
    points = [p for p in calibration if p["phase"] == "calibration"]
    if len(points) != 9 or len({p["target_y"] for p in points}) != 3:
        raise ValueError("nine ordinary calibration presentations across three rows required")
    values = [p[field] for p in points]
    if len(set(values)) < 2:
        raise ValueError("calibration feature lacks variation")
    fit = linear_regression(values, [p["target_y"] for p in points])
    if not all(isfinite(value) for value in (fit.slope, fit.intercept)):
        raise ValueError("nonfinite mapping")
    return fit.slope, fit.intercept


def _describe(values: list[float]) -> dict:
    return {
        "median": median(values),
        "mean": mean(values),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


def _feature_presentations(report: dict, candidate: str, reference: dict) -> list[dict]:
    width, height = report["camera_resolution"]
    grouped = defaultdict(list)
    for row in report["rows"]:
        if row["status"] == "usable":
            grouped[row["presentation_order"]].append(row)
    result = []
    for presentation in report["presentations"]:
        rows = grouped[presentation["order"]]
        if len(rows) != presentation["usable_count"]:
            raise ValueError("usable row count disagrees with presentation")
        binocular_values = [binocular(row, candidate, reference, width, height) for row in rows]
        eye_values = {
            eye: median(
                feature(row, candidate, eye, reference.get(eye), width, height) for row in rows
            )
            for eye in EYES
        }
        result.append(
            {
                **{
                    key: presentation[key]
                    for key in ("order", "phase", "target_id", "target_y", "condition", "block")
                },
                "binocular": median(binocular_values),
                **eye_values,
            }
        )
    return result


def _natural(presentations: list[dict], slope: float, intercept: float, field: str) -> dict:
    natural = [
        p for p in presentations if p["phase"] == "diagnostic" and p["condition"] == "natural"
    ]
    errors = [slope * p[field] + intercept - p["target_y"] for p in natural]
    rows = {
        target: median(slope * p[field] + intercept for p in natural if p["target_id"] == target)
        for target in ("upper", "center", "lower")
    }
    return {
        "mae": mean(abs(error) for error in errors),
        "median_absolute_error": median(abs(error) for error in errors),
        "p95_absolute_error": percentile([abs(error) for error in errors], 0.95),
        "bias": mean(errors),
        "predicted_rows": rows,
        "ordered": rows["upper"] < rows["center"] < rows["lower"],
        "upper_center_margin": rows["center"] - rows["upper"],
        "center_lower_margin": rows["lower"] - rows["center"],
    }


def _condition_pairs(presentations: list[dict], slope: float, field: str) -> dict:
    keyed = {
        (p["target_id"], p["block"], p["condition"]): p
        for p in presentations
        if p["phase"] == "diagnostic"
    }
    output = {}
    for condition in ("comfortably_narrow", "comfortably_wide"):
        pairs = []
        for target in ("upper", "center", "lower"):
            for block in (1, 2, 3):
                natural = keyed[target, block, "natural"]
                changed = keyed[target, block, condition]
                delta = changed[field] - natural[field]
                pairs.append(
                    {
                        "target": target,
                        "block": block,
                        "feature_delta": delta,
                        "mapped_y_delta": slope * delta,
                    }
                )
        output[condition] = {
            "feature_absolute": _describe([abs(pair["feature_delta"]) for pair in pairs]),
            "mapped_absolute": _describe([abs(pair["mapped_y_delta"]) for pair in pairs]),
            "positive": sum(pair["mapped_y_delta"] > 0 for pair in pairs),
            "negative": sum(pair["mapped_y_delta"] < 0 for pair in pairs),
            "by_row": {
                target: _describe(
                    [abs(pair["mapped_y_delta"]) for pair in pairs if pair["target"] == target]
                )
                for target in ("upper", "center", "lower")
            },
            "pairs": pairs,
        }
    return output


def _repeated(presentations: list[dict], slope: float, field: str) -> dict:
    diagnostic = [p for p in presentations if p["phase"] == "diagnostic"]
    pairs = []
    for target in ("upper", "center", "lower"):
        for condition in ("comfortably_narrow", "natural", "comfortably_wide"):
            group = sorted(
                (p for p in diagnostic if p["target_id"] == target and p["condition"] == condition),
                key=lambda p: p["block"],
            )
            if len(group) != 3:
                raise ValueError("exactly three repeated blocks required")
            for first, second in combinations(group, 2):
                pairs.append(
                    {
                        "target": target,
                        "condition": condition,
                        "first_block": first["block"],
                        "second_block": second["block"],
                        "feature_absolute": abs(second[field] - first[field]),
                        "mapped_absolute": abs(slope * (second[field] - first[field])),
                    }
                )
    return {
        "feature_absolute": _describe([p["feature_absolute"] for p in pairs]),
        "mapped_absolute": _describe([p["mapped_absolute"] for p in pairs]),
        "natural_mapped_absolute": _describe(
            [p["mapped_absolute"] for p in pairs if p["condition"] == "natural"]
        ),
        "pairs": pairs,
    }


def analyze(report: dict) -> dict:
    """Validate one protocol, derive candidates, and never fit on diagnostic rows."""
    protocol = report.get("protocol_name")
    if protocol not in PROTOCOLS or report.get("protocol_version") != PROTOCOLS[protocol][0]:
        raise ValueError("incompatible study protocol")
    tier = PROTOCOLS[protocol][1]
    if tier == "primary":
        face_analysis.aggregate(report)
    else:
        geometry_analysis.aggregate(report)
    width, height = report["camera_resolution"]
    references = calibration_references(report["rows"], width, height)
    candidates = (
        CANDIDATES if tier == "primary" else tuple(c for c in CANDIDATES if c != FACE_IRIS_Y)
    )
    output = {}
    for candidate in candidates:
        presentations = _feature_presentations(report, candidate, references)
        results = {}
        for field in ("binocular", *EYES):
            slope, intercept = fit_mapping(presentations, field)
            if candidate == BASELINE and field == "binocular":
                saved = report["mapping_coefficients"]
                if (
                    abs(slope - saved["y_slope"]) > 1e-8
                    or abs(intercept - saved["y_intercept"]) > 1e-8
                ):
                    raise ValueError("baseline calibration does not reproduce saved mapping")
            calibration = [p for p in presentations if p["phase"] == "calibration"]
            calibration_errors = [
                abs(slope * p[field] + intercept - p["target_y"]) for p in calibration
            ]
            feature_span = max(p[field] for p in calibration) - min(p[field] for p in calibration)
            results[field] = {
                "slope": slope,
                "intercept": intercept,
                "calibration_feature_span": feature_span,
                "calibration_mae": mean(calibration_errors),
                "mapped_change_for_0_001_feature": abs(slope) * 0.001,
                "natural": _natural(presentations, slope, intercept, field),
                "conditions": _condition_pairs(presentations, slope, field),
                "repeated": _repeated(presentations, slope, field),
            }
        output[candidate] = results
    return {
        "participant": report["participant"],
        "session": report["session"],
        "protocol": protocol,
        "tier": tier,
        "references": {
            eye: {
                "span_px": reference.span_px,
                "normal_x": reference.normal_x,
                "normal_y": reference.normal_y,
            }
            for eye, reference in references.items()
        },
        "candidates": output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps([analyze(json.loads(path.read_text())) for path in args.reports], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
