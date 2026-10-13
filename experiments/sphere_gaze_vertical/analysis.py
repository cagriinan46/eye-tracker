"""Compare eye-sphere candidates with the frozen Issue #77 candidates (Issue #92); see README.md.

The eye-sphere feature follows Jason Orlosky's MIT-licensed prototype
(JEOresearch/EyeTracker, ``Webcam3DTracker/MonitorTracking.py``): while the
participant looks at screen centre, a virtual eyeball centre is locked in the
nose head frame one eyeball radius behind each iris; gaze is the averaged
unit vector from those centres to the irises, rotated back to camera space.
Every candidate is fitted on calibration and scored on validation of the same
session and the same common frames. Rules are preregistered; do not tune.
"""

import argparse
import json
import sys
from math import atan2, degrees
from statistics import fmean, median

import numpy as np

from experiments.sphere_gaze_vertical.capture import ROTATION_FIELDS, SPHERE_FIELDS
from experiments.vertical_signal_comparison import analysis as frozen

# Preregistered for Issue #92 before any session; do not tune.
PROTOTYPE_RADIUS_PX = 20.0  # prototype's eyeball radius at calibration distance
PROTOTYPE_FRAME_WIDTH = 640  # assumed prototype capture width; radius scales with width
PROTOTYPE_PITCH_HALF_RANGE_DEG = 5.0  # prototype: ±5° pitch reaches the screen edges
LOCK_TARGET = "K-center"
SPHERE_BETTER_MARGIN = 0.02  # SPHERE vs R0, both one-feature candidates
COMBO_BETTER_MARGIN = 0.01  # SPHERE_COMBO vs COMBO, both four-feature candidates
SPHERE_CANDIDATES = {
    "SPHERE": ("sphere_pitch",),
    "SPHERE_COMBO": ("sphere_pitch", "opening", "blend", "pitch"),
}


def _rotation(row: dict) -> np.ndarray:
    return np.array([row[name] for name in ROTATION_FIELDS], dtype=float).reshape(3, 3)


def _local(row: dict, eye: str) -> np.ndarray:
    return np.array([row[f"{eye}_iris_local_{axis}"] for axis in "xyz"], dtype=float)


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        raise ValueError("zero-length vector")
    return vector / norm


def common_rows(rows: list[dict]) -> list[dict]:
    """Frozen common-frame rule plus complete eye-sphere numbers."""
    return [
        row
        for row in rows
        if frozen.frame_features(row) is not None
        and all(row.get(name) is not None for name in SPHERE_FIELDS)
    ]


def lock_offsets(rows: list[dict], frame_width: int) -> dict | None:
    """Head-local eyeball centres from the first usable screen-centre checkpoint."""
    by_presentation: dict[int, list[dict]] = {}
    for row in rows:
        if row["target_id"] == LOCK_TARGET:
            by_presentation.setdefault(row["presentation"], []).append(row)
    usable = [
        p for p in sorted(by_presentation) if len(by_presentation[p]) >= frozen.MIN_USABLE_SAMPLES
    ]
    if not usable:
        return None
    frames = by_presentation[usable[0]]
    radius_px = PROTOTYPE_RADIUS_PX * frame_width / PROTOTYPE_FRAME_WIDTH
    scale = median(row["nose_scale_px"] for row in frames)
    # Camera direction (0, 0, 1) expressed in the head frame is the rotation's last row.
    camera_local = _unit(np.median([_rotation(row)[2, :] for row in frames], axis=0))
    offsets = {}
    for eye in ("left", "right"):
        iris = np.median([_local(row, eye) for row in frames], axis=0)
        offsets[eye] = iris + (radius_px / scale) * camera_local
    return {"presentation": usable[0], "frames": len(frames), "offsets": offsets}


def gaze_angles(row: dict, offsets: dict) -> tuple[float, float]:
    """Prototype pitch (up positive) and yaw in degrees of the averaged camera-space gaze."""
    rotation = _rotation(row)
    direction = _unit(sum(_unit(rotation @ (_local(row, eye) - offsets[eye])) for eye in offsets))
    pitch = degrees(atan2(-direction[1], -direction[2]))
    yaw = degrees(atan2(direction[0], -direction[2]))
    return pitch, yaw


def presentation_records(rows: list[dict], offsets: dict) -> list[dict]:
    """Frozen per-presentation medians plus sphere pitch/yaw medians over the same frames."""
    records = frozen.presentation_medians(rows)
    angles: dict[int, list[tuple[float, float]]] = {}
    for row in rows:
        angles.setdefault(row["presentation"], []).append(gaze_angles(row, offsets))
    for record in records:
        if record["available"]:
            values = angles[record["presentation"]]
            record["sphere_pitch"] = median(pitch for pitch, _ in values)
            record["sphere_yaw"] = median(yaw for _, yaw in values)
    return records


def _candidate(calibration, validation, features) -> dict:
    coefficients = frozen.fit(calibration, features, "target_y")
    if coefficients is None:
        return {"available": False, "passes": False}
    metrics = frozen.score(
        [(r, frozen.predict(coefficients, r, features)) for r in validation], "target_y"
    )
    values = [r["target_y"] for r in calibration]
    mean_value = fmean(values)
    total = sum((v - mean_value) ** 2 for v in values)
    residual = sum(
        (r["target_y"] - frozen.predict(coefficients, r, features)) ** 2 for r in calibration
    )
    return {
        "available": True,
        "coefficients": coefficients,
        "calibration_r_squared": 1 - residual / total if total > 0 else 0.0,
        **metrics,
        "passes": frozen.passes(metrics),
    }


def analyze_session(report: dict) -> dict:
    """Frozen #77 candidates and eye-sphere candidates on identical common frames."""
    rows = common_rows(report["rows"])
    frame_width = report["camera_resolution"][0]
    baseline = frozen.analyze_session({**report, "rows": rows})
    lock = lock_offsets(rows, frame_width)
    summary = {
        "participant": report["participant"],
        "session": report["session"],
        "frozen": baseline,
        "lock": None
        if lock is None
        else {"presentation": lock["presentation"], "frames": lock["frames"]},
        "valid": baseline["valid"] and lock is not None,
    }
    if not summary["valid"]:
        return {**summary, "sphere": {}}
    records = presentation_records(rows, lock["offsets"])
    calibration = [r for r in records if r["phase"] == "calibration" and r["available"]]
    validation = [r for r in records if r["phase"] == "validation" and r["available"]]
    sphere = {name: _candidate(calibration, validation, f) for name, f in SPHERE_CANDIDATES.items()}
    lock_pitch = median(
        r["sphere_pitch"]
        for r in records
        if r["available"] and r["presentation"] == lock["presentation"]
    )
    published = [
        (r, 0.5 - (r["sphere_pitch"] - lock_pitch) / (2 * PROTOTYPE_PITCH_HALF_RANGE_DEG))
        for r in validation
    ]
    sphere["AS_PUBLISHED_descriptive"] = frozen.score(published, "target_y")
    x_coefficients = frozen.fit(calibration, ("sphere_yaw",), "target_x")
    sphere["x_from_sphere_yaw_descriptive"] = (
        None
        if x_coefficients is None
        else frozen.score(
            [(r, frozen.predict(x_coefficients, r, ("sphere_yaw",))) for r in validation],
            "target_x",
        )
    )
    sphere["pitch_range_deg_descriptive"] = {
        "validation_row_medians": {
            str(y): median(r["sphere_pitch"] for r in validation if r["target_y"] == y)
            for y in sorted({r["target_y"] for r in validation})
        }
    }
    return {**summary, "sphere": sphere}


def combine(sessions: list[dict]) -> dict:
    """Apply the preregistered Issue #92 rule across sessions of one participant."""
    keys = [(s["participant"], s["session"]) for s in sessions]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate participant/session")
    if len({s["participant"] for s in sessions}) != 1:
        raise ValueError("combine one participant at a time")
    complete = len(sessions) >= 2 and all(s["valid"] for s in sessions)
    methods: dict[str, list[dict]] = {}
    for session in sessions:
        for name, result in session["frozen"].get("candidates", {}).items():
            methods.setdefault(name, []).append(result)
        for name in SPHERE_CANDIDATES:
            methods.setdefault(name, []).append(session["sphere"].get(name, {}))
    ranking = []
    if complete:
        for name, results in methods.items():
            if all(result.get("available") for result in results):
                ranking.append(
                    {
                        "method": name,
                        "mean_y_mae": fmean(result["mae"] for result in results),
                        "passes_all_sessions": all(result["passes"] for result in results),
                    }
                )
        ranking.sort(key=lambda item: item["mean_y_mae"])
    mae = {item["method"]: item["mean_y_mae"] for item in ranking}

    def better(candidate: str, reference: str, margin: float) -> bool | None:
        if not complete or candidate not in mae or reference not in mae:
            return None
        return mae[candidate] <= mae[reference] - margin

    passing = [item["method"] for item in ranking if item["passes_all_sessions"]]
    return {
        "participant": sessions[0]["participant"],
        "sessions": [s["session"] for s in sessions],
        "complete": complete,
        "sphere_better_than_r0_primary": better("SPHERE", "R0", SPHERE_BETTER_MARGIN),
        "sphere_combo_better_than_combo_secondary": better(
            "SPHERE_COMBO", "COMBO", COMBO_BETTER_MARGIN
        ),
        "vertical_solved_by_sphere": (
            any(name in passing for name in SPHERE_CANDIDATES) if complete else None
        ),
        "methods_passing_all_sessions": passing,
        "ranking": ranking,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=argparse.FileType("r", encoding="utf-8"))
    args = parser.parse_args(argv)
    try:
        sessions = [analyze_session(json.load(handle)) for handle in args.datasets]
        output = {"sessions": sessions, "combined": combine(sessions)}
        print(json.dumps(output, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError) as error:
        print(f"Cannot analyze dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
