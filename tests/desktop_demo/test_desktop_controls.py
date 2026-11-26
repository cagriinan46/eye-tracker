from experiments.desktop_demo.confirmation import Confirmation
from experiments.desktop_demo.ring_magnet import RingMagnet
from experiments.desktop_demo.runtime import DesktopAPI
from experiments.unigaze.desktop_worker import EyeClosure
from eye_tracker.intent.targets import TargetRect


def test_desktop_and_repeat_calibration_share_the_ready_session(monkeypatch, tmp_path):
    monkeypatch.setattr("experiments.desktop_demo.runtime.sys.platform", "darwin")
    api = DesktopAPI(output=tmp_path)
    s = api._session
    geometry = [1200, 800, 0, 0, 2]
    api._camera = "ready"
    assert not api.command("desktop_start")["ok"]
    s.start_calibration(geometry)
    s.calibrated = True
    s.transition("ready")
    assert api.command("desktop_start")["ok"]
    assert api.desktop_sample()[0]
    api.command("focus", {"active": False})
    assert api.desktop_sample()[0]
    api.request_native_page("settings")
    assert api.snapshot()["native_page"] == "settings"
    assert api.desktop_sample()[0]
    api.request_native_page("calibration")
    assert not api.desktop_sample()[0]
    api.command("focus", {"active": True})
    assert api.command("calibrate", {"geometry": geometry})["ok"]
    assert s.phase == "calibration"
    assert not s.calibrated and not api.desktop_sample()[0]
    api.close()


def test_bilateral_closure_and_invalid_samples_are_distinct():
    eyes = EyeClosure(0.16)
    assert eyes.update([0.10, 0.10]) is None
    assert eyes.update([0.29, 0.30]) is False
    assert eyes.update([0.11, 0.12]) is True
    assert eyes.update([0.29, 0.12]) is None
    assert eyes.update(None) is None
    assert eyes.update([0.25, 0.27]) is False


def test_click_needs_two_complete_blinks_after_fixation():
    confirmation = Confirmation()
    for i in range(14):
        confirmation.update(i / 10, "target", False)
    assert confirmation.phase == "armed"
    for timestamp, closed in ((1.4, True), (1.5, False), (1.6, True)):
        assert confirmation.update(timestamp, "target", closed) == "armed"
    assert confirmation.update(1.7, "target", False) == "confirmed"


def test_magnet_locks_nearby_verified_target_and_releases():
    magnet = RingMagnet()
    near = TargetRect(90, 80, 24, 24)
    gaze = (56, 91)
    assert magnet.update(10, gaze, [("near", near, True)]) == gaze
    assert magnet.update(10.23, gaze, [("near", near, True)]) == near.center
    assert magnet.locked == near
    assert magnet.update(10.24, gaze, [("near", near, False)]) == gaze
    assert magnet.locked is None
    assert magnet.update(10.3, (30, 91), [("near", near, True)]) == (30, 91)
    assert magnet.status == "outside_ring"
    other = TargetRect(95, 80, 24, 24)
    assert magnet.update(10.4, gaze, [("near", near, True), ("other", other, True)]) == gaze
    assert magnet.status == "ambiguous"


def test_completed_trials_can_open_desktop_without_clearing_results(monkeypatch, tmp_path):
    monkeypatch.setattr("experiments.desktop_demo.runtime.sys.platform", "darwin")
    api = DesktopAPI(output=tmp_path)
    s = api._session
    api._camera = "ready"
    geometry = [1200, 800, 0, 0, 2]
    s.start_calibration(geometry)
    s.calibrated = True
    s.transition("ready")
    s.start_demo()
    for _ in range(12):
        s.finish_trial(s.expected, 2)
    assert s.phase == "results"
    assert api.command("desktop_start")["ok"]
    assert api.desktop_sample()[0]
    assert s.phase == "results" and len(s.trials) == 12
    assert s.geometry == geometry and s.calibrated
    api.close()


def test_home_after_partial_trial_can_open_desktop(monkeypatch, tmp_path):
    monkeypatch.setattr("experiments.desktop_demo.runtime.sys.platform", "darwin")
    api = DesktopAPI(output=tmp_path)
    s = api._session
    api._camera = "ready"
    geometry = [1200, 800, 0, 0, 2]
    s.start_calibration(geometry)
    s.calibrated = True
    s.transition("ready")
    assert api.command("demo")["ok"]
    s.finish_trial(s.expected, 2)
    assert api.command("home")["ok"]
    assert s.phase == "preparation"
    assert api.command("desktop_start")["ok"]
    assert api.desktop_sample()[0] and s.geometry == geometry
    api.close()


def test_desktop_fixation_holds_against_noise_and_allows_a_deliberate_shift():
    from experiments.desktop_demo.desktop_gaze_filter import DesktopGazeFilter

    gaze = DesktopGazeFilter()
    center = (400, 300)
    assert gaze.update(1.0, center) == center
    assert gaze.update(1.1, (411, 293)) == center
    assert gaze.update(1.2, (620, 610)) == center
    assert gaze.update(1.3, (403, 309)) == center
    assert gaze.update(1.4, (550, 400)) == center
    assert gaze.update(1.5, (552, 401)) == (550, 400)
    assert gaze.update(1.5, (100, 100)) == (550, 400)
    assert gaze.update(2.0, center) == center


def test_held_direction_glides_and_stops_when_gaze_leaves():
    from experiments.desktop_demo.desktop_gaze_filter import HeldDirection

    direction = HeldDirection()
    steps = [direction.step(i / 60, "right") for i in range(121)]
    assert not any(steps[:18])
    assert 100 < sum(steps) < 240
    assert 0 < steps[30] < steps[-1] < 3
    assert direction.step(2.01, None) == 0
    assert direction.step(2.02, "left") == 0


def test_gaze_check_separates_bias_and_tremor():
    from experiments.desktop_demo.protocol import fixation_errors

    assert fixation_errors([(18, 10), (22, 10)]) == {
        "bias_px": [20, 10],
        "jitter_rms_px": 2.0,
    }


def test_two_fast_closures_survive_brief_uncertain_frames():
    c = Confirmation()
    for i in range(14):
        c.update(i / 10, "target", False)
    assert c.phase == "armed"
    for stamp, closed in (
        (1.36, True),
        (1.39, None),
        (1.41, False),
        (1.49, False),
        (1.56, True),
    ):
        assert c.update(stamp, "target", closed) == "armed"
    assert c.update(1.60, "target", False) == "confirmed"


def test_lost_face_does_not_confirm_or_bridge_blinks():
    c = Confirmation()
    for i in range(14):
        c.update(i / 10, "target", False)
    assert c.update(1.39, "target", True) == "armed"
    assert c.update(1.48, "target", False) == "armed"
    assert c.update(1.72, "target", None) == "idle"
    for stamp, closed in ((1.75, True), (1.81, False)):
        assert c.update(stamp, "target", closed) != "confirmed"
