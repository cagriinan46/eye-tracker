import pytest

from eye_tracker.platform_adapters.macos_outline import visible_rect


def test_coordinate_conversion_and_expiration_without_new_messages():
    values = (10, 20, 30, 40, 1.12)
    assert visible_rect(values, 1, (500, 400)) == ((10, 340), (30, 40))
    assert visible_rect(values, 1.12, (500, 400)) is None
    assert visible_rect(values, 2, (500, 400)) is None


@pytest.mark.parametrize(
    "values",
    [
        (10, 20, 0, 40, 1.1),
        (-1, 20, 30, 40, 1.1),
        (490, 20, 30, 40, 1.1),
        (10, 390, 30, 40, 1.1),
        (10, 20, 30, 40, 100),
        (float("nan"), 20, 30, 40, 1.1),
        (10, 20, 30, 40, float("inf")),
    ],
)
def test_invalid_or_unbounded_messages_hide(values):
    assert visible_rect(values, 1, (500, 400)) is None


def test_invalid_clock_hides():
    assert visible_rect((10, 20, 30, 40, 1.1), float("nan"), (500, 400)) is None


def test_panel_is_nonactivating_nonkey_and_mouse_transparent():
    from types import SimpleNamespace

    from eye_tracker.platform_adapters.macos_outline import _make_panel

    class Base:
        def __init__(self):
            self.calls = []

        @classmethod
        def alloc(cls):
            return cls()

        def initWithContentRect_styleMask_backing_defer_(self, rect, mask, backing, defer):
            self.mask = mask
            return self

        def initWithFrame_(self, frame):
            return self

        def __getattr__(self, name):
            return lambda *args: self.calls.append((name, args))

    api = SimpleNamespace(
        NSPanel=Base,
        NSView=Base,
        NSWindowStyleMaskBorderless=0,
        NSWindowStyleMaskNonactivatingPanel=128,
        NSBackingStoreBuffered=2,
        NSFloatingWindowLevel=3,
        NSColor=SimpleNamespace(clearColor=lambda: None),
    )
    panel, view = _make_panel(api)
    assert panel.mask == 128
    assert not panel.canBecomeKeyWindow() and not panel.canBecomeMainWindow()
    assert ("setIgnoresMouseEvents_", (True,)) in panel.calls
    for obj in (panel, view):
        assert ("setAccessibilityElement_", (False,)) in obj.calls
        assert ("setAccessibilityChildren_", ([],)) in obj.calls
        assert not any("makeKey" in name or "activate" == name for name, _ in obj.calls)


def test_mailbox_expiry_escape_and_bounded_helper_cleanup():
    import multiprocessing
    from types import SimpleNamespace

    from eye_tracker.intent.targets import TargetRect
    from eye_tracker.platform_adapters.macos_outline import MacOSOutline

    ctx = multiprocessing.get_context("spawn")
    calls = []
    process = SimpleNamespace(
        start=lambda: calls.append("start"),
        is_alive=lambda: True,
        join=lambda timeout: calls.append(("join", timeout)),
        terminate=lambda: calls.append("terminate"),
    )
    context = SimpleNamespace(
        Array=ctx.Array, Event=ctx.Event, Value=ctx.Value, Process=lambda **kwargs: process
    )
    outline = MacOSOutline((500, 400), context=context, clock=lambda: 1)
    outline.start()
    outline.show(TargetRect(10, 20, 30, 40), 1.1)
    assert visible_rect(tuple(outline.mailbox), 1, outline.size) is not None
    assert visible_rect(tuple(outline.mailbox), 1.2, outline.size) is None
    outline.status.value = 2
    with pytest.raises(InterruptedError):
        outline.check_stop()
    outline.close()
    assert "terminate" in calls
    assert tuple(outline.mailbox) == (0, 0, 0, 0, 0)
    outline.show(TargetRect(10, 20, 30, 40), 1.1)
    assert tuple(outline.mailbox) == (0, 0, 0, 0, 0)
    with pytest.raises(RuntimeError):
        outline.start()


def test_helper_hides_expired_outline_without_parent_updates(monkeypatch):
    import multiprocessing
    import os
    import sys
    from types import SimpleNamespace

    from eye_tracker.platform_adapters import macos_outline as module

    ticks, calls = [0], []
    panel = SimpleNamespace(
        orderOut_=lambda _: calls.append("hide"),
        setFrame_display_=lambda *a: None,
        orderFrontRegardless=lambda: calls.append("show"),
        displayIfNeeded=lambda: None,
        close=lambda: calls.append("close"),
    )
    view = SimpleNamespace(setNeedsDisplay_=lambda _: None)
    app = SimpleNamespace(
        setActivationPolicy_=lambda _: True,
        nextEventMatchingMask_untilDate_inMode_dequeue_=lambda *a: None,
    )
    pool = SimpleNamespace(drain=lambda: None)
    api = SimpleNamespace(
        NSApplication=SimpleNamespace(sharedApplication=lambda: app),
        NSApplicationActivationPolicyAccessory=1,
        NSEventMaskAny=1,
        NSAutoreleasePool=SimpleNamespace(alloc=lambda: SimpleNamespace(init=lambda: pool)),
    )
    monkeypatch.setitem(sys.modules, "AppKit", api)
    monkeypatch.setitem(
        sys.modules,
        "Quartz",
        SimpleNamespace(
            CGEventSourceKeyState=lambda *a: False, kCGEventSourceStateCombinedSessionState=0
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "Foundation",
        SimpleNamespace(NSDate=SimpleNamespace(date=lambda: None), NSDefaultRunLoopMode="default"),
    )
    monkeypatch.setattr(module, "_make_panel", lambda _: (panel, view))
    monkeypatch.setattr(module, "_screen_matches", lambda *a: True)
    monkeypatch.setattr(module, "monotonic", lambda: 1 + ticks[0] * 0.2)
    mailbox = multiprocessing.get_context("spawn").Array("d", [10, 20, 30, 40, 1.1])

    def wait(_):
        ticks[0] += 1

    stop = SimpleNamespace(is_set=lambda: ticks[0] >= 2, wait=wait)
    status = SimpleNamespace(value=0)
    module._serve((500, 400), mailbox, stop, status, os.getppid())
    assert status.value == 1
    assert calls == ["show", "hide", "hide", "close"]


def test_failed_process_start_can_close_without_joining_unstarted_process():
    import multiprocessing
    from types import SimpleNamespace

    from eye_tracker.platform_adapters.macos_outline import MacOSOutline

    ctx = multiprocessing.get_context("spawn")

    def fail():
        raise RuntimeError("spawn failed")

    def invalid_join(timeout):
        raise AssertionError("cannot join unstarted process")

    process = SimpleNamespace(start=fail, join=invalid_join)
    context = SimpleNamespace(
        Array=ctx.Array, Event=ctx.Event, Value=ctx.Value, Process=lambda **kwargs: process
    )
    outline = MacOSOutline((500, 400), context=context)
    with pytest.raises(RuntimeError, match="spawn failed"):
        outline.start()
    outline.close()
