"""Hardware-free checks for Issue #84's schedule, calibration fits, pointing and analysis."""

import json

import pytest

from experiments.head_vertical_targeting import analysis, online, protocol


def test_calibration_blocks_are_ordered_and_shuffled_within_block() -> None:
    order = protocol.calibration_schedule()
    assert [p.phase for p in order] == ["eye_x"] * 5 + ["head_y"] * 5 + ["head_x"] * 5
    assert sorted(p.target.x for p in order[:5]) == list(protocol.POSITIONS)
    assert {p.target.y for p in order[:5]} == {0.5}
    assert sorted(p.target.y for p in order[5:10]) == list(protocol.POSITIONS)
    assert {p.target.x for p in order[5:10]} == {0.5}
    assert [p.target.x for p in order[:5]] != list(protocol.POSITIONS)
    assert order == protocol.calibration_schedule()


def test_trial_schedule_covers_both_conditions_and_layouts() -> None:
    for session, first in (("A", "HYBRID"), ("B", "HEAD")):
        trials = protocol.trial_schedule(session)
        assert len(trials) == 50 and trials[0].condition == first
        for condition in protocol.CONDITIONS:
            for layout, (rows, columns) in protocol.LAYOUTS.items():
                cells = [t.target for t in trials if (t.condition, t.layout) == (condition, layout)]
                assert sorted(cells) == [(r, c) for r in range(rows) for c in range(columns)]
        assert all(t.cue != t.target for t in trials)
        assert trials == protocol.trial_schedule(session)


def _row(block, position, x, y, **values) -> dict:
    return {
        "presentation": position,
        "phase": block,
        "target_x": x,
        "target_y": y,
        "status": "usable",
        "horizontal": 0.6 - 0.3 * x,
        "head_pitch_deg": 10.0 + 20.0 * y,
        "head_yaw_deg": -15.0 + 30.0 * x,
        "blink_left": 0.05,
        "blink_right": 0.0,
        **values,
    }


def _calibration_rows(**overrides) -> list[dict]:
    rows = []
    for position, item in enumerate(protocol.calibration_schedule(), start=1):
        for _ in range(6):
            rows.append(_row(item.phase, position, item.target.x, item.target.y, **overrides))
    return rows


def test_calibration_lines_map_each_signal_to_its_axis() -> None:
    lines = online.fit_calibration(_calibration_rows())
    assert lines["eye_x"](0.6 - 0.3 * 0.7) == pytest.approx(0.7)
    assert lines["head_y"](10.0 + 20.0 * 0.3) == pytest.approx(0.3)
    assert lines["head_x"](-15.0 + 30.0 * 0.9) == pytest.approx(0.9)
    frame = _row("trial", 0, 0.25, 0.75)
    assert online.frame_point(frame, lines, "HYBRID") == pytest.approx((0.25, 0.75))
    assert online.frame_point(frame, lines, "HEAD") == pytest.approx((0.25, 0.75))


def test_blink_blocks_eye_x_but_not_head_only_pointing() -> None:
    lines = online.fit_calibration(_calibration_rows())
    blink = _row("trial", 0, 0.25, 0.75, blink_left=0.9)
    assert online.frame_point(blink, lines, "HYBRID") is None
    assert online.frame_point(blink, lines, "HEAD") == pytest.approx((0.25, 0.75))
    missing_pose = _row("trial", 0, 0.25, 0.75, head_pitch_deg=None)
    assert online.frame_point(missing_pose, lines, "HEAD") is None
    assert online.frame_point({**blink, "status": "unavailable_no_face"}, lines, "HEAD") is None


def test_calibration_fails_without_variation_or_enough_presentations() -> None:
    assert online.fit_calibration(_calibration_rows(head_pitch_deg=12.0)) is None
    assert online.fit_calibration(_calibration_rows(blink_left=0.9)) is None
    rows = [
        r for r in _calibration_rows() if not (r["phase"] == "head_x" and r["presentation"] > 13)
    ]
    assert online.fit_calibration(rows) is None  # only 3 of 5 head_x presentations


def test_shared_selection_logic_matches_issue_81_definitions() -> None:
    smoother = online.Smoother()
    for index, value in enumerate((0.1, 0.9, 0.2, 0.3)):
        smoothed = smoother.update(0.01 * index, (value, value))
    assert smoothed == (0.25, 0.25)
    smoother.reset()
    assert smoother.update(1.0, None) is None
    assert online.cell_of((-0.2, 1.4), 3, 3) == (2, 0)
    selector = online.DwellSelector()
    assert selector.update(0.0, (1, 1)) is None
    assert selector.update(1.0, (1, 1)) == (1, 1)


def test_settings_are_preregistered() -> None:
    assert online.BLINK_MAX == 0.5
    assert online.MIN_BLOCK_PRESENTATIONS == 4
    assert (online.SMOOTHING_FRAMES, online.SMOOTHING_MAX_AGE_SECONDS) == (7, 0.5)
    assert (online.DWELL_SECONDS, online.TIMEOUT_SECONDS, online.CUE_SECONDS) == (1.0, 5.0, 0.75)
    assert online.CONDITION_AXES == {"HYBRID": ("eye_x", "head_y"), "HEAD": ("head_x", "head_y")}
    assert (analysis.PASS_SUCCESS_RATE, analysis.PASS_MAX_WRONG_RATE) == (0.80, 0.10)


def _report(session: str, results) -> dict:
    outcomes = []
    for number, trial in enumerate(protocol.trial_schedule(session), start=1):
        result = results(trial)
        selected = (
            None
            if result == "timeout"
            else trial.target
            if result == "success"
            else ((trial.target[0] + 1) % trial.rows, trial.target[1])
        )
        outcomes.append(
            {
                "trial": number,
                "condition": trial.condition,
                "layout": trial.layout,
                "target": list(trial.target),
                "result": result,
                "selected": list(selected) if selected else None,
                "selection_seconds": None if result == "timeout" else 1.4,
            }
        )
    return {"participant": "p", "session": session, "seed": 84, "outcomes": outcomes}


def test_analysis_scores_each_condition_and_layout(tmp_path, capsys) -> None:
    def results(trial):
        return "success" if trial.condition == "HEAD" else "wrong"

    a = analysis.analyze_session(_report("A", results))
    assert a["results"]["HEAD/3x3"]["passes"] and a["results"]["HEAD/4x4"]["success_rate"] == 1
    assert (
        a["results"]["HYBRID/4x4"]["wrong_rate"] == 1 and not a["results"]["HYBRID/4x4"]["passes"]
    )
    b = analysis.analyze_session(_report("B", results))
    combined = analysis.combine([a, b])["passes"]
    assert combined == {
        "HYBRID/3x3": False,
        "HYBRID/4x4": False,
        "HEAD/3x3": True,
        "HEAD/4x4": True,
    }
    assert not any(analysis.combine([a])["passes"].values())
    short = _report("A", results)
    short["outcomes"].pop()
    with pytest.raises(ValueError, match="every planned trial"):
        analysis.analyze_session(short)
    path = tmp_path / "A.json"
    path.write_text(json.dumps(_report("A", results)), encoding="utf-8")
    assert analysis.main([str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["sessions"][0]["results"]["HEAD/3x3"]["passes"]


def test_collector_cli_requires_screen_size_and_ignored_output() -> None:
    from experiments.head_vertical_targeting.run import parse_args

    base = ["--participant", "fatih", "--session", "A", "--camera-index", "0"]
    output = ["--output", ".venv/head-vertical-fatih-A.json"]
    assert parse_args(base + output + ["--screen-size", "1512x982"]).seed == 84
    with pytest.raises(SystemExit):
        parse_args(base + output)
