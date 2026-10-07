"""Capture/schema/R0 inspection only; never evaluate R1/R2 or holdout outcomes."""

import argparse
import json
from math import isclose, isfinite
from pathlib import Path

from experiments.fixed_window_gaze_diagnostic.analysis import validate_capture as validate_base
from experiments.fixed_window_gaze_diagnostic.protocol import configuration as base_configuration

from .geometry import (
    FACE_ANCHOR_INDICES,
    REQUIRED_INDICES,
    SELECTED_INDICES,
    eye_records,
    interocular_distance,
    reconstruct_r0,
)
from .protocol import SESSION_ROLES, configuration


def _same_numbers(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same_numbers(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same_numbers(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
        return isfinite(a) and isfinite(b) and isclose(a, b, abs_tol=1e-10, rel_tol=1e-10)
    return a == b


def _validate_geometry(row, report):
    geometry = row["raw_geometry"]
    if geometry is None:
        if row["feature_status"] == "usable":
            raise ValueError("usable R0 sample without required geometry")
        return None
    if (
        geometry["schema_version"] != 1
        or geometry["frame_timestamp_ns"] != row["frame_timestamp_ns"]
        or geometry["camera_resolution"] != row["camera_resolution"]
        or row["camera_resolution"] != report["camera_resolution"]
        or row["geometry_error"] is not None
        or not row["camera_frame_available"]
    ):
        raise ValueError("incompatible geometry/frame identity")
    stamp, detector_stamp = geometry["frame_timestamp_ns"], geometry["detector_timestamp_ms"]
    if (
        not isinstance(stamp, int)
        or stamp < 0
        or not isinstance(detector_stamp, int)
        or detector_stamp < stamp // 1_000_000
    ):
        raise ValueError("invalid frame/detector timestamp")
    start, observed = (
        row["measurement_started_monotonic_seconds"],
        row["monotonic_timestamp_seconds"],
    )
    if not isfinite(start) or not start <= stamp / 1e9 <= observed:
        raise ValueError("frame was not captured within the logged measurement attempt")
    points = geometry["landmarks"]
    if set(points) != {str(i) for i in SELECTED_INDICES}:
        raise ValueError("landmark whitelist mismatch")
    for point in points.values():
        if point is None:
            continue
        if set(point) != {"x", "y", "z"} or any(
            isinstance(point[a], bool)
            or not isinstance(point[a], (int, float))
            or not isfinite(point[a])
            for a in ("x", "y")
        ):
            raise ValueError("invalid required x/y geometry")
        if point["z"] is not None and (
            isinstance(point["z"], bool)
            or not isinstance(point["z"], (int, float))
            or not isfinite(point["z"])
        ):
            raise ValueError("nonfinite z must be explicitly absent")
    missing = [i for i in REQUIRED_INDICES if points[str(i)] is None]
    optional = [i for i in SELECTED_INDICES if i not in REQUIRED_INDICES and points[str(i)] is None]
    z_missing = [
        i for i in SELECTED_INDICES if points[str(i)] is None or points[str(i)]["z"] is None
    ]
    if (
        geometry["missing_required_indices"] != missing
        or geometry["missing_optional_indices"] != optional
        or geometry["missing_z_indices"] != z_missing
    ):
        raise ValueError("missing-geometry flags disagree with raw primitives")
    if missing and row["feature_status"] == "usable":
        raise ValueError("usable frame missing required face/eye anchors")
    if geometry["face_anchors"] != {str(i): points[str(i)] for i in FACE_ANCHOR_INDICES}:
        raise ValueError("face anchors disagree with raw landmarks")
    width, height = geometry["camera_resolution"]
    if not _same_numbers(geometry["eyes"], eye_records(points, width, height)):
        raise ValueError("derived eye record disagrees with raw landmarks")
    if not _same_numbers(
        geometry["interocular_distance_px"], interocular_distance(geometry["eyes"], width, height)
    ):
        raise ValueError("interocular distance disagrees with raw primitives")
    if row["feature_status"] == "usable":
        baseline = reconstruct_r0(geometry)
        if baseline is None or not all(
            isclose(getattr(baseline, axis), row[f"{axis}_feature"], abs_tol=1e-10, rel_tol=1e-10)
            for axis in ("horizontal", "vertical")
        ):
            raise ValueError("raw geometry does not reconstruct recorded R0")
    matrix, status = geometry["facial_transformation_matrix"], geometry["pose_transform_status"]
    if status not in ("available", "not_exposed", "malformed"):
        raise ValueError("invalid optional pose status")
    if status == "available":
        if (
            not isinstance(matrix, list)
            or len(matrix) != 4
            or any(
                not isinstance(r, list)
                or len(r) != 4
                or any(
                    not isinstance(v, (int, float)) or isinstance(v, bool) or not isfinite(v)
                    for v in r
                )
                for r in matrix
            )
        ):
            raise ValueError("invalid optional pose matrix")
    elif matrix is not None:
        raise ValueError("unavailable pose must not have a matrix")
    return geometry


def inspect_capture(report):
    """Schema-only inspection is permitted on the holdout; no accuracy metrics."""
    try:
        for key, expected in configuration().items():
            if report[key] != expected:
                raise ValueError(f"incompatible protocol/schema: {key}")
        if (
            report["session"] not in SESSION_ROLES
            or report["session_role"] != SESSION_ROLES[report["session"]]
        ):
            raise ValueError("incompatible session/holdout identity")
        detector = report["detector"]
        if (
            not detector["mediapipe_version"]
            or len(detector["model_sha256"]) != 64
            or detector["options_policy"] != "production_defaults_unchanged"
            or detector["camera_intrinsics"] is not None
        ):
            raise ValueError("missing detector/model/intrinsics provenance")
        # Explicit adapter ONLY AFTER checking the new study identity; reuse the
        # frozen schedule/timing/calibration verifier, never silently mix studies.
        validate_base({**report, **base_configuration()})
        counts = {
            k: 0
            for k in (
                "calibration_geometry_frames",
                "validation_geometry_frames",
                "complete_z_frames",
                "partial_z_frames",
                "missing_z_frames",
                "pose_transform_frames",
                "missing_geometry_attempts",
                "partial_xy_frames",
                "malformed_pose_frames",
                "usable_validation_samples",
                "unavailable_validation_samples",
            )
        }
        for phase, presentations in (
            ("calibration", report["calibration_presentations"]),
            ("validation", report["trials"]),
        ):
            for presentation in presentations:
                order = (
                    presentation["order"] if phase == "calibration" else presentation["trial_order"]
                )
                for row in presentation["samples"]:
                    if row["phase"] != phase or row["presentation_order"] != order:
                        raise ValueError("sample phase/order mismatch")
                    if phase == "validation":
                        counts[
                            "usable_validation_samples"
                            if row["gaze_status"] == "usable"
                            else "unavailable_validation_samples"
                        ] += 1
                    geometry = _validate_geometry(row, report)
                    if geometry is None:
                        counts["missing_geometry_attempts"] += 1
                        continue
                    counts[f"{phase}_geometry_frames"] += 1
                    missing_z = len(geometry["missing_z_indices"])
                    counts[
                        "complete_z_frames"
                        if missing_z == 0
                        else "missing_z_frames"
                        if missing_z == len(SELECTED_INDICES)
                        else "partial_z_frames"
                    ] += 1
                    counts["partial_xy_frames"] += bool(geometry["missing_required_indices"])
                    counts["pose_transform_frames"] += (
                        geometry["pose_transform_status"] == "available"
                    )
                    counts["malformed_pose_frames"] += (
                        geometry["pose_transform_status"] == "malformed"
                    )
        if not isinstance(report["camera_reads"], int) or report["camera_reads"] < sum(
            len(t["samples"]) for t in report["calibration_presentations"] + report["trials"]
        ):
            raise ValueError("camera reads smaller than logged attempts")
        return {
            "participant": report["participant"],
            "session": report["session"],
            "session_role": report["session_role"],
            "protocol_name": report["protocol_name"],
            "protocol_version": report["protocol_version"],
            **counts,
            "camera_reads": report["camera_reads"],
            "failed_camera_reads": report["failed_camera_reads"],
            "no_face_observations": report["no_face_observations"],
            "note": "Schema/R0 consistency only; no R1/R2 evaluation or holdout outcome inspection.",
        }
    except (KeyError, TypeError, OverflowError, AttributeError) as error:
        raise ValueError(f"missing/malformed raw-geometry capture: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect_capture(json.loads(args.capture.read_text()))
    serialized = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
            parser.error("inspection output must stay under ignored .venv")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            output.write(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
