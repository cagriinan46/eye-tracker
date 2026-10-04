"""Offline summaries and monotonic-time acquisition state for coarse targeting."""

from dataclasses import dataclass
from math import hypot
from statistics import mean, median

from experiments.coarse_gaze_targeting_validation.protocol import (
    DWELL_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGET_HALF_HEIGHT,
    TARGET_HALF_WIDTH,
    TARGETS,
    TIMEOUT_SECONDS,
    TargetingTrial,
    inside_target,
    schedule,
)
from validation.real_calibration import CALIBRATION_TARGETS, Target, percentile

PRIMARY_SESSIONS = ("live-3", "live-4", "live-5")


def _median_or_none(values: list[float]) -> float | None:
    return median(values) if values else None


def _p95_or_none(values: list[float]) -> float | None:
    return percentile(values, 95) if values else None


@dataclass(slots=True)
class DwellState:
    """Observed continuous dwell; missing/outside samples break the interval."""

    onset: float
    target: Target
    active_since: float | None = None
    first_entry_time: float | None = None
    successful_entry_time: float | None = None
    acquired_time: float | None = None
    entries: int = 0
    interruptions: int = 0
    longest_dwell: float = 0.0
    outcome: str | None = None
    last_time: float | None = None

    def observe(
        self, timestamp: float, prediction: tuple[float, float] | None
    ) -> tuple[bool, float]:
        """Consume one timestamped raw prediction; success includes the 4 s boundary."""
        if timestamp < self.onset or (self.last_time is not None and timestamp < self.last_time):
            raise ValueError("sample timestamps must be monotonic after target onset")
        if self.outcome is not None:
            raise ValueError("trial already ended")
        self.last_time = timestamp
        if timestamp > self.onset + TIMEOUT_SECONDS:
            self.outcome = "timeout"
            return False, 0.0
        inside = prediction is not None and inside_target(*prediction, self.target)
        if not inside:
            if self.active_since is not None:
                self.interruptions += 1
            self.active_since = None
            return False, 0.0
        if self.active_since is None:
            self.active_since = timestamp
            self.entries += 1
            if self.first_entry_time is None:
                self.first_entry_time = timestamp
        dwell = timestamp - self.active_since
        self.longest_dwell = max(self.longest_dwell, dwell)
        if dwell >= DWELL_SECONDS - 1e-9:
            self.outcome = "success"
            self.successful_entry_time = self.active_since
            self.acquired_time = timestamp
        return True, dwell

    def expire(self, timestamp: float) -> None:
        if timestamp < self.onset:
            raise ValueError("timeout precedes target onset")
        if self.outcome is None and timestamp >= self.onset + TIMEOUT_SECONDS:
            self.outcome = "timeout"

    def timing(self) -> dict:
        return {
            "outcome": self.outcome,
            "first_entry_seconds": self.first_entry_time - self.onset
            if self.first_entry_time is not None
            else None,
            "successful_entry_seconds": self.successful_entry_time - self.onset
            if self.successful_entry_time is not None
            else None,
            "confirmed_acquisition_seconds": self.acquired_time - self.onset
            if self.acquired_time is not None
            else None,
            "target_entries": self.entries,
            "target_reentries": max(0, self.entries - 1),
            "dwell_interruptions": self.interruptions,
            "longest_dwell_seconds": self.longest_dwell,
        }


def summarize_trial(trial: TargetingTrial, state: DwellState, rows: list[dict]) -> dict:
    """Use every raw usable estimate for un-clipped spatial and availability metrics."""
    if state.outcome not in ("success", "timeout"):
        raise ValueError("trial has no terminal outcome")
    usable = [row for row in rows if row["status"] == "usable"]
    x_errors = [abs(row["raw_predicted_x"] - trial.target.x) for row in usable]
    y_errors = [abs(row["raw_predicted_y"] - trial.target.y) for row in usable]
    distances = [hypot(dx, dy) for dx, dy in zip(x_errors, y_errors)]
    return {
        **trial.identity(),
        **state.timing(),
        "usable_prediction_count": len(usable),
        "unavailable_prediction_count": len(rows) - len(usable),
        "availability_fraction": len(usable) / len(rows) if rows else 0.0,
        "median_absolute_x_error": _median_or_none(x_errors),
        "median_absolute_y_error": _median_or_none(y_errors),
        "median_euclidean_error": _median_or_none(distances),
        "p95_euclidean_error": _p95_or_none(distances),
        "final_prediction": [usable[-1]["raw_predicted_x"], usable[-1]["raw_predicted_y"]]
        if usable
        else None,
    }


def _group(trials: list[dict], rows: list[dict]) -> dict:
    successes = [item for item in trials if item["outcome"] == "success"]
    usable = [row for row in rows if row["status"] == "usable"]
    latencies = [item["confirmed_acquisition_seconds"] for item in successes]
    entries = [item["successful_entry_seconds"] for item in successes]
    x_error = [abs(row["raw_predicted_x"] - row["target_x"]) for row in usable]
    y_error = [abs(row["raw_predicted_y"] - row["target_y"]) for row in usable]
    euclidean = [hypot(dx, dy) for dx, dy in zip(x_error, y_error)]
    return {
        "trials": len(trials),
        "successful_trials": len(successes),
        "success_rate": len(successes) / len(trials) if trials else None,
        "timeout_rate": 1 - len(successes) / len(trials) if trials else None,
        "median_entry_latency_seconds": _median_or_none(entries),
        "median_confirmed_acquisition_seconds": _median_or_none(latencies),
        "p95_confirmed_acquisition_seconds": _p95_or_none(latencies),
        "x_mae": mean(x_error) if x_error else None,
        "y_mae": mean(y_error) if y_error else None,
        "mean_euclidean_error": mean(euclidean) if euclidean else None,
        "median_euclidean_error": _median_or_none(euclidean),
        "p95_euclidean_error": _p95_or_none(euclidean),
        "usable_predictions": len(usable),
        "unavailable_predictions": len(rows) - len(usable),
        "usable_fraction": len(usable) / len(rows) if rows else 0.0,
        "target_reentries": sum(item["target_reentries"] for item in trials),
        "dwell_interruptions": sum(item["dwell_interruptions"] for item in trials),
        "median_longest_dwell_seconds": _median_or_none(
            [item["longest_dwell_seconds"] for item in trials]
        ),
    }


def _repeated_targets(trials: list[dict]) -> dict:
    """Block-to-block variation in raw trial median predictions, same target."""
    by_target: dict[str, list[dict]] = {}
    for trial in trials:
        by_target.setdefault(trial["target_id"], []).append(trial)
    pairs = []
    for target_id, target_trials in by_target.items():
        available = [
            trial
            for trial in target_trials
            if trial["median_raw_predicted_x"] is not None
            and trial["median_raw_predicted_y"] is not None
        ]
        for index, left in enumerate(available):
            for right in available[index + 1 :]:
                dx = right["median_raw_predicted_x"] - left["median_raw_predicted_x"]
                dy = right["median_raw_predicted_y"] - left["median_raw_predicted_y"]
                pairs.append(
                    {
                        "target_id": target_id,
                        "blocks": [left["block"], right["block"]],
                        "absolute_x_difference": abs(dx),
                        "absolute_y_difference": abs(dy),
                        "euclidean_difference": hypot(dx, dy),
                    }
                )
    distances = [pair["euclidean_difference"] for pair in pairs]
    return {
        "pairs": pairs,
        "median_euclidean_difference": _median_or_none(distances),
        "p95_euclidean_difference": _p95_or_none(distances),
        "maximum_euclidean_difference": max(distances) if distances else None,
    }


def analyze_session(report: dict) -> dict:
    """Reject other protocols and summarize all 27 trials without success selection."""
    if report.get("participant") != "cagri" or report.get("session") not in (
        "live-1",
        "live-2",
        "live-3",
        "live-4",
        "live-5",
    ):
        raise ValueError("unexpected participant or session")
    if (report.get("protocol_name"), report.get("protocol_version")) != (
        PROTOCOL_NAME,
        PROTOCOL_VERSION,
    ):
        raise ValueError("incompatible targeting protocol")
    if report.get("order_seed") != ORDER_SEED:
        raise ValueError("unexpected trial order seed")
    if (
        report.get("ready_screen_used") is not True
        or report.get("second_ready_screen_used") is not True
        or report.get("calibration_settle_seconds") != 0.8
        or report.get("calibration_sample_seconds") != 1.2
    ):
        raise ValueError("incompatible capture flow")
    if (
        report.get("target_half_width") != TARGET_HALF_WIDTH
        or report.get("target_half_height") != TARGET_HALF_HEIGHT
        or report.get("dwell_seconds") != DWELL_SECONDS
        or report.get("trial_timeout_seconds") != TIMEOUT_SECONDS
    ):
        raise ValueError("incompatible acceptance/timing protocol")
    calibration = report.get("calibration_presentations", [])
    if [
        (row.get("target_id"), row.get("target_x"), row.get("target_y")) for row in calibration
    ] != [(target.name, target.x, target.y) for target in CALIBRATION_TARGETS]:
        raise ValueError("missing or reordered standard calibration")
    if any(row.get("usable_samples", 0) < 5 for row in calibration):
        raise ValueError("insufficient usable calibration samples")
    trials = report.get("trials", [])
    expected = schedule()
    if len(trials) != len(expected) or any(
        any(actual.get(key) != value for key, value in planned.identity().items())
        for actual, planned in zip(trials, expected)
    ):
        raise ValueError("missing, duplicate, or reordered targeting trials")
    rows = report.get("samples", [])
    if any(row.get("trial_order") not in range(1, 28) for row in rows):
        raise ValueError("sample references unknown trial")
    by_order = {trial["trial_order"]: [] for trial in trials}
    for row in rows:
        trial = trials[row["trial_order"] - 1]
        if any(
            row.get(key) != trial[key] for key in ("block", "target_id", "target_x", "target_y")
        ):
            raise ValueError("sample target identity does not match trial")
        by_order[row["trial_order"]].append(row)
    enriched = []
    for trial in trials:
        trial_rows = by_order[trial["trial_order"]]
        usable = [row for row in trial_rows if row["status"] == "usable"]
        if (
            len(usable) != trial["usable_prediction_count"]
            or len(trial_rows) - len(usable) != trial["unavailable_prediction_count"]
        ):
            raise ValueError("trial sample counts do not match")
        if trial["outcome"] not in ("success", "timeout"):
            raise ValueError("trial outcome missing")
        enriched.append(
            {
                **trial,
                "median_raw_predicted_x": _median_or_none(
                    [row["raw_predicted_x"] for row in usable]
                ),
                "median_raw_predicted_y": _median_or_none(
                    [row["raw_predicted_y"] for row in usable]
                ),
            }
        )
    by_row = {}
    by_column = {}
    by_target = {}
    for index, value in enumerate((0.2, 0.5, 0.8), start=1):
        by_row[f"row-{index}"] = _group(
            [trial for trial in enriched if trial["target_y"] == value],
            [row for row in rows if row["target_y"] == value],
        )
        by_column[f"column-{index}"] = _group(
            [trial for trial in enriched if trial["target_x"] == value],
            [row for row in rows if row["target_x"] == value],
        )
    for target in TARGETS:
        by_target[target.name] = _group(
            [trial for trial in enriched if trial["target_id"] == target.name],
            [row for row in rows if row["target_id"] == target.name],
        )
    return {
        "participant": report["participant"],
        "session": report["session"],
        "overall": _group(enriched, rows),
        "by_row": by_row,
        "by_column": by_column,
        "by_target": by_target,
        "repeated_targets": _repeated_targets(enriched),
        "failed_camera_reads_including_calibration": report[
            "failed_camera_reads_including_calibration"
        ],
        "no_face_observations_including_calibration": report[
            "no_face_observations_including_calibration"
        ],
    }


def acquisition_details(report: dict) -> dict:
    """Report early entry/acquisition on all trials without relabeling successes."""
    analyze_session(report)
    trials = report["trials"]
    first_rows = {}
    for row in report["samples"]:
        if row["status"] == "usable":
            first_rows.setdefault(row["trial_order"], row)
    already_inside = sum(
        trial["trial_order"] in first_rows
        and inside_target(
            first_rows[trial["trial_order"]]["raw_predicted_x"],
            first_rows[trial["trial_order"]]["raw_predicted_y"],
            Target(trial["target_id"], trial["target_x"], trial["target_y"]),
        )
        for trial in trials
    )
    successful = [trial for trial in trials if trial["outcome"] == "success"]
    first_entry = [
        trial["first_entry_seconds"] for trial in trials if trial["first_entry_seconds"] is not None
    ]
    successful_entry = [trial["successful_entry_seconds"] for trial in successful]
    confirmed = [trial["confirmed_acquisition_seconds"] for trial in successful]
    dwell_at_success = [
        trial["confirmed_acquisition_seconds"] - trial["successful_entry_seconds"]
        for trial in successful
    ]
    return {
        "trials": len(trials),
        "first_sample_inside": already_inside,
        "first_sample_inside_fraction": already_inside / len(trials),
        "first_entry": _distribution(first_entry),
        "successful_entry": _distribution(successful_entry),
        "confirmed_acquisition": _distribution(confirmed),
        "dwell_at_success": _distribution(dwell_at_success),
        "success_by_seconds": {
            "0.50": sum(value <= 0.5 for value in confirmed),
            "0.75": sum(value <= 0.75 for value in confirmed),
            "1.00": sum(value <= 1.0 for value in confirmed),
        },
    }


def _distribution(values: list[float]) -> dict:
    return {
        "count": len(values),
        "median": _median_or_none(values),
        "p95": _p95_or_none(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
    }


def analyze_primary(reports: list[dict]) -> dict:
    """Pool only the three predesignated natural-use sessions, retaining trials."""
    by_session = {report.get("session"): report for report in reports}
    if len(reports) != len(PRIMARY_SESSIONS) or set(by_session) != set(PRIMARY_SESSIONS):
        raise ValueError("primary pool requires exactly live-3, live-4, and live-5")
    per_session = {session: analyze_session(by_session[session]) for session in PRIMARY_SESSIONS}
    trials = [trial for session in PRIMARY_SESSIONS for trial in by_session[session]["trials"]]
    rows = [row for session in PRIMARY_SESSIONS for row in by_session[session]["samples"]]
    by_row = {}
    by_column = {}
    by_target = {}
    for index, value in enumerate((0.2, 0.5, 0.8), start=1):
        by_row[f"row-{index}"] = _group(
            [trial for trial in trials if trial["target_y"] == value],
            [row for row in rows if row["target_y"] == value],
        )
        by_column[f"column-{index}"] = _group(
            [trial for trial in trials if trial["target_x"] == value],
            [row for row in rows if row["target_x"] == value],
        )
    for target in TARGETS:
        by_target[target.name] = _group(
            [trial for trial in trials if trial["target_id"] == target.name],
            [row for row in rows if row["target_id"] == target.name],
        )
    repeat_pairs = [
        pair
        for session in PRIMARY_SESSIONS
        for pair in per_session[session]["repeated_targets"]["pairs"]
    ]
    repeat_distances = [pair["euclidean_difference"] for pair in repeat_pairs]
    early = {session: acquisition_details(by_session[session]) for session in PRIMARY_SESSIONS}
    first_entry = [
        trial["first_entry_seconds"] for trial in trials if trial["first_entry_seconds"] is not None
    ]
    successful = [trial for trial in trials if trial["outcome"] == "success"]
    successful_entry = [trial["successful_entry_seconds"] for trial in successful]
    confirmed = [trial["confirmed_acquisition_seconds"] for trial in successful]
    dwell_at_success = [
        trial["confirmed_acquisition_seconds"] - trial["successful_entry_seconds"]
        for trial in successful
    ]
    return {
        "sessions": list(PRIMARY_SESSIONS),
        "per_session": per_session,
        "overall": _group(trials, rows),
        "by_row": by_row,
        "by_column": by_column,
        "by_target": by_target,
        "repeated_targets": {
            "pairs_within_session": len(repeat_pairs),
            "median_euclidean_difference": _median_or_none(repeat_distances),
            "p95_euclidean_difference": _p95_or_none(repeat_distances),
            "maximum_euclidean_difference": max(repeat_distances) if repeat_distances else None,
        },
        "early_acquisition": {
            "per_session": early,
            "first_sample_inside": sum(item["first_sample_inside"] for item in early.values()),
            "first_sample_inside_fraction": sum(
                item["first_sample_inside"] for item in early.values()
            )
            / len(trials),
            "first_entry": _distribution(first_entry),
            "successful_entry": _distribution(successful_entry),
            "confirmed_acquisition": _distribution(confirmed),
            "dwell_at_success": _distribution(dwell_at_success),
            "success_by_seconds": {
                "0.50": sum(value <= 0.5 for value in confirmed),
                "0.75": sum(value <= 0.75 for value in confirmed),
                "1.00": sum(value <= 1.0 for value in confirmed),
            },
        },
        "failed_camera_reads": sum(
            by_session[session]["failed_camera_reads_including_calibration"]
            for session in PRIMARY_SESSIONS
        ),
        "no_face_observations": sum(
            by_session[session]["no_face_observations_including_calibration"]
            for session in PRIMARY_SESSIONS
        ),
    }
