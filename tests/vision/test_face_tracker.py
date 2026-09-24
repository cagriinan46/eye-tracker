"""Hardware-free checks for MediaPipe-to-project landmark conversion."""

from types import SimpleNamespace

import pytest

from eye_tracker.vision import face_tracker
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint


class FakeLandmarker:
    def __init__(self, faces: list[list[object]]) -> None:
        self.faces = faces
        self.timestamps: list[int] = []
        self.closed = 0

    def detect_for_video(self, image: object, timestamp_ms: int) -> object:
        self.timestamps.append(timestamp_ms)
        return SimpleNamespace(face_landmarks=self.faces)

    def close(self) -> None:
        self.closed += 1


def fake_libraries(monkeypatch: pytest.MonkeyPatch, landmarker: FakeLandmarker) -> None:
    class FakeFaceLandmarker:
        @staticmethod
        def create_from_options(options: object) -> FakeLandmarker:
            assert options.running_mode == "VIDEO"
            assert options.num_faces == 1
            assert options.base_options.model_asset_path.endswith("face.task")
            return landmarker

    vision = SimpleNamespace(
        FaceLandmarkerOptions=lambda **kwargs: SimpleNamespace(**kwargs),
        FaceLandmarker=FakeFaceLandmarker,
        RunningMode=SimpleNamespace(VIDEO="VIDEO"),
    )
    mp = SimpleNamespace(
        tasks=SimpleNamespace(
            vision=vision, BaseOptions=lambda **kwargs: SimpleNamespace(**kwargs)
        ),
        ImageFormat=SimpleNamespace(SRGB="SRGB"),
        Image=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    cv2 = SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=lambda data, code: (data, code))
    monkeypatch.setattr(face_tracker, "_load_mediapipe", lambda: mp)
    monkeypatch.setattr(face_tracker, "_load_cv2", lambda: cv2)


def frame(timestamp_ns: int = 5_000_000) -> CameraFrame:
    return CameraFrame(payload=object(), width=640, height=480, timestamp_ns=timestamp_ns)


def test_landmarks_become_immutable_vendor_neutral_points(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    model = tmp_path / "face.task"
    model.write_bytes(b"test model placeholder")
    landmarker = FakeLandmarker([[SimpleNamespace(x=0.2, y=0.8), SimpleNamespace(x=1.1, y=-0.1)]])
    fake_libraries(monkeypatch, landmarker)

    with face_tracker.MediaPipeFaceLandmarkExtractor(model) as extractor:
        observation = extractor.extract(frame())

    assert observation == LandmarkObservation(
        timestamp_ns=5_000_000,
        landmarks=(NormalizedPoint(0.2, 0.8), NormalizedPoint(1.1, -0.1)),
    )
    assert all(type(point) is NormalizedPoint for point in observation.landmarks)
    assert landmarker.timestamps == [5]
    assert landmarker.closed == 1


def test_missing_face_is_explicitly_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    model = tmp_path / "face.task"
    model.write_bytes(b"test model placeholder")
    landmarker = FakeLandmarker([])
    fake_libraries(monkeypatch, landmarker)

    with face_tracker.MediaPipeFaceLandmarkExtractor(model) as extractor:
        observation = extractor.extract(frame())

    assert observation.landmarks is None
    assert observation.timestamp_ns == 5_000_000


def test_video_timestamps_increase_even_within_one_millisecond(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    model = tmp_path / "face.task"
    model.write_bytes(b"test model placeholder")
    landmarker = FakeLandmarker([])
    fake_libraries(monkeypatch, landmarker)

    with face_tracker.MediaPipeFaceLandmarkExtractor(model) as extractor:
        first = extractor.extract(frame(5_000_000))
        second = extractor.extract(frame(5_000_001))

    assert first.timestamp_ns == 5_000_000
    assert second.timestamp_ns == 5_000_001
    assert landmarker.timestamps == [5, 6]


def test_missing_model_fails_clearly(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="face.task"):
        face_tracker.MediaPipeFaceLandmarkExtractor(tmp_path / "face.task")
