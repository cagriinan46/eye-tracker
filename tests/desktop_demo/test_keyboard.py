"""Synthetic keyboard checks; no camera, model or human typing result."""

import json

import numpy as np
import pytest

from experiments.desktop_demo.keyboard import (
    KEY_IDS,
    LETTER_ROWS,
    SYMBOL_ROWS,
    WORDS_PATH,
    Keyboard,
    Suggester,
    turkish_lower,
    turkish_upper,
)
from experiments.desktop_demo.protocol import Session
from experiments.desktop_demo.runtime import DesktopAPI

WORDS = [("merhaba", 50), ("mesaj", 30), ("meyve", 20), ("merak", 40), ("ışık", 9), ("bir", 99)]


def key_for(keyboard, character):
    for row, letters in enumerate(keyboard.rows):
        if character in letters:
            return f"r{row}c{letters.index(character)}"
    raise AssertionError(character)


def type_text(keyboard, text, now=0.0):
    for character in text:
        if character == " ":
            assert keyboard.press("space", now)
            continue
        if character == ".":
            assert keyboard.press("period", now)
            continue
        if not any(character in row for row in keyboard.rows):
            if any(
                turkish_lower(character) in r or turkish_upper(character) in r
                for r in keyboard.rows
            ):
                assert keyboard.press("shift", now)
            else:
                assert keyboard.press("page", now)
        assert keyboard.press(key_for(keyboard, character), now)
        now += 1.0
    return now


def test_layout_is_turkish_q_with_q_w_x_on_the_first_page():
    letters = "".join(LETTER_ROWS)
    assert sorted(letters) == sorted("abcçdefgğhıijklmnoöprsştuüvyzqwx") and len(letters) == 32
    assert LETTER_ROWS[0].startswith("qwerty") and LETTER_ROWS[1].startswith("asdf")
    assert [len(row) for row in LETTER_ROWS] == [12, 11, 9]
    assert [len(row) for row in SYMBOL_ROWS] == [12, 11, 9]
    assert set("0123456789") <= set("".join(SYMBOL_ROWS))
    assert len(KEY_IDS) == 32 + 4 + 6


def test_turkish_case_mapping_keeps_dotted_and_dotless_i_apart():
    assert turkish_upper("ıi") == "Iİ" and turkish_lower("Iİ") == "ıi"
    keyboard = Keyboard()
    assert keyboard.shift and "İ" in keyboard.rows[1] and "I" in keyboard.rows[0]
    type_text(keyboard, "Işık İyi")
    assert keyboard.text == "Işık İyi"


def test_shift_applies_to_one_letter_and_returns_after_a_sentence():
    keyboard = Keyboard()
    type_text(keyboard, "Evet. Peki")
    assert keyboard.text == "Evet. Peki" and not keyboard.shift
    keyboard.press("backspace", 0)
    assert keyboard.text == "Evet. Pek" and keyboard.counts["backspace"] == 1


def test_first_page_types_q_w_x_and_symbol_page_types_digits():
    keyboard = Keyboard()
    type_text(keyboard, "Qwx")
    assert keyboard.text == "Qwx" and keyboard.page == "letters"
    type_text(keyboard, "2")
    assert keyboard.text == "Qwx2" and keyboard.page == "symbols"
    assert keyboard.press("page", 0) and keyboard.page == "letters"
    assert not keyboard.press("r2c9", 0) and not keyboard.press("unknown", 0)


def test_delete_word_removes_the_last_word_and_its_trailing_space():
    keyboard = Keyboard()
    type_text(keyboard, "Bir iki ")
    keyboard.press("delete_word", 0)
    assert keyboard.text == "Bir "
    keyboard.press("delete_word", 0)
    keyboard.press("delete_word", 0)
    assert keyboard.text == "" and keyboard.shift


def test_suggestions_rank_by_frequency_and_follow_the_typed_capital():
    suggester = Suggester(WORDS)
    assert suggester.suggest("me") == ["merhaba", "merak", "mesaj", "meyve"]
    assert suggester.suggest("I") == ["ışık"] and suggester.suggest("zz") == []
    assert suggester.suggest("bir") == []  # A finished word is not offered again.
    keyboard = Keyboard(suggester)
    assert keyboard.suggestions[0] == "Bir"  # Empty word: common words, capitalized.
    type_text(keyboard, "Me")
    assert keyboard.suggestions == ["Merhaba", "Merak", "Mesaj", "Meyve"]
    assert keyboard.press("sug0", 5)
    assert keyboard.text == "Merhaba " and keyboard.counts["suggestion"] == 1
    keyboard.press("period", 6)
    assert keyboard.text == "Merhaba."  # The automatic space yields to punctuation.


def test_suggestions_can_be_switched_off_and_empty_slots_do_nothing():
    keyboard = Keyboard(Suggester(WORDS))
    type_text(keyboard, "Iş")
    assert keyboard.suggestions == ["Işık"] and not keyboard.press("sug1", 0)
    assert not keyboard.press("suggest_toggle", 0)  # Only the settings page switches it.
    keyboard.suggestions_on = False
    assert keyboard.suggestions == [] and not keyboard.press("sug0", 0)
    assert keyboard.snapshot()["suggestions"] == ["", "", "", ""]
    assert keyboard.text == "Iş"


def test_bundled_word_list_loads_and_completes_common_words():
    suggester = Suggester.from_file(WORDS_PATH)
    assert len(suggester.words) > 15000
    assert suggester.suggest("")[0] == "bir"
    assert len(suggester.suggest("gü")) == 4 and all(
        w.startswith("gü") for w in suggester.suggest("gü")
    )


def test_stats_hold_counts_and_timing_but_never_the_text():
    keyboard = Keyboard(target="Ev.")
    assert keyboard.stats()["words_per_minute"] is None
    type_text(keyboard, "Ev.", now=10.0)
    stats = keyboard.stats()
    assert stats["target_completed_s"] == pytest.approx(2.0) and stats["characters"] == 3
    assert stats["words_per_minute"] == pytest.approx(3 / 5 / (2 / 60))
    assert "Ev." not in json.dumps(stats) and "text" not in stats
    keyboard.press("space", 30.0)
    assert keyboard.stats()["target_completed_s"] == pytest.approx(2.0)


def keyboard_session(calibrated=True):
    session = Session(model_name="unigaze")
    if calibrated:
        session.geometry = [1000, 800, 0, 0, 1]
        session.calibrated = True
    session.start_keyboard(Suggester(WORDS))
    session.set_regions({"r0c0": [0.0, 0.5, 0.1, 0.1], "r0c1": [0.11, 0.5, 0.1, 0.1]})
    session.ack(session.token, 0)
    return session


def look(session, point, start, seconds, step=0.1):
    for now in np.arange(start, start + seconds + 1e-9, step):
        session.sample(float(now), [0.0, 0.0], point)
    return start + seconds


def test_gaze_types_a_key_only_after_pull_and_dwell_and_repeats_need_a_new_dwell():
    session = keyboard_session()
    now = look(session, [0.05, 0.55], 0.1, 0.9)
    assert session.keyboard.text == ""  # 0.3 s pull + 0.8 s dwell not reached.
    now = look(session, [0.05, 0.55], now + 0.1, 0.4)
    assert session.keyboard.text == "Q" and session.keyboard.counts["gaze"] == 1
    look(session, [0.05, 0.55], now + 0.1, 0.6)
    assert session.keyboard.text == "Q"
    look(session, [0.05, 0.55], now + 0.8, 0.8)
    assert session.keyboard.text == "Qq"
    assert session.snapshot()["keyboard"]["text"] == "Qq"


def test_glancing_between_keys_or_pausing_never_types():
    session = keyboard_session()
    now = 0.1
    for _ in range(4):
        now = look(session, [0.05, 0.55], now + 0.1, 0.5)
        now = look(session, [0.16, 0.55], now + 0.1, 0.5)
    assert session.keyboard.text == ""
    look(session, [0.05, 0.55], now + 0.1, 0.9)
    session.pause(now + 1.1)
    look(session, [0.05, 0.55], now + 1.2, 2.0)
    assert session.keyboard.text == "" and session.snapshot()["paused"]


def test_uncalibrated_keyboard_ignores_gaze_but_accepts_manual_keys():
    session = keyboard_session(calibrated=False)
    look(session, [0.05, 0.55], 0.1, 3.0)
    assert session.keyboard.text == ""
    assert session.press_key("r0c0", 4.0, "manual")
    assert session.keyboard.text == "Q" and session.keyboard.counts == dict(
        gaze=0, manual=1, backspace=0, delete_word=0, suggestion=0
    )


def test_keyboard_regions_must_be_known_keys_inside_the_viewport():
    session = keyboard_session()
    with pytest.raises(ValueError):
        session.set_regions({"save": [0, 0, 0.1, 0.1]})
    with pytest.raises(ValueError):
        session.set_regions({"r0c0": [0.95, 0, 0.1, 0.1]})
    with pytest.raises(ValueError):
        session.set_regions({})


def test_bridge_opens_keyboard_without_camera_and_records_no_text(tmp_path):
    api = DesktopAPI(model_name="mgaze", output=tmp_path, preferences_path=tmp_path / "p.json")
    assert not api.command("key", {"key": "r0c0"})["ok"]
    assert api.command("keyboard")["ok"]
    state = api.snapshot()
    assert state["phase"] == "keyboard" and state["keyboard"]["suggestions"][0] == "Bir"
    assert api.command("key", {"key": "r0c0"})["ok"] and api.command("key", {"key": "nope"})["ok"]
    assert api.snapshot()["keyboard"]["text"] == "Q"
    assert api.command("home")["ok"] and api.snapshot()["keyboard"] is None
    assert api.command("keyboard")["ok"] and api.snapshot()["keyboard"]["text"] == ""
    api.close()
    assert not list(tmp_path.glob("desktop-gaze-*"))


def test_session_record_keeps_keyboard_counts_only(tmp_path):
    api = DesktopAPI(model_name="mgaze", output=tmp_path, preferences_path=tmp_path / "p.json")
    api._camera = "ready"
    assert api.command("calibrate", {"geometry": [1000, 800, 0, 0, 1]})["ok"]
    api._session.calibrated = True
    api._session.transition("ready")
    assert api.command("keyboard")["ok"]
    for key in ("r1c5", "r1c6"):
        assert api.command("key", {"key": key})["ok"]
    assert api.command("home")["ok"]
    record_path = next(tmp_path.glob("desktop-gaze-*")) / "session.json"
    record = json.loads(record_path.read_text())
    assert record["keyboard"]["characters"] == 2 and record["keyboard"]["manual"] == 2
    assert record["keyboard"]["text_saved"] is False and record["keyboard"]["dwell_seconds"] == 0.8
    assert "Hj" not in record_path.read_text()
    api.close()


def test_word_suggestions_follow_the_saved_setting_and_dark_theme_is_accepted(tmp_path):
    path = tmp_path / "p.json"
    api = DesktopAPI(model_name="mgaze", output=tmp_path, preferences_path=path)
    assert api.command("preferences", {"theme": "dark", "word_suggestions": False})["ok"]
    assert not api.command("preferences", {"word_suggestions": "no"})["ok"]
    assert not api.command("preferences", {"keyboard_size": "huge"})["ok"]
    assert api.command("preferences", {"keyboard_size": "large"})["ok"]
    assert api.snapshot()["preferences"]["keyboard_size"] == "large"
    assert api.command("keyboard")["ok"]
    assert api.snapshot()["keyboard"]["suggestions"] == ["", "", "", ""]
    assert api.command("preferences", {"word_suggestions": True})["ok"]
    assert api.snapshot()["keyboard"]["suggestions"][0] == "Bir"
    api.close()
    other = DesktopAPI(model_name="mgaze", output=tmp_path, preferences_path=path)
    assert other.snapshot()["preferences"]["theme"] == "dark"
    other.close()
