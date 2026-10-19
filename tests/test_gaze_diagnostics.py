"""Synthetic diagnostic contracts: no camera, OS actions or participant files."""

import json

import pytest

from eye_tracker.actions.pointer import PointerController


def api():
    from validation import gaze_diagnostics

    return gaze_diagnostics


def test_error_summary_separates_bias_jitter_and_missing_predictions():
    result = api().error_summary([(0.5, 0.5), (0.7, 0.5), None], (0.5, 0.5), (100, 100))
    assert result["valid"] == 2
    assert result["attempts"] == 3
    assert result["bias_px"] == pytest.approx([10, 0])
    assert result["centered_rms_px"] == pytest.approx(10)
    assert result["mean_distance_px"] == pytest.approx(10)
    assert result["within_30px_fraction_all_attempts"] == pytest.approx(2 / 3)
    empty = api().error_summary([None], (0.5, 0.5), (100, 100))
    assert empty["bias_px"] is None
    json.dumps(empty, allow_nan=False)


def test_coordinate_contract_known_screen_points_and_invalid_input():
    # Real controller, inert endpoint: no pyautogui import or desktop interaction.
    class Sink:
        screen_size = (1512, 982)

        def check_stop(self):
            pass

        def move(self, x, y):
            pass

        def click(self):
            raise AssertionError("No clicks expected")

    controller = PointerController(Sink(), (0, 33, 1512, 949))
    cases = [((0, 0), [0, 33]), ((0.5, 0.5), [756, 508]), ((1, 1), [1511, 981])]
    for i, (point, expected) in enumerate(cases):
        assert controller.update(i, point)["pixel"] == expected
    assert controller.update(4, (-0.01, 0.5))["pixel"] is None


def test_coordinate_audit_detects_missing_window_offset():
    desktop = {"region": [0, 33, 1512, 949], "screen_size": [1512, 982]}
    records = [
        {"displayed_predictions": {"point": [0.5, 0.5]}, "desktop_action": {"pixel": p}}
        for p in ([756, 508], [756, 475])
    ]
    report = api().coordinate_audit(records, desktop, (1512, 949))
    assert report["compared"] == 2
    assert report["mismatches"] == 1
    assert report["max_error_px"] == 33
    assert not report["physical_screen_alignment_verified"]


def test_calibration_quality_preserves_bad_rows_and_reports_per_target_spread():
    rows = []
    for p, value in enumerate((0.1, 0.5, 0.9)):
        for offset in (-0.01, 0, 0.01, 0, 0):
            rows.append(
                dict(
                    phase="calibration",
                    camera="macbook",
                    presentation=p,
                    target_x=value,
                    target_y=value,
                    status="usable",
                    blink_left=0.1,
                    blink_right=0.1,
                    horizontal=value + offset,
                    vertical=value + offset,
                    head_pitch_deg=0,
                    head_yaw_deg=0,
                    head_roll_deg=0,
                )
            )
    rows.append(dict(rows[0], blink_left=0.9, vertical=999))
    before = json.dumps(rows)
    report = api().calibration_quality(rows)
    assert json.dumps(rows) == before
    assert report["eligible_rows"] == 15
    assert report["excluded_rows"] == 1
    assert report["features"]["vertical"]["median_span"] == pytest.approx(0.8)
    assert report["features"]["vertical"]["correlation_target_y"] == pytest.approx(1)
    assert report["features"]["head_pitch_deg"]["correlation_target_y"] is None


def test_live_segments_do_not_mix_revisits_and_exclude_settling():
    def row(t, target, prediction):
        return dict(
            seconds=t,
            target=target,
            predictions={"point": prediction},
            displayed_predictions={"point": prediction},
        )

    records = [
        row(0, [0.5, 0.5], [9, 9]),
        row(1, [0.5, 0.5], [0.6, 0.5]),
        row(2, [0.8, 0.8], [9, 9]),
        row(3, [0.8, 0.8], None),
        row(4, [0.5, 0.5], [9, 9]),
        row(5, [0.5, 0.5], [0.5, 0.5]),
    ]
    segments = api().live_segments(records, (100, 100))
    assert len(segments) == 3
    assert segments[0]["raw"]["mean_distance_px"] == pytest.approx(10)
    assert segments[1]["raw"]["valid"] == 0
    assert segments[2]["raw"]["mean_distance_px"] == 0
    assert all(s["gaze_on_target_verified"] is False for s in segments)


def test_report_rejects_archival_or_symlink_input_before_reading(tmp_path):
    root = tmp_path / "results"
    root.mkdir()
    outside = tmp_path / ".venv"
    outside.mkdir()
    alias = root / "cagri-live-macbook-svr-alias"
    alias.symlink_to(outside, target_is_directory=True)
    for path in (outside, alias):
        with pytest.raises(ValueError):
            api().read_session(path, root)


def test_probe_schedule_is_finite_with_separate_pose_blocks():
    trials = api().probe_schedule()
    assert len(trials) == 10
    assert [t["target"] for t in trials[:5]] == [t["target"] for t in trials[5:]]
    assert {t["condition"] for t in trials[:5]} == {"baseline"}
    assert {t["condition"] for t in trials[5:]} == {"after_position_change"}


def test_probe_requires_two_ready_gates_and_never_refits_or_moves_pointer(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import live_svr_demo as demo

    gates = []
    ticks = iter(i * 0.1 for i in range(2000))
    monkeypatch.setattr(demo, "wait_ready", lambda *args: gates.append(args[-1]))
    monkeypatch.setattr(demo, "_draw_target", lambda *args: object())
    monkeypatch.setattr(demo, "text", lambda *args, **kwargs: None)
    monkeypatch.setattr(demo, "measure_signals", lambda *args: (None, {}))
    monkeypatch.setattr(demo, "predict_single", lambda *args: {"point": (0.5, 0.5)})
    monkeypatch.setattr(demo, "PyAutoGUIPointer", lambda: pytest.fail("OS adapter opened"))
    monkeypatch.setattr(demo, "fit_calibration", lambda *args: pytest.fail("Unexpected fit"))
    cv = SimpleNamespace(
        imshow=lambda *args: None,
        waitKey=lambda *args: -1,
        getWindowProperty=lambda *args: 1,
        WND_PROP_VISIBLE=0,
    )
    count = demo.run_diagnostic_probe(
        cv,
        None,
        "window",
        (100, 100),
        {},
        {"macbook": None},
        {"macbook": None},
        {"macbook": None},
        tmp_path,
        clock=lambda: next(ticks),
    )
    assert len(gates) == 2
    records = [json.loads(line) for line in (tmp_path / "live.jsonl").read_text().splitlines()]
    assert len(records) == count > 10
    assert len({(r["diagnostic"]["condition"], r["diagnostic"]["trial"]) for r in records}) == 10
    assert all(r["desktop_action"] is None for r in records)
    assert any(not r["diagnostic"]["sampling"] for r in records)
    assert any(r["diagnostic"]["sampling"] for r in records)
    summary = json.loads((tmp_path / "diagnostic-summary.json").read_text())
    assert len(summary["segments"]) == 10
    assert all(s["raw"]["valid"] > 0 for s in summary["segments"])


def test_diagnostic_and_pointer_flags_are_rejected_before_run(monkeypatch):
    import sys

    import live_svr_demo as demo

    monkeypatch.setattr(sys, "argv", ["live_svr_demo.py", "--diagnostic", "--control-pointer"])
    monkeypatch.setattr(demo, "run", lambda args: pytest.fail("Must not start a camera"))
    with pytest.raises(SystemExit) as error:
        demo.main()
    assert error.value.code == 2


def test_diagnostic_flag_selects_observation_only_mode(monkeypatch):
    import sys

    import live_svr_demo as demo

    received = []
    monkeypatch.setattr(sys, "argv", ["live_svr_demo.py", "--diagnostic"])
    monkeypatch.setattr(demo, "run", lambda args: received.append(args) or 0)
    assert demo.main() == 0
    assert received[0].diagnostic
    assert not received[0].control_pointer


def test_probe_escape_preserves_partial_rows_without_final_summary(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import live_svr_demo as demo

    ticks = iter(i * 0.1 for i in range(100))
    keys = iter((-1, -1, 27))
    monkeypatch.setattr(demo, "wait_ready", lambda *args: None)
    monkeypatch.setattr(demo, "_draw_target", lambda *args: object())
    monkeypatch.setattr(demo, "text", lambda *args, **kwargs: None)
    monkeypatch.setattr(demo, "measure_signals", lambda *args: (None, {}))
    monkeypatch.setattr(demo, "predict_single", lambda *args: {"point": None})
    cv = SimpleNamespace(
        imshow=lambda *args: None,
        waitKey=lambda *args: next(keys),
        getWindowProperty=lambda *args: 1,
        WND_PROP_VISIBLE=0,
    )
    with pytest.raises(InterruptedError):
        demo.run_diagnostic_probe(
            cv,
            None,
            "window",
            (100, 100),
            {},
            {"macbook": None},
            {"macbook": None},
            {"macbook": None},
            tmp_path,
            clock=lambda: next(ticks),
        )
    assert len((tmp_path / "live.jsonl").read_text().splitlines()) == 2
    assert not (tmp_path / "diagnostic-summary.json").exists()
