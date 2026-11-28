"""Issue #160 follow-up: winks, long blink, head scroll, recentre button, wink settings."""

from types import SimpleNamespace

import pytest

from experiments.desktop_demo import eye_gestures, preferences
from experiments.desktop_demo.eye_gestures import EyeGestures, scroll_step
from experiments.desktop_demo.runtime import DesktopAPI


def run(gestures, frames, start=0.0, step=1 / 30):
    events = []
    for i, frame in enumerate(frames):
        events += gestures.update(start + i * step, *frame)
    return events


OPEN = (0.10, 0.12)  # user (left, right) at rest
BLINK = (0.70, 0.66)  # natural blink: both closed, slight left bias
RIGHT = (0.58, 0.72)  # this user's right wink also half-closes the left eye
LEFT = (0.68, 0.57)


def frames(closed, n, rest=3):
    return [OPEN] * rest + [closed] * n + [OPEN] * rest


def test_right_wink_is_classified_by_asymmetry_even_with_other_eye_half_closed() -> None:
    assert run(EyeGestures(), frames(RIGHT, 14)) == ["wink_right"]  # ~0.47 s
    assert run(EyeGestures(), frames(RIGHT, 5)) == []  # 0.17 s: too short


def test_left_wink_needs_to_be_longer_than_a_natural_blink() -> None:
    assert run(EyeGestures(), frames(LEFT, 22)) == ["wink_left"]  # ~0.73 s
    assert run(EyeGestures(), frames(LEFT, 13)) == []  # ~0.43 s: like a blink


def test_natural_blinks_never_click_and_long_closure_fires_once() -> None:
    assert run(EyeGestures(), frames(BLINK, 12)) == []  # 0.40 s
    assert run(EyeGestures(), frames(BLINK, 45)) == ["long_blink"]  # 1.5 s, no wink after
    # A 1.33 s right-dominant closure is a long closure, never a click.
    assert run(EyeGestures(), frames(RIGHT, 40)) == ["long_blink"]


def test_pending_tracks_an_ongoing_closure() -> None:
    g = EyeGestures()
    g.update(0.0, *OPEN)
    assert not g.pending
    g.update(0.033, *RIGHT)
    assert g.pending
    g.update(0.066, 0.42, 0.41)  # hysteresis keeps the episode open
    assert g.pending
    g.update(0.1, *OPEN)
    assert not g.pending


def test_smile_fires_once_per_smile_but_not_during_a_wink() -> None:
    g = EyeGestures()
    smile = [(0.1, 0.1, 0.8)] * 20
    neutral = [(0.1, 0.1, 0.02)] * 5
    assert run(g, neutral + smile + neutral + smile) == ["smile", "smile"]
    g = EyeGestures()
    grimace = [(0.68, 0.57, 0.8)] * 22  # left wink with a squint
    assert run(g, [(0.1, 0.1, 0.0)] * 3 + grimace + [(0.1, 0.1, 0.0)] * 3) == ["wink_left"]
    assert run(EyeGestures(), [(0.1, 0.1, 0.8)] * 10) == []  # 0.3 s: too short


def test_refractory_duplicates_and_gaps() -> None:
    g = EyeGestures()
    assert run(g, frames(RIGHT, 14), start=0.0) == ["wink_right"]
    assert run(g, frames(RIGHT, 14), start=3.0) == ["wink_right"]
    events = []
    g._emit(events, "smile", g.last_event + 0.2)  # inside the refractory period
    assert events == []
    g = EyeGestures()
    g.update(0.0, *OPEN)
    g.update(0.033, *RIGHT)
    assert g.update(0.033, *RIGHT) == [] and g.pending  # repeated sample ignored
    g.update(0.6, *OPEN)  # long gap: reset, no event
    assert not g.pending
    assert g.update(0.65, None, 0.1) == []


def test_feed_maps_blendshapes_to_user_eyes(monkeypatch) -> None:
    samples = [(i / 30, *pair) for i, pair in enumerate(frames(RIGHT, 14))]
    assert EyeGestures().feed(samples) == ["wink_right"]
    monkeypatch.setattr(eye_gestures, "BLENDSHAPE_LEFT_IS_USER_LEFT", False)
    assert EyeGestures().feed(samples) == []  # swapped: a weak "left" closure
    assert EyeGestures().feed(None) == []


def test_thresholds_are_the_recorded_values() -> None:
    g = eye_gestures
    assert (g.LONG_BLINK_SECONDS, g.LEFT_WINK_MIN_SECONDS, g.RIGHT_WINK_MIN_SECONDS) == (
        1.0,
        0.55,
        0.25,
    )
    assert (g.RIGHT_ASYMMETRY, g.LEFT_ASYMMETRY, g.SMILE_ON, g.SMILE_HOLD_SECONDS) == (
        0.07,
        -0.06,
        0.5,
        0.4,
    )


def test_scroll_step_dead_zone_direction_and_limit() -> None:
    assert scroll_step(0) == 0 and scroll_step(39) == 0 and scroll_step(-40) == 0
    assert scroll_step(80) == 10 and scroll_step(-80) == -10
    assert scroll_step(1000) == 60 and scroll_step(-1000) == -60


def test_wink_preferences_default_validate_and_migrate(tmp_path) -> None:
    assert preferences.DEFAULTS["wink_left"] == "left"
    assert preferences.DEFAULTS["wink_right"] == "right"
    assert preferences.validated({"wink_right": "off"})["wink_right"] == "off"
    assert preferences.DEFAULTS["smile"] == "left"
    with pytest.raises(ValueError, match="Gülümseme"):
        preferences.validated({"smile": "both"})
    with pytest.raises(ValueError, match="Göz kırpma"):
        preferences.validated({"wink_left": "double"})
    old = tmp_path / "prefs.json"
    old.write_text('{"theme": "dark", "keyboard_size": "large"}')
    loaded = preferences.load(old)
    assert (loaded["theme"], loaded["wink_left"], loaded["wink_right"]) == ("dark", "left", "right")


def test_runtime_wink_actions_follow_saved_preferences(tmp_path) -> None:
    api = DesktopAPI(model_name="head", output=tmp_path, preferences_path=tmp_path / "p.json")
    assert api.wink_actions() == {"left": "left", "right": "right", "smile": "left"}
    assert api.command("preferences", {"wink_right": "left", "wink_left": "off"})["ok"]
    assert api.wink_actions() == {"left": "off", "right": "left", "smile": "left"}
    assert api.command("preferences", {"wink_left": "middle"})["ok"] is False
    api.close()


def _toolbar():
    toolbar_module = pytest.importorskip("experiments.desktop_demo.macos_toolbar")
    t = toolbar_module.Toolbar.__new__(toolbar_module.Toolbar)
    t.head_scroll = t.anchor = t.recentre_at = t.reveal_after = None
    t.active_mode = t.aim_since = t.front_pid = None
    t.last_action_stamp = None
    t.keyboard_owned = t.on_rail = t.visible = t.tools_ready = t.paused = False
    t.center_left = False
    t.confirm = SimpleNamespace(phase="idle", reset=lambda: None)
    t.scrolling = t.direction = SimpleNamespace(reset=lambda: None)
    t.mark = lambda *a: None
    t.hints = []
    t.show_hint = t.hints.append
    t.hide = lambda *a: None
    return toolbar_module, t


def test_head_scroll_follows_tilt_and_long_blink_stops() -> None:
    _, t = _toolbar()
    scrolled = []
    t.scroll = lambda direction, amount: scrolled.append((direction, amount))
    t.head_scroll, t.anchor, t.active_mode = 500.0, (300, 500), "scroll"
    assert t.desktop_gaze(1.0, (300, 580), False, True, None) is True
    assert t.desktop_gaze(1.0, (300, 580), False, True, None) is True  # same frame: once
    t.desktop_gaze(1.1, (300, 420), False, True, None)
    t.desktop_gaze(1.2, (300, 520), False, True, None)  # inside the dead zone
    t.desktop_gaze(1.3, (300, 900), True, True, None)  # eyes closed: no scroll
    assert scrolled == [("down", 10), ("up", 10)]
    assert not t.pointer_free
    assert t.stop_head_scroll() and t.head_scroll is None and t.active_mode is None
    assert t.hints[-1] == "Kaydırma durdu."
    assert not t.stop_head_scroll()


def test_recentre_button_waits_then_recentres_and_click_reveals_keyboard() -> None:
    module, t = _toolbar()
    calls = []
    t.recentre = lambda: calls.append("recentre") or True
    t.cancel_mode = lambda: None
    t.command("recentre")
    assert t.recentre_at is not None and calls == []
    t.pending_actions(t.recentre_at - 0.1)
    assert calls == []
    t.pending_actions(t.recentre_at + 0.01)
    assert calls == ["recentre"] and t.hints[-1] == "Kafa ortalandı."
    revealed = []
    t.keyboard = SimpleNamespace(target=None, reveal=lambda: revealed.append(1) or True)
    t.reveal_after = 5.0
    t.pending_actions(4.9)
    assert revealed == []
    t.pending_actions(5.0)
    assert revealed == [1] and t.reveal_after is None
    assert module.RECENTRE in module.COMMANDS + (module.RECENTRE,)
    assert module.RECENTRE not in module.COMMANDS


def test_pointer_free_over_keyboard_rail_and_pages_but_not_when_armed() -> None:
    _, t = _toolbar()
    assert not t.pointer_free
    t.keyboard_owned = True
    assert t.pointer_free
    t.confirm.phase = "armed"
    assert not t.pointer_free
    t.confirm.phase, t.keyboard_owned, t.visible = "idle", False, True
    assert t.pointer_free
    t.tools_ready = True
    assert not t.pointer_free


def test_runtime_starts_app_dictation_and_inserts_the_result(tmp_path) -> None:
    from experiments.desktop_demo.keyboard import Keyboard

    api = DesktopAPI(model_name="head", output=tmp_path, preferences_path=tmp_path / "p.json")
    started = []

    class FakeDictation:
        def start(self, target):
            started.append(target)
            return len(started) == 1

        def close(self):
            pass

    api._dictation = FakeDictation()
    keyboard = Keyboard()
    api._poll_app_dictation(keyboard)
    assert started == [] and keyboard.dictation_status is None
    keyboard.press("dictation", 1.0, "manual")
    api._poll_app_dictation(keyboard)
    assert started == ["app"] and keyboard.dictation_status == "listening"
    keyboard.press("dictation", 2.0, "manual")  # second press stops recording
    api._poll_app_dictation(keyboard)
    assert keyboard.dictation_status == "processing"
    api._dictation_results.put(("app", "merhaba", None))
    api._poll_app_dictation(keyboard)
    assert keyboard.text == "merhaba" and keyboard.dictation_status is None
    api._dictation_results.put(("app", None, "Mikrofon açılamadı."))
    api._poll_app_dictation(keyboard)
    assert keyboard.dictation_error == "Mikrofon açılamadı."
    api.close()


def test_scroll_stop_preference_and_desktop_routing(tmp_path, monkeypatch) -> None:
    assert preferences.validated({"scroll_stop": "smile"})["scroll_stop"] == "smile"
    with pytest.raises(ValueError, match="kaydırma"):
        preferences.validated({"scroll_stop": "nod"})
    api = DesktopAPI(model_name="head", output=tmp_path, preferences_path=tmp_path / "p.json")
    assert api.scroll_stop() == "long_blink"
    assert api.command("preferences", {"scroll_stop": "wink_right"})["ok"]
    assert api.scroll_stop() == "wink_right"
    api.close()

    desktop_module = pytest.importorskip("experiments.desktop_demo.macos_desktop")
    desktop = desktop_module.MacOSDesktop.__new__(desktop_module.MacOSDesktop)
    clicks, stops = [], []
    desktop.api = SimpleNamespace(
        wink_actions=lambda: {"left": "left", "right": "left", "smile": "right"},
        scroll_stop=lambda: "smile",
    )
    desktop.toolbar = SimpleNamespace(
        head_scroll=500.0,
        paused=False,
        stop_head_scroll=lambda: stops.append(1),
        click=lambda side, point: clicks.append(side),
        show_hint=lambda text: None,
    )
    desktop.wink_point = None
    desktop.mouse_location = lambda: (10.0, 20.0)
    events = iter([["wink_right", "long_blink"], ["smile"], ["wink_right"]])
    desktop.gestures = SimpleNamespace(pending=False, feed=lambda samples: next(events))
    desktop.eye_gestures([])  # scrolling: no clicks, long blink is not the stop gesture
    assert clicks == [] and stops == []
    desktop.eye_gestures([])  # the chosen stop gesture
    assert stops == [1] and clicks == []
    desktop.toolbar.head_scroll = None
    desktop.eye_gestures([])  # not scrolling: the wink clicks again
    assert clicks == ["left"]


def test_chromium_browsers_are_asked_once_per_process(monkeypatch) -> None:
    keyboard_module = pytest.importorskip("experiments.desktop_demo.macos_keyboard")
    calls = []
    monkeypatch.setattr(
        keyboard_module.AX, "AXUIElementCreateApplication", lambda pid: ("app", pid)
    )
    monkeypatch.setattr(
        keyboard_module.AX,
        "AXUIElementSetAttributeValue",
        lambda element, name, value: calls.append((element, name, value)) or -25208,
    )

    def app(bundle, pid):
        return SimpleNamespace(bundleIdentifier=lambda: bundle, processIdentifier=lambda: pid)

    web = keyboard_module.WebAccessibility()
    assert keyboard_module.needs_web_accessibility("com.brave.Browser")
    assert not keyboard_module.needs_web_accessibility("com.apple.Safari")
    assert web.update(app("com.brave.Browser", 41))
    assert not web.update(app("com.brave.Browser", 41))
    assert not web.update(app("com.apple.Terminal", 7)) and not web.update(None)
    assert calls == [(("app", 41), "AXEnhancedUserInterface", True)]
