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


def context_backend():
    native = AXBackend()
    native._frontmost_pid = lambda: 42
    native.trusted = lambda: True
    native.create_application = lambda pid: ("app", pid)
    native._own = lambda value: value
    native._element = lambda value: value
    native.same = lambda a, b: a == b
    return native


def test_initial_window_messaging_failure_recovers_once():
    from eye_tracker.platform_adapters._macos_ax import AXMessagingError

    native = context_backend()
    reads = iter([AXMessagingError("busy"), "window"])

    def read(node, name):
        value = next(reads)
        if isinstance(value, Exception):
            raise value
        return value

    native._attr = read
    assert native.context() == native.context_id
    assert native.initial_context == (("app", 42), "window")


@pytest.mark.parametrize("change", ["pid", "permission", "persistent", "established", "invalid"])
def test_initial_window_recovery_stops_on_changed_or_unrecoverable_state(change):
    from eye_tracker.platform_adapters._macos_ax import AXMessagingError

    native = context_backend()
    calls = []
    if change == "established":
        native.initial_context = (("app", 42), "old-window")

    def read(node, name):
        calls.append(name)
        if change == "pid":
            native._frontmost_pid = lambda: 43
        if change == "permission":
            native.trusted = lambda: False
        if change == "invalid":
            raise AXReadError("invalid reference")
        raise AXMessagingError("busy")

    native._attr = read
    if change in {"pid", "permission"}:
        assert native.context() is None
    else:
        with pytest.raises(AXReadError):
            native.context()
    assert len(calls) == (2 if change == "persistent" else 1)
    if change != "established":
        assert native.initial_context is None


def test_foreground_change_during_successful_window_read_is_not_adopted():
    native = context_backend()

    def read(node, name):
        native._frontmost_pid = lambda: 43
        return "window"

    native._attr = read
    assert native.context() is None
    assert native.initial_context is None


def test_native_messaging_error_is_classified_without_retrying_other_reads():
    import ctypes as C

    from eye_tracker.platform_adapters._macos_ax import AXMessagingError

    native = AXBackend()
    with pytest.raises(AXMessagingError):
        native._out(-25204, C.c_void_p())
    with pytest.raises(AXReadError) as caught:
        native._out(-25202, C.c_void_p())
    assert not isinstance(caught.value, AXMessagingError)


@pytest.mark.parametrize("change", ["pid", "permission"])
def test_state_change_during_successful_retry_does_not_establish_context(change):
    from eye_tracker.platform_adapters._macos_ax import AXMessagingError

    native = context_backend()
    calls = []

    def read(node, name):
        calls.append(name)
        if len(calls) == 1:
            raise AXMessagingError("busy")
        if change == "pid":
            native._frontmost_pid = lambda: 43
        else:
            native.trusted = lambda: False
        return "window"

    native._attr = read
    assert native.context() is None
    assert native.initial_context is None
    assert len(calls) == 2


def test_initial_window_retry_does_not_reset_snapshot_time_budget():
    from eye_tracker.platform_adapters._macos_ax import AXMessagingError

    native = context_backend()
    now = [1.0]
    calls = []

    def read(node, name):
        calls.append(name)
        if len(calls) == 1:
            raise AXMessagingError("busy")
        now[0] = 1.6
        return "window"

    native._attr = read
    backend = Backend()
    backend.context = native.context
    result = MacOSAccessibility(backend=backend, clock=lambda: now[0]).snapshot()
    assert result.status == "incomplete" and result.targets == ()
    assert result.captured_at == 1.0
    assert backend.closed
