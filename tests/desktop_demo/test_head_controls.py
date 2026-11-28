"""Issue #160 follow-up: winks, long blink, head scroll, recentre button, wink settings."""

from types import SimpleNamespace

import pytest

from experiments.desktop_demo import eye_gestures, preferences
from experiments.desktop_demo.eye_gestures import EyeGestures, scroll_step
from experiments.desktop_demo.runtime import DesktopAPI


def run(gestures, frames, start=0.0, step=1 / 30):
    events = []
    for i, (left, right) in enumerate(frames):
        events += gestures.update(start + i * step, left, right)
    return events


OPEN, SHUT, SQUINT = 0.05, 0.8, 0.45


def test_right_and_left_winks_fire_on_release() -> None:
    g = EyeGestures()
    frames = [(OPEN, OPEN)] * 3 + [(OPEN, SHUT)] * 6 + [(OPEN, OPEN)] * 2
    assert run(g, frames) == ["wink_right"]
    g = EyeGestures()
    frames = [(OPEN, OPEN)] * 3 + [(SHUT, OPEN)] * 6 + [(OPEN, OPEN)] * 2
    assert run(g, frames) == ["wink_left"]


def test_pending_is_true_while_one_eye_closes() -> None:
    g = EyeGestures()
    g.update(0.0, OPEN, OPEN)
    assert not g.pending
    g.update(0.033, OPEN, SHUT)
    assert g.pending
    g.update(0.3, OPEN, OPEN)
    assert not g.pending


def test_natural_blink_is_never_a_wink_and_long_blink_fires_once() -> None:
    g = EyeGestures()
    # Brief bilateral blink, with one eye closing a frame earlier.
    frames = [(OPEN, OPEN), (OPEN, SHUT), (SHUT, SHUT), (SHUT, SHUT), (OPEN, OPEN)]
    assert run(g, frames) == []
    g = EyeGestures()
    frames = [(OPEN, OPEN)] + [(SHUT, SHUT)] * 15 + [(OPEN, OPEN)]
    assert run(g, frames) == ["long_blink"]


def test_too_short_too_long_or_squinting_winks_are_ignored() -> None:
    g = EyeGestures()
    assert run(g, [(OPEN, OPEN), (OPEN, SHUT), (OPEN, SHUT), (OPEN, OPEN)]) == []
    g = EyeGestures()
    assert run(g, [(OPEN, OPEN)] + [(OPEN, SHUT)] * 32 + [(OPEN, OPEN)]) == []
    g = EyeGestures()
    frames = [(OPEN, OPEN)] + [(OPEN, SHUT)] * 3 + [(SQUINT, SHUT)] * 3 + [(OPEN, OPEN)]
    assert run(g, frames) == []


def test_refractory_duplicates_and_gaps() -> None:
    g = EyeGestures()
    wink = [(OPEN, SHUT)] * 6 + [(OPEN, OPEN)]
    assert run(g, wink, start=0.0) == ["wink_right"]
    assert run(g, wink, start=0.24) == []  # next release too soon after the first
    assert run(g, wink, start=1.0) == ["wink_right"]
    g = EyeGestures()
    g.update(0.0, OPEN, OPEN)
    g.update(0.033, OPEN, SHUT)
    assert g.update(0.033, OPEN, SHUT) == [] and g.pending  # repeated sample ignored
    g.update(0.6, OPEN, OPEN)  # long gap: reset, no event
    assert not g.pending
    assert g.update(0.65, None, OPEN) == []


def test_feed_maps_blendshapes_to_user_eyes(monkeypatch) -> None:
    samples = [(0.0, OPEN, OPEN)] + [(0.033 * i, OPEN, SHUT) for i in range(1, 7)]
    samples.append((0.3, OPEN, OPEN))
    assert EyeGestures().feed(samples) == ["wink_right"]
    monkeypatch.setattr(eye_gestures, "BLENDSHAPE_LEFT_IS_USER_LEFT", False)
    assert EyeGestures().feed(samples) == ["wink_left"]
    assert EyeGestures().feed(None) == []


def test_scroll_step_dead_zone_direction_and_limit() -> None:
    assert scroll_step(0) == 0 and scroll_step(39) == 0 and scroll_step(-40) == 0
    assert scroll_step(80) == 10 and scroll_step(-80) == -10
    assert scroll_step(1000) == 60 and scroll_step(-1000) == -60


def test_wink_preferences_default_validate_and_migrate(tmp_path) -> None:
    assert preferences.DEFAULTS["wink_left"] == "left"
    assert preferences.DEFAULTS["wink_right"] == "right"
    assert preferences.validated({"wink_right": "off"})["wink_right"] == "off"
    with pytest.raises(ValueError, match="Göz kırpma"):
        preferences.validated({"wink_left": "double"})
    old = tmp_path / "prefs.json"
    old.write_text('{"theme": "dark", "keyboard_size": "large"}')
    loaded = preferences.load(old)
    assert (loaded["theme"], loaded["wink_left"], loaded["wink_right"]) == ("dark", "left", "right")


def test_runtime_wink_actions_follow_saved_preferences(tmp_path) -> None:
    api = DesktopAPI(model_name="head", output=tmp_path, preferences_path=tmp_path / "p.json")
    assert api.wink_actions() == {"left": "left", "right": "right"}
    assert api.command("preferences", {"wink_right": "left", "wink_left": "off"})["ok"]
    assert api.wink_actions() == {"left": "off", "right": "left"}
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
