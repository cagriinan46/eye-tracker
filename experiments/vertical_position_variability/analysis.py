"""Describe fixed-Y position and identical-target repeat variation separately."""

from collections import Counter, defaultdict
from math import isfinite
from statistics import median

from experiments.vertical_collapse_diagnostics.analysis import describe_values

_MEASURES = (
    "vertical",
    "horizontal",
    "left_vertical",
    "right_vertical",
    "left_horizontal",
    "right_horizontal",
    "left_eye_opening",
    "right_eye_opening",
    "binocular_eye_opening",
    "head_center_y",
)


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _validated_rows(rows: object, participant: str, session: str) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("nonempty diagnostic rows are required")
    coordinates: dict[tuple[str, str], tuple[float, float]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("diagnostic row must be an object")
        if row.get("participant") != participant or row.get("session") != session:
            raise ValueError("diagnostic rows must belong to one participant/session")
        phase, target_id, status = row.get("phase"), row.get("target_id"), row.get("status")
        if phase not in {"calibration", "validation", "checkpoint", "diagnostic"}:
            raise ValueError("unexpected diagnostic phase")
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("target ID is required")
        if not isinstance(status, str) or not status:
            raise ValueError("availability status is required")
        trial = row.get("checkpoint") if phase == "checkpoint" else row.get("trial_number")
        if isinstance(trial, bool) or not isinstance(trial, int) or trial < 0:
            raise ValueError("trial/checkpoint identifier is invalid")
        x, y = (_finite(row.get(key), key) for key in ("target_x", "target_y"))
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("target coordinates must be normalized")
        key = (phase, target_id)
        if key in coordinates and coordinates[key] != (x, y):
            raise ValueError("one target ID has conflicting coordinates")
        coordinates[key] = (x, y)
        _finite(row.get("monotonic_seconds"), "monotonic time")
        for name in _MEASURES:
            value = row.get(name)
            if status == "usable" and value is None:
                raise ValueError(f"usable row needs {name}")
            if value is not None:
                _finite(value, name)
    return rows


def _presentation_summaries(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for row in rows:
        trial = row.get("checkpoint") if row["phase"] == "checkpoint" else row["trial_number"]
        groups[row["phase"], row["target_id"], trial].append(row)
    presentations = []
    for (phase, target_id, trial), group in groups.items():
        usable = [row for row in group if row["status"] == "usable"]
        if not usable:
            raise ValueError(f"{phase} {target_id}/{trial} has no usable observations")
        dimensions = {(row["target_x"], row["target_y"]) for row in group}
        if len(dimensions) != 1:
            raise ValueError("presentation changed target coordinates")
        x, y = dimensions.pop()
        measures = {
            name: describe_values(row[name] for row in usable if row.get(name) is not None)
            for name in _MEASURES
        }
        presentations.append(
            {
                "phase": phase,
                "target_id": target_id,
                "trial": trial,
                "target_x": x,
                "target_y": y,
                "time_seconds": median(row["monotonic_seconds"] for row in usable),
                "usable_count": len(usable),
                "unavailable_count": len(group) - len(usable),
                "measures": measures,
            }
        )
    return sorted(presentations, key=lambda item: item["time_seconds"])


def _position_comparisons(
    presentations: list[dict], slope: float, *, split_diagnostic_trials: bool = False
) -> list[dict]:
    grouped: dict[tuple[str, float, int | None], dict[float, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in presentations:
        if item["phase"] == "checkpoint":
            continue
        if split_diagnostic_trials and item["phase"] != "diagnostic":
            continue
        trial = item["trial"] if split_diagnostic_trials else None
        grouped[item["phase"], item["target_y"], trial][item["target_x"]].append(item)
    comparisons = []
    for (phase, y, trial), x_groups in sorted(grouped.items()):
        if len(x_groups) < 2:
            continue
        positions = []
        for x, group in sorted(x_groups.items()):
            positions.append(
                {
                    "target_x": x,
                    "target_ids": sorted({item["target_id"] for item in group}),
                    "presentation_count": len(group),
                    "vertical_median": median(
                        item["measures"]["vertical"]["median"] for item in group
                    ),
                    "time_median_seconds": median(item["time_seconds"] for item in group),
                    "first_time_seconds": min(item["time_seconds"] for item in group),
                    "last_time_seconds": max(item["time_seconds"] for item in group),
                    "max_within_presentation_iqr": max(
                        item["measures"]["vertical"]["iqr"] for item in group
                    ),
                    "measure_medians": {
                        name: median(item["measures"][name]["median"] for item in group)
                        for name in _MEASURES
                    },
                }
            )
        values = [item["vertical_median"] for item in positions]
        span = max(values) - min(values)
        comparisons.append(
            {
                "phase": phase,
                "target_y": y,
                "trial": trial,
                "positions": positions,
                "observed_x_order": [
                    item["target_x"]
                    for item in sorted(
                        (entry for group in x_groups.values() for entry in group),
                        key=lambda entry: entry["time_seconds"],
                    )
                ],
                "vertical_median_span": span,
                "mapped_y_span": abs(slope) * span,
                "max_within_presentation_iqr": max(
                    item["max_within_presentation_iqr"] for item in positions
                ),
                "x_time_order_confounded": all(
                    left["last_time_seconds"] < right["first_time_seconds"]
                    for left, right in zip(positions, positions[1:])
                )
                or all(
                    right["last_time_seconds"] < left["first_time_seconds"]
                    for left, right in zip(positions, positions[1:])
                ),
            }
        )
    return comparisons


def _repeated_targets(presentations: list[dict], slope: float) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in presentations:
        grouped[item["phase"], item["target_id"]].append(item)
    repeats = []
    for (phase, target_id), group in sorted(grouped.items()):
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda item: item["time_seconds"])
        first, last = ordered[0], ordered[-1]
        values = [item["measures"]["vertical"]["median"] for item in ordered]
        delta = values[-1] - values[0]
        repeats.append(
            {
                "phase": phase,
                "target_id": target_id,
                "target_x": first["target_x"],
                "target_y": first["target_y"],
                "presentation_count": len(group),
                "vertical_medians": values,
                "vertical_median_span": max(values) - min(values),
                "vertical_median_delta": delta,
                "mapped_y_delta": slope * delta,
                "elapsed_seconds": last["time_seconds"] - first["time_seconds"],
                "first_time_seconds": first["time_seconds"],
                "last_time_seconds": last["time_seconds"],
                "measure_deltas": {
                    name: last["measures"][name]["median"] - first["measures"][name]["median"]
                    for name in _MEASURES
                },
            }
        )
    return repeats


def analyze_session(report: dict) -> dict:
    """Summarize one session without pooling participants or altering predictions."""
    if not isinstance(report, dict):
        raise ValueError("session report must be an object")
    participant, session = report.get("participant"), report.get("session")
    if (
        not isinstance(participant, str)
        or not participant
        or not isinstance(session, str)
        or not session
    ):
        raise ValueError("participant and session identifiers are required")
    coefficients = report.get("mapping_coefficients")
    if not isinstance(coefficients, dict):
        raise ValueError("mapping coefficients are required")
    slope = _finite(coefficients.get("y_slope"), "vertical slope")
    rows = _validated_rows(report.get("rows"), participant, session)
    presentations = _presentation_summaries(rows)
    return {
        "participant": participant,
        "session": session,
        "vertical_slope": slope,
        "availability": dict(Counter(row["status"] for row in rows)),
        "presentations": presentations,
        "position_comparisons": _position_comparisons(presentations, slope),
        "pass_comparisons": _position_comparisons(
            presentations, slope, split_diagnostic_trials=True
        ),
        "repeats": _repeated_targets(presentations, slope),
    }
