import sys

import pytest
from test_macos_accessibility import Backend

from eye_tracker.intent.targets import TargetRect
from eye_tracker.platform_adapters._macos_ax import (
    AXBackend,
    AXReadError,
    AXUnavailable,
    UnsupportedCoordinates,
)
from eye_tracker.platform_adapters.macos_accessibility import MacOSAccessibility


def test_native_initialization_is_lazy_and_rejects_non_macos(monkeypatch):
    backend = AXBackend()
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(AXUnavailable):
        with backend:
            pass


@pytest.mark.parametrize(
    "error, status",
    [
        (AXReadError("read"), "incomplete"),
        (AXUnavailable("missing"), "unavailable"),
        (UnsupportedCoordinates("displays"), "unsupported_coordinates"),
    ],
)
def test_backend_failures_close_context_and_expose_no_targets(error, status):
    backend = Backend()

    def fail():
        raise error

    backend.screen = fail
    result = MacOSAccessibility(backend=backend).snapshot()
    assert result.status == status and result.targets == ()
    assert backend.closed


def test_native_owned_references_release_in_reverse_order():
    backend = AXBackend()
    released = []
    backend.release = released.append
    backend.owned = [11, 22, 33]
    backend.__exit__(None, None, None)
    assert released == [33, 22, 11]
    assert backend.owned == []


def test_context_uses_frontmost_pid_and_detects_window_changes():
    backend = AXBackend()
    backend._frontmost_pid = lambda: 42
    backend.create_application = lambda pid: ("app", pid)
    backend._own = lambda p: p
    backend._element = lambda p: p
    backend.same = lambda a, b: a == b
    backend._attr = lambda node, name: (
        "window-one" if name == "AXFocusedWindow" else pytest.fail("unexpected attribute")
    )
    first = backend.context()
    assert first is not None
    assert backend.context() == first
    backend._attr = lambda node, name: "window-two"
    assert backend.context() != first


def test_no_foreground_application_has_no_context():
    backend = AXBackend()
    backend._frontmost_pid = lambda: None
    assert backend.context() is None


def geometry_backend(size, position=(10.0, 20.0), role="AXButton"):
    """Supply raw AX geometry while exercising the real description logic."""
    native = AXBackend()
    native._attr = lambda node, name: role if name == "AXRole" else pytest.fail(name)
    native._text = lambda value: value
    native._pair = lambda node, name, kind: position if name == "AXPosition" else size
    return native


@pytest.mark.parametrize("size", [(0.0, 20.0), (20.0, 0.0), (0.0, 0.0)])
def test_zero_area_control_does_not_discard_neighbors_or_descendants(size):
    native = geometry_backend(size)
    backend = Backend()
    backend.tree["window"] = ["button", "empty"]
    backend.tree["empty"] = ["child"]
    backend.info["child"] = ("AXButton", TargetRect(80, 20, 40, 40), True, ("AXPress",))
    describe = backend.describe
    backend.describe = lambda node: native.describe(node) if node == "empty" else describe(node)
    backend.hit_test = lambda x, y: "button" if x < 70 else "child"
    result = MacOSAccessibility(backend=backend).snapshot()
    assert result.status == "ok"
    assert len(result.targets) == 2
    assert backend.closed


@pytest.mark.parametrize(
    "size, position",
    [
        ((-1.0, 20.0), (10.0, 20.0)),
        ((0.0, -20.0), (10.0, 20.0)),
        ((float("nan"), 20.0), (10.0, 20.0)),
        ((0.0, float("inf")), (10.0, 20.0)),
        ((0.0, 20.0), (float("nan"), 20.0)),
        ((0.0, 20.0), (10.0, float("inf"))),
        ((0.0, 1e308), (10.0, 1e308)),
    ],
)
def test_invalid_geometry_still_invalidates_entire_snapshot(size, position):
    native = geometry_backend(size, position)
    backend = Backend()
    backend.tree["window"] = ["button", "bad"]
    describe = backend.describe
    backend.describe = lambda node: native.describe(node) if node == "bad" else describe(node)
    result = MacOSAccessibility(backend=backend).snapshot()
    assert result.status == "incomplete"
    assert result.targets == ()
    assert backend.closed


@pytest.mark.parametrize("role", ["AXWindow", "AXMenuBar"])
def test_empty_root_geometry_does_not_prove_complete_coverage(role):
    native = geometry_backend((0.0, 20.0), role=role)
    backend = Backend()
    backend.describe = native.describe
    result = MacOSAccessibility(backend=backend).snapshot()
    assert result.status == "incomplete"
    assert result.targets == ()


@pytest.mark.parametrize("role", ["AXMenuButton", "AXTextField"])
def test_shared_press_controls_read_native_geometry_state_and_capability(role):
    native = geometry_backend((40.0, 30.0), role=role)
    native._attr = lambda node, name: {"AXRole": role, "AXEnabled": None}[name]
    native._timeout = lambda node: None
    native.copy_actions = lambda node, output: 0
    native._out = lambda code, output, optional: ("AXPress",)
    native._array = lambda value, cap: value
    assert native.describe("control") == (role, TargetRect(10, 20, 40, 30), None, ("AXPress",))
