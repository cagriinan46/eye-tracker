import numpy as np
import pytest

from experiments.desktop_demo.protocol import CALIBRATION_POINTS, SHAPES, Session


def ready_session():
    s = Session()
    s.phase = "ready"
    s.check_results = [{"n": 10, "mean_px": 50}]
    s.geometry = [1000, 800, 0, 0, 1]
    return s


def test_calibration_samples_require_render_ack_and_settle():
    s = Session()
    s.start_calibration([1000, 800, 0, 0, 1])
    s.sample(10, np.ones(258), None)
    assert not s.samples
    s.ack(s.token, 11)
    s.sample(12, np.ones(258), None)
    assert not s.samples
    v = np.ones(258)
    s.sample(12.6, v, None)
    v[:] = 99
    assert s.samples[0][0] == 1


def test_full_calibration_and_independent_check():
    s = Session()
    s.start_calibration([1000, 800, 0, 0, 1])
    now = 0
    for _ in CALIBRATION_POINTS:
        s.ack(s.token, now)
        for j in range(45):
            s.sample(now + 1.6 + j * 0.04, np.ones(258), None)
        now += 5
    assert s.phase == "fitting"
    x, y = s.calibration_arrays()
    assert x.shape == (585, 258) and y.shape == (585, 2)
    s.fitted()
    for _ in range(5):
        s.ack(s.token, now)
        target = s.point
        for j in range(60):
            s.sample(now + 1 + j * 0.04, None, target)
        s.sample(now + 3.5, None, target)
        now += 5
    assert s.phase == "ready"
    assert all(r["mean_px"] == 0 for r in s.check_results)


def test_demo_counts_wrong_selection_not_just_success():
    s = ready_session()
    s.start_demo()
    s.ack(s.token, 0)
    wrong = next(x for x in SHAPES if x != s.expected)
    s.set_regions({key: [i * 0.25, 0, 0.24, 1] for i, key in enumerate(SHAPES)})
    x = SHAPES.index(wrong) * 0.25 + 0.1
    for i in range(16):
        s.sample(1 + i * 0.1, None, [x, 0.5])
    assert len(s.trials) == 1
    assert s.trials[0]["outcome"] == "incorrect"
    assert s.trials[0]["selected"] == wrong


def test_timeout_and_pause_exclude_paused_duration():
    s = ready_session()
    s.start_demo()
    s.ack(s.token, 0)
    s.pause(5)
    s.resume(105)
    s.sample(114, None, None)
    assert not s.trials
    s.sample(116, None, None)
    assert s.trials[0]["outcome"] == "timeout"
    assert s.trials[0]["elapsed_s"] == 15


def test_resize_invalidates_calibration_and_selection():
    s = ready_session()
    s.start_demo()
    s.geometry_changed([1001, 800, 0, 0, 1])
    assert s.phase == "error"
    assert s.dwell.target is None


def test_regions_reject_overlap_and_nonfinite():
    s = ready_session()
    with pytest.raises(ValueError):
        s.set_regions({k: [0, 0, 1, 1] for k in SHAPES})
    with pytest.raises(ValueError):
        s.set_regions({k: [float("nan"), 0, 0.1, 0.1] for k in SHAPES})


def test_stale_ack_does_not_start_new_target():
    s = Session()
    s.start_calibration([1000, 800, 0, 0, 1])
    s.ack(s.token - 1, 0)
    assert s.onset is None


def test_gaze_loss_and_pause_cannot_complete_old_dwell():
    s = ready_session()
    s.start_demo()
    s.ack(s.token, 0)
    s.set_regions({key: [i * 0.25, 0, 0.24, 1] for i, key in enumerate(SHAPES)})
    for i in range(10):
        s.sample(1 + i * 0.1, None, [0.1, 0.5])
    s.sample(2, None, None)
    s.sample(2.1, None, [0.1, 0.5])
    assert not s.trials and s.dwell.progress == 0
    s.pause(2.2)
    s.resume(10)
    s.sample(10.1, None, [0.1, 0.5])
    assert not s.trials and s.dwell.progress == 0


def test_insufficient_check_data_fails_without_fake_zero_error():
    s = Session()
    s.geometry = [1000, 800, 0, 0, 1]
    s.fitted()
    s.ack(s.token, 0)
    s.sample(3.1, None, None)
    assert s.phase == "error" and not s.check_results


def test_long_camera_gap_does_not_skip_dwell():
    s = ready_session()
    s.start_demo()
    s.ack(s.token, 0)
    s.set_regions({key: [i * 0.25, 0, 0.24, 1] for i, key in enumerate(SHAPES)})
    s.sample(1, None, [0.1, 0.5])
    s.sample(4, None, [0.1, 0.5])
    assert not s.trials and s.dwell.progress == 0


def test_pause_before_render_ack_can_resume_with_new_handshake():
    s = ready_session()
    s.start_demo()
    old = s.token
    s.pause(0)
    s.ack(old, 0.1)
    s.resume(2)
    assert s.token != old and s.onset is None
    s.ack(s.token, 2.1)
    assert s.onset == 2.1


def test_web_scenario_records_real_control_and_target_size():
    s = Session(scenario="web")
    s.phase = "ready"
    s.geometry = [1000, 800, 0, 0, 1]
    s.start_demo()
    assert s.expected == "overview"
    regions = {name: [i * 0.11, 0.1, 0.09, 0.05] for i, name in enumerate(s.targets)}
    s.set_regions(regions)
    s.ack(s.token, 0)
    for i in range(16):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    assert s.trials[0]["selected"] == "overview"
    assert s.trials[0]["target_size_px"] == [90, 40]
    assert s.trials[0]["scenario"] == "web"
    assert len(s.trial_order) == 12


def test_web_scenario_rejects_unregistered_control_regions():
    s = Session(scenario="web")
    with pytest.raises(ValueError):
        s.set_regions({"pretend": [0, 0, 0.1, 0.1]})
