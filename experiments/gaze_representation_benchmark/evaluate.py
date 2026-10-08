"""One-shot Stage B2 evaluator. Frozen representations and production stay untouched."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from statistics import median

from experiments.raw_geometry_gaze_diagnostic.analysis import inspect_capture
from eye_tracker.gaze.calibration import aggregate_calibration_observations, fit_independent_linear
from validation.real_calibration import MIN_USABLE_SAMPLES

from . import evaluation_metrics as metrics
from . import representations as rep
from .calibration import fit_candidates, parse_presentations

ROOT = Path(__file__).resolve().parents[2]
FREEZE_COMMIT = "c4ad261b63fcce3b3998ce8335f8d81fa2118b32"
CAPTURE_PATHS = {
    session: ROOT / ".venv" / f"raw-geometry-gaze-cagri-{session}.json"
    for session in ("geometry-1", "geometry-2")
}
WINDOWS = {"primary": (0.0, 3.0), "secondary": (0.8, 3.0)}
CHANNELS = ("left", "right", "binocular")


def verify_capture(report, expected_session):
    """Schema/R0/fresh-calibration integrity only, without outcome summaries."""
    if expected_session not in CAPTURE_PATHS or report.get("session") != expected_session:
        raise ValueError("unexpected session identity")
    if report.get("participant") != "cagri":
        raise ValueError("unexpected participant identity")
    return inspect_capture(report)


def load_captures(paths=None):
    paths = CAPTURE_PATHS if paths is None else paths
    if set(paths) != set(CAPTURE_PATHS) or any(
        Path(paths[s]).absolute() != CAPTURE_PATHS[s].absolute() or Path(paths[s]).is_symlink()
        for s in CAPTURE_PATHS
    ):
        raise ValueError("only the two expected capture paths are permitted")
    reports, provenance = [], {}
    for session in CAPTURE_PATHS:
        payload = Path(paths[session]).read_bytes()
        report = json.loads(payload)
        integrity = verify_capture(report, session)
        reports.append(report)
        provenance[session] = {
            "path": f".venv/{Path(paths[session]).name}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "integrity": integrity,
        }
    return reports, provenance


def _features(name, geometry, reference):
    if geometry is None:
        return rep.Features(None, None, None, "raw geometry absent")
    if name == "R0":
        return rep.r0(geometry)
    return rep.r1(geometry, reference) if name == "R1" else rep.r2(geometry, reference)


def _unavailable_reason(name, channel, features, geometry, reference):
    """Classify a failed frozen output, never replacing its feature/availability."""
    if name != "R2" or geometry is None:
        return features.unavailable_reason
    if channel == "binocular":
        return "; ".join(
            f"{side}: {_unavailable_reason(name, side, features, geometry, reference)}"
            for side in ("left", "right")
            if getattr(features, side) is None
        )
    try:
        local = rep.local_eye(geometry, channel)
        if reference is None or reference.get(channel) is None:
            return "R2 calibration contour reference absent"
        transform = rep.fit_affine(local.contour, reference[channel])
        if transform is None:
            return "R2 unavailable finite full-rank affine solution"
        # Features were already rejected by the authoritative frozen implementation.
        return "R2 transformed iris or fixed-reference production geometry unavailable"
    except (KeyError, TypeError, ValueError, FloatingPointError, OverflowError) as error:
        return f"R2 local geometry unavailable: {error}"


def _project(presentations, name, reference, calibration):
    channels = {channel: [] for channel in CHANNELS}
    for p in presentations:
        order = p["order" if calibration else "trial_order"]
        output = {channel: [] for channel in CHANNELS}
        for index, sample in enumerate(p["samples"]):
            if calibration and sample["feature_status"] != "usable":
                features = rep.Features(None, None, None, "recorded calibration R0 unavailable")
            else:
                features = _features(name, sample["raw_geometry"], reference)
            for channel in CHANNELS:
                feature = getattr(features, channel)
                reason = (
                    None
                    if feature
                    else features.unavailable_reason
                    if calibration and sample["feature_status"] != "usable"
                    else _unavailable_reason(
                        name, channel, features, sample["raw_geometry"], reference
                    )
                )
                if name == "R0" and channel == "binocular" and sample["feature_status"] != "usable":
                    feature = None
                    reason = f"recorded production: {sample['unavailable_reason']}"
                output[channel].append(
                    {
                        "key": [order, index, sample["frame_timestamp_ns"]],
                        "t": sample["trial_relative_seconds"],
                        "h": feature.horizontal if feature else None,
                        "v": feature.vertical if feature else None,
                        "prediction": None,
                        "reason": reason,
                    }
                )
        for channel in CHANNELS:
            channels[channel].append(
                {k: p[k] for k in ("target_id", "target_x", "target_y")}
                | {"order": order, "block": p.get("block", 0), "samples": output[channel]}
            )
    return channels


def _fit_monocular(calibration):
    medians = []
    for p in calibration:
        observations = [(r["h"], r["v"]) for r in p["samples"] if r["h"] is not None]
        if len(observations) < MIN_USABLE_SAMPLES:
            return None, "not evaluable: fewer than five usable observations at a calibration"
        medians.append(
            aggregate_calibration_observations(observations, p["target_x"], p["target_y"])
        )
    try:
        return fit_independent_linear(medians), None
    except ValueError as error:
        return None, f"not evaluable: {error}"


def _reference_digest(reference):
    if reference is None:
        return None
    arrays = reference.values() if isinstance(reference, dict) else (reference,)
    digest = hashlib.sha256()
    for array in arrays:
        if array is None:
            digest.update(b"absent")
        else:
            digest.update(str(array.shape).encode())
            digest.update(array.astype("<f8").tobytes())
    return digest.hexdigest()


def prepare_session(report):
    """Fit/reference from calibration, freeze maps, then project validation geometry."""
    fits = fit_candidates(parse_presentations(report["calibration_presentations"]))
    prepared = {"session": report["session"], "fits": fits, "data": {}, "reference_sha256": {}}
    for name in rep.REPRESENTATIONS:
        fit = fits[name]
        calibration = _project(report["calibration_presentations"], name, fit.reference, True)
        mappings, reasons = {}, {}
        for channel in CHANNELS:
            if channel == "binocular":
                mappings[channel], reasons[channel] = fit.mapping, fit.unavailable_reason
            else:
                mappings[channel], reasons[channel] = _fit_monocular(calibration[channel])
        # All fitting has completed before validation presentations enter this function.
        trials = _project(report["trials"], name, fit.reference, False)
        for channel, mapping in mappings.items():
            for p in calibration[channel] + trials[channel]:
                for row in p["samples"]:
                    if mapping is not None and row["h"] is not None:
                        row["prediction"] = list(mapping.predict(row["h"], row["v"]))
        prepared["data"][name] = {
            "calibration": calibration,
            "trials": trials,
            "maps": mappings,
            "map_reasons": reasons,
        }
        prepared["reference_sha256"][name] = _reference_digest(fit.reference)
    return prepared


def _calibration_summary(presentations, mapping, reason):
    output, residuals = [], []
    for p in presentations:
        rows = [r for r in p["samples"] if r["h"] is not None]
        h, v = (median(r[key] for r in rows) if rows else None for key in ("h", "v"))
        prediction = list(mapping.predict(h, v)) if mapping is not None and h is not None else None
        dx, dy = (
            prediction[k] - p[key] if prediction else None
            for k, key in enumerate(("target_x", "target_y"))
        )
        if prediction is not None:
            residuals.append({"dx": dx, "dy": dy})
        output.append(
            {k: p[k] for k in ("order", "target_id", "target_x", "target_y")}
            | {
                "usable": len(rows),
                "horizontal_median": h,
                "vertical_median": v,
                "prediction": prediction,
                "dx": dx,
                "dy": dy,
                "availability": metrics.availability([p]),
            }
        )
    return {
        "mapping": asdict(mapping) if mapping else None,
        "mapping_unavailable_reason": reason,
        "presentations": output,
        "presentation_errors": metrics.screen_summary(residuals),
        "availability": metrics.availability(presentations),
    }


def summarize_session(prepared):
    result = {
        "reference_sha256": prepared["reference_sha256"],
        "representations": {},
        "comparisons": {},
    }
    for name in rep.REPRESENTATIONS:
        data = prepared["data"][name]
        result["representations"][name] = {}
        for channel in CHANNELS:
            cal, trials, mapping = (
                data["calibration"][channel],
                data["trials"][channel],
                data["maps"][channel],
            )
            result["representations"][name][channel] = {
                "calibration": _calibration_summary(cal, mapping, data["map_reasons"][channel]),
                **{
                    window: metrics.window_diagnostics(cal, trials, mapping, *bounds)
                    for window, bounds in WINDOWS.items()
                },
            }
    baseline = prepared["data"]["R0"]
    for name in ("R1", "R2"):
        candidate = prepared["data"][name]
        common_a, common_b = metrics.common_frames(
            baseline["trials"]["binocular"], candidate["trials"]["binocular"]
        )
        comparison = {"native": {}, "common": {}}
        for window, bounds in WINDOWS.items():
            comparison["native"][window] = {
                "baseline": result["representations"]["R0"]["binocular"][window],
                "candidate": result["representations"][name]["binocular"][window],
            }
            comparison["common"][window] = {
                role: metrics.window_diagnostics(
                    data["calibration"]["binocular"], trials, data["maps"]["binocular"], *bounds
                )
                for role, data, trials in (
                    ("baseline", baseline, common_a),
                    ("candidate", candidate, common_b),
                )
            }
        for view in ("native", "common"):
            pair = comparison[view]["primary"]
            comparison[view]["primary_comparison"] = metrics.gate_comparison(
                pair["baseline"], pair["candidate"], True
            )
        result["comparisons"][name] = comparison
    return result


def coverage_gate(comparison):
    """Same five criteria in both required coverage views; neither hides failure."""
    gates = {view: comparison[view]["primary_comparison"] for view in ("native", "common")}
    criteria = {
        str(k): {
            "value": {view: gate["criteria"][str(k)]["value"] for view, gate in gates.items()},
            "threshold": gates["native"]["criteria"][str(k)].get("threshold"),
            "pass": all(gate["criteria"][str(k)]["pass"] for gate in gates.values()),
        }
        for k in range(1, 6)
    }
    return {
        "criteria": criteria,
        "overall": "PROMISING" if all(c["pass"] for c in criteria.values()) else "FAIL",
    }


def evaluate_reports(reports, provenance):
    if len(reports) != 2:
        raise ValueError("exactly two expected sessions required")
    # Validate BOTH inputs before any fitting/outcome calculation.
    for session, report in zip(CAPTURE_PATHS, reports, strict=True):
        verify_capture(report, session)
    sessions = {r["session"]: summarize_session(prepare_session(r)) for r in reports}
    holdout = sessions["geometry-2"]
    return {
        "freeze_commit": FREEZE_COMMIT,
        "windows": {k: list(v) for k, v in WINDOWS.items()},
        "captures": provenance,
        "sessions": sessions,
        "holdout_gate": {
            name: coverage_gate(holdout["comparisons"][name]) for name in ("R1", "R2")
        },
        "gate_policy": "The same five frozen primary criteria must be supported in native and exact common-frame views; neither view can hide/rescue a failure in the other. No additional thresholds; undefined fails.",
        "provenance_policy": "Session-local calibration only; immutable representations; no validation fitting, future-frame dependence or post-holdout tuning.",
    }


def serialize(result):
    return json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"


def verify_frozen_sources():
    import subprocess

    frozen = [
        "experiments/gaze_representation_benchmark/" + name
        for name in (
            "__init__.py",
            "representations.py",
            "calibration.py",
            "analysis.py",
            "REPRESENTATION_FREEZE.md",
        )
    ] + [
        "src/eye_tracker/vision/eye_features.py",
        "src/eye_tracker/gaze/calibration.py",
        "experiments/raw_geometry_gaze_diagnostic/PREREGISTRATION.md",
        "tests/experiments/test_gaze_representation_benchmark.py",
        "experiments/raw_geometry_gaze_diagnostic/geometry.py",
        "experiments/raw_geometry_gaze_diagnostic/protocol.py",
        "experiments/raw_geometry_gaze_diagnostic/analysis.py",
        "experiments/fixed_window_gaze_diagnostic/protocol.py",
        "experiments/fixed_window_gaze_diagnostic/analysis.py",
        "experiments/intentional_gaze_targeting/protocol.py",
        "validation/real_calibration.py",
        "src/eye_tracker/vision/contracts.py",
        "src/eye_tracker/vision/eye_topology.py",
        "src/eye_tracker/vision/face_tracker.py",
    ]
    hashes = {}
    for relative in frozen:
        expected = subprocess.check_output(["git", "show", f"{FREEZE_COMMIT}:{relative}"], cwd=ROOT)
        actual = (ROOT / relative).read_bytes()
        if actual != expected:
            raise ValueError(f"immutable freeze content changed: {relative}")
        hashes[relative] = hashlib.sha256(actual).hexdigest()
    return hashes


def run_once():
    """No retries/overwrite: seal source provenance before revealing any outcomes."""
    import platform
    import subprocess

    import numpy as np

    from .report import render

    output = ROOT / "experiments/gaze_representation_benchmark"
    marker = ROOT / ".venv/stage-b2-one-shot-evaluation.json"
    if marker.exists() or any(
        (output / name).exists() for name in ("RESULTS.md", "results_summary.json")
    ):
        raise ValueError("one-shot evaluation already started or output exists; do not re-evaluate")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise ValueError("commit the tested evaluator before outcome evaluation")
    hashes = verify_frozen_sources()
    reports, provenance = load_captures()
    code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    seal = {
        "evaluator_commit": code_commit,
        "freeze_commit": FREEZE_COMMIT,
        "captures": {s: {k: v[k] for k in ("sha256", "bytes")} for s, v in provenance.items()},
        "status": "started",
    }
    with marker.open("x") as stream:
        stream.write(serialize(seal))
    result = evaluate_reports(reports, provenance)
    result["execution"] = {
        "evaluator_commit": code_commit,
        "frozen_source_sha256": hashes,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "freeze_merge": "PR #70 squash-merged: original freeze is not an ancestor of main; merged full tree verified byte-identical before evaluation.",
        "one_shot": True,
    }
    encoded, markdown = serialize(result), render(result)
    # Ensure data identity survived evaluation without modifying either input.
    for session, path in CAPTURE_PATHS.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != provenance[session]["sha256"]:
            raise ValueError("capture changed during evaluation; stop without publishing results")
    with (output / "results_summary.json").open("x") as stream:
        stream.write(encoded)
    with (output / "RESULTS.md").open("x") as stream:
        stream.write(markdown)
    seal.update(status="complete", summary_sha256=hashlib.sha256(encoded.encode()).hexdigest())
    marker.write_text(serialize(seal))
    print(serialize({"holdout_gate": result["holdout_gate"], "evaluator_commit": code_commit}))


def main():
    import sys

    if len(sys.argv) != 1:
        raise SystemExit("No path/options: only the two frozen final captures may be evaluated.")
    run_once()


if __name__ == "__main__":
    main()
