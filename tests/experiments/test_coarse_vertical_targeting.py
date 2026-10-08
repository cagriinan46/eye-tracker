"""Hardware-free checks for Issue #81's schedule, online selection logic and analysis."""

import json

import pytest

from experiments.coarse_vertical_targeting import analysis, online, protocol

# Protocol


def test_trial_schedule_counts_order_and_cues() -> None:
    for session, first in (("A", "3x3"), ("B", "4x4")):
        trials = protocol.trial_schedule(session)
        assert len(trials) == 34
        assert trials[0].layout == first
        three = [t.target for t in trials if t.layout == "3x3"]
        four = [t.target for t in trials if t.layout == "4x4"]
        assert sorted(three) == sorted([(r, c) for r in range(3) for c in range(3)] * 2)
        assert sorted(four) == sorted((r, c) for r in range(4) for c in range(4))
        assert all(t.cue != t.target for t in trials)
        assert trials == protocol.trial_schedule(session)
    assert protocol.mirrored_cue((1, 1), 3, 3) == (0, 0)
    assert protocol.mirrored_cue((0, 2), 3, 3) == (2, 0)
    assert protocol.trial_schedule("A") != protocol.trial_schedule("A", seed=82)


def test_calibration_schedule_is_shuffled_5x5() -> None:
    order = protocol.calibration_schedule()
    assert len(order) == 25 and len({p.target for p in order}) == 25
    assert [p.target.y for p in order] != sorted(p.target.y for p in order)


# Online logic


def _calibration_rows(count: int = 25, blink: float = 0.05) -> list[dict]:
    rows = []
    for position, item in enumerate(protocol.calibration_schedule()[:count], start=1):
        x, y = item.target.x, item.target.y
        for frame in range(6):
            jitter = (frame - 3) * 1e-4
            rows.append(
                {
                    "presentation": position,
                    "phase": "calibration",
                    "target_id": item.target.name,
                    "target_x": x,
                    "target_y": y,
                    "trial_number": 1,
                    "status": "usable",
                    "horizontal": 0.2 + 0.6 * x + jitter,
                    "vertical": -0.05 + 0.02 * y,
                    "binocular_eye_opening": 0.4 - 0.1 * y + 0.01 * x * x,
                    "look_up_left": 0.3 - 0.2 * y + 0.05 * x,
                    "look_up_right": 0.3 - 0.2 * y + 0.05 * x,
                    "look_down_left": 0.1 + 0.5 * y,
                    "look_down_right": 0.1 + 0.5 * y,
                    "blink_left": blink,
                    "blink_right": 0.0,
                    "head_pitch_deg": 2.0 + 0.3 * x * y,
                }
            )
    return rows


def test_mapping_fits_calibration_and_maps_frames() -> None:
    rows = _calibration_rows()
    mapping = online.fit_mapping(rows)
    assert mapping is not None and mapping.calibration_presentations == 25
    x, y = online.frame_point(rows[0], mapping)
    assert x == pytest.approx(rows[0]["target_x"], abs=1e-3)
    assert y == pytest.approx(rows[0]["target_y"], abs=1e-3)
    assert online.frame_point({**rows[0], "blink_left": 0.9}, mapping) is None
    assert online.frame_point({**rows[0], "status": "unavailable_no_face"}, mapping) is None


def test_mapping_requires_twenty_calibration_presentations() -> None:
    assert online.fit_mapping(_calibration_rows(count=19)) is None
    assert online.fit_mapping(_calibration_rows(blink=0.9)) is None


def test_smoother_uses_median_of_recent_valid_points() -> None:
    smoother = online.Smoother()
    assert smoother.update(0.0, None) is None
    for index, value in enumerate((0.1, 0.9, 0.2, 0.3)):
        smoothed = smoother.update(0.01 * index, (value, value))
    assert smoothed == (0.25, 0.25)
    assert smoother.update(0.2, None) == (0.25, 0.25)  # blink gap keeps recent estimate
    assert smoother.update(0.6, None) is None  # all points older than 0.5 s
    for index in range(10):
        smoothed = smoother.update(1.0 + 0.01 * index, (float(index), 0.0))
    assert smoothed == (6.0, 0.0)  # only the last seven points (3..9)


def test_cells_fill_the_screen_and_clamp_outside_points() -> None:
    assert online.cell_of((0.0, 0.0), 3, 3) == (0, 0)
    assert online.cell_of((0.34, 0.66), 3, 3) == (1, 1)
    assert online.cell_of((0.999, 1.0), 4, 4) == (3, 3)
    assert online.cell_of((-0.4, 1.7), 3, 3) == (2, 0)


def test_dwell_selects_any_cell_after_one_second_and_resets() -> None:
    selector = online.DwellSelector()
    assert selector.update(0.0, (0, 0)) is None
    assert selector.progress(0.5) == pytest.approx(0.5)
    assert selector.update(0.9, (0, 0)) is None
    assert selector.update(1.0, (0, 0)) == (0, 0)
    assert selector.update(1.1, (1, 1)) is None
    assert selector.update(1.5, (1, 2)) is None  # change restarts dwell
    assert selector.update(2.4, (1, 2)) is None
    assert selector.update(2.45, None) is None  # unavailable resets
    assert selector.update(3.0, (1, 2)) is None
    assert selector.update(4.0, (1, 2)) == (1, 2)


def test_selection_settings_are_preregistered() -> None:
    assert online.MIN_CALIBRATION_PRESENTATIONS == 20
    assert online.SMOOTHING_FRAMES == 7
    assert online.SMOOTHING_MAX_AGE_SECONDS == 0.5
    assert online.DWELL_SECONDS == 1.0
    assert online.TIMEOUT_SECONDS == 5.0
    assert online.CUE_SECONDS == 0.75
    assert online.Y_FEATURES == ("vertical", "opening", "blend", "pitch")
    assert analysis.PASS_SUCCESS_RATE == 0.80
    assert analysis.PASS_MAX_WRONG_RATE == 0.10


# Analysis


def _report(session: str, results) -> dict:
    outcomes = []
    for number, trial in enumerate(protocol.trial_schedule(session), start=1):
        result = results(trial, number)
        selected = (
            None
            if result == "timeout"
            else trial.target
            if result == "success"
            else (min(trial.rows - 1, trial.target[0] + 1), trial.target[1])
        )
        outcomes.append(
            {
                "trial": number,
                "layout": trial.layout,
                "rows": trial.rows,
                "columns": trial.columns,
                "target": list(trial.target),
                "cue": list(trial.cue),
                "result": result,
                "selected": list(selected) if selected else None,
                "selection_seconds": None if result == "timeout" else 1.5,
            }
        )
    return {"participant": "p", "session": session, "seed": 81, "outcomes": outcomes}


def test_layout_summary_and_pass_rule() -> None:
    def results(trial, number):
        if trial.layout == "4x4" and trial.target[0] == 3:
            return "wrong"
        return "success"

    session = analysis.analyze_session(_report("A", results))
    three, four = session["layouts"]["3x3"], session["layouts"]["4x4"]
    assert three["success_rate"] == 1.0 and three["passes"]
    assert four["wrong"] == 4 and four["wrong_rate"] == 0.25 and not four["passes"]
    assert four["success_by_target_row"]["3"] == 0.0
    assert four["median_success_seconds"] == 1.5
    json.dumps(session, allow_nan=False)


def test_validation_rejects_reordered_or_incomplete_sessions() -> None:
    report = _report("A", lambda trial, number: "success")
    report["outcomes"][0], report["outcomes"][1] = report["outcomes"][1], report["outcomes"][0]
    if report["outcomes"][0]["target"] != report["outcomes"][1]["target"]:
        with pytest.raises(ValueError, match="frozen schedule"):
            analysis.analyze_session(report)
    short = _report("A", lambda trial, number: "success")
    short["outcomes"].pop()
    with pytest.raises(ValueError, match="every planned trial"):
        analysis.analyze_session(short)


def test_combine_needs_both_sessions_to_pass(tmp_path, capsys) -> None:
    good = analysis.analyze_session(_report("A", lambda t, n: "success"))
    timeouts = analysis.analyze_session(_report("B", lambda t, n: "timeout"))
    assert analysis.combine([good, timeouts])["layout_passes"] == {"3x3": False, "4x4": False}
    good_b = analysis.analyze_session(_report("B", lambda t, n: "success"))
    assert analysis.combine([good, good_b])["layout_passes"] == {"3x3": True, "4x4": True}
    assert analysis.combine([good])["layout_passes"] == {"3x3": False, "4x4": False}
    with pytest.raises(ValueError, match="duplicate"):
        analysis.combine([good, good])
    path = tmp_path / "A.json"
    path.write_text(json.dumps(_report("A", lambda t, n: "success")), encoding="utf-8")
    assert analysis.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["sessions"][0]["layouts"]["3x3"]["passes"]


def test_collector_cli_requires_screen_size_and_ignored_output() -> None:
    from experiments.coarse_vertical_targeting.run import parse_args

    base = ["--participant", "fatih", "--session", "A", "--camera-index", "0"]
    output = ["--output", ".venv/coarse-vertical-fatih-A.json"]
    assert parse_args(base + output + ["--screen-size", "1512x982"]).seed == 81
    with pytest.raises(SystemExit):
        parse_args(base + output)
    with pytest.raises(SystemExit):
        parse_args(base + ["--output", "x.json", "--screen-size", "1512x982"])
