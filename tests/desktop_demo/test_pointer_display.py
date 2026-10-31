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
