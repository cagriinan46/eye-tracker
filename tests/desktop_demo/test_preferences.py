import json

from experiments.desktop_demo.runtime import DesktopAPI


def test_appearance_survives_restart_without_camera_or_calibration(tmp_path):
    path = tmp_path / "settings.json"
    api = DesktopAPI(preferences_path=path)
    assert api.snapshot()["preferences"] == {
        "theme": "lavender",
        "reduced_motion": False,
        "word_suggestions": True,
        "keyboard_size": "medium",
        "wink_left": "left",
        "wink_right": "right",
        "smile": "left",
        "scroll_stop": "long_blink",
        "wink_sensitivity": "medium",
        "wink_right_min_ms": 250,
        "wink_left_min_ms": 550,
        "wink_max_ms": 1000,
        "long_blink_ms": 1000,
        "smile_hold_ms": 400,
    }
    assert api.command("preferences", {"theme": "sunflower", "reduced_motion": True})["ok"]
    other = DesktopAPI(preferences_path=path)
    assert other.snapshot()["preferences"] == {
        "theme": "sunflower",
        "reduced_motion": True,
        "word_suggestions": True,
        "keyboard_size": "medium",
        "wink_left": "left",
        "wink_right": "right",
        "smile": "left",
        "scroll_stop": "long_blink",
        "wink_sensitivity": "medium",
        "wink_right_min_ms": 250,
        "wink_left_min_ms": 550,
        "wink_max_ms": 1000,
        "long_blink_ms": 1000,
        "smile_hold_ms": 400,
    }
    assert other.snapshot()["camera"] == "off"
    assert not other.snapshot()["can_demo"]
    assert json.loads(path.read_text()) == other.snapshot()["preferences"]


def test_invalid_preferences_do_not_change_disk_or_session(tmp_path):
    api = DesktopAPI(preferences_path=tmp_path / "settings.json")
    for payload in ({"theme": "unknown"}, {"reduced_motion": "false"}, {"model": "mgaze"}):
        assert not api.command("preferences", payload)["ok"]
    assert not (tmp_path / "settings.json").exists()
    assert api.snapshot()["phase"] == "preparation"


def test_damaged_preferences_fall_back_safely(tmp_path):
    path = tmp_path / "settings.json"
    for value in ("broken", "null", "[]", '{"theme": "bad"}'):
        path.write_text(value)
        api = DesktopAPI(preferences_path=path)
        assert api.snapshot()["preferences"]["theme"] == "lavender"
        assert path.read_text() == value


def test_preferences_write_failure_keeps_previous_settings_and_calibration(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("occupied")
    api = DesktopAPI(preferences_path=blocker / "settings.json")
    api._session.phase = "ready"
    api._session.calibrated = True
    result = api.command("preferences", {"theme": "sage"})
    assert not result["ok"]
    assert api.snapshot()["preferences"]["theme"] == "lavender"
    assert api.snapshot()["phase"] == "ready"
    assert api.snapshot()["can_demo"]
