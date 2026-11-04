import numpy as np
import pytest

from experiments.desktop_demo.protocol import CALIBRATION_POINTS, SHAPES, Session
from eye_tracker.intent.region_magnet import RegionMagnet


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
    for i in range(25):
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
    s.magnet = RegionMagnet(pull_seconds=1e-6)  # These gap rules concern the dwell alone.
    s.start_demo()
    s.ack(s.token, 0)
    s.set_regions({key: [i * 0.25, 0, 0.24, 1] for i, key in enumerate(SHAPES)})
    for i in range(10):
        s.sample(1 + i * 0.1, None, [0.1, 0.5])
    s.sample(2, None, None)
    s.sample(2.1, None, [0.1, 0.5])
    # A short measurement gap holds 0.8 s of progress; its 0.2 s is not credited.
    assert not s.trials and abs(s.dwell.progress - 0.8 / 1.2) < 1e-9
    s.sample(2.2, None, None)
    s.sample(2.7, None, None)
    s.sample(2.75, None, [0.1, 0.5])
    assert not s.trials and s.dwell.progress == 0
    s.sample(2.85, None, [0.1, 0.5])
    s.pause(2.9)
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
    for i in range(25):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    assert s.trials[0]["selected"] == "overview"
    assert s.trials[0]["target_size_px"] == [90, 40]
    assert s.trials[0]["scenario"] == "web"
    assert len(s.trial_order) == 12


def test_web_scenario_rejects_unregistered_control_regions():
    s = Session(scenario="web")
    with pytest.raises(ValueError):
        s.set_regions({"pretend": [0, 0, 0.1, 0.1]})


def test_short_gaze_gaps_delay_but_do_not_change_selection():
    s = ready_session()
    s.magnet = RegionMagnet(pull_seconds=1e-6)  # These gap rules concern the dwell alone.
    s.start_demo()
    s.ack(s.token, 0)
    s.set_regions({key: [i * 0.25, 0, 0.24, 1] for i, key in enumerate(SHAPES)})
    t = 1.0
    for _ in range(3):
        for _ in range(4):
            s.sample(t, None, [0.1, 0.5])
            t += 0.125
        for _ in range(2):
            s.sample(t, None, None)
            t += 0.125
    assert not s.trials
    while not s.trials:
        s.sample(t, None, [0.1, 0.5])
        t += 0.125
    assert s.trials[0]["selected"] == SHAPES[0]
    # 1.2 s observed in-region time plus the uncredited gaps.
    assert s.trials[0]["elapsed_s"] > 2.2 + 0.7


def test_web_instructions_name_each_task_control_with_location():
    from experiments.desktop_demo.protocol import WEB_INSTRUCTIONS, WEB_ORDER

    labels = {
        "overview": "Genel bakış",
        "notes": "Notlar",
        "search": "Notlarda ara",
        "title": "Başlık",
        "reminder": "Hatırlatıcı ekle",
        "save": "Notu kaydet",
        "details": "Ayrıntı",
        "clear": "Temizle",
    }
    places = ("üst", "sol", "sağ", "alt")
    assert len(WEB_INSTRUCTIONS) == len(WEB_ORDER) == 12
    for target, text in zip(WEB_ORDER, WEB_INSTRUCTIONS, strict=True):
        assert "“" + labels[target] + "”" in text
        assert any(word in text.lower() for word in places)
        assert text.endswith("seç.")
        # Stays on one heading line at the 960 px minimum window width.
        assert len(text) <= 70


def test_snapshot_shows_instruction_only_for_active_web_task():
    s = Session(scenario="web")
    assert s.snapshot()["instruction"] is None
    s.phase = "ready"
    s.geometry = [1000, 800, 0, 0, 1]
    s.start_demo()
    assert "“Genel bakış”" in s.snapshot()["instruction"]
    shapes = ready_session()
    shapes.start_demo()
    assert shapes.snapshot()["instruction"] is None


def web_demo():
    s = Session(scenario="web")
    s.phase = "ready"
    s.geometry = [1000, 800, 0, 0, 1]
    s.start_demo()
    s.set_regions({name: [i * 0.11, 0.1, 0.09, 0.05] for i, name in enumerate(s.targets)})
    s.ack(s.token, 0)
    return s


def test_trial_error_averages_distance_to_requested_control_center():
    s = web_demo()
    s.sample(0.5, None, [0.9, 0.9])  # Cue time is not measured.
    s.sample(1.0, None, None)  # Missing measurement has no distance.
    for i in range(25):
        s.sample(1.05 + i * 0.1, None, [0.03, 0.12])
    trial = s.trials[0]
    assert trial["selected"] == "overview"
    assert trial["error_samples"] >= 20  # 0.8 s pull + 1.2 s dwell at 0.1 s spacing.
    # Center (0.045, 0.125) of a 1000x800 viewport: offsets 15 px and 4 px.
    assert trial["mean_error_px"] == pytest.approx((15**2 + 4**2) ** 0.5)


def test_trial_error_uses_requested_control_when_another_is_selected():
    s = web_demo()
    for i in range(25):
        s.sample(1 + i * 0.1, None, [0.155, 0.125])
    assert s.trials[0]["outcome"] == "incorrect"
    # Center of "notes" is 110 px right of the requested "overview" center.
    assert s.trials[0]["mean_error_px"] == pytest.approx(110)


def test_trial_error_starts_fresh_each_trial_and_is_empty_without_gaze():
    s = web_demo()
    for i in range(25):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    s.ack(s.token, 10)
    s.sample(25.1, None, None)
    assert s.trials[1]["outcome"] == "timeout"
    assert s.trials[1]["mean_error_px"] is None
    assert s.trials[1]["error_samples"] == 0


def test_selection_needs_settled_pull_and_then_the_full_dwell():
    s = web_demo()
    for i in range(19):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    assert not s.trials
    for i in range(19, 25):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    assert s.trials[0]["selected"] == "overview"


def test_passing_glance_attracts_the_cursor_but_cannot_select():
    s = web_demo()
    for i in range(7):
        s.sample(1 + i * 0.1, None, [0.03, 0.12])
    assert s.magnet.target == "overview"
    assert s.dwell.target is None and s.dwell.progress == 0
    s.sample(1.7, None, [0.5, 0.9])
    assert s.magnet.target is None
    for i in range(20):
        s.sample(1.8 + i * 0.1, None, [0.5, 0.9])
    assert not s.trials
