"""Hardware-free checks for Issue #90's dual-camera collector arguments and fusion analysis."""

import json
import random
from math import sin

import pytest

from experiments.dual_camera_vertical import analysis
from experiments.vertical_signal_comparison import protocol
from eye_tracker.gaze.estimator import GazeUnavailable, UnavailableReason

# Collector


def test_collector_requires_distinct_cameras_and_ignored_output() -> None:
    from experiments.dual_camera_vertical.run import parse_args

    base = ["--participant", "fatih-dual", "--session", "A", "--screen-size", "1512x982"]
    output = ["--output", "validation/results/dual-camera-fatih-A.json"]
    args = parse_args(base + output + ["--top-index", "0", "--bottom-index", "1"])
    assert (args.top_index, args.bottom_index, args.seed) == (0, 1, 77)
    with pytest.raises(SystemExit):
        parse_args(base + output + ["--top-index", "1", "--bottom-index", "1"])
    with pytest.raises(SystemExit):
        parse_args(base + output + ["--top-index", "-1", "--bottom-index", "1"])
    with pytest.raises(SystemExit):
        parse_args(base + ["--output", "elsewhere.json", "--top-index", "0", "--bottom-index", "1"])


def test_loop_is_usable_when_either_camera_has_features() -> None:
    from experiments.dual_camera_vertical.run import first_usable

    missing = GazeUnavailable(UnavailableReason.MISSING_FEATURES)
    features = object()
    assert first_usable([missing, features]) is features
    assert first_usable([features, missing]) is features
    assert first_usable([missing, missing]) is missing


# Analysis


def _signals(y: float, noise: dict[str, float]) -> dict:
    """Each feature follows the row y with its own error and nonlinearity."""
    return {
        "vertical": -0.05 + 0.02 * (y + noise["vertical"]),
        "binocular_eye_opening": 0.40 - 0.10 * (y + noise["opening"]) ** 2,
        "look_down": 0.1 + 0.5 * (y + noise["blend"]) ** 3,
        "look_up": 0.3,
        "head_pitch_deg": 2.0 + sin(3 * (y + noise["pitch"])),
    }


def _report(
    session: str = "A",
    errors: dict[str, float] | None = None,
    blink: dict[str, set[int]] | None = None,
    frames: int = 6,
    seed: int = 1,
) -> dict:
    """Synthetic dual session; each camera gets independent per-presentation error."""
    generator = random.Random(seed)
    errors = errors or {"top": 0.06, "bottom": 0.06}
    blink = blink or {}
    rows, loop = [], 0
    for position, item in enumerate(protocol.build_schedule(), start=1):
        x, y = item.target.x, item.target.y
        noise = {
            camera: {
                name: generator.gauss(0.0, errors[camera])
                for name in ("vertical", "opening", "blend", "pitch")
            }
            for camera in analysis.CAMERAS
        }
        for frame in range(frames):
            loop += 1
            for offset, camera in enumerate(analysis.CAMERAS):
                values = _signals(y, noise[camera])
                jitter = (frame - frames / 2) * 1e-4
                rows.append(
                    {
                        "camera": camera,
                        "loop": loop,
                        "presentation": position,
                        "phase": item.phase,
                        "target_id": item.target.name,
                        "target_x": x,
                        "target_y": y,
                        "trial_number": item.trial,
                        "status": "usable",
                        "timestamp_ns": loop * 40_000_000 + offset * 15_000_000,
                        "horizontal": 0.2 + 0.6 * x + jitter,
                        "vertical": values["vertical"] + jitter,
                        "binocular_eye_opening": values["binocular_eye_opening"] + jitter,
                        "look_up_left": values["look_up"],
                        "look_up_right": values["look_up"],
                        "look_down_left": values["look_down"],
                        "look_down_right": values["look_down"],
                        "blink_left": 0.9 if position in blink.get(camera, set()) else 0.05,
                        "blink_right": 0.0,
                        "head_pitch_deg": values["head_pitch_deg"],
                        "extract_ms": 7.0,
                    }
                )
    return {"participant": "synthetic", "session": session, "rows": rows}


def test_preregistered_constants() -> None:
    assert analysis.FUSION_BETTER_MARGIN == 0.01
    assert analysis.BOTTOM_BETTER_MARGIN == 0.02
    assert analysis.LATE_SOURCE == "COMBO"
    assert analysis.SPLIT_FEATURES == (
        "top_opening",
        "bottom_vertical",
        "bottom_blend",
        "top_pitch",
    )


def test_both_cameras_are_scored_on_presentations_common_to_both() -> None:
    first_validation = 32  # 3 checkpoints + 25 calibration + 3 checkpoints + 1
    report = _report(blink={"bottom": {first_validation}})
    keep = analysis.common_presentations(report)
    assert len(keep) == 49 and first_validation not in keep
    result = analysis.analyze_session(report)
    assert result["valid"] and result["common_presentations"] == 49
    for camera in analysis.CAMERAS:
        assert result["cameras"][camera]["validation_presentations"] == 15
    assert result["inter_camera_gap_ms"] == {"loops": 300, "median": 15.0, "max": 15.0}
    json.dumps(result, allow_nan=False)


def test_too_few_common_presentations_invalidate_the_session() -> None:
    validation = set(range(32, 36))
    report = _report(blink={"top": validation, "bottom": {36}})
    result = analysis.analyze_session(report)
    assert not result["valid"] and result["fusion"] == {}
    assert not analysis.combine([result, analysis.analyze_session(_report("B"))])["complete"]


def test_late_fusion_averages_independent_camera_errors() -> None:
    result = analysis.analyze_session(_report(errors={"top": 0.08, "bottom": 0.08}, seed=3))
    top = result["cameras"]["top"]["candidates"]["COMBO"]["mae"]
    bottom = result["cameras"]["bottom"]["candidates"]["COMBO"]["mae"]
    late = result["fusion"]["LATE"]
    assert late["available"] and late["mae"] < min(top, bottom)
    assert set(late["checkpoint_last_minus_first"]) == {"K-bottom", "K-center", "K-top"}
    assert len(result["fusion"]["SPLIT"]["coefficients"]) == 5


def test_noise_free_cameras_pass_and_fusion_is_exact() -> None:
    result = analysis.analyze_session(_report(errors={"top": 0.0, "bottom": 0.0}))
    for name in ("LATE", "SPLIT"):
        assert result["fusion"][name]["passes"]
        assert result["fusion"][name]["mae"] == pytest.approx(0.0, abs=1e-3)


def test_combine_applies_the_preregistered_rule() -> None:
    errors = {"top": 0.10, "bottom": 0.10}
    sessions = [
        analysis.analyze_session(_report(name, errors=errors, seed=seed))
        for name, seed in (("A", 5), ("B", 6))
    ]
    combined = analysis.combine(sessions)
    assert combined["complete"]
    ranking = {item["method"]: item["mean_y_mae"] for item in combined["ranking"]}
    assert {"TOP:COMBO", "BOTTOM:R0", "LATE", "SPLIT"} <= set(ranking)
    single = combined["best_single"]["mean_y_mae"]
    assert single == min(v for k, v in ranking.items() if ":" in k)
    expected = ranking["LATE"] <= single - analysis.FUSION_BETTER_MARGIN
    assert combined["fusion_better_primary_late"] is expected
    assert isinstance(combined["bottom_better_than_top"], bool)
    with pytest.raises(ValueError):
        analysis.combine([sessions[0], sessions[0]])


def test_cli_prints_sessions_and_decision(tmp_path, capsys) -> None:
    paths = []
    for name in ("A", "B"):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(_report(name)), encoding="utf-8")
        paths.append(str(path))
    assert analysis.main(paths) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["combined"]["complete"] and len(output["sessions"]) == 2
