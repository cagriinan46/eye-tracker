"""Replay a fixed linear baseline with causal CENTER-derived additive offsets."""

from collections import defaultdict
from math import isclose, isfinite
from statistics import median

from experiments.vertical_error_decomposition.analysis import (
    calibration_from_rows,
    verify_recorded_mapping,
)
from experiments.vertical_mapping_evaluation.analysis import evaluate_held_out
from validation.real_calibration import VALIDATION_TARGETS, _evaluate_predictions

TARGETS = {target.name: target for target in VALIDATION_TARGETS}


def center_offset(known_center_y: float, baseline_prediction: float) -> float:
    """Calculate the sole correction; the existing slope stays fixed."""
    if not all(isfinite(value) for value in (known_center_y, baseline_prediction)):
        raise ValueError("center and baseline prediction must be finite")
    return known_center_y - baseline_prediction


def checkpoint_segments(events: list[tuple]) -> dict[tuple[str, int], int]:
    """Assign trials to the latest already observed CENTER checkpoint."""
    current = None
    segments = {}
    for phase, checkpoint, trial in events:
        if phase == "checkpoint":
            if (
                not isinstance(checkpoint, int)
                or isinstance(checkpoint, bool)
                or checkpoint != (0 if current is None else current + 1)
            ):
                raise ValueError("checkpoints must start at zero and be sequential")
            current = checkpoint
        elif phase == "validation":
            if current is None:
                raise ValueError("validation trial before checkpoint 0")
            if trial in segments:
                raise ValueError("duplicate validation trial")
            segments[trial] = current
        else:
            raise ValueError("unknown event phase")
    return segments


def apply_offsets(trials: list[dict], segments: dict, offsets: dict[int, float]) -> list[dict]:
    """Return trial copies with only their y prediction shifted."""
    corrected = []
    for trial in trials:
        key = (trial["target_id"], trial["trial_number"])
        checkpoint = segments[key]
        offset = offsets[checkpoint]
        corrected.append({**trial, "predicted_y": trial["predicted_y"] + offset})
    return corrected


def _events_and_features(rows: list[dict]) -> tuple[list[tuple], dict[int, tuple[float, float]]]:
    """Read presentation order from recorded rows, never from target labels."""
    grouped = []
    last_key = None
    last_time = float("-inf")
    for row in rows:
        timestamp = row.get("monotonic_seconds")
        if (
            not isinstance(timestamp, (int, float))
            or not isfinite(timestamp)
            or timestamp < last_time
        ):
            raise ValueError("rows must have chronological finite timestamps")
        last_time = timestamp
        phase = row.get("phase")
        key = (
            phase,
            row.get("checkpoint")
            if phase == "checkpoint"
            else (row.get("target_id"), row.get("trial_number")),
        )
        if key != last_key:
            grouped.append((key, []))
            last_key = key
        grouped[-1][1].append(row)

    events = []
    features = {}
    seen_calibration = set()
    calibration_finished = False
    for (phase, identifier), group in grouped:
        if phase == "calibration":
            if calibration_finished or identifier in seen_calibration:
                raise ValueError("calibration must precede checkpoints without repeats")
            seen_calibration.add(identifier)
            continue
        calibration_finished = True
        if phase == "checkpoint":
            if any((row.get("target_x"), row.get("target_y")) != (0.5, 0.5) for row in group):
                raise ValueError("checkpoint must be exact CENTER")
            usable = [row for row in group if row.get("status") == "usable"]
            if len(usable) < 5 or any(
                not isinstance(row.get(axis), (int, float)) or not isfinite(row[axis])
                for row in usable
                for axis in ("horizontal", "vertical")
            ):
                raise ValueError("checkpoint needs five finite usable features")
            features[identifier] = (
                median(row["horizontal"] for row in usable),
                median(row["vertical"] for row in usable),
            )
            events.append((phase, identifier, None))
        elif phase == "validation":
            events.append((phase, None, identifier))
        else:
            raise ValueError("unknown presentation phase")
    return events, features


def _metrics(trials: list[dict], width: int, height: int) -> dict:
    points = [
        (TARGETS[item["target_id"]], item["trial_number"], item["predicted_x"], item["predicted_y"])
        for item in trials
    ]
    result = _evaluate_predictions(points, width, height)
    summary = result["summary"]
    return {
        "sample_count": len(trials),
        "vertical_mae": summary["mean_vertical_absolute_error"],
        "signed_vertical_bias": summary["mean_signed_y_bias"],
        "median_absolute_vertical_error": summary["median_vertical_absolute_error"],
        "p95_absolute_vertical_error": summary["p95_vertical_absolute_error"],
        "vertical_ordering": result["spatial_ordering"]["y"],
    }


def analyze_session(report: dict) -> dict:
    """Verify baseline replay, then compare three predeclared offsets on held-out trials."""
    rows = report["rows"]
    mapping, samples = calibration_from_rows(rows)
    verify_recorded_mapping(mapping, report["mapping_coefficients"])
    width, height = report["window_image_area"]
    baseline = evaluate_held_out(rows, mapping, width, height)
    trials = baseline["trials"]
    saved = report["held_out_validation"]["trials"]
    saved_by_key = {(item["target_id"], item["trial_number"]): item for item in saved}
    if len(saved_by_key) != len(trials):
        raise ValueError("saved baseline trial count differs from replay")
    for trial in trials:
        recorded = saved_by_key.get((trial["target_id"], trial["trial_number"]))
        if recorded is None or any(
            not isclose(trial[key], recorded[key], rel_tol=1e-9, abs_tol=1e-10)
            for key in ("predicted_x", "predicted_y")
        ):
            raise ValueError("baseline replay disagrees with recorded prediction")

    events, features = _events_and_features(rows)
    segments = checkpoint_segments(events)
    if set(segments) != set(saved_by_key) or sorted(features) != list(range(5)):
        raise ValueError("expected five checkpoints and all 16 held-out trials")
    by_segment = defaultdict(list)
    for trial in trials:
        by_segment[segments[trial["target_id"], trial["trial_number"]]].append(trial)
    if {key: len(value) for key, value in by_segment.items()} != {0: 4, 1: 4, 2: 4, 3: 4}:
        raise ValueError("expected four trials after each applicable checkpoint")

    center = next(sample for sample in samples if (sample.target_x, sample.target_y) == (0.5, 0.5))
    known_y = center.target_y

    offsets = {
        index: center_offset(known_y, mapping.predict(*feature)[1])
        for index, feature in features.items()
    }
    calibration_offset = center_offset(
        known_y, mapping.predict(center.horizontal_feature, center.vertical_feature)[1]
    )
    candidate_trials = {
        "calibration_center": apply_offsets(
            trials, {key: 0 for key in segments}, {0: calibration_offset}
        ),
        "immediate_center": apply_offsets(trials, {key: 0 for key in segments}, {0: offsets[0]}),
        "checkpoint_refresh": apply_offsets(trials, segments, offsets),
    }
    candidates = {
        name: {
            "metrics": _metrics(candidate, width, height),
            "offsets": {"calibration": calibration_offset}
            if name == "calibration_center"
            else ({0: offsets[0]} if name == "immediate_center" else offsets),
        }
        for name, candidate in candidate_trials.items()
    }
    candidates["checkpoint_refresh"]["segments"] = [
        {
            "checkpoint": index,
            "offset": offsets[index],
            "baseline": _metrics(by_segment[index], width, height),
            "corrected": _metrics(
                [
                    trial
                    for trial in candidate_trials["checkpoint_refresh"]
                    if segments[trial["target_id"], trial["trial_number"]] == index
                ],
                width,
                height,
            ),
        }
        for index in range(4)
    ]
    return {
        "participant": report["participant"],
        "session": report["session"],
        "baseline_coefficients": report["mapping_coefficients"],
        "baseline": _metrics(trials, width, height),
        "candidates": candidates,
        "checkpoint_4_has_no_future_trials": True,
    }
