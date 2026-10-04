"""Development, untouched holdout, and secondary offline lid-feature evaluation."""

import argparse
import json
from collections import defaultdict
from math import isfinite
from pathlib import Path
from statistics import mean, median

from experiments.alternative_vertical_feature_benchmark.analysis import (
    _condition_pairs,
    _natural,
    _repeated,
    fit_mapping,
    percentile,
)
from experiments.eye_geometry_decomposition_study import analysis as geometry_analysis
from experiments.face_reference_corner_stability_study import analysis as face_analysis
from experiments.lid_reference_vertical_feature_benchmark.candidates import (
    BASELINE,
    CANDIDATES,
    EYES,
    InvalidAperture,
    calibration_references,
    feature,
)

PROTOCOLS = {
    "face_reference_corner_stability": (1, "primary"),
    "eye_geometry_decomposition": (1, "secondary"),
}
HOLDOUT = "live-3"
MAX_WORSENING_RATIO = 1.15
MIN_IMPROVEMENT_RATIO = 0.85


def _validated_report(report: dict) -> str:
    protocol = report.get("protocol_name")
    if protocol not in PROTOCOLS or report.get("protocol_version") != PROTOCOLS[protocol][0]:
        raise ValueError("incompatible study protocol")
    if report.get("participant") != "cagri" or report.get("session") not in (
        "live-1",
        "live-2",
        "live-3",
    ):
        raise ValueError("unexpected participant or session")
    tier = PROTOCOLS[protocol][1]
    if tier == "primary":
        face_analysis.aggregate(report)
    else:
        geometry_analysis.aggregate(report)
    return tier


def feature_presentations(
    report: dict, candidate: str, references: dict
) -> tuple[list[dict], dict, int]:
    """Aggregate simultaneous valid samples, retaining calibration-only noise data."""
    width, height = report["camera_resolution"]
    grouped: dict[int, list[dict]] = defaultdict(list)
    for row in report["rows"]:
        if row["status"] == "usable":
            grouped[row["presentation_order"]].append(row)
    summaries = []
    calibration_deviations: dict[str, list[float]] = {field: [] for field in ("binocular", *EYES)}
    skipped = 0
    for presentation in report["presentations"]:
        samples = {field: [] for field in ("binocular", *EYES)}
        rows = grouped[presentation["order"]]
        if len(rows) != presentation["usable_count"]:
            raise ValueError("usable sample count disagrees with saved presentation")
        for row in rows:
            try:
                eye_values = {
                    eye: feature(row, candidate, eye, references[eye], width, height)
                    for eye in EYES
                }
            except InvalidAperture:
                skipped += 1
                continue
            samples["binocular"].append(mean(eye_values.values()))
            for eye in EYES:
                samples[eye].append(eye_values[eye])
        if len(samples["binocular"]) < report["minimum_usable_samples_per_presentation"]:
            raise ValueError("candidate has insufficient usable samples")
        summary = {
            **{
                key: presentation[key]
                for key in ("order", "phase", "target_id", "target_y", "condition", "block")
            },
            "candidate_usable_count": len(samples["binocular"]),
        }
        for field, values in samples.items():
            midpoint = median(values)
            summary[field] = midpoint
            if presentation["phase"] == "calibration":
                calibration_deviations[field].append(
                    median(abs(value - midpoint) for value in values)
                )
        summaries.append(summary)
    if any(len(values) != 9 for values in calibration_deviations.values()):
        raise ValueError("nine ordinary calibration presentations required")
    return (
        summaries,
        {field: median(values) for field, values in calibration_deviations.items()},
        skipped,
    )


def analyze_session(report: dict) -> dict:
    """Evaluate only the three declared formulas; validation precedes computation."""
    tier = _validated_report(report)
    width, height = report["camera_resolution"]
    references = calibration_references(report["rows"], width, height)
    candidates = {}
    for candidate in CANDIDATES:
        presentations, calibration_mad, skipped = feature_presentations(
            report, candidate, references
        )
        fields = {}
        for field in ("binocular", *EYES):
            slope, intercept = fit_mapping(presentations, field)
            if candidate == BASELINE and field == "binocular":
                saved = report["mapping_coefficients"]
                if (
                    abs(slope - saved["y_slope"]) > 1e-8
                    or abs(intercept - saved["y_intercept"]) > 1e-8
                ):
                    raise ValueError("production fit disagrees with saved coefficients")
            calibration = [p for p in presentations if p["phase"] == "calibration"]
            residuals = [slope * p[field] + intercept - p["target_y"] for p in calibration]
            values = [p[field] for p in calibration]
            fields[field] = {
                "slope": slope,
                "intercept": intercept,
                "calibration_feature_span": max(values) - min(values),
                "calibration_mae": mean(abs(value) for value in residuals),
                "calibration_residuals": residuals,
                "calibration_residual_p95_absolute": percentile(
                    [abs(value) for value in residuals], 0.95
                ),
                "calibration_within_presentation_mad": calibration_mad[field],
                "calibration_mapped_noise": abs(slope) * calibration_mad[field],
                "natural": _natural(presentations, slope, intercept, field),
                "conditions": _condition_pairs(presentations, slope, field),
                "repeated": _repeated(presentations, slope, field),
            }
        candidates[candidate] = {"skipped_aperture_samples": skipped, "fields": fields}
    return {
        "participant": report["participant"],
        "session": report["session"],
        "protocol": report["protocol_name"],
        "tier": tier,
        "candidate_references": {
            eye: {"span_px": ref.span_px, "normal_x": ref.normal_x, "normal_y": ref.normal_y}
            for eye, ref in references.items()
        },
        "candidates": candidates,
    }


def ratio(candidate: float, baseline: float) -> float:
    """Nonnegative candidate/baseline ratio with explicit zero handling."""
    if not all(isfinite(v) and v >= 0 for v in (candidate, baseline)):
        raise ValueError("ratio inputs must be finite and nonnegative")
    if baseline == 0:
        return 1.0 if candidate == 0 else float("inf")
    return candidate / baseline


def eligibility(holdout: dict) -> dict:
    """Apply the README's immutable six-part rule to primary live-3 only."""
    if holdout["tier"] != "primary" or holdout["session"] != HOLDOUT:
        raise ValueError("eligibility requires primary live-3 holdout")
    baseline = holdout["candidates"][BASELINE]["fields"]["binocular"]
    output = {}
    for candidate in CANDIDATES[1:]:
        tested = holdout["candidates"][candidate]["fields"]["binocular"]
        natural_ratio = ratio(tested["natural"]["mae"], baseline["natural"]["mae"])
        narrow_ratio = ratio(
            tested["conditions"]["comfortably_narrow"]["mapped_absolute"]["median"],
            baseline["conditions"]["comfortably_narrow"]["mapped_absolute"]["median"],
        )
        wide_ratio = ratio(
            tested["conditions"]["comfortably_wide"]["mapped_absolute"]["median"],
            baseline["conditions"]["comfortably_wide"]["mapped_absolute"]["median"],
        )
        repeat_ratio = ratio(
            tested["repeated"]["mapped_absolute"]["median"],
            baseline["repeated"]["mapped_absolute"]["median"],
        )
        noise_ratio = ratio(
            tested["calibration_mapped_noise"], baseline["calibration_mapped_noise"]
        )
        checks = {
            "row_ordering": tested["natural"]["ordered"],
            "natural_mae": natural_ratio <= MAX_WORSENING_RATIO,
            "one_opening_improves": min(narrow_ratio, wide_ratio) <= MIN_IMPROVEMENT_RATIO,
            "other_opening_not_worse": max(narrow_ratio, wide_ratio) <= MAX_WORSENING_RATIO,
            "repeated_target": repeat_ratio <= MAX_WORSENING_RATIO,
            "calibration_amplification": noise_ratio <= MAX_WORSENING_RATIO,
        }
        output[candidate] = {
            "ratios": {
                "natural_mae": natural_ratio,
                "narrow_shift": narrow_ratio,
                "wide_shift": wide_ratio,
                "repeated_target": repeat_ratio,
                "calibration_amplification": noise_ratio,
            },
            "checks": checks,
            "eligible": all(checks.values()),
        }
    return output


def evaluate_split(
    development: list[dict], holdout: dict, historical: list[dict] | None = None
) -> dict:
    """Evaluate live-1/2 first, then live-3; historical results cannot change rule."""
    if [r.get("session") for r in development] != ["live-1", "live-2"] or holdout.get(
        "session"
    ) != HOLDOUT:
        raise ValueError("development must be live-1/2 and holdout live-3")
    if any(
        r.get("protocol_name") != "face_reference_corner_stability" for r in (*development, holdout)
    ):
        raise ValueError("primary split requires face-reference protocol")
    dev_results = [analyze_session(report) for report in development]
    holdout_result = analyze_session(holdout)
    decision = eligibility(holdout_result)
    historical_results = []
    if historical is not None:
        if [r.get("session") for r in historical] != ["live-1", "live-2", "live-3"] or any(
            r.get("protocol_name") != "eye_geometry_decomposition" for r in historical
        ):
            raise ValueError("historical check requires three older geometry sessions")
        historical_results = [analyze_session(report) for report in historical]
    return {
        "development": dev_results,
        "holdout": holdout_result,
        "eligibility": decision,
        "winner": next((name for name, outcome in decision.items() if outcome["eligible"]), None),
        "historical": historical_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development_live_1", type=Path)
    parser.add_argument("development_live_2", type=Path)
    parser.add_argument("holdout_live_3", type=Path)
    parser.add_argument("--historical", nargs=3, type=Path)
    args = parser.parse_args(argv)

    def read(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    output = evaluate_split(
        [read(args.development_live_1), read(args.development_live_2)],
        read(args.holdout_live_3),
        [read(path) for path in args.historical] if args.historical else None,
    )
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
