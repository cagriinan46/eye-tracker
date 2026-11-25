import time
from unittest.mock import Mock

import pytest

from experiments.desktop_demo.runtime import DesktopAPI


def test_desktop_click_starts_directly_after_calibration(tmp_path):
    api = DesktopAPI(output=tmp_path)
    api._desktop_supported = True
    api._desktop_permission = lambda: True
    assert not api.command("desktop_click")["ok"]
    s = api._session
    s.calibrated = True
    s.transition("ready")
    api._camera = "ready"
    assert api.command("desktop_click")["ok"]
    api.command("focus", {"active": False})
    s.last_point = [0.3, 0.4]
    api._tracking = True
    api._pointer_captured = time.monotonic()
    assert api._desktop_frame()[3] == s.last_point
    api._pointer_captured -= 1
    assert api._desktop_frame()[3] is None
    api.command("pause")
    assert s.phase == "ready" and s.calibrated and not s.trials and api._desktop_frame() is None
    api.close()


def test_native_click_once_per_visit(monkeypatch):
    mac = pytest.importorskip("experiments.desktop_demo.macos_desktop_dwell")
    rect = mac.UI.NSMakeRect(0, 0, 400, 400)
    window = Mock()
    window.native.convertRectToScreen_.return_value = rect
    api = Mock()
    controller = mac.DesktopDwell(window, api, None)
    controller.ring = Mock()
    monkeypatch.setattr(mac.AX, "AXIsProcessTrusted", lambda: True)
    monkeypatch.setattr(controller, "escape_down", lambda: False)
    key_rect = mac.UI.NSMakeRect(0, 0, 200, 400)
    monkeypatch.setattr(controller, "hit", lambda p, _: ("key", key_rect) if p[0] < 200 else None)
    post = Mock()
    monkeypatch.setattr(mac.Quartz, "CGEventPost", post)
    clock = [0.0]
    monkeypatch.setattr(mac.time, "monotonic", lambda: clock[0])

    def sample(mode, token, point):
        clock[0] += 0.1
        frame = (mode, token, clock[0], point)
        api._desktop_frame.return_value = frame
        controller.observe(frame)

    for _ in range(12):
        sample("desktop_click", 2, [0.1, 0.2])
    post.assert_not_called()
    sample("desktop_click", 2, [0.1, 0.2])
    assert post.call_count == 2
    for _ in range(22):
        sample("desktop_click", 2, [0.1, 0.2])
    assert post.call_count == 2
    for _ in range(12):
        sample("desktop_click", 2, None)
    for _ in range(24):
        sample("desktop_click", 2, [0.1, 0.2])
    assert post.call_count == 2
    sample("desktop_click", 2, [0.8, 0.2])
    for _ in range(24):
        sample("desktop_click", 2, [0.1, 0.2])
    assert post.call_count == 4
