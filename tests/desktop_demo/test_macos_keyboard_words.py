"""Exercise native selection checks without accessing a user's focused editor."""

from unittest.mock import Mock

import pytest

panel = pytest.importorskip("experiments.desktop_demo.macos_keyboard")


@pytest.mark.parametrize(
    ("prefix", "caret", "preceding", "expected"),
    [
        ("", (0, 0), "", True),
        ("me", (2, 0), "me", True),
        ("me", (8, 0), " me", True),
        ("me", (8, 0), "ime", False),
        ("me", (8, 0), " ke", False),
        ("me", (2, 1), "me", False),
        ("me", (1, 0), "m", False),
    ],
)
def test_prefix_rechecked_before_completion(monkeypatch, prefix, caret, preceding, expected):
    keyboard = panel.FocusKeyboard.__new__(panel.FocusKeyboard)
    keyboard.target = (123, object())
    keyboard.prefix = prefix
    selected = panel.AX.AXValueCreate(panel.AX.kAXValueCFRangeType, caret)
    monkeypatch.setattr(panel, "attribute", Mock(return_value=selected))
    monkeypatch.setattr(
        panel.AX, "AXUIElementCopyParameterizedAttributeValue", Mock(return_value=(0, preceding))
    )
    assert keyboard.prefix_at_caret() is expected
