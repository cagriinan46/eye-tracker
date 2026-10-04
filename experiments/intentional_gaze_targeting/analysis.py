"""Target-only dwell and offline summaries for intentional targeting v2."""

from dataclasses import dataclass, field
from math import hypot, isclose
from statistics import mean, median

from experiments.intentional_gaze_targeting.protocol import (
    CUE_ASSIGNMENT,
    FIXATION_CUE_SECONDS,
    ORDER_SEED,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGET_DWELL_SECONDS,
    TARGET_HALF_HEIGHT,
    TARGET_HALF_WIDTH,
    TARGET_TIMEOUT_SECONDS,
    TARGETS,
    Trial,
    inside_region,
    schedule,
)
from validation.real_calibration import CALIBRATION_TARGETS, percentile


def _median(values: list[float]) -> float | None:
    return median(values) if values else None


def _p95(values: list[float]) -> float | None:
    return percentile(values, 95) if values else None


@dataclass(slots=True)
class DwellState:
    """Target acquisition based only on observed raw predictions."""

    onset: float
    center_x: float
    center_y: float
    half_width: float
    half_height: float
    dwell_seconds: float
    timeout_seconds: float
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
        if timestamp < self.onset or (self.last_time is not None and timestamp < self.last_time):
            raise ValueError("nonmonotonic sample timestamp")
        if self.outcome is not None:
            raise ValueError("acquisition phase already ended")
        self.last_time = timestamp
        if timestamp > self.onset + self.timeout_seconds:
            self.outcome = "timeout"
            return False, 0.0
        inside = prediction is not None and inside_region(
            *prediction, self.center_x, self.center_y, self.half_width, self.half_height
        )
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
        if dwell >= self.dwell_seconds - 1e-9:
            self.outcome = "success"
            self.successful_entry_time = self.active_since
            self.acquired_time = timestamp
        return True, dwell

    def expire(self, timestamp: float) -> None:
        if timestamp < self.onset:
            raise ValueError("timeout precedes target onset")
        if self.outcome is None and timestamp >= self.onset + self.timeout_seconds:
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


@dataclass(slots=True)
class CueFlow:
    """Time the fixation cue; always allow the target after the fixed interval."""

    trial: Trial
    cue_onset: float
    target: DwellState | None = field(default=None, init=False)

    def begin_target(self, onset: float) -> DwellState:
        if self.target is not None or onset < self.cue_onset + FIXATION_CUE_SECONDS - 1e-9:
            raise ValueError("target must start once, after the full fixation cue")
        self.target = DwellState(
            onset,
            self.trial.target.x,
            self.trial.target.y,
            TARGET_HALF_WIDTH,
            TARGET_HALF_HEIGHT,
            TARGET_DWELL_SECONDS,
            TARGET_TIMEOUT_SECONDS,
        )
        return self.target


def _sample_counts(rows: list[dict]) -> dict:
    usable = sum(row["status"] == "usable" for row in rows)
    return {
        "usable_prediction_count": usable,
        "unavailable_prediction_count": len(rows) - usable,
        "availability_fraction": usable / len(rows) if rows else 0.0,
    }


def summarize_target(trial: Trial, state: DwellState, rows: list[dict]) -> dict:
    if state.outcome not in ("success", "timeout"):
        raise ValueError("target phase did not finish")
    usable = [row for row in rows if row["status"] == "usable"]
    x_error = [abs(row["raw_predicted_x"] - trial.target.x) for row in usable]
    y_error = [abs(row["raw_predicted_y"] - trial.target.y) for row in usable]
    distance = [hypot(dx, dy) for dx, dy in zip(x_error, y_error)]
    return {
        **state.timing(),
        **_sample_counts(rows),
        "median_absolute_x_error": _median(x_error),
        "median_absolute_y_error": _median(y_error),
        "median_euclidean_error": _median(distance),
        "p95_euclidean_error": _p95(distance),
        "final_prediction": [usable[-1]["raw_predicted_x"], usable[-1]["raw_predicted_y"]]
        if usable
        else None,
    }


def _target_group(trials: list[dict], rows: list[dict]) -> dict:
    started = [trial["target_summary"] for trial in trials]
    successes = [item for item in started if item["outcome"] == "success"]
    usable = [row for row in rows if row["status"] == "usable"]
    x_error = [abs(row["raw_predicted_x"] - row["target_x"]) for row in usable]
    y_error = [abs(row["raw_predicted_y"] - row["target_y"]) for row in usable]
    distance = [hypot(dx, dy) for dx, dy in zip(x_error, y_error)]
    first_entry = [
        item["first_entry_seconds"] for item in started if item["first_entry_seconds"] is not None
    ]
    entry = [item["successful_entry_seconds"] for item in successes]
    confirmed = [item["confirmed_acquisition_seconds"] for item in successes]
    return {
        "planned_trials": len(trials),
        "attempted_trials": len(trials),
        "successful_trials": len(successes),
        "timeout_trials": len(started) - len(successes),
        "success_rate": len(successes) / len(started) if started else None,
        "timeout_rate": 1 - len(successes) / len(started) if started else None,
        "median_first_entry_seconds": _median(first_entry),
        "p95_first_entry_seconds": _p95(first_entry),
        "median_successful_entry_seconds": _median(entry),
        "p95_successful_entry_seconds": _p95(entry),
        "median_confirmed_acquisition_seconds": _median(confirmed),
        "p95_confirmed_acquisition_seconds": _p95(confirmed),
        "x_mae": mean(x_error) if x_error else None,
        "y_mae": mean(y_error) if y_error else None,
        "mean_euclidean_error": mean(distance) if distance else None,
        "median_euclidean_error": _median(distance),
        "p95_euclidean_error": _p95(distance),
        "usable_predictions": len(usable),
        "unavailable_predictions": len(rows) - len(usable),
        "usable_fraction": len(usable) / len(rows) if rows else 0.0,
        "target_reentries": sum(item["target_reentries"] for item in started),
        "dwell_interruptions": sum(item["dwell_interruptions"] for item in started),
        "median_longest_dwell_seconds": _median(
            [item["longest_dwell_seconds"] for item in started]
        ),
    }


def _repeated_targets(trials: list[dict], rows: list[dict]) -> dict:
    medians = {}
    for trial in trials:
        values = [
            row
            for row in rows
            if row["trial_order"] == trial["trial_order"] and row["status"] == "usable"
        ]
        if values:
            medians[trial["trial_order"]] = (
                median(row["raw_predicted_x"] for row in values),
                median(row["raw_predicted_y"] for row in values),
            )
    differences = []
    for target in TARGETS:
        target_trials = [
            trial
            for trial in trials
            if trial["target_id"] == target.name and trial["trial_order"] in medians
        ]
        for index, left in enumerate(target_trials):
            for right in target_trials[index + 1 :]:
                a, b = medians[left["trial_order"]], medians[right["trial_order"]]
                differences.append(hypot(b[0] - a[0], b[1] - a[1]))
    return {
        "pairs": len(differences),
        "median_euclidean_difference": _median(differences),
        "p95_euclidean_difference": _p95(differences),
        "maximum_euclidean_difference": max(differences) if differences else None,
    }


def _verify_trial_replay(trial: dict, rows: list[dict]) -> None:
    """Check logged acquisition outcomes against raw timestamped predictions."""
    onset = trial["target_onset_monotonic_seconds"]
    state = DwellState(
        onset,
        trial["target_x"],
        trial["target_y"],
        TARGET_HALF_WIDTH,
        TARGET_HALF_HEIGHT,
        TARGET_DWELL_SECONDS,
        TARGET_TIMEOUT_SECONDS,
    )
    for row in rows:
        if row.get("status") not in ("usable", "unavailable"):
            raise ValueError("invalid sample status")
        prediction = (
            (row["raw_predicted_x"], row["raw_predicted_y"]) if row["status"] == "usable" else None
        )
        inside, dwell = state.observe(row["monotonic_seconds"], prediction)
        if row.get("inside_target") != inside or not isclose(
            row.get("active_dwell_seconds", float("nan")), dwell, abs_tol=1e-8
        ):
            raise ValueError("sample dwell disagrees with raw prediction replay")
    end = trial["target_end_monotonic_seconds"]
    if end < onset or (rows and end < rows[-1]["monotonic_seconds"]):
        raise ValueError("target end precedes an observation")
    state.expire(end)
    for key, expected in state.timing().items():
        actual = trial["target_summary"].get(key)
        if isinstance(expected, float):
            if not isinstance(actual, (int, float)) or not isclose(actual, expected, abs_tol=1e-8):
                raise ValueError(f"saved target {key} disagrees with raw replay")
        elif actual != expected:
            raise ValueError(f"saved target {key} disagrees with raw replay")


def failure_summary(report: dict) -> dict:
    """Describe overlapping spatial and dwell evidence in target timeouts."""
    failed = [
        trial for trial in report["trials"] if trial["target_summary"]["outcome"] == "timeout"
    ]
    entered = [trial for trial in failed if trial["target_summary"]["target_entries"] > 0]
    longest = [trial["target_summary"]["longest_dwell_seconds"] for trial in failed]
    median_outside_x = median_outside_y = both = 0
    late_outside_x = late_outside_y = late_trials = 0
    inside_samples = usable_samples = 0
    for trial in failed:
        rows = [
            row
            for row in report["target_samples"]
            if row["trial_order"] == trial["trial_order"] and row["status"] == "usable"
        ]
        usable_samples += len(rows)
        inside_samples += sum(row["inside_target"] for row in rows)
        if not rows:
            continue
        dx = median(row["raw_predicted_x"] for row in rows) - trial["target_x"]
        dy = median(row["raw_predicted_y"] for row in rows) - trial["target_y"]
        outside_x = abs(dx) > TARGET_HALF_WIDTH
        outside_y = abs(dy) > TARGET_HALF_HEIGHT
        median_outside_x += outside_x
        median_outside_y += outside_y
        both += outside_x and outside_y
        # Secondary diagnostic: exclude the initial three seconds of gaze travel.
        late = [
            row
            for row in rows
            if row["monotonic_seconds"] >= trial["target_onset_monotonic_seconds"] + 3.0
        ]
        if late:
            late_trials += 1
            late_dx = median(row["raw_predicted_x"] for row in late) - trial["target_x"]
            late_dy = median(row["raw_predicted_y"] for row in late) - trial["target_y"]
            late_outside_x += abs(late_dx) > TARGET_HALF_WIDTH
            late_outside_y += abs(late_dy) > TARGET_HALF_HEIGHT
    return {
        "timeouts": len(failed),
        "entered_target": len(entered),
        "never_entered_target": len(failed) - len(entered),
        "with_dwell_interruptions": sum(
            trial["target_summary"]["dwell_interruptions"] > 0 for trial in failed
        ),
        "longest_dwell_median_seconds": _median(longest),
        "longest_dwell_p95_seconds": _p95(longest),
        "longest_dwell_at_least_0_50": sum(value >= 0.50 for value in longest),
        "longest_dwell_at_least_0_75": sum(value >= 0.75 for value in longest),
        "longest_dwell_at_least_0_90": sum(value >= 0.90 for value in longest),
        "longest_dwell_at_least_0_95": sum(value >= 0.95 for value in longest),
        "median_prediction_outside_x": median_outside_x,
        "median_prediction_outside_y": median_outside_y,
        "median_prediction_outside_both": both,
        "late_window_start_seconds": 3.0,
        "late_window_trials": late_trials,
        "late_median_prediction_outside_x": late_outside_x,
        "late_median_prediction_outside_y": late_outside_y,
        "usable_samples": usable_samples,
        "inside_samples": inside_samples,
        "inside_sample_fraction": inside_samples / usable_samples if usable_samples else None,
    }


def pooled_failure_summary(reports: list[dict]) -> dict:
    """Pool timeout counts while recomputing dwell quantiles from all trials."""
    summaries = [failure_summary(report) for report in reports]
    longest = [
        trial["target_summary"]["longest_dwell_seconds"]
        for report in reports
        for trial in report["trials"]
        if trial["target_summary"]["outcome"] == "timeout"
    ]
    count_keys = (
        "timeouts",
        "entered_target",
        "never_entered_target",
        "with_dwell_interruptions",
        "longest_dwell_at_least_0_50",
        "longest_dwell_at_least_0_75",
        "longest_dwell_at_least_0_90",
        "longest_dwell_at_least_0_95",
        "median_prediction_outside_x",
        "median_prediction_outside_y",
        "median_prediction_outside_both",
        "late_window_trials",
        "late_median_prediction_outside_x",
        "late_median_prediction_outside_y",
        "usable_samples",
        "inside_samples",
    )
    pooled = {key: sum(summary[key] for summary in summaries) for key in count_keys}
    pooled["longest_dwell_median_seconds"] = _median(longest)
    pooled["late_window_start_seconds"] = 3.0
    pooled["longest_dwell_p95_seconds"] = _p95(longest)
    pooled["inside_sample_fraction"] = (
        pooled["inside_samples"] / pooled["usable_samples"] if pooled["usable_samples"] else None
    )
    return pooled


def calibration_summary(report: dict) -> dict:
    """Reconstruct calibration-median fit residuals from saved coefficients."""
    mapping = report["mapping_coefficients"]
    details = []
    for item in report["calibration_presentations"]:
        x = mapping["x_slope"] * item["median_horizontal_feature"] + mapping["x_intercept"]
        y = mapping["y_slope"] * item["median_vertical_feature"] + mapping["y_intercept"]
        details.append(
            {
                "target_id": item["target_id"],
                "predicted_x": x,
                "predicted_y": y,
                "x_error": x - item["target_x"],
                "y_error": y - item["target_y"],
            }
        )
    horizontal = [item["median_horizontal_feature"] for item in report["calibration_presentations"]]
    vertical = [item["median_vertical_feature"] for item in report["calibration_presentations"]]
    return {
        "mapping_coefficients": mapping,
        "horizontal_feature_span": max(horizontal) - min(horizontal),
        "vertical_feature_span": max(vertical) - min(vertical),
        "x_mae": mean(abs(item["x_error"]) for item in details),
        "y_mae": mean(abs(item["y_error"]) for item in details),
        "targets": details,
    }


def early_stop_bound(successes: int, completed_trials: int, remaining_trials: int) -> dict:
    """Maximum final success if every remaining planned trial succeeds."""
    if not (
        0 <= successes <= completed_trials
        and remaining_trials >= 0
        and completed_trials + remaining_trials > 0
    ):
        raise ValueError("invalid early-stop counts")
    maximum_successes = successes + remaining_trials
    final_trials = completed_trials + remaining_trials
    return {
        "maximum_successes": maximum_successes,
        "final_trials": final_trials,
        "maximum_rate": maximum_successes / final_trials,
        "below_60_percent_locked": maximum_successes / final_trials < 0.60,
    }


def analyze_sessions(reports: list[dict]) -> dict:
    """Pool only separately validated cue-based sessions; retain per-session results."""
    if not reports or len({report.get("session") for report in reports}) != len(reports):
        raise ValueError("provide distinct valid sessions")
    sessions = {report["session"]: analyze_session(report) for report in reports}
    trials = [trial for report in reports for trial in report["trials"]]
    rows = [row for report in reports for row in report["target_samples"]]
    by_row, by_column, by_target = {}, {}, {}
    for index, value in enumerate((0.2, 0.5, 0.8), start=1):
        by_row[f"row-{index}"] = _target_group(
            [trial for trial in trials if trial["target_y"] == value],
            [row for row in rows if row["target_y"] == value],
        )
        by_column[f"column-{index}"] = _target_group(
            [trial for trial in trials if trial["target_x"] == value],
            [row for row in rows if row["target_x"] == value],
        )
    for target in TARGETS:
        by_target[target.name] = _target_group(
            [trial for trial in trials if trial["target_id"] == target.name],
            [row for row in rows if row["target_id"] == target.name],
        )
    return {
        "sessions": sessions,
        "pooled": _target_group(trials, rows),
        "by_row": by_row,
        "by_column": by_column,
        "by_target": by_target,
        "failures_by_session": {report["session"]: failure_summary(report) for report in reports},
        "pooled_failures": pooled_failure_summary(reports),
        "calibration_by_session": {
            report["session"]: calibration_summary(report) for report in reports
        },
        "failed_camera_reads": sum(
            report["failed_camera_reads_including_calibration"] for report in reports
        ),
        "no_face_observations": sum(
            report["no_face_observations_including_calibration"] for report in reports
        ),
    }


def analyze_session(report: dict) -> dict:
    """Validate cue-based protocol and summarize every planned target trial."""
    if (report.get("protocol_name"), report.get("protocol_version")) != (
        PROTOCOL_NAME,
        PROTOCOL_VERSION,
    ):
        raise ValueError("incompatible protocol identity")
    if report.get("participant") != "cagri" or report.get("session") not in (
        "live-1",
        "live-2",
        "live-3",
    ):
        raise ValueError("unexpected participant or session")
    expected_meta = {
        "order_seed": ORDER_SEED,
        "target_half_width": TARGET_HALF_WIDTH,
        "target_half_height": TARGET_HALF_HEIGHT,
        "target_dwell_seconds": TARGET_DWELL_SECONDS,
        "target_timeout_seconds": TARGET_TIMEOUT_SECONDS,
        "fixation_cue_seconds": FIXATION_CUE_SECONDS,
        "cue_assignment": CUE_ASSIGNMENT,
    }
    if any(report.get(key) != value for key, value in expected_meta.items()):
        raise ValueError("incompatible protocol parameters")
    if any(
        key in report for key in ("reset_samples", "reset_dwell_seconds", "reset_timeout_seconds")
    ):
        raise ValueError("reset-gated pilot is incompatible with the fixation-cue protocol")
    calibration = report.get("calibration_presentations", [])
    if [
        (item.get("target_id"), item.get("target_x"), item.get("target_y")) for item in calibration
    ] != [(target.name, target.x, target.y) for target in CALIBRATION_TARGETS] or any(
        item.get("usable_samples", 0) < 5 for item in calibration
    ):
        raise ValueError("invalid standard calibration")
    trials, expected = report.get("trials", []), schedule()
    if len(trials) != 27 or any(
        any(actual.get(key) != value for key, value in planned.identity().items())
        for actual, planned in zip(trials, expected)
    ):
        raise ValueError("missing or reordered trials")
    target_rows = report.get("target_samples", [])
    for row in target_rows:
        order = row.get("trial_order")
        if not isinstance(order, int) or not 1 <= order <= 27:
            raise ValueError("sample references unknown trial")
        trial = trials[order - 1]
        if any(
            row.get(key) != trial[key]
            for key in ("block", "target_id", "target_x", "target_y", "cue_x", "cue_y")
        ):
            raise ValueError("sample identity disagrees with trial")
    for trial in trials:
        if "reset_summary" in trial:
            raise ValueError("reset-gated pilot trial is incompatible")
        target_trial_rows = [
            row for row in target_rows if row["trial_order"] == trial["trial_order"]
        ]
        target = trial.get("target_summary")
        if (
            target is None
            or target.get("outcome") not in ("success", "timeout")
            or (
                target.get("usable_prediction_count")
                != sum(row["status"] == "usable" for row in target_trial_rows)
                or target.get("unavailable_prediction_count")
                != sum(row["status"] == "unavailable" for row in target_trial_rows)
            )
        ):
            raise ValueError("missing target attempt or invalid summary")
        cue_onset = trial.get("cue_onset_monotonic_seconds")
        cue_end = trial.get("cue_end_monotonic_seconds")
        target_onset = trial.get("target_onset_monotonic_seconds")
        if (
            cue_onset is None
            or cue_end is None
            or target_onset is None
            or cue_end < cue_onset + FIXATION_CUE_SECONDS - 1e-9
            or target_onset < cue_end
        ):
            raise ValueError("target began before full fixation cue")
        _verify_trial_replay(trial, target_trial_rows)
    by_row, by_column, by_target = {}, {}, {}
    for index, value in enumerate((0.2, 0.5, 0.8), start=1):
        by_row[f"row-{index}"] = _target_group(
            [trial for trial in trials if trial["target_y"] == value],
            [row for row in target_rows if row["target_y"] == value],
        )
        by_column[f"column-{index}"] = _target_group(
            [trial for trial in trials if trial["target_x"] == value],
            [row for row in target_rows if row["target_x"] == value],
        )
    for target in TARGETS:
        by_target[target.name] = _target_group(
            [trial for trial in trials if trial["target_id"] == target.name],
            [row for row in target_rows if row["target_id"] == target.name],
        )
    return {
        "participant": report["participant"],
        "session": report["session"],
        "target": _target_group(trials, target_rows),
        "by_row": by_row,
        "by_column": by_column,
        "by_target": by_target,
        "repeated_targets": _repeated_targets(trials, target_rows),
        "failed_camera_reads": report["failed_camera_reads_including_calibration"],
        "no_face_observations": report["no_face_observations_including_calibration"],
    }
