"""Hardware-free checks for Issue #156: signals, calibration, filter, dwell, rule."""

import json
from math import cos, radians, sin

import pytest

from experiments.head_pointer import analysis, pointer, protocol, signals


def _matrix(yaw_deg=0.0, pitch_deg=0.0, position=(0.0, 0.0, -50.0)):
    """Rotation about y (yaw) then x (pitch); forward axis starts at +z (toward camera)."""
    cy, sy = cos(radians(yaw_deg)), sin(radians(yaw_deg))
    cp, sp = cos(radians(pitch_deg)), sin(radians(pitch_deg))
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rx = [[1, 0, 0], [0, cp, -sp], [0, sp, cp]]
    r = [[sum(rx[i][k] * ry[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return [[*r[i], position[i]] for i in range(3)] + [[0, 0, 0, 1]]


def test_frozen_constants() -> None:
    assert signals.CANDIDATES == ("NOSE", "ANGLES", "RAY")
    assert protocol.SESSION_ORDER == {
        "A": ("NOSE", "ANGLES", "RAY"),
        "B": ("RAY", "ANGLES", "NOSE"),
    }
    assert protocol.TARGET_DIAMETERS == (30, 60)
    assert protocol.DWELL_SECONDS == 0.8 and protocol.TIMEOUT_SECONDS == 8.0
    assert protocol.MAX_TIMEOUTS_PER_SESSION == 1 and protocol.TIE_FRACTION == 0.05
    assert (protocol.ONE_EURO_MIN_CUTOFF, protocol.ONE_EURO_BETA) == (1.0, 0.01)
    assert protocol.MIN_POINTS == 7 and protocol.MIN_FRAMES_PER_POINT == 5


def test_nose_signal_reads_tip_and_rejects_bad_input() -> None:
    landmarks = [(0.0, 0.0), (0.42, 0.61), (0.9, 0.9)]
    assert signals.nose_signal(landmarks) == (0.42, 0.61)
    assert signals.nose_signal(None) is None
    assert signals.nose_signal([(0.1, 0.1)]) is None
    assert signals.nose_signal([(0, 0), (float("nan"), 0.5)]) is None


def test_angle_signal_recovers_yaw_and_pitch() -> None:
    yaw, pitch = signals.angle_signal(_matrix(yaw_deg=12.0))
    assert yaw == pytest.approx(12.0) and pitch == pytest.approx(0.0, abs=1e-9)
    yaw, pitch = signals.angle_signal(_matrix(pitch_deg=-8.0))
    assert yaw == pytest.approx(0.0, abs=1e-9) and pitch == pytest.approx(-8.0)
    assert signals.angle_signal([[1, 2], [3]]) is None


def test_ray_signal_combines_position_and_rotation() -> None:
    assert signals.ray_signal(_matrix()) == pytest.approx((0.0, 0.0))
    # Translating the head shifts the ray point one-to-one.
    assert signals.ray_signal(_matrix(position=(3.0, -2.0, -50.0))) == pytest.approx((3.0, -2.0))
    # Turning 10 degrees at 50 cm moves the point by 50 * tan(10 deg) along x.
    x, y = signals.ray_signal(_matrix(yaw_deg=10.0))
    assert x == pytest.approx(50 * sin(radians(10)) / cos(radians(10)))
    assert y == pytest.approx(0.0, abs=1e-9)
    # Facing away or parallel to the camera plane gives no point.
    assert signals.ray_signal(_matrix(yaw_deg=180.0)) is None
    assert signals.ray_signal(_matrix(yaw_deg=85.0)) is None


def test_calibration_schedule_is_shuffled_3x3() -> None:
    schedule = protocol.calibration_schedule()
    assert len(schedule) == 9 and schedule == protocol.calibration_schedule()
    assert sorted((p.x, p.y) for p in schedule) == sorted(
        (x, y) for x in (0.1, 0.5, 0.9) for y in (0.1, 0.5, 0.9)
    )
    assert [p.index for p in schedule] == list(range(1, 10))


def test_target_schedule_covers_each_candidate_without_repeats() -> None:
    for session, order in protocol.SESSION_ORDER.items():
        trials = protocol.target_schedule(session)
        assert trials == protocol.target_schedule(session)
        assert tuple(dict.fromkeys(t.candidate for t in trials)) == order
        for candidate in order:
            block = [t for t in trials if t.candidate == candidate]
            assert len(block) == protocol.PRACTICE_TRIALS + 16
            assert all(t.practice for t in block[: protocol.PRACTICE_TRIALS])
            scored = [t for t in block if not t.practice]
            assert sorted((round(t.x, 6), round(t.y, 6), t.diameter) for t in scored) == sorted(
                (round(x, 6), round(y, 6), d)
                for a in protocol.TARGET_ANGLES
                for x, y in [protocol.target_position(a)]
                for d in protocol.TARGET_DIAMETERS
            )
            assert all((a.x, a.y) != (b.x, b.y) for a, b in zip(scored, scored[1:], strict=False))
            assert all(0.05 < t.x < 0.95 and 0.05 < t.y < 0.95 for t in block)
    with pytest.raises(ValueError):
        protocol.target_schedule("C")


def _calibration_rows(candidate_fn, frames=6, drop=()):
    rows = []
    for point in protocol.calibration_schedule():
        if point.index in drop:
            continue
        for i in range(frames):
            noise = 0.001 * (i - (frames - 1) / 2)
            rows.append(
                {
                    "point": point.index,
                    "target_x": point.x,
                    "target_y": point.y,
                    "signals": {
                        "NOSE": candidate_fn(point.x, point.y, noise),
                        "ANGLES": None,
                        "RAY": [float("nan"), 0.0],
                    },
                }
            )
    return rows


def test_fit_mapping_inverts_a_linear_signal() -> None:
    rows = _calibration_rows(lambda x, y, n: [0.6 - 0.2 * x + n, 0.3 + 0.1 * y + n])
    mapping = pointer.fit_mapping(rows, "NOSE")
    assert mapping((0.6 - 0.2 * 0.25, 0.3 + 0.1 * 0.75)) == pytest.approx((0.25, 0.75), abs=1e-6)
    assert pointer.fit_mapping(rows, "ANGLES") is None
    assert pointer.fit_mapping(rows, "RAY") is None


def test_fit_mapping_needs_enough_points_and_frames() -> None:
    linear = lambda x, y, n: [x + n, y + n]  # noqa: E731
    assert pointer.fit_mapping(_calibration_rows(linear, drop=(1, 2)), "NOSE") is not None
    assert pointer.fit_mapping(_calibration_rows(linear, drop=(1, 2, 3)), "NOSE") is None
    assert pointer.fit_mapping(_calibration_rows(linear, frames=4), "NOSE") is None
    assert pointer.fit_line([(1.0, 0.2), (1.0, 0.8)]) is None


def test_one_euro_smooths_jitter_but_follows_motion() -> None:
    f = pointer.OneEuroFilter2D()
    assert f.update(0.0, (100.0, 100.0)) == (100.0, 100.0)
    # Alternating 4 px jitter at 30 Hz is strongly reduced at rest.
    outputs = [f.update(i / 30, (100.0 + (2 if i % 2 else -2), 100.0)) for i in range(1, 60)]
    assert max(abs(o[0] - 100.0) for o in outputs[-20:]) < 1.0
    # A sustained move is followed within about half a second.
    for i in range(60, 75):
        out = f.update(i / 30, (600.0, 100.0))
    assert out[0] > 580.0
    # Non-increasing time keeps the last value; a long gap restarts at the new point.
    assert f.update(74 / 30, (0.0, 0.0)) == out
    assert f.update(10.0, (5.0, 6.0)) == (5.0, 6.0)


def test_dwell_trial_selects_after_contiguous_dwell() -> None:
    trial = pointer.DwellTrial((100.0, 100.0), 15.0)
    assert trial.update(0.0, (300.0, 300.0)) is None
    trial.update(0.5, (105.0, 100.0))
    trial.update(0.9, (120.0, 100.0))  # left the circle: dwell restarts
    trial.update(1.0, (101.0, 99.0))
    assert trial.update(1.7, (99.0, 101.0)) is None
    assert trial.progress(1.7) == pytest.approx(0.7 / 0.8)
    trial.update(1.85, None)  # lost face also restarts the dwell
    trial.update(2.0, (100.0, 100.0))
    assert trial.update(2.8, (100.0, 100.0)) == "selected"
    assert (trial.elapsed, trial.entries, trial.first_entry) == (2.8, 3, 0.5)
    assert trial.hold_jitter() == pytest.approx(0.0)
    assert trial.update(5.0, (900.0, 900.0)) == "selected"


def test_dwell_trial_times_out() -> None:
    trial = pointer.DwellTrial((100.0, 100.0), 15.0)
    assert trial.update(7.9, (500.0, 500.0)) is None
    assert trial.update(8.0, (500.0, 500.0)) == "timeout"
    assert trial.hold_jitter() is None


def _session(name, outcomes):
    trials = []
    for candidate, (timeouts, time, jitter) in outcomes.items():
        trials.append(
            {
                "candidate": candidate,
                "practice": True,
                "diameter": 60,
                "outcome": "timeout",
                "elapsed": 8.0,
                "entries": 0,
                "hold_jitter_px": None,
            }
        )
        for i in range(16):
            selected = i >= timeouts
            trials.append(
                {
                    "candidate": candidate,
                    "practice": False,
                    "diameter": (30, 60)[i % 2],
                    "outcome": "selected" if selected else "timeout",
                    "elapsed": time if selected else 8.0,
                    "entries": 1,
                    "hold_jitter_px": jitter if selected else None,
                }
            )
    return {
        "session": name,
        "completed": True,
        "mappings": dict.fromkeys(outcomes),
        "trials": trials,
    }


def test_winner_rule_passes_fastest_with_tie_break_on_jitter() -> None:
    sessions = [
        _session("A", {"NOSE": (0, 2.00, 3.0), "ANGLES": (1, 1.95, 1.0), "RAY": (2, 1.0, 1.0)}),
        _session("B", {"NOSE": (1, 2.00, 3.0), "ANGLES": (0, 1.95, 1.0), "RAY": (0, 1.0, 1.0)}),
    ]
    summary = analysis.summarize(sessions)
    c = summary["candidates"]
    assert (c["NOSE"]["passes"], c["ANGLES"]["passes"], c["RAY"]["passes"]) == (True, True, False)
    assert c["RAY"]["sessions"]["A"]["timeouts"] == 2
    # ANGLES is faster but NOSE is within 5 %; ANGLES has lower jitter anyway.
    assert summary["winner"] == "ANGLES"
    json.dumps(summary)


def test_winner_tie_break_prefers_lower_jitter_over_speed() -> None:
    sessions = [
        _session(s, {"NOSE": (0, 2.00, 1.0), "ANGLES": (0, 1.95, 4.0), "RAY": (5, 1.0, 1.0)})
        for s in "AB"
    ]
    assert analysis.winner(analysis.summarize(sessions)["candidates"]) == "NOSE"
    sessions = [
        _session(s, {"NOSE": (0, 2.50, 1.0), "ANGLES": (0, 1.95, 4.0), "RAY": (5, 1.0, 1.0)})
        for s in "AB"
    ]
    assert analysis.summarize(sessions)["winner"] == "ANGLES"


def test_no_winner_when_nothing_passes_or_session_incomplete() -> None:
    bad = {"NOSE": (2, 2.0, 1.0), "ANGLES": (3, 2.0, 1.0), "RAY": (16, 1.0, 1.0)}
    assert analysis.summarize([_session("A", bad), _session("B", bad)])["winner"] is None
    partial = _session("B", {"NOSE": (0, 2.0, 1.0)})
    summary = analysis.summarize([_session("A", {"NOSE": (0, 2.0, 1.0)}), partial])
    assert summary["candidates"]["ANGLES"]["passes"] is False
    assert summary["winner"] == "NOSE"


def test_analysis_cli_reads_session_files(tmp_path, capsys) -> None:
    paths = []
    for name in "AB":
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(_session(name, {"NOSE": (0, 2.0, 1.0)})))
        paths.append(str(path))
    assert analysis.main(paths) == 0
    assert json.loads(capsys.readouterr().out)["winner"] == "NOSE"


def test_run_arguments_require_full_screen_size() -> None:
    from experiments.head_pointer import run

    args = run.parse_args(
        [
            "--participant",
            "p",
            "--session",
            "A",
            "--camera-index",
            "0",
            "--screen-size",
            "1512x982",
            "--output",
            "x.json",
        ]
    )
    assert args.screen_size == (1512, 982)
    with pytest.raises(SystemExit):
        run.parse_args(
            [
                "--participant",
                "p",
                "--session",
                "A",
                "--camera-index",
                "0",
                "--screen-size",
                "big",
                "--output",
                "x.json",
            ]
        )
