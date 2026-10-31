def test_window_pointer_uses_logical_coordinates_and_rejects_outside():
    from eye_tracker.actions.window_pointer import window_point

    assert window_point([0.5, 0.25], [100, 50, 1000, 800]) == (600, 250)
    assert window_point([1, 1], [100, 50, 1000, 800]) == (1099, 849)
    for p in (None, [-0.1, 0.5], [0.5, 1.1], [float("nan"), 0.5]):
        assert window_point(p, [100, 50, 1000, 800]) is None


def test_pointer_gate_requires_live_focused_unpaused_demo(tmp_path):
    import time

    from experiments.desktop_demo.runtime import DesktopAPI

    api = DesktopAPI(output=tmp_path)
    assert api.pointer_sample() is None
    api._session.phase = "demo"
    api._tracking = True
    api._camera = "ready"
    api._session.last_point = [0.5, 0.5]
    api._pointer_captured = time.monotonic()
    assert api.pointer_sample() == [0.5, 0.5]
    api.command("pause")
    assert api.pointer_sample() is None
    api.command("resume")
    api._focused = False
    assert api.pointer_sample() is None
    api._focused = True
    api._pointer_captured = time.monotonic() - 1
    assert api.pointer_sample() is None


def test_native_pointer_poll_does_not_wait_for_inference_lock(tmp_path):
    import threading
    import time

    from experiments.desktop_demo.runtime import DesktopAPI

    api = DesktopAPI(output=tmp_path)
    locked, release = threading.Event(), threading.Event()

    def hold():
        with api._lock:
            locked.set()
            release.wait(2)

    worker = threading.Thread(target=hold)
    worker.start()
    assert locked.wait(1)
    try:
        start = time.monotonic()
        assert api.pointer_sample() is None
        assert time.monotonic() - start < 0.1
    finally:
        release.set()
        worker.join(2)


def test_pointer_smoother_glides_without_overshoot_and_holds_on_missing():
    from eye_tracker.actions.window_pointer import PointerSmoother

    s = PointerSmoother(fast=0.03, slow=0.1, distance=80, max_gap=0.15)
    assert s.update(0, (100, 100)) == (100, 100)
    xs = [s.update(i / 60, (400, 100))[0] for i in range(1, 9)]
    assert all(a < b for a, b in zip(xs, xs[1:], strict=False))
    # About one UniGaze inference interval (~125 ms) covers > 90 % of the move.
    assert 100 < xs[0] < 400 and xs[-1] > 370
    xs += [s.update(i / 60, (400, 100))[0] for i in range(9, 60)]
    assert max(xs) == xs[-1] == 400
    assert s.update(1.1, None) is None
    assert s.point == (400, 100)
    assert s.update(1.11, (float("nan"), 0)) is None


def test_pointer_smoother_is_faster_for_large_moves_than_small_jitter():
    from eye_tracker.actions.window_pointer import PointerSmoother

    def fraction(distance):
        s = PointerSmoother()
        s.update(0, (0, 0))
        return s.update(1 / 60, (distance, 0))[0] / distance

    assert fraction(300) > 0.4
    assert fraction(10) < 0.2
    assert fraction(300) > fraction(40) > fraction(10)


def test_pointer_smoother_snaps_after_gap_or_reset():
    from eye_tracker.actions.window_pointer import PointerSmoother

    s = PointerSmoother(max_gap=0.15)
    s.update(0, (0, 0))
    assert s.update(0.5, (500, 500)) == (500, 500)
    s.reset()
    assert s.update(0.51, (10, 10)) == (10, 10)
    assert s.update(0.4, (90, 90)) == (90, 90)


def test_macos_pointer_glides_inside_window_and_resets_on_viewport_change(monkeypatch):
    import sys
    import types

    from eye_tracker.platform_adapters.macos_window_pointer import MacOSWindowPointer

    class Rect:
        def __init__(self, x, y, w, h):
            self.origin = types.SimpleNamespace(x=x, y=y)
            self.size = types.SimpleNamespace(width=w, height=h)

    class Native:
        frame = Rect(100, 100, 1000, 800)

        def isKeyWindow(self):
            return True

        def contentView(self):
            return types.SimpleNamespace(frame=lambda: None)

        def convertRectToScreen_(self, _):
            return self.frame

    warps, clock = [], [0.0]
    quartz = types.SimpleNamespace(
        CGEventSourceKeyState=lambda *_: False,
        kCGEventSourceStateCombinedSessionState=0,
        CGWarpMouseCursorPosition=warps.append,
    )
    screen = types.SimpleNamespace(frame=lambda: Rect(0, 0, 1440, 1000))
    appkit = types.SimpleNamespace(NSScreen=types.SimpleNamespace(screens=lambda: [screen]))
    helper = types.SimpleNamespace(callLater=lambda *_: None, callAfter=lambda *_: None)
    monkeypatch.setitem(sys.modules, "Quartz", quartz)
    monkeypatch.setitem(sys.modules, "AppKit", appkit)
    monkeypatch.setitem(sys.modules, "PyObjCTools", types.SimpleNamespace(AppHelper=helper))
    monkeypatch.setattr("time.monotonic", lambda: clock[0])
    native = Native()
    points = iter([[0.0, 0.0], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
    pointer = MacOSWindowPointer(
        types.SimpleNamespace(native=native), lambda: next(points), lambda: None
    )
    for _ in range(3):
        pointer._tick()
        clock[0] += 1 / 60
    assert warps[0] == (100, 100)
    assert 100 < warps[1][0] < warps[2][0] < 600
    native.frame = Rect(200, 100, 1000, 800)
    pointer._tick()
    assert warps[-1] == (700, 500)
