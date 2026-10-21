import sys

import pytest
from test_macos_accessibility import Backend

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
