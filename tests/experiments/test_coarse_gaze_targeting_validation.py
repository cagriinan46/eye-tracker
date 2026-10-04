"""Deterministic protocol and analysis checks for coarse gaze targeting."""

from copy import deepcopy

import pytest

from experiments.coarse_gaze_targeting_validation.analysis import (
    DwellState,
    acquisition_details,
    analyze_primary,
    analyze_session,
    summarize_trial,
)
from experiments.coarse_gaze_targeting_validation.protocol import (
    DWELL_SECONDS,
    ORDER_SEED,
    TARGET_HALF_HEIGHT,
    TARGET_HALF_WIDTH,
    TARGETS,
    TIMEOUT_SECONDS,
    cursor_pixel,
    inside_target,
    schedule,
    screen_content,
)
from experiments.coarse_gaze_targeting_validation.run import parse_args
from validation.real_calibration import CALIBRATION_TARGETS


def test_design_and_balanced_deterministic_order():
    plan = schedule()
    assert schedule() == plan
    assert ORDER_SEED == 20261006
    assert len(CALIBRATION_TARGETS) == len(TARGETS) == 9
    assert len(plan) == 27
    assert {trial.block for trial in plan} == {1, 2, 3}
    assert {trial.target.name for trial in plan} == {target.name for target in TARGETS}
    assert all(sum(trial.target == target for trial in plan) == 3 for target in TARGETS)
    assert all(
        sum(trial.target == target and trial.block == block for trial in plan) == 1
        for target in TARGETS
        for block in (1, 2, 3)
    )
    assert [trial.target.x for trial in plan[:9]] != [target.x for target in TARGETS]
    assert (TARGET_HALF_WIDTH, TARGET_HALF_HEIGHT, DWELL_SECONDS, TIMEOUT_SECONDS) == (
        0.14,
        0.14,
        0.3,
        4.0,
    )


def test_ready_and_target_display_are_separate():
    assert screen_content("calibration_ready").target is None
    assert screen_content("targeting_ready").target is None
    assert "SPACE" in screen_content("targeting_ready").lines[0]
    content = screen_content("trial", TARGETS[0])
    assert content.target == TARGETS[0]
    assert content.lines == ()
    assert screen_content("success").target is None


def test_raw_acceptance_inclusive_and_render_omits_only_marker():
    target = TARGETS[0]
    assert inside_target(target.x + 0.14, target.y - 0.14, target)
    assert not inside_target(target.x + 0.141, target.y, target)
    assert cursor_pixel(-0.1, 0.2, 1000, 1000) is None
    assert cursor_pixel(0.8, 1.01, 1000, 1000) is None
    assert cursor_pixel(0.8, 0.7, 1000, 1000) == (800, 700)


def test_continuous_dwell_success_boundary_and_latency():
    target = TARGETS[0]
    state = DwellState(10.0, target)
    assert state.observe(10.1, (0.2, 0.2)) == (True, 0.0)
    assert state.observe(10.399, (0.2, 0.2))[1] == pytest.approx(0.299)
    assert state.outcome is None
    state.observe(10.4, (0.2, 0.2))
    assert state.outcome == "success"
    timing = state.timing()
    assert timing["first_entry_seconds"] == pytest.approx(0.1)
    assert timing["successful_entry_seconds"] == pytest.approx(0.1)
    assert timing["confirmed_acquisition_seconds"] == pytest.approx(0.4)
    with pytest.raises(ValueError, match="ended"):
        state.observe(10.5, None)


def test_dwell_resets_on_leave_or_unavailable_and_reentry_counts():
    state = DwellState(0, TARGETS[0])
    for timestamp, prediction in (
        (0, (0.2, 0.2)),
        (0.2, None),
        (0.3, (0.2, 0.2)),
        (0.4, (0.9, 0.9)),
        (0.5, (0.2, 0.2)),
        (0.79, (0.2, 0.2)),
    ):
        state.observe(timestamp, prediction)
    assert state.outcome is None
    state.observe(0.8, (0.2, 0.2))
    assert state.outcome == "success"
    assert state.entries == 3
    assert state.interruptions == 2
    assert state.timing()["target_reentries"] == 2


def test_timeout_and_exact_deadline_success():
    target = TARGETS[0]
    state = DwellState(1.0, target)
    state.observe(4.7, (0.2, 0.2))
    state.observe(5.0, (0.2, 0.2))
    assert state.outcome == "success"
    timeout = DwellState(1.0, target)
    timeout.observe(4.9, (0.2, 0.2))
    timeout.expire(5.0)
    assert timeout.outcome == "timeout"
    late = DwellState(1.0, target)
    assert late.observe(5.01, (0.2, 0.2)) == (False, 0.0)
    assert late.outcome == "timeout"


def test_trial_summary_keeps_unclipped_error_and_unavailable():
    trial = schedule()[0]
    state = DwellState(0, trial.target)
    state.observe(0.1, (2.0, -1.0))
    state.observe(0.2, None)
    state.expire(4.0)
    rows = [
        {"status": "usable", "raw_predicted_x": 2.0, "raw_predicted_y": -1.0},
        {"status": "unavailable", "raw_predicted_x": None, "raw_predicted_y": None},
    ]
    summary = summarize_trial(trial, state, rows)
    assert summary["availability_fraction"] == 0.5
    assert summary["outcome"] == "timeout"
    assert summary["median_absolute_x_error"] == pytest.approx(abs(2 - trial.target.x))
    assert summary["final_prediction"] == [2.0, -1.0]


def _report():
    trials = []
    samples = []
    for item in schedule():
        state = DwellState(0.0, item.target)
        state.observe(0.1, (item.target.x, item.target.y))
        state.observe(0.4, (item.target.x, item.target.y))
        rows = [
            {
                **item.identity(),
                "status": "usable",
                "raw_predicted_x": item.target.x,
                "raw_predicted_y": item.target.y,
            }
        ] * 2
        trials.append(summarize_trial(item, state, rows))
        samples.extend(rows)
    return {
        "participant": "cagri",
        "session": "live-1",
        "protocol_name": "coarse_gaze_targeting",
        "protocol_version": 1,
        "order_seed": ORDER_SEED,
        "ready_screen_used": True,
        "second_ready_screen_used": True,
        "calibration_settle_seconds": 0.8,
        "calibration_sample_seconds": 1.2,
        "target_half_width": 0.14,
        "target_half_height": 0.14,
        "dwell_seconds": 0.3,
        "trial_timeout_seconds": 4.0,
        "calibration_presentations": [
            {
                "target_id": target.name,
                "target_x": target.x,
                "target_y": target.y,
                "usable_samples": 5,
            }
            for target in CALIBRATION_TARGETS
        ],
        "trials": trials,
        "samples": samples,
        "failed_camera_reads_including_calibration": 0,
        "no_face_observations_including_calibration": 0,
    }


def test_session_summary_grouping_repeatability_and_determinism():
    report = _report()
    result = analyze_session(report)
    assert result == analyze_session(report)
    assert result["overall"]["successful_trials"] == 27
    assert result["overall"]["success_rate"] == 1
    assert result["overall"]["x_mae"] == 0
    assert result["overall"]["median_confirmed_acquisition_seconds"] == pytest.approx(0.4)
    assert len(result["by_row"]) == len(result["by_column"]) == 3
    assert all(group["trials"] == 9 for group in result["by_row"].values())
    assert all(group["trials"] == 3 for group in result["by_target"].values())
    assert len(result["repeated_targets"]["pairs"]) == 27
    assert result["repeated_targets"]["maximum_euclidean_difference"] == 0


@pytest.mark.parametrize(
    "change",
    [
        {"protocol_name": "eye_opening_controlled"},
        {"protocol_version": 2},
        {"order_seed": 42},
        {"dwell_seconds": 0.5},
    ],
)
def test_reject_incompatible_protocol(change):
    report = _report()
    report.update(change)
    with pytest.raises(ValueError):
        analyze_session(report)


def test_reject_missing_or_duplicate_cells_and_bad_sample_count():
    report = _report()
    report["trials"][1] = deepcopy(report["trials"][0])
    with pytest.raises(ValueError):
        analyze_session(report)
    report = _report()
    report["samples"].pop()
    with pytest.raises(ValueError):
        analyze_session(report)
    report = _report()
    report["samples"][0] = {**report["samples"][0], "target_y": 0.123}
    with pytest.raises(ValueError, match="sample target identity"):
        analyze_session(report)


def test_timeout_is_a_valid_result_not_a_capture_failure():
    report = _report()
    report["trials"][0] = {
        **report["trials"][0],
        "outcome": "timeout",
        "successful_entry_seconds": None,
        "confirmed_acquisition_seconds": None,
    }
    result = analyze_session(report)
    assert result["overall"]["successful_trials"] == 26
    assert result["overall"]["timeout_rate"] == pytest.approx(1 / 27)


def test_primary_pool_excludes_exploratory_and_aggregates_trials():
    reports = []
    for session in ("live-3", "live-4", "live-5"):
        report = _report()
        report["session"] = session
        reports.append(report)
    result = analyze_primary(reports)
    assert result["overall"]["trials"] == 81
    assert result["overall"]["successful_trials"] == 81
    assert result["by_target"]["T-3-3"]["trials"] == 9
    assert result["repeated_targets"]["pairs_within_session"] == 81
    assert result["early_acquisition"]["success_by_seconds"]["0.50"] == 81
    reports[0]["session"] = "live-2"
    with pytest.raises(ValueError, match="primary pool"):
        analyze_primary(reports)


def test_first_sample_inside_and_latency_details_are_threshold_free():
    report = _report()
    report["samples"][0] = {**report["samples"][0], "raw_predicted_x": 2.0}
    details = acquisition_details(report)
    assert details["first_sample_inside"] == 26
    assert details["first_sample_inside_fraction"] == pytest.approx(26 / 27)
    assert details["first_entry"]["median"] == pytest.approx(0.1)
    assert details["successful_entry"]["p95"] == pytest.approx(0.1)
    assert details["confirmed_acquisition"]["median"] == pytest.approx(0.4)
    assert details["dwell_at_success"]["median"] == pytest.approx(0.3)


def test_first_usable_prediction_skips_unavailable_sample():
    report = _report()
    report["samples"][0] = {
        **report["samples"][0],
        "status": "unavailable",
        "raw_predicted_x": None,
        "raw_predicted_y": None,
    }
    report["trials"][0]["usable_prediction_count"] = 1
    report["trials"][0]["unavailable_prediction_count"] = 1
    assert acquisition_details(report)["first_sample_inside"] == 27


@pytest.mark.parametrize("session", ["live-4", "live-5"])
def test_replacement_session_ids_are_accepted_by_runner_and_analyzer(session):
    args = parse_args(
        [
            "--participant",
            "cagri",
            "--session",
            session,
            "--camera-index",
            "1",
            "--output",
            f".venv/coarse-gaze-cagri-{session}.json",
        ]
    )
    assert args.session == session
    report = _report()
    report["session"] = session
    assert analyze_session(report)["session"] == session


def test_cli_only_allows_local_ignored_json():
    args = parse_args(
        [
            "--participant",
            "cagri",
            "--session",
            "live-2",
            "--camera-index",
            "1",
            "--output",
            ".venv/coarse-gaze-cagri-live-2.json",
        ]
    )
    assert args.session == "live-2"
    with pytest.raises(SystemExit):
        parse_args(
            [
                "--participant",
                "cagri",
                "--session",
                "live-1",
                "--camera-index",
                "1",
                "--output",
                "capture.json",
            ]
        )
