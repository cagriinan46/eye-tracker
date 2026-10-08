"""Hardware-free checks for Issue #77's protocol, capture side outputs and analysis."""

import json
from math import cos, radians, sin
from types import SimpleNamespace

import pytest

from experiments.vertical_signal_comparison import analysis, capture, protocol
from eye_tracker.gaze.calibration import CalibrationSample, fit_independent_linear
from eye_tracker.vision import face_tracker
from eye_tracker.vision.contracts import CameraFrame, LandmarkObservation, NormalizedPoint

# Protocol


def test_schedule_has_checkpoints_shuffled_grids_and_fixed_seed() -> None:
    order = protocol.build_schedule()
    phases = [item.phase for item in order]
    assert len(order) == 50
    assert (
        phases
        == ["checkpoint"] * 3
        + ["calibration"] * 25
        + ["checkpoint"] * 3
        + ["validation"] * 16
        + ["checkpoint"] * 3
    )
    assert [item.trial for item in order if item.phase == "checkpoint"] == [1] * 3 + [2] * 3 + [
        3
    ] * 3
    calibration = [item.target for item in order if item.phase == "calibration"]
    validation = [item.target for item in order if item.phase == "validation"]
    assert set(calibration) == set(protocol.CALIBRATION_TARGETS)
    assert set(validation) == set(protocol.VALIDATION_TARGETS)
    assert calibration != list(protocol.CALIBRATION_TARGETS)
    assert not {(t.x, t.y) for t in validation} & {(t.x, t.y) for t in calibration}
    assert order == protocol.build_schedule()
    assert order != protocol.build_schedule(seed=78)


# Capture side outputs


def _category(name: str, score: object) -> SimpleNamespace:
    return SimpleNamespace(category_name=name, score=score)


def test_blendshape_scores_keep_selected_finite_values_only() -> None:
    np = pytest.importorskip("numpy")
    result = SimpleNamespace(
        face_blendshapes=[
            [
                _category("eyeLookUpLeft", np.float32(0.25)),
                _category("eyeLookDownRight", 0.5),
                _category("eyeBlinkLeft", float("nan")),
                _category("jawOpen", 0.9),
            ]
        ]
    )
    scores = capture.blendshape_scores(result)
    assert scores["look_up_left"] == 0.25 and type(scores["look_up_left"]) is float
    assert scores["look_down_right"] == 0.5
    assert scores["blink_left"] is None and scores["look_up_right"] is None
    assert set(scores) == set(capture.BLENDSHAPES.values())
    assert all(v is None for v in capture.blendshape_scores(SimpleNamespace()).values())


def test_head_pose_reads_rotation_and_rejects_missing_or_malformed() -> None:
    angle = radians(10)
    pitch = [
        [1, 0, 0, 0],
        [0, cos(angle), -sin(angle), 0],
        [0, sin(angle), cos(angle), 0],
        [0, 0, 0, 1],
    ]
    pose = capture.head_pose_degrees(SimpleNamespace(facial_transformation_matrixes=[pitch]))
    assert pose["head_pitch_deg"] == pytest.approx(10)
    assert pose["head_yaw_deg"] == pytest.approx(0)
    assert pose["head_roll_deg"] == pytest.approx(0)
    for result in (
        SimpleNamespace(),
        SimpleNamespace(facial_transformation_matrixes=[]),
        SimpleNamespace(facial_transformation_matrixes=[[[1, 2]]]),
        SimpleNamespace(facial_transformation_matrixes=[[[float("nan")] * 4] * 4]),
    ):
        assert all(v is None for v in capture.head_pose_degrees(result).values())


class _FakeNative:
    def __init__(self, result: object) -> None:
        self.result = result
        self.closed = 0

    def detect_for_video(self, image: object, timestamp_ms: int) -> object:
        return self.result

    def close(self) -> None:
        self.closed += 1


def test_signal_extractor_adds_outputs_without_changing_landmarks(monkeypatch, tmp_path) -> None:
    result = SimpleNamespace(
        face_landmarks=[[SimpleNamespace(x=0.2, y=0.8)]],
        face_blendshapes=[[_category("eyeLookDownLeft", 0.7)]],
        facial_transformation_matrixes=[[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]],
    )
    created, options_seen = [], []

    def create(options):
        options_seen.append(options)
        created.append(_FakeNative(result))
        return created[-1]

    vision = SimpleNamespace(
        FaceLandmarkerOptions=lambda **kwargs: SimpleNamespace(**kwargs),
        FaceLandmarker=SimpleNamespace(create_from_options=create),
        RunningMode=SimpleNamespace(VIDEO="VIDEO"),
    )
    mp = SimpleNamespace(
        tasks=SimpleNamespace(vision=vision, BaseOptions=lambda **k: SimpleNamespace(**k)),
        ImageFormat=SimpleNamespace(SRGB="SRGB"),
        Image=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    cv2 = SimpleNamespace(COLOR_BGR2RGB=1, cvtColor=lambda data, code: data)
    monkeypatch.setattr(face_tracker, "_load_mediapipe", lambda: mp)
    monkeypatch.setattr(face_tracker, "_load_cv2", lambda: cv2)
    model = tmp_path / "face.task"
    model.write_bytes(b"placeholder")

    with capture.SignalExtractor(model) as extractor:
        observation = extractor.extract(CameraFrame(object(), 640, 480, 5_000_000))
        signals, elapsed = extractor.last_signals, extractor.last_extract_ms

    assert observation == LandmarkObservation(5_000_000, (NormalizedPoint(0.2, 0.8),))
    assert created[0].closed == 1 and created[1].closed == 1
    extended = options_seen[1]
    assert extended.output_face_blendshapes and extended.output_facial_transformation_matrixes
    assert extended.running_mode == "VIDEO" and extended.num_faces == 1
    assert not hasattr(options_seen[0], "output_face_blendshapes")
    assert signals["look_down_left"] == 0.7 and signals["look_up_left"] is None
    assert signals["head_pitch_deg"] == pytest.approx(0)
    assert isinstance(elapsed, float) and elapsed >= 0


def _observation() -> LandmarkObservation:
    from eye_tracker.vision.eye_topology import _LEFT_CONTOUR, _RIGHT_CONTOUR

    points = [NormalizedPoint(0.5, 0.5) for _ in range(478)]
    for contour, center_x, corners, upper, lower, iris in (
        (_LEFT_CONTOUR, 0.3, (263, 362), 386, 374, (474, 475, 476, 477)),
        (_RIGHT_CONTOUR, 0.7, (33, 133), 159, 145, (469, 470, 471, 472)),
    ):
        for index in contour:
            points[index] = NormalizedPoint(center_x, 0.3)
        points[corners[0]] = NormalizedPoint(center_x - 0.1, 0.3)
        points[corners[1]] = NormalizedPoint(center_x + 0.1, 0.3)
        points[upper] = NormalizedPoint(center_x, 0.28)
        points[lower] = NormalizedPoint(center_x, 0.32)
        for index in iris:
            points[index] = NormalizedPoint(center_x, 0.3)
    return LandmarkObservation(123, tuple(points))


def test_measure_signals_merges_fresh_side_outputs_and_is_json_safe() -> None:
    frame = CameraFrame(object(), 640, 480, 123)
    signals = SimpleNamespace(last_signals=None, last_extract_ms=None)

    class Extractor:
        def extract(self, _frame):
            signals.last_signals = {"look_down_left": 0.4, "head_pitch_deg": 3.0}
            signals.last_extract_ms = 12.5
            return _observation()

    result, details = capture.measure_signals(
        SimpleNamespace(read=lambda: frame), Extractor(), signals
    )
    assert details["status"] == "usable" and details["vertical"] is not None
    assert details["look_down_left"] == 0.4 and details["look_up_left"] is None
    assert details["extract_ms"] == 12.5
    json.dumps(details, allow_nan=False)

    signals.last_signals = {"look_down_left": 0.9}
    signals.last_extract_ms = 1.0
    _, missing = capture.measure_signals(SimpleNamespace(read=lambda: None), Extractor(), signals)
    assert missing["look_down_left"] is None and missing["extract_ms"] is None


def test_collector_requires_screen_size_and_ignored_output() -> None:
    from experiments.vertical_signal_comparison.run import parse_args

    base = ["--participant", "fatih", "--session", "A", "--camera-index", "0"]
    output = ["--output", ".venv/vertical-signals-fatih-A.json"]
    args = parse_args(base + output + ["--screen-size", "1512x982"])
    assert args.screen_size == (1512, 982) and args.seed == 77
    with pytest.raises(SystemExit):
        parse_args(base + output)
    with pytest.raises(SystemExit):
        parse_args(base + ["--output", "elsewhere.json", "--screen-size", "1512x982"])


# Analysis


def _features(x, y, phase, block):
    return {
        "horizontal": 0.2 + 0.6 * x,
        "vertical": -0.05 + 0.001 * x,
        "binocular_eye_opening": 0.40 - 0.10 * y,
        "look_down": 0.1 + 0.5 * y,
        "look_up": 0.3 - 0.2 * y + 0.05 * x,
        "head_pitch_deg": 2.0 + 0.3 * x * y,
    }


def _report(features=_features, session="A", blink_presentations=(), frames=6) -> dict:
    rows = []
    for position, item in enumerate(protocol.build_schedule(), start=1):
        x, y = item.target.x, item.target.y
        values = features(x, y, item.phase, item.trial)
        for frame in range(frames):
            blink = 0.9 if position in blink_presentations else 0.05
            jitter = (frame - frames / 2) * 1e-4
            rows.append(
                {
                    "presentation": position,
                    "phase": item.phase,
                    "target_id": item.target.name,
                    "target_x": x,
                    "target_y": y,
                    "trial_number": item.trial,
                    "status": "usable",
                    "horizontal": values["horizontal"] + jitter,
                    "vertical": values["vertical"] + jitter,
                    "binocular_eye_opening": values["binocular_eye_opening"] + jitter,
                    "look_up_left": values["look_up"],
                    "look_up_right": values["look_up"],
                    "look_down_left": values["look_down"],
                    "look_down_right": values["look_down"],
                    "blink_left": blink,
                    "blink_right": 0.0,
                    "head_pitch_deg": values["head_pitch_deg"],
                    "extract_ms": 10.0 + frame,
                }
            )
    return {"participant": "synthetic", "session": session, "rows": rows}


def test_thresholds_and_candidates_are_the_preregistered_values() -> None:
    assert analysis.BLINK_MAX == 0.5
    assert analysis.MIN_CALIBRATION_PRESENTATIONS == 20
    assert analysis.MIN_VALIDATION_PRESENTATIONS == 14
    assert analysis.PASS_Y_MAE == 0.08
    assert analysis.PASS_ORDERING == 19 / 21
    assert analysis.PASS_ABS_BIAS == 0.05
    assert analysis.ORDERING_MIN_DELTA == 0.05
    assert analysis.CANDIDATES == {
        "R0": ("vertical",),
        "OPEN": ("opening",),
        "OPEN_Q": ("opening", "opening_squared"),
        "BLEND": ("blend",),
        "COMBO": ("vertical", "opening", "blend", "pitch"),
    }


def test_r0_fit_matches_the_production_independent_linear_fitter() -> None:
    def related(x, y, phase, block):
        return {**_features(x, y, phase, block), "vertical": -0.05 + 0.02 * y + 0.001 * x}

    records = analysis.presentation_medians(_report(related)["rows"])
    calibration = [r for r in records if r["phase"] == "calibration"]
    ours = analysis.fit(calibration, ("vertical",), "target_y")
    production = fit_independent_linear(
        CalibrationSample(r["horizontal"], r["vertical"], r["target_x"], r["target_y"])
        for r in calibration
    )
    assert ours[1] == pytest.approx(production.y_slope)
    assert ours[0] == pytest.approx(production.y_intercept)


def test_signal_that_tracks_rows_passes_and_weak_signal_fails() -> None:
    result = analysis.analyze_session(_report())
    candidates = result["candidates"]
    assert result["valid"] and result["validation_presentations"] == 16
    assert candidates["OPEN"]["passes"] and candidates["BLEND"]["passes"]
    assert candidates["OPEN"]["ordering"]["total_pairs"] == 96
    assert candidates["OPEN"]["mae"] == pytest.approx(0.0, abs=1e-3)
    assert not candidates["R0"]["passes"]
    assert result["x"]["ordering"]["proportion"] == 1.0
    assert result["extract_ms"] == {"median": 12.5, "p95": 15.0}
    json.dumps(result, allow_nan=False)


def test_constant_pitch_makes_combo_rank_deficient_not_a_crash() -> None:
    def flat_pitch(x, y, phase, block):
        return {**_features(x, y, phase, block), "head_pitch_deg": 2.0}

    result = analysis.analyze_session(_report(flat_pitch))
    assert result["candidates"]["COMBO"] == {"available": False, "passes": False}


def test_blink_frames_are_excluded_and_too_few_presentations_invalidate() -> None:
    blinked = analysis.presentation_medians(_report(blink_presentations=(4,))["rows"])
    assert blinked[3]["frames"] == 0 and not blinked[3]["available"]
    calibration_positions = tuple(range(4, 10))  # six of 25 calibration presentations
    result = analysis.analyze_session(_report(blink_presentations=calibration_positions))
    assert result["calibration_presentations"] == 19
    assert result["valid"] is False and result["candidates"] == {}


def test_bias_alone_fails_and_checkpoint_drift_is_reported() -> None:
    def drifting(x, y, phase, block):
        values = _features(x, y, phase, block)
        if phase == "validation" or (phase == "checkpoint" and block == 3):
            values["binocular_eye_opening"] -= 0.01  # 0.1 screen-y upward shift
        return values

    result = analysis.analyze_session(_report(drifting))
    opening = result["candidates"]["OPEN"]
    assert opening["ordering"]["proportion"] == 1.0
    assert opening["bias"] == pytest.approx(0.1, abs=1e-3)
    assert not opening["passes"]
    assert opening["checkpoint_drift"]["mean_abs_last_minus_first"] == pytest.approx(0.1, abs=1e-3)


def test_combine_selects_lowest_mae_candidate_passing_every_session() -> None:
    def session(name, passing):
        return {
            "participant": "p",
            "session": name,
            "valid": True,
            "candidates": {
                c: {"available": True, "mae": mae, "passes": c in passing}
                for c, mae in (("R0", 0.2), ("OPEN", 0.07), ("OPEN_Q", 0.05), ("BLEND", 0.06))
            }
            | {"COMBO": {"available": False, "passes": False}},
        }

    combined = analysis.combine([session("A", {"OPEN", "BLEND"}), session("B", {"OPEN"})])
    assert combined["winner"] == "OPEN"
    assert [item["candidate"] for item in combined["ranking"]] == ["OPEN_Q", "BLEND", "OPEN", "R0"]
    assert analysis.combine([session("A", set()), session("B", set())])["winner"] is None
    assert analysis.combine([session("A", {"OPEN"})])["winner"] is None
    with pytest.raises(ValueError, match="duplicate"):
        analysis.combine([session("A", set()), session("A", set())])


def test_cli_prints_sessions_and_winner(tmp_path, capsys) -> None:
    paths = []
    for name in ("A", "B"):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(_report(session=name)), encoding="utf-8")
        paths.append(str(path))
    assert analysis.main(paths) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["combined"]["winner"] in {"OPEN", "OPEN_Q", "BLEND", "COMBO"}
