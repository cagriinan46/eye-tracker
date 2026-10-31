import time

import numpy as np
import pytest


def test_capture_keeps_newest_frame_while_inference_is_busy():
    from experiments.unigaze.camera_stream import LatestCamera

    class Capture:
        def __init__(self):
            self.n = 0
            self.released = False

        def read(self):
            time.sleep(0.005)
            self.n += 1
            return True, np.full((4, 4, 3), self.n % 255, np.uint8)

        def release(self):
            self.released = True

    cap = Capture()
    stream = LatestCamera(cap, encode=lambda f: str(int(f[0, 0, 0])))
    try:
        first = stream.read_after(-1)
        time.sleep(0.06)  # Stand in for an independently blocked inference consumer.
        latest = stream.read_after(first[0])
        assert latest[0] > first[0] + 2
        assert latest[1] > first[1]
        snap = stream.preview()
        assert snap["preview"] is not None
        assert snap["preview_sequence"] >= latest[0]
        assert time.monotonic() - snap["preview_captured"] < 0.1
    finally:
        stream.close()
    assert cap.released and not stream.thread.is_alive()


def test_capture_failure_does_not_leave_a_frozen_preview():
    from experiments.unigaze.camera_stream import LatestCamera

    class Capture:
        def read(self):
            return False, None

        def release(self):
            pass

    stream = LatestCamera(Capture(), encode=lambda f: "image")
    try:
        with pytest.raises(RuntimeError, match="Kamera"):
            stream.read_after(-1)
        assert stream.preview()["preview"] is None
    finally:
        stream.close()
