from experiments.desktop_demo.model import CameraModel


def test_cleanup_attempts_all_resources_even_if_one_release_fails():
    calls = []

    class Resource:
        def __init__(self, name):
            self.name = name

        def release(self):
            calls.append(self.name)
            if self.name == "cap":
                raise RuntimeError("device already closed")

    model = CameraModel.__new__(CameraModel)
    model.cap = Resource("cap")
    model.face = Resource("face")
    model.gaze = Resource("gaze")
    model.close()
    assert calls == ["cap", "face", "gaze"]
    assert model.cap is model.face is model.gaze is None
