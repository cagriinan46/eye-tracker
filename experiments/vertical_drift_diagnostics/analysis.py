"""Descriptive fixed-center summaries; never infer causes from association."""

from collections import Counter, defaultdict
from math import isfinite
from statistics import StatisticsError, correlation

from experiments.vertical_collapse_diagnostics.analysis import describe_values

_DIAGNOSTICS = (
    "horizontal",
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
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def summarize_checkpoints(rows: list[dict], calibration_center_vertical: float) -> dict:
    """Group repeated CENTER samples and report shifts relative to two baselines."""
    baseline = _finite(calibration_center_vertical, "calibration center")
    grouped: dict[int, list[dict]] = defaultdict(list)
    if not rows:
        raise ValueError("checkpoint rows are required")
    for row in rows:
        if not isinstance(row, dict) or row.get("phase") != "checkpoint":
            raise ValueError("only checkpoint rows are accepted")
        checkpoint = row.get("checkpoint")
        if isinstance(checkpoint, bool) or not isinstance(checkpoint, int) or checkpoint < 0:
            raise ValueError("checkpoint ID must be a nonnegative integer")
        if (_finite(row.get("target_x"), "target x"), _finite(row.get("target_y"), "target y")) != (
            0.5,
            0.5,
        ):
            raise ValueError("checkpoint target must be CENTER (0.5, 0.5)")
        _finite(row.get("monotonic_seconds"), "monotonic time")
        status = row.get("status")
        if not isinstance(status, str) or not status:
            raise ValueError("availability status is required")
        for key in _DIAGNOSTICS:
            value = row.get(key)
            if value is not None:
                _finite(value, key)
        if status == "usable" and any(row.get(key) is None for key in _DIAGNOSTICS):
            raise ValueError("usable checkpoint needs all derived diagnostics")
        grouped[checkpoint].append(row)

    if 0 not in grouped or sorted(grouped) != list(range(max(grouped) + 1)):
        raise ValueError("checkpoints must start at zero and have no missing IDs")
    checkpoints = []
    first_median = None
    first_diagnostics = None
    for checkpoint, group in sorted(grouped.items()):
        usable = [row for row in group if row["status"] == "usable"]
        if not usable:
            raise ValueError(f"checkpoint {checkpoint} has no usable samples")
        features = {key: describe_values(row[key] for row in usable) for key in _DIAGNOSTICS}
        current = features["vertical"]["median"]
        if first_median is None:
            first_median = current
            first_diagnostics = {key: value["median"] for key, value in features.items()}
        checkpoints.append(
            {
                "checkpoint": checkpoint,
                "elapsed_seconds": describe_values(row["monotonic_seconds"] for row in group),
                "availability": dict(Counter(row["status"] for row in group)),
                **features,
                "delta_from_calibration_center": current - baseline,
                "delta_from_checkpoint_0": current - first_median,
                "diagnostic_deltas_from_checkpoint_0": {
                    key: value["median"] - first_diagnostics[key]
                    for key, value in features.items()
                    if key != "vertical"
                },
            }
        )

    associations = {}
    vertical_medians = [item["vertical"]["median"] for item in checkpoints]
    # Binocular vertical is the mean of the two eyes, so correlating it with
    # either constituent eye would be partly tautological. Per-eye deltas above
    # are the descriptive one-eye comparison instead.
    for key in ("binocular_eye_opening", "head_center_y"):
        values = [item[key]["median"] for item in checkpoints]
        try:
            associations[key] = correlation(vertical_medians, values)
        except StatisticsError:
            associations[key] = None
    return {
        "calibration_center_vertical": baseline,
        "checkpoints": checkpoints,
        "first_to_last_vertical_delta": checkpoints[-1]["vertical"]["median"] - first_median,
        "checkpoint_median_associations": associations,
    }


def compare_sessions(reports: list[dict]) -> dict:
    """Compare two fresh sessions without pooling their frame distributions."""
    if len(reports) != 2:
        raise ValueError("exactly two session reports are required")
    by_session = {}
    participants = set()
    for report in reports:
        participant, session = report.get("participant"), report.get("session")
        if not isinstance(participant, str) or not participant.strip():
            raise ValueError("participant ID is required")
        if session not in {"A", "B"} or session in by_session:
            raise ValueError("one distinct A and B session is required")
        participants.add(participant)
        by_session[session] = summarize_checkpoints(
            [row for row in report.get("rows", []) if row.get("phase") == "checkpoint"],
            report.get("calibration_center_vertical"),
        )
    if len(participants) != 1:
        raise ValueError("sessions must belong to the same participant")
    first, second = by_session["A"], by_session["B"]
    a_checkpoints, b_checkpoints = first["checkpoints"], second["checkpoints"]
    if len(a_checkpoints) != len(b_checkpoints):
        raise ValueError("sessions have different checkpoint counts")
    return {
        "participant": participants.pop(),
        "sessions": by_session,
        "B_minus_A": {
            "calibration_center_vertical": second["calibration_center_vertical"]
            - first["calibration_center_vertical"],
            "checkpoint_vertical_medians": [
                b["vertical"]["median"] - a["vertical"]["median"]
                for a, b in zip(a_checkpoints, b_checkpoints, strict=True)
            ],
        },
    }
