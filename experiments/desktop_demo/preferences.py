"""Validated appearance and keyboard preferences, independent of calibration records."""

import json
import os
import tempfile
from pathlib import Path

DEFAULTS = {
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
# Per-user detection times (Issue #160): (minimum, maximum) in ms, 50 ms steps.
GESTURE_TIMES = {
    "wink_right_min_ms": (100, 800),
    "wink_left_min_ms": (200, 1000),
    "wink_max_ms": (500, 2000),
    "long_blink_ms": (500, 3000),
    "smile_hold_ms": (200, 1500),
}
SENSITIVITIES = ("low", "medium", "high")
SCROLL_STOPS = ("long_blink", "smile", "wink_right", "wink_left")
WINK_ACTIONS = ("left", "right", "off")
KEYBOARD_SIZES = ("small", "medium", "large")
DEFAULT_PATH = Path.home() / ".eye-tracker" / "desktop-preferences.json"


def validated(values):
    if not isinstance(values, dict) or set(values) - DEFAULTS.keys():
        raise ValueError("Geçersiz görünüm ayarı.")
    result = DEFAULTS | values
    if result["theme"] not in ("lavender", "sunflower", "sage", "dark"):
        raise ValueError("Geçersiz renk teması.")
    if type(result["reduced_motion"]) is not bool:
        raise ValueError("Hareket ayarı açık veya kapalı olmalı.")
    if type(result["word_suggestions"]) is not bool:
        raise ValueError("Kelime önerisi ayarı açık veya kapalı olmalı.")
    if result["keyboard_size"] not in KEYBOARD_SIZES:
        raise ValueError("Geçersiz klavye boyutu.")
    if result["wink_left"] not in WINK_ACTIONS or result["wink_right"] not in WINK_ACTIONS:
        raise ValueError("Göz kırpma ayarı sol tık, sağ tık veya kapalı olmalı.")
    if result["smile"] not in WINK_ACTIONS:
        raise ValueError("Gülümseme ayarı sol tık, sağ tık veya kapalı olmalı.")
    if result["scroll_stop"] not in SCROLL_STOPS:
        raise ValueError("Geçersiz kaydırma durdurma hareketi.")
    if result["wink_sensitivity"] not in SENSITIVITIES:
        raise ValueError("Geçersiz göz kırpma hassasiyeti.")
    for key, (low, high) in GESTURE_TIMES.items():
        value = result[key]
        if type(value) is not int or not low <= value <= high or value % 50:
            raise ValueError("Algılama süresi geçersiz.")
    return result


def load(path):
    try:
        return validated(json.loads(path.read_text()))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def save(path, values):
    values = validated(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
            name = f.name
            json.dump(values, f)
        os.replace(name, path)
    finally:
        if name is not None and os.path.exists(name):
            os.unlink(name)
    return values
