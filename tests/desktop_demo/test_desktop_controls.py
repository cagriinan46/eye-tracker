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
