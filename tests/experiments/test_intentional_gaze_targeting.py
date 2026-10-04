"""Deterministic checks for the fixed-cue intentional targeting protocol."""

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from experiments.coarse_gaze_targeting_validation.protocol import schedule as v1_schedule
from experiments.intentional_gaze_targeting.analysis import (
    CueFlow,
    DwellState,
    analyze_session,
    analyze_sessions,
    calibration_summary,
    early_stop_bound,
    failure_summary,
    summarize_target,
)
from experiments.intentional_gaze_targeting.protocol import (
    CUE_ASSIGNMENT,
    FIXATION_CUE_SECONDS,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    TARGET_DWELL_SECONDS,
    TARGET_HALF_HEIGHT,
    TARGET_HALF_WIDTH,
    TARGET_TIMEOUT_SECONDS,
    TARGETS,
    cue_for_target,
    inside_region,
    schedule,
    screen_content,
)
from experiments.intentional_gaze_targeting.run import draw_screen, parse_args
from validation.real_calibration import CALIBRATION_TARGETS, Target


def test_fixed_design_and_v1_target_order():
    plan = schedule()
    assert (PROTOCOL_NAME, PROTOCOL_VERSION) == ("intentional_gaze_targeting", 2)
    assert len(CALIBRATION_TARGETS) == len(TARGETS) == 9
    assert len(plan) == 27 and schedule() == plan
    assert [(item.block, item.target) for item in plan] == [
        (item.block, item.target) for item in v1_schedule()
    ]
    assert all(
        sum(item.target == target and item.block == block for item in plan) == 1
        for target in TARGETS
        for block in (1, 2, 3)
    )
    assert (
        TARGET_HALF_WIDTH,
        TARGET_HALF_HEIGHT,
        TARGET_DWELL_SECONDS,
        TARGET_TIMEOUT_SECONDS,
    ) == (
        0.10,
        0.10,
        1.0,
        5.0,
    )
    assert FIXATION_CUE_SECONDS == 0.75


def test_cue_assignment_is_deterministic_and_separate_from_target():
    assert cue_for_target(Target("top-left", 0.2, 0.2)) == (0.8, 0.8)
    assert cue_for_target(Target("top-right", 0.8, 0.2)) == pytest.approx((0.2, 0.8))
    assert cue_for_target(Target("center", 0.5, 0.5)) == (0.2, 0.2)
    assert cue_for_target(Target("left", 0.2, 0.5)) == (0.8, 0.5)
    for trial in schedule():
        assert (trial.cue_x, trial.cue_y) == cue_for_target(trial.target)
        assert not (
            abs(trial.cue_x - trial.target.x) <= TARGET_HALF_WIDTH
            and abs(trial.cue_y - trial.target.y) <= TARGET_HALF_HEIGHT
        )


def test_screen_phases_contain_only_the_relevant_marker():
    trial = schedule()[0]
    assert screen_content("calibration_ready").target is None
    assert screen_content("targeting_ready").target is None
    cue = screen_content("cue", trial)
    assert (cue.target.x, cue.target.y) == (trial.cue_x, trial.cue_y)
    assert cue.lines == () and not cue.show_cursor and not cue.show_region
    target = screen_content("target", trial)
    assert target.target == trial.target and target.lines == ()
    assert target.show_cursor and target.show_region
    with pytest.raises(ValueError):
        screen_content("reset_failed")


def test_rendering_shows_cue_then_target_and_cursor_without_text():
    class CV2:
        def __init__(self):
            self.circles = []
            self.rectangles = []
            self.text = []

        def circle(self, _, center, *args):
            self.circles.append(center)

        def rectangle(self, _, top_left, bottom_right, *args):
            self.rectangles.append((top_left, bottom_right))

        def putText(self, _, line, *args):
            self.text.append(line)

    trial = schedule()[0]
    cv2 = CV2()
    draw_screen(
        cv2,
        np,
        screen_content("cue", trial),
        1000,
        1000,
        SimpleNamespace(x=trial.target.x, y=trial.target.y),
    )
    assert cv2.circles == [(round(trial.cue_x * 1000), round(trial.cue_y * 1000))] * 2
    assert cv2.rectangles == [] and cv2.text == []
    cv2 = CV2()
    draw_screen(
        cv2,
        np,
        screen_content("target", trial),
        1000,
        1000,
        SimpleNamespace(x=trial.target.x, y=trial.target.y),
    )
    assert len(cv2.rectangles) == 2 and len(cv2.circles) == 4 and cv2.text == []


def test_cli_restricts_sessions_and_ignored_local_output():
    args = parse_args(
        [
            "--participant",
            "cagri",
            "--session",
            "live-3",
            "--camera-index",
            "1",
            "--output",
            ".venv/intentional-gaze-cagri-live-3.json",
        ]
    )
    assert args.session == "live-3" and args.camera_index == 1
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--participant",
                "cagri",
                "--session",
                "live-4",
                "--camera-index",
                "1",
                "--output",
                ".venv/intentional-gaze-cagri-live-4.json",
            ]
        )


def test_raw_region_boundary_is_inclusive_without_clipping():
    assert inside_region(0.3, 0.1, 0.2, 0.2, 0.1, 0.1)
    assert not inside_region(0.301, 0.2, 0.2, 0.2, 0.1, 0.1)
    assert not inside_region(1.3, 0.2, 0.2, 0.2, 0.1, 0.1)


def test_cue_is_timed_only_and_target_always_starts_without_gaze_input():
    trial = schedule()[0]
    flow = CueFlow(trial, cue_onset=2.0)
    with pytest.raises(ValueError):
        flow.begin_target(2.749)
    target = flow.begin_target(2.75)
    assert target.onset == 2.75
    with pytest.raises(ValueError):
        flow.begin_target(3.0)
    target.observe(2.85, (trial.target.x, trial.target.y))
    target.observe(3.85, (trial.target.x, trial.target.y))
    assert target.timing()["confirmed_acquisition_seconds"] == pytest.approx(1.10)


def test_target_dwell_resets_on_outside_or_unavailable_prediction():
    state = DwellState(0, 0.5, 0.5, 0.1, 0.1, 1.0, 5.0)
    state.observe(0.1, (0.5, 0.5))
    state.observe(0.5, (0.8, 0.8))
    state.observe(0.6, (0.5, 0.5))
    state.observe(0.8, None)
    state.observe(0.9, (0.5, 0.5))
    state.observe(1.89, (0.5, 0.5))
    assert state.outcome is None
    state.observe(1.9, (0.5, 0.5))
    assert state.outcome == "success"
    assert state.entries == 3 and state.interruptions == 2


def test_target_timeout_boundary_and_raw_error_summary():
    trial = schedule()[0]
    state = DwellState(0, trial.target.x, trial.target.y, 0.1, 0.1, 1, 5)
    state.observe(0.1, (2.0, -1.0))
    state.observe(0.2, None)
    state.expire(4.999)
    assert state.outcome is None
    state.expire(5.0)
    rows = [
        {"status": "usable", "raw_predicted_x": 2.0, "raw_predicted_y": -1.0},
        {"status": "unavailable", "raw_predicted_x": None, "raw_predicted_y": None},
    ]
    summary = summarize_target(trial, state, rows)
    assert summary["outcome"] == "timeout" and summary["availability_fraction"] == 0.5
    assert summary["median_absolute_x_error"] == pytest.approx(abs(2 - trial.target.x))
    assert summary["final_prediction"] == [2.0, -1.0]


def _report():
    trials, target_samples = [], []
    for item in schedule():
        state = DwellState(0.75, item.target.x, item.target.y, 0.1, 0.1, 1, 5)
        state.observe(0.85, (item.target.x, item.target.y))
        state.observe(1.85, (item.target.x, item.target.y))
        rows = [
            {
                **item.identity(),
                "status": "usable",
                "raw_predicted_x": item.target.x,
                "raw_predicted_y": item.target.y,
                "inside_target": True,
                "monotonic_seconds": timestamp,
                "active_dwell_seconds": timestamp - 0.85,
            }
            for timestamp in (0.85, 1.85)
        ]
        target_samples.extend(rows)
        trials.append(
            {
                **item.identity(),
                "cue_onset_monotonic_seconds": 0.0,
                "cue_end_monotonic_seconds": 0.75,
                "target_onset_monotonic_seconds": 0.75,
                "target_end_monotonic_seconds": 1.85,
                "target_summary": summarize_target(item, state, rows),
            }
        )
    return {
        "participant": "cagri",
        "session": "live-1",
        "protocol_name": PROTOCOL_NAME,
        "protocol_version": PROTOCOL_VERSION,
        "order_seed": 20261006,
        "target_half_width": 0.1,
        "target_half_height": 0.1,
        "target_dwell_seconds": 1.0,
        "target_timeout_seconds": 5.0,
        "fixation_cue_seconds": 0.75,
        "cue_assignment": CUE_ASSIGNMENT,
        "calibration_presentations": [
            {
                "target_id": x.name,
                "target_x": x.x,
                "target_y": x.y,
                "usable_samples": 5,
                "median_horizontal_feature": x.x,
                "median_vertical_feature": x.y,
            }
            for x in CALIBRATION_TARGETS
        ],
        "mapping_coefficients": {
            "x_slope": 1.0,
            "x_intercept": 0.0,
            "y_slope": 1.0,
            "y_intercept": 0.0,
        },
        "trials": trials,
        "target_samples": target_samples,
        "failed_camera_reads_including_calibration": 0,
        "no_face_observations_including_calibration": 0,
    }


def _make_timeout(report, index=0):
    trial = report["trials"][index]
    state = DwellState(0.75, trial["target_x"], trial["target_y"], 0.1, 0.1, 1, 5)
    rows = [row for row in report["target_samples"] if row["trial_order"] == trial["trial_order"]]
    for row in rows:
        row["raw_predicted_y"] = trial["target_y"] + 0.2
        row["inside_target"] = False
        row["active_dwell_seconds"] = 0.0
        state.observe(row["monotonic_seconds"], (row["raw_predicted_x"], row["raw_predicted_y"]))
    state.expire(5.75)
    trial["target_end_monotonic_seconds"] = 5.75
    planned = schedule()[index]
    trial["target_summary"] = summarize_target(planned, state, rows)


def test_analysis_requires_every_target_even_if_cue_gaze_unavailable():
    report = _report()
    _make_timeout(report)
    result = analyze_session(report)
    assert result["target"]["attempted_trials"] == 27
    assert result["target"]["successful_trials"] == 26
    assert result["target"]["timeout_trials"] == 1
    assert "reset" not in result and "overall_completion_rate" not in result


def test_old_reset_pilot_and_incompatible_metadata_are_rejected():
    report = _report()
    report["protocol_version"] = 1
    with pytest.raises(ValueError, match="protocol"):
        analyze_session(report)
    report = _report()
    del report["fixation_cue_seconds"]
    report["reset_dwell_seconds"] = 0.5
    with pytest.raises(ValueError, match="parameters"):
        analyze_session(report)
    report = _report()
    report["target_timeout_seconds"] = 4.0
    with pytest.raises(ValueError, match="parameters"):
        analyze_session(report)
    report = _report()
    report["reset_samples"] = []
    with pytest.raises(ValueError, match="pilot"):
        analyze_session(report)


def test_analysis_rejects_missing_cells_and_short_cue():
    report = _report()
    report["trials"][1] = deepcopy(report["trials"][0])
    with pytest.raises(ValueError):
        analyze_session(report)
    report = _report()
    report["trials"][0]["target_onset_monotonic_seconds"] = 0.5
    with pytest.raises(ValueError, match="cue"):
        analyze_session(report)
    report = _report()
    report["trials"][0]["target_summary"] = None
    with pytest.raises(ValueError, match="target attempt"):
        analyze_session(report)
    report = _report()
    report["target_samples"][0]["raw_predicted_y"] += 0.4
    with pytest.raises(ValueError, match="replay"):
        analyze_session(report)


def test_analysis_position_latency_availability_and_repeatability():
    result = analyze_session(_report())
    assert result["target"]["successful_trials"] == 27
    assert result["target"]["median_first_entry_seconds"] == pytest.approx(0.1)
    assert result["target"]["median_confirmed_acquisition_seconds"] == pytest.approx(1.1)
    assert result["target"]["x_mae"] == 0 and result["target"]["usable_fraction"] == 1
    assert result["by_row"]["row-1"]["successful_trials"] == 9
    assert result["by_column"]["column-2"]["successful_trials"] == 9
    assert result["by_target"]["T-3-3"]["successful_trials"] == 3
    assert result["repeated_targets"]["median_euclidean_difference"] == 0


def test_pooled_metrics_keep_sessions_distinct_and_group_targets():
    first, second = _report(), _report()
    second["session"] = "live-2"
    _make_timeout(second)
    pooled = analyze_sessions([first, second])
    assert pooled["pooled"]["attempted_trials"] == 54
    assert pooled["pooled"]["successful_trials"] == 53
    assert pooled["by_row"]["row-1"]["planned_trials"] == 18
    assert pooled["by_target"][first["trials"][0]["target_id"]]["planned_trials"] == 6
    assert pooled["pooled_failures"]["timeouts"] == 1
    with pytest.raises(ValueError, match="distinct"):
        analyze_sessions([first, deepcopy(first)])


def test_early_stop_bound_is_exact_and_threshold_is_not_softened():
    result = early_stop_bound(20, 54, 27)
    assert result["maximum_successes"] == 47
    assert result["final_trials"] == 81
    assert result["maximum_rate"] == pytest.approx(47 / 81)
    assert result["below_60_percent_locked"] is True
    assert early_stop_bound(22, 54, 27)["below_60_percent_locked"] is False
    with pytest.raises(ValueError):
        early_stop_bound(55, 54, 27)


def test_timeout_entry_and_dwell_thresholds_are_reported_without_exclusion():
    report = _report()
    entered, missed = report["trials"][:2]
    entered["target_summary"].update(
        outcome="timeout", target_entries=1, dwell_interruptions=1, longest_dwell_seconds=0.8
    )
    missed["target_summary"].update(
        outcome="timeout", target_entries=0, dwell_interruptions=0, longest_dwell_seconds=0.0
    )
    rows = report["target_samples"]
    for row in rows:
        if row["trial_order"] == missed["trial_order"]:
            row["raw_predicted_y"] = missed["target_y"] + 0.2
            row["inside_target"] = False
    summary = failure_summary(report)
    assert (summary["timeouts"], summary["entered_target"], summary["never_entered_target"]) == (
        2,
        1,
        1,
    )
    assert summary["with_dwell_interruptions"] == 1
    assert summary["longest_dwell_at_least_0_50"] == 1
    assert summary["longest_dwell_at_least_0_75"] == 1
    assert summary["longest_dwell_at_least_0_90"] == 0
    assert summary["median_prediction_outside_y"] == 1


def test_calibration_residuals_use_saved_mapping_and_presentation_medians():
    report = _report()
    assert calibration_summary(report)["x_mae"] == 0
    assert calibration_summary(report)["y_mae"] == 0
    report["mapping_coefficients"]["y_intercept"] = 0.2
    result = calibration_summary(report)
    assert result["y_mae"] == pytest.approx(0.2)
    assert result["vertical_feature_span"] == pytest.approx(0.6)
