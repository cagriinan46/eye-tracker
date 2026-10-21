from dataclasses import FrozenInstanceError

import pytest

from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget


def test_rectangle_geometry_and_negative_origins():
    rect = TargetRect(10, 20, 30, 40)
    assert rect.center == (25, 40)
    assert rect.distance_to(15, 25) == 0
    assert rect.distance_to(0, 25) == 10
    assert TargetRect(-100, -50, 100, 100).center == (-50, 0)
    with pytest.raises(FrozenInstanceError):
        rect.x = 1


@pytest.mark.parametrize(
    "values",
    [
        (0, 0, 0, 1),
        (0, 0, 1, -1),
        (float("nan"), 0, 1, 1),
        (0, 0, float("inf"), 1),
        (1e308, 0, 1e308, 1),
    ],
)
def test_invalid_rectangles(values):
    with pytest.raises(ValueError):
        TargetRect(*values)


def test_snapshot_rejects_duplicate_ids_and_failed_targets():
    rect = TargetRect(0, 0, 100, 100)
    target = UITarget("1", "AXButton", rect, True, "press")
    assert UISnapshot("s", 1, "c", rect, (target,), "ok").targets == (target,)
    for targets, status in [((target, target), "ok"), ((target,), "incomplete")]:
        with pytest.raises(ValueError):
            UISnapshot("s", 1, "c", rect, targets, status)


@pytest.mark.parametrize(
    "status", ["unavailable", "incomplete", "context_changed", "unsupported_coordinates"]
)
def test_failure_snapshot_can_have_no_screen(status):
    assert UISnapshot("s", 1, None, None, (), status).status == status


def test_snapshot_requires_known_status_finite_time_and_complete_context():
    rect = TargetRect(0, 0, 100, 100)
    for time, context, screen, status in [
        (float("nan"), "c", rect, "ok"),
        (1, None, rect, "ok"),
        (1, "c", None, "ok"),
        (1, "c", rect, "guess"),
    ]:
        with pytest.raises(ValueError):
            UISnapshot("s", time, context, screen, (), status)
    with pytest.raises(TypeError):
        UISnapshot("s", 1, "c", rect, [], "ok")
