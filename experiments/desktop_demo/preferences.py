"""Validated appearance-only preferences, independent of calibration records."""

import json
import os
import tempfile
from pathlib import Path

DEFAULTS = {"theme": "lavender", "reduced_motion": False}
DEFAULT_PATH = Path.home() / ".eye-tracker" / "desktop-preferences.json"


def validated(values):
    if not isinstance(values, dict) or set(values) - DEFAULTS.keys():
        raise ValueError("Geçersiz görünüm ayarı.")
    result = DEFAULTS | values
    if result["theme"] not in ("lavender", "sunflower", "sage"):
        raise ValueError("Geçersiz renk teması.")
    if type(result["reduced_motion"]) is not bool:
        raise ValueError("Hareket ayarı açık veya kapalı olmalı.")
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
