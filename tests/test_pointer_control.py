from unittest.mock import Mock

import pytest

from eye_tracker.actions.pointer import PointerController
from eye_tracker.intent.dwell import DwellClick
from eye_tracker.platform_adapters.pyautogui_pointer import PyAutoGUIPointer


def test_dwell_clicks_once_until_leaving_anchor_circle():
    dwell = DwellClick()
    assert not dwell.update(0, (100, 100))
    for t in (0.3, 0.6, 0.9, 1.2):
        assert not dwell.update(t, (110, 100))
    assert dwell.update(1.5, (120, 100))
    assert not dwell.update(1.8, (100, 100))
    assert not dwell.update(2, None)
    assert not dwell.update(2.2, (100, 100))
    assert not dwell.update(2.4, (200, 100))
    for t in (2.7, 3, 3.3, 3.6):
        assert not dwell.update(t, (200, 100))
    assert dwell.update(4, (200, 100))


def test_gap_loss_and_motion_restart_countdown():
    for point in (None, (131, 100)):
        dwell = DwellClick()
        dwell.update(0, (100, 100))
        dwell.update(0.4, point)
        assert not dwell.update(0.6, (100, 100))
        assert not dwell.update(1.7, (100, 100))
    dwell = DwellClick()
    dwell.update(0, (100, 100))
    assert not dwell.update(10, (100, 100))


def test_adapter_and_controller_use_region_pixels_and_stop_on_escape():
    api = Mock(FAILSAFE=True, PAUSE=0.1)
    api.size.return_value = (1512, 982)
    escape = Mock(return_value=False)
    backend = PyAutoGUIPointer(api=api, escape_pressed=escape)
    controller = PointerController(backend, (0, 33, 1512, 949))
    assert api.FAILSAFE is False
    controller.update(0, (0.5, 0.5))
    api.moveTo.assert_called_with(756, 508, duration=0)
    for t in (0.3, 0.6, 0.9, 1.2, 1.5):
        controller.update(t, (0.5, 0.5))
    api.click.assert_called_once_with(button="left")
    count = api.moveTo.call_count
    controller.update(1.6, None)
    controller.update(1.7, (-0.1, 0.5))
    assert api.moveTo.call_count == count
    escape.return_value = True
    with pytest.raises(InterruptedError):
        controller.update(1.8, (0.5, 0.5))
    assert api.moveTo.call_count == count
    backend.close()
    assert api.FAILSAFE is True
    assert api.PAUSE == 0.1
