"""Small, preregistered mapping and causal-filter benchmark on v2 captures."""

import json
from collections import deque
from dataclasses import dataclass
from math import hypot, isclose, isfinite
from pathlib import Path
from statistics import mean, median

from experiments.gaze_failure_solution_benchmark.analysis import diagnose_records
from experiments.intentional_gaze_targeting.analysis import DwellState, analyze_session
from eye_tracker.gaze.calibration import CalibrationSample, IndependentLinearMapping
from eye_tracker.gaze.calibration import fit_independent_linear as fit_production
from validation.real_calibration import percentile

DATA_PATHS = tuple(Path(f".venv/intentional-gaze-cagri-live-{n}.json") for n in (1, 2))
LEVELS = (0.2, 0.5, 0.8)
MAPPINGS = ("M0", "M1", "M2")
FILTERS = ("T0", "T1", "T2")


@dataclass(frozen=True)
class AffineMapping:
    x_h: float
    x_v: float
    x_intercept: float
    y_h: float
    y_v: float
    y_intercept: float

    def predict(self, horizontal: float, vertical: float) -> tuple[float, float]:
        return (
            self.x_h * horizontal + self.x_v * vertical + self.x_intercept,
            self.y_h * horizontal + self.y_v * vertical + self.y_intercept,
        )


def _solve_3x3(matrix: list[list[float]], values: list[float]) -> tuple[float, float, float]:
    """Solve normal equations with pivoting; reject rank-deficient calibration."""
    augmented = [row[:] + [value] for row, value in zip(matrix, values)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("calibration feature matrix is rank deficient")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(3):
            if row != column:
                factor = augmented[row][column]
                augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return tuple(augmented[row][3] for row in range(3))


def _affine_axis(points: list[dict], target_key: str) -> tuple[float, float, float]:
    vectors = [(p["median_horizontal_feature"], p["median_vertical_feature"], 1.0) for p in points]
    matrix = [[sum(v[i] * v[j] for v in vectors) for j in range(3)] for i in range(3)]
    targets = [sum(v[i] * p[target_key] for v, p in zip(vectors, points)) for i in range(3)]
    return _solve_3x3(matrix, targets)


def fit_mapping(points: list[dict], kind: str):
    """Fit only saved ordinary calibration presentation medians."""
    if kind not in MAPPINGS:
        raise ValueError("unknown mapping")
    if len(points) < 3:
        raise ValueError("insufficient calibration presentations")
    for point in points:
        if any(
            not isinstance(point.get(key), (int, float)) or not isfinite(point[key])
            for key in (
                "median_horizontal_feature",
                "median_vertical_feature",
                "target_x",
                "target_y",
            )
        ):
            raise ValueError("missing or nonfinite calibration feature or target")
    if kind == "M1":
        if any(sum(p["target_x"] == value for p in points) < 2 for value in LEVELS) or any(
            sum(p["target_y"] == value for p in points) < 2 for value in LEVELS
        ):
            raise ValueError("axis-median calibration requires all three levels")
        points = [
            {
                "median_horizontal_feature": median(
                    p["median_horizontal_feature"] for p in points if p["target_x"] == value
                ),
                "median_vertical_feature": median(
                    p["median_vertical_feature"] for p in points if p["target_y"] == value
                ),
                "target_x": value,
                "target_y": value,
            }
            for value in LEVELS
        ]
    if kind in ("M0", "M1"):
        return fit_production(
            CalibrationSample(
                p["median_horizontal_feature"],
                p["median_vertical_feature"],
                p["target_x"],
                p["target_y"],
            )
            for p in points
        )
    if len(points) < 4:
        raise ValueError("affine calibration requires at least four presentations")
    return AffineMapping(*_affine_axis(points, "target_x"), *_affine_axis(points, "target_y"))


def mapping_coefficients(mapping) -> dict:
    return {key: getattr(mapping, key) for key in mapping.__dataclass_fields__}


def calibration_diagnostics(points: list[dict], kind: str) -> dict:
    mapping = fit_mapping(points, kind)
    residuals = []
    leave_one_out = []
    for index, point in enumerate(points):
        prediction = mapping.predict(
            point["median_horizontal_feature"], point["median_vertical_feature"]
        )
        residuals.append(
            {
                "target_x": point["target_x"],
                "target_y": point["target_y"],
                "x": prediction[0] - point["target_x"],
                "y": prediction[1] - point["target_y"],
            }
        )
        held_out = fit_mapping(points[:index] + points[index + 1 :], kind)
        predicted = held_out.predict(
            point["median_horizontal_feature"], point["median_vertical_feature"]
        )
        leave_one_out.append((predicted[0] - point["target_x"], predicted[1] - point["target_y"]))
    coefficients = mapping_coefficients(mapping)
    if isinstance(mapping, IndependentLinearMapping):
        gain_x, gain_y = abs(mapping.x_slope), abs(mapping.y_slope)
    else:
        gain_x = hypot(mapping.x_h, mapping.x_v)
        gain_y = hypot(mapping.y_h, mapping.y_v)
    return {
        "coefficients": coefficients,
        "x_mae": mean(abs(item["x"]) for item in residuals),
        "y_mae": mean(abs(item["y"]) for item in residuals),
        "leave_one_out_x_mae": mean(abs(pair[0]) for pair in leave_one_out),
        "leave_one_out_y_mae": mean(abs(pair[1]) for pair in leave_one_out),
        "x_feature_gain_norm": gain_x,
        "y_feature_gain_norm": gain_y,
        "residuals": residuals,
    }


def validate_report(report: dict) -> None:
    """Exclude all other protocols, pilots, participants, and sessions."""
    if (report.get("protocol_name"), report.get("protocol_version")) != (
        "intentional_gaze_targeting",
        2,
    ):
        raise ValueError("incompatible protocol")
    if report.get("participant") != "cagri" or report.get("session") not in (
        "live-1",
        "live-2",
    ):
        raise ValueError("incompatible participant or session")
    analyze_session(report)
    for row in report["target_samples"]:
        if row["status"] == "usable" and any(
            not isinstance(row.get(key), (int, float)) or not isfinite(row[key])
            for key in ("horizontal_feature", "vertical_feature")
        ):
            raise ValueError("usable target sample lacks finite raw feature")


def filter_predictions(
    predictions: list[tuple[float, float] | None], kind: str
) -> list[tuple[float, float] | None]:
    """Apply one causal filter per trial; unavailable observations clear state."""
    if kind not in FILTERS:
        raise ValueError("unknown temporal filter")
    output = []
    previous = None
    history: deque[tuple[float, float]] = deque(maxlen=5)
    for prediction in predictions:
        if prediction is None:
            previous = None
            history.clear()
            output.append(None)
        elif kind == "T0":
            output.append(prediction)
        elif kind == "T1":
            previous = (
                prediction
                if previous is None
                else tuple(0.35 * raw + 0.65 * old for raw, old in zip(prediction, previous))
            )
            output.append(previous)
        else:
            history.append(prediction)
            output.append((median(p[0] for p in history), median(p[1] for p in history)))
    return output


def replay_trial(trial: dict, rows: list[dict], predictions: list[tuple[float, float] | None]):
    """Replay observed timestamps; production early successes censor later outcomes."""
    if len(rows) != len(predictions):
        raise ValueError("prediction count differs from sample count")
    state = DwellState(
        trial["target_onset_monotonic_seconds"],
        trial["target_x"],
        trial["target_y"],
        0.10,
        0.10,
        1.0,
        5.0,
    )
    for row, prediction in zip(rows, predictions):
        if state.outcome is not None:
            break
        state.observe(row["monotonic_seconds"], prediction)
    if state.outcome is None:
        if trial["target_summary"]["outcome"] == "success":
            state.outcome = "censored"
        else:
            state.expire(trial["target_end_monotonic_seconds"])
    if state.outcome is None:
        raise ValueError("incomplete target observation window")
    return state.timing()


def _p95(values: list[float]) -> float | None:
    return percentile(values, 95) if values else None


def _median(values: list[float]) -> float | None:
    return median(values) if values else None


def _summarize(records: list[dict]) -> dict:
    trials = [record["timing"] for record in records]
    rows = [sample for record in records for sample in record["samples"]]
    usable = [row for row in rows if row["prediction"] is not None]
    errors = [
        (abs(row["prediction"][0] - row["target_x"]), abs(row["prediction"][1] - row["target_y"]))
        for row in usable
    ]
    successful = [trial for trial in trials if trial["outcome"] == "success"]
    first = [
        trial["first_entry_seconds"] for trial in trials if trial["first_entry_seconds"] is not None
    ]
    entry = [trial["successful_entry_seconds"] for trial in successful]
    confirmed = [trial["confirmed_acquisition_seconds"] for trial in successful]
    return {
        "trials": len(trials),
        "successes": len(successful),
        "observed_success_rate": len(successful) / len(trials) if trials else None,
        "timeouts": sum(trial["outcome"] == "timeout" for trial in trials),
        "censored": sum(trial["outcome"] == "censored" for trial in trials),
        "median_first_entry_seconds": _median(first),
        "median_successful_entry_seconds": _median(entry),
        "median_confirmed_acquisition_seconds": _median(confirmed),
        "p95_confirmed_acquisition_seconds": _p95(confirmed),
        "x_mae": mean(pair[0] for pair in errors) if errors else None,
        "y_mae": mean(pair[1] for pair in errors) if errors else None,
        "euclidean_mae": mean(hypot(*pair) for pair in errors) if errors else None,
        "p95_euclidean_error": _p95([hypot(*pair) for pair in errors]),
        "usable_predictions": len(usable),
        "unavailable_predictions": len(rows) - len(usable),
        "target_entries": sum(trial["target_entries"] for trial in trials),
        "target_reentries": sum(trial["target_reentries"] for trial in trials),
        "dwell_interruptions": sum(trial["dwell_interruptions"] for trial in trials),
        "median_longest_dwell_seconds": _median(
            [trial["longest_dwell_seconds"] for trial in trials]
        ),
    }


def evaluate(reports: list[dict], mapping_kind: str, temporal_kind: str) -> dict:
    """Fit calibration-only mapping, then evaluate fixed recorded target windows."""
    if len(reports) != 2 or {r.get("session") for r in reports} != {"live-1", "live-2"}:
        raise ValueError("benchmark requires exactly the two valid sessions")
    records = []
    calibrations = {}
    baseline_max_error = 0.0
    baseline_timing_mismatches = 0
    for report in reports:
        validate_report(report)
        session = report["session"]
        mapping = fit_mapping(report["calibration_presentations"], mapping_kind)
        calibrations[session] = calibration_diagnostics(
            report["calibration_presentations"], mapping_kind
        )
        if mapping_kind == "M0" and mapping_coefficients(mapping) != report["mapping_coefficients"]:
            raise ValueError("M0 does not reproduce saved calibration coefficients")
        by_trial = {trial["trial_order"]: [] for trial in report["trials"]}
        for row in report["target_samples"]:
            by_trial[row["trial_order"]].append(row)
        for trial in report["trials"]:
            rows = by_trial[trial["trial_order"]]
            raw = [
                mapping.predict(row["horizontal_feature"], row["vertical_feature"])
                if row["status"] == "usable"
                else None
                for row in rows
            ]
            if mapping_kind == "M0":
                for row, prediction in zip(rows, raw):
                    if prediction is not None:
                        baseline_max_error = max(
                            baseline_max_error,
                            abs(prediction[0] - row["raw_predicted_x"]),
                            abs(prediction[1] - row["raw_predicted_y"]),
                        )
            filtered = filter_predictions(raw, temporal_kind)
            timing = replay_trial(trial, rows, filtered)
            if mapping_kind == "M0" and temporal_kind == "T0":
                saved = trial["target_summary"]
                for key, value in timing.items():
                    actual = saved[key]
                    if isinstance(value, float):
                        matches = isclose(value, actual, rel_tol=0, abs_tol=1e-8)
                    else:
                        matches = value == actual
                    baseline_timing_mismatches += not matches
            records.append(
                {
                    "session": session,
                    "target_id": trial["target_id"],
                    "target_x": trial["target_x"],
                    "target_y": trial["target_y"],
                    "block": trial["block"],
                    "target_onset": trial["target_onset_monotonic_seconds"],
                    "timing": timing,
                    "samples": [
                        {
                            "timestamp": row["monotonic_seconds"],
                            "target_x": row["target_x"],
                            "target_y": row["target_y"],
                            "prediction": prediction,
                        }
                        for row, prediction in zip(rows, filtered)
                    ],
                }
            )
    if mapping_kind == "M0" and (
        baseline_max_error > 1e-10 or (temporal_kind == "T0" and baseline_timing_mismatches)
    ):
        raise ValueError("baseline replay disagrees with recorded production outcomes")
    return {
        "mapping": mapping_kind,
        "temporal": temporal_kind,
        "pooled": _summarize(records),
        "sessions": {
            session: _summarize([r for r in records if r["session"] == session])
            for session in ("live-1", "live-2")
        },
        "by_row": {str(y): _summarize([r for r in records if r["target_y"] == y]) for y in LEVELS},
        "by_column": {
            str(x): _summarize([r for r in records if r["target_x"] == x]) for x in LEVELS
        },
        "by_target": {
            target: _summarize([r for r in records if r["target_id"] == target])
            for target in sorted({r["target_id"] for r in records})
        },
        "calibration": calibrations,
        "baseline_max_prediction_error": baseline_max_error if mapping_kind == "M0" else None,
        "baseline_timing_mismatches": baseline_timing_mismatches
        if mapping_kind == "M0" and temporal_kind == "T0"
        else None,
        "residual_diagnosis": diagnose_records(records),
    }


def candidate_gates(baseline: dict, candidate: dict, family: str) -> dict[str, bool]:
    """Apply fixed engineering gates to conservative observed-success counts."""
    success_gain = candidate["success_rate"] - baseline["success_rate"]
    x_ratio = candidate["x_mae"] / baseline["x_mae"]
    y_ratio = candidate["y_mae"] / baseline["y_mae"]
    latency_delta = (
        candidate["median_confirmed_acquisition_seconds"]
        - baseline["median_confirmed_acquisition_seconds"]
    )
    if family == "mapping":
        return {
            "success_gain": success_gain >= 0.10 - 1e-12,
            "sessions": all(
                candidate["session_rates"][key] >= value - 0.05 - 1e-12
                for key, value in baseline["session_rates"].items()
            ),
            "y_mae": y_ratio <= 0.85 + 1e-12,
            "x_mae": x_ratio <= 1.15 + 1e-12,
            "latency": latency_delta <= 0.50 + 1e-12,
            "calibration_only": True,
        }
    if family == "temporal":
        return {
            "success_gain": success_gain >= 0.05 - 1e-12,
            "stability": (
                candidate["dwell_interruptions"] <= 0.8 * baseline["dwell_interruptions"]
                or candidate["target_reentries"] <= 0.8 * baseline["target_reentries"]
            ),
            "y_mae": y_ratio <= 1.10 + 1e-12,
            "x_mae": x_ratio <= 1.10 + 1e-12,
            "latency": latency_delta <= 0.50 + 1e-12,
        }
    if family == "combined":
        return {
            "sessions": all(
                candidate["session_rates"][key] > value
                for key, value in baseline["session_rates"].items()
            ),
            "success_gain": success_gain >= 0.15 - 1e-12,
            "y_mae": y_ratio <= 0.85 + 1e-12,
            "x_mae": x_ratio <= 1.15 + 1e-12,
            "latency": latency_delta <= 0.50 + 1e-12,
        }
    raise ValueError("unknown candidate family")


def gate_metrics(result: dict) -> dict:
    pooled = result["pooled"]
    return {
        "success_rate": pooled["observed_success_rate"],
        "session_rates": {
            name: item["observed_success_rate"] for name, item in result["sessions"].items()
        },
        "x_mae": pooled["x_mae"],
        "y_mae": pooled["y_mae"],
        "median_confirmed_acquisition_seconds": pooled["median_confirmed_acquisition_seconds"]
        if pooled["median_confirmed_acquisition_seconds"] is not None
        else float("inf"),
        "dwell_interruptions": pooled["dwell_interruptions"],
        "target_reentries": pooled["target_reentries"],
    }


def run_benchmark(reports: list[dict]) -> dict:
    results = {
        "M0_T0": evaluate(reports, "M0", "T0"),
        "M0_T1": evaluate(reports, "M0", "T1"),
        "M0_T2": evaluate(reports, "M0", "T2"),
        "M1_T0": evaluate(reports, "M1", "T0"),
        "M2_T0": evaluate(reports, "M2", "T0"),
    }
    baseline = gate_metrics(results["M0_T0"])
    gates = {}
    for key, family in (
        ("M0_T1", "temporal"),
        ("M0_T2", "temporal"),
        ("M1_T0", "mapping"),
        ("M2_T0", "mapping"),
    ):
        gates[key] = candidate_gates(baseline, gate_metrics(results[key]), family)
    temporal_pass = [key for key in ("M0_T1", "M0_T2") if all(gates[key].values())]
    mapping_pass = [key for key in ("M1_T0", "M2_T0") if all(gates[key].values())]
    if temporal_pass and mapping_pass:
        best_t = max(temporal_pass, key=lambda key: results[key]["pooled"]["successes"])
        best_m = max(mapping_pass, key=lambda key: results[key]["pooled"]["successes"])
        combined_key = best_m[:2] + "_" + best_t[-2:]
        results[combined_key] = evaluate(reports, best_m[:2], best_t[-2:])
        gates[combined_key] = candidate_gates(
            baseline, gate_metrics(results[combined_key]), "combined"
        )
    return {"results": results, "gates": gates}


def main() -> None:
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in DATA_PATHS]
    result = run_benchmark(reports)
    # Summaries contain derived numbers only; raw captures stay ignored locally.
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
