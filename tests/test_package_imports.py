"""Import contracts for the Phase 1 package boundaries."""

from importlib import import_module


def test_production_package_and_initial_boundaries_are_importable() -> None:
    for name in ("eye_tracker", "eye_tracker.vision", "eye_tracker.gaze"):
        assert import_module(name) is not None
