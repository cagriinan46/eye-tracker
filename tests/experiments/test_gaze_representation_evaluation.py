"""Frozen evaluation metrics on deterministic synthetic aggregates/captures only."""

import copy
import json
from dataclasses import asdict

import pytest

from experiments.gaze_representation_benchmark import evaluation_metrics as m
from eye_tracker.gaze.calibration import IndependentLinearMapping


def presentation(x, y, block, order, offsets=(0, 0), times=(0.1, 0.8, 1.5, 2.9)):
    return {
        "target_id": f"T-{x}-{y}",
        "target_x": x,
        "target_y": y,
        "block": block,
        "order": order,
        "samples": [
            {
                "key": [order, k],
                "t": t,
                "h": x + offsets[0],
                "v": y + offsets[1],
                "prediction": [x + offsets[0], y + offsets[1]],
                "reason": None,
            }
            for k, t in enumerate(times)
        ],
    }


def grid(shift=(0, 0)):
    cal, trials = [], []
    for k, (y, x) in enumerate((y, x) for y in (0.2, 0.5, 0.8) for x in (0.2, 0.5, 0.8)):
        cal.append(presentation(x, y, 0, k + 1))
        for block in (1, 2, 3):
            trials.append(presentation(x, y, block, k * 3 + block, shift))
    return cal, trials


def test_sample_weighted_screen_errors_and_euclidean_statistics():
    rows = [{"dx": 3, "dy": 4}, {"dx": -3, "dy": 0}, {"dx": 0, "dy": -4}]
    result = m.screen_summary(rows)
    assert result["count"] == 3
    assert result["x_mae"] == 2 and result["y_mae"] == pytest.approx(8 / 3)
    assert result["x_bias"] == 0 and result["y_bias"] == 0
    assert result["mean_euclidean"] == 4
    assert result["median_euclidean"] == 4
    assert result["p95_euclidean"] == pytest.approx(4.9)


def test_primary_secondary_windows_and_halves_are_exact():
    cal, trials = grid()
    trial = trials[0]
    trial["samples"] = [
        dict(trial["samples"][0], key=[1, k], t=t, h=1 + k, v=1 + k, prediction=[1 + k, 1 + k])
        for k, t in enumerate((-0.01, 0, 0.79, 0.8, 1.49, 1.5, 2.99, 3))
    ]
    mapping = IndependentLinearMapping(1, 0, 1, 0)
    primary = m.window_diagnostics(cal, trials, mapping, 0, 3)
    secondary = m.window_diagnostics(cal, trials, mapping, 0.8, 3)
    p, s = primary["presentations"][0], secondary["presentations"][0]
    assert p["horizontal"]["count"] == 6 and s["horizontal"]["count"] == 4
    assert p["halves"]["horizontal"]["first"]["count"] == 4
    assert p["halves"]["horizontal"]["second"]["count"] == 2
    assert s["halves"]["horizontal"]["first"]["count"] == 2
    assert s["halves"]["horizontal"]["second"]["count"] == 2


def test_equal_presentation_weight_and_calibration_direction():
    cal, trials = grid()
    trials[0]["samples"] *= 20
    for sample in trials[0]["samples"]:
        sample["v"] = 0.1
    diagnostic = m.axis_diagnostics(cal, trials, "vertical")
    assert diagnostic["direction"] == 1
    assert diagnostic["ordering"]["pooled"]["level_medians"] == pytest.approx([0.2, 0.5, 0.8])
    assert diagnostic["ordering"]["pooled"]["minimum_separation"] == pytest.approx(0.3)
    # Validation reversed cannot change calibration-derived direction.
    for t in trials:
        for row in t["samples"]:
            row["v"] = 1 - t["target_y"]
    diagnostic = m.axis_diagnostics(cal, trials, "vertical")
    assert diagnostic["direction"] == 1
    assert diagnostic["ordering"]["pooled"]["ordered"] is False


def test_exact_target_transfer_and_normalized_vertical_ratio():
    cal, trials = grid((0.03, 0.06))
    diagnostic = m.axis_diagnostics(cal, trials, "vertical")
    assert diagnostic["median_absolute_transfer"] == pytest.approx(0.06)
    assert diagnostic["normalized_transfer"] == pytest.approx(0.2)
    assert len(diagnostic["targets"]) == 9
    for target in diagnostic["targets"]:
        assert target["signed_transfer"] == pytest.approx(0.06)
        assert target["absolute_transfer"] == pytest.approx(0.06)
        assert target["first_half_transfer"] == pytest.approx(0.06)
        assert target["second_half_transfer"] == pytest.approx(0.06)


def test_mad_iqr_ranges_pairwise_changes_and_halves():
    cal, trials = grid()
    for trial in trials:
        for k, row in enumerate(trial["samples"]):
            row["v"] = trial["target_y"] + 0.02 * trial["block"] + (0, 0, 0.02, 0.02)[k]
    diagnostic = m.axis_diagnostics(cal, trials, "vertical")
    target = diagnostic["targets"][0]
    assert target["block_range"] == pytest.approx(0.04)
    assert target["pairwise_block_changes"] == pytest.approx([0.02, 0.04, 0.02])
    assert diagnostic["median_block_range"] == pytest.approx(0.04)
    assert diagnostic["maximum_block_range"] == pytest.approx(0.04)
    assert diagnostic["within_presentations"][0]["mad"] == pytest.approx(0.01)
    assert diagnostic["within_presentations"][0]["iqr"] == pytest.approx(0.02)
    assert diagnostic["within_presentations"][0]["half_shift"] == pytest.approx(0.02)


def test_missing_target_median_is_not_silently_dropped():
    cal, trials = grid((0, 0.06))
    for row in trials[0]["samples"]:
        row["h"] = row["v"] = None
    diagnostic = m.axis_diagnostics(cal, trials, "vertical")
    assert diagnostic["targets"][0]["validation_median"] is None
    assert diagnostic["median_absolute_transfer"] is None
    assert diagnostic["normalized_transfer"] is None
    assert diagnostic["ordering"]["pooled"]["ordered"] is None
    assert len(diagnostic["ordering"]) == 16


def metric_result(x=0.1, y=0.1, transfer=0.5, ordered=True):
    return {
        "screen": {"all": {"x_mae": x, "y_mae": y}},
        "features": {
            "vertical": {
                "normalized_transfer": transfer,
                "ordering": {"pooled": {"ordered": ordered}},
            }
        },
    }


def test_gate_all_five_required_and_undefined_denominators_fail():
    baseline = metric_result()
    candidate = metric_result(x=0.115, y=0.08, transfer=0.375)
    good = m.gate_comparison(baseline, candidate, True)
    assert good["overall"] == "PROMISING"
    assert all(c["pass"] for c in good["criteria"].values())
    for index in range(1, 6):
        bad = copy.deepcopy(candidate)
        provenance = True
        if index == 1:
            bad["screen"]["all"]["y_mae"] = 0.081
        elif index == 2:
            bad["features"]["vertical"]["normalized_transfer"] = 0.376
        elif index == 3:
            bad["features"]["vertical"]["ordering"]["pooled"]["ordered"] = None
        elif index == 4:
            bad["screen"]["all"]["x_mae"] = 0.116
        else:
            provenance = False
        result = m.gate_comparison(baseline, bad, provenance)
        assert result["overall"] == "FAIL"
        assert result["criteria"][str(index)]["pass"] is False
    for field in ("x_mae", "y_mae"):
        bad = copy.deepcopy(baseline)
        bad["screen"]["all"][field] = 0
        assert m.gate_comparison(bad, candidate, True)["overall"] == "FAIL"
    bad = copy.deepcopy(baseline)
    bad["features"]["vertical"]["normalized_transfer"] = None
    assert m.gate_comparison(bad, candidate, True)["criteria"]["2"]["pass"] is False
    undefined = copy.deepcopy(baseline)
    undefined["features"]["vertical"]["ordering"]["pooled"]["ordered"] = None
    assert m.gate_comparison(undefined, candidate, True)["criteria"]["3"]["pass"] is False


def test_common_frame_mask_keeps_original_mapping_and_frames():
    cal, left = grid((0.1, 0.2))
    right = copy.deepcopy(left)
    right[0]["samples"][0]["v"] = None
    a, b = m.common_frames(left, right)
    assert len(a[0]["samples"]) == 3 and len(b[0]["samples"]) == 3
    assert a[0]["samples"][0]["key"] == [1, 1]
    assert a[0]["samples"][0]["prediction"] == pytest.approx([0.3, 0.4])
    # Shared masking cannot mutate full native input or its fixed predictions.
    assert len(left[0]["samples"]) == 4


def test_json_aggregate_serialization_has_no_sample_traces():
    cal, trials = grid((0.03, 0.06))
    result = m.window_diagnostics(cal, trials, IndependentLinearMapping(1, 0, 1, 0), 0, 3)
    encoded = json.dumps(result, sort_keys=True, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded["screen"]["all"]["count"] == 108
    assert '"samples"' not in encoded and '"key"' not in encoded


def test_feature_group_medians_include_both_rows_and_columns():
    cal, trials = grid((0.03, 0.06))
    result = m.axis_diagnostics(cal, trials, "horizontal")
    assert [r["median"] for r in result["validation_group_medians"]["target_y"]] == pytest.approx(
        [0.53] * 3
    )
    assert [r["median"] for r in result["validation_group_medians"]["target_x"]] == pytest.approx(
        [0.23, 0.53, 0.83]
    )


def synthetic_capture(session="geometry-1", offset=0):
    from test_raw_geometry_gaze_diagnostic import capture

    from experiments.raw_geometry_gaze_diagnostic.geometry import FACE_ANCHOR_INDICES, eye_records
    from validation.real_calibration import Target, fit_session_calibration

    report = capture(session)
    report["participant"] = "cagri"
    for p in report["calibration_presentations"] + report["trials"]:
        for sample in p["samples"]:
            geom = sample["raw_geometry"]
            for k, index in enumerate(FACE_ANCHOR_INDICES):
                geom["landmarks"][str(index)] = {
                    "x": 0.2 + (k % 3) * 0.15 + offset,
                    "y": 0.2 + (k // 3) * 0.15,
                    "z": (k % 5) * 0.017,
                }
            geom["face_anchors"] = {str(i): geom["landmarks"][str(i)] for i in FACE_ANCHOR_INDICES}
            # Offset features and fit the synthetic session independently.
            from experiments.raw_geometry_gaze_diagnostic.geometry import EYES, reconstruct_r0

            for eye in EYES.values():
                for index in eye["iris_ring"]:
                    geom["landmarks"][str(index)]["x"] += offset
            geom["eyes"] = eye_records(geom["landmarks"], 1920, 1080)
            f = reconstruct_r0(geom)
            sample["horizontal_feature"], sample["vertical_feature"] = f.horizontal, f.vertical
    mapping, _ = fit_session_calibration(
        [
            (
                Target(p["target_id"], p["target_x"], p["target_y"]),
                [(s["horizontal_feature"], s["vertical_feature"]) for s in p["samples"]],
            )
            for p in report["calibration_presentations"]
        ]
    )
    report["mapping_coefficients"] = asdict(mapping)
    for p in report["trials"]:
        for sample in p["samples"]:
            sample["predicted_x"], sample["predicted_y"] = mapping.predict(
                sample["horizontal_feature"], sample["vertical_feature"]
            )
    return report


def test_expected_session_and_complete_schedule_validation():
    from experiments.gaze_representation_benchmark import evaluate as e

    report = synthetic_capture()
    assert e.verify_capture(report, "geometry-1")["session"] == "geometry-1"
    for key, value in (
        ("session", "geometry-2"),
        ("session_role", "holdout"),
        ("protocol_version", 2),
    ):
        bad = copy.deepcopy(report)
        bad[key] = value
        with pytest.raises(ValueError):
            e.verify_capture(bad, "geometry-1")
    for key in ("calibration_presentations", "trials"):
        bad = copy.deepcopy(report)
        bad[key].pop()
        with pytest.raises(ValueError):
            e.verify_capture(bad, "geometry-1")


def test_only_calibration_enters_candidate_fit_and_session_maps_are_independent(monkeypatch):
    from experiments.gaze_representation_benchmark import evaluate as e

    original = e.fit_candidates
    seen = []

    def checked(presentations):
        assert all(s["phase"] == "calibration" for p in presentations for s in p.samples)
        seen.append(presentations)
        return original(presentations)

    monkeypatch.setattr(e, "fit_candidates", checked)
    a = e.prepare_session(synthetic_capture())
    b = e.prepare_session(synthetic_capture("geometry-2", 0.01))
    assert len(seen) == 2
    assert a["fits"]["R0"].mapping.x_intercept != b["fits"]["R0"].mapping.x_intercept
    assert a["reference_sha256"]["R1"] != b["reference_sha256"]["R1"]
    assert a["fits"]["R1"].reference is not b["fits"]["R1"].reference


def test_common_analysis_does_not_call_fit_or_rebuild_references(monkeypatch):
    from experiments.gaze_representation_benchmark import evaluate as e

    prepared = e.prepare_session(synthetic_capture())

    def no_fitting(*args, **kwargs):
        pytest.fail("common-frame analysis attempted fitting")

    monkeypatch.setattr(e, "fit_candidates", no_fitting)
    monkeypatch.setattr(e, "fit_independent_linear", no_fitting)
    result = e.summarize_session(prepared)
    assert tuple(result["representations"]) == ("R0", "R1", "R2")
    for name in ("R1", "R2"):
        assert (
            result["comparisons"][name]["common"]["primary"]["baseline"]["screen"]["all"]["count"]
            == 162
        )


def test_capture_provenance_and_allowed_paths(tmp_path, monkeypatch):
    from experiments.gaze_representation_benchmark import evaluate as e

    paths = {
        session: tmp_path / f"raw-geometry-gaze-cagri-{session}.json"
        for session in ("geometry-1", "geometry-2")
    }
    monkeypatch.setattr(e, "CAPTURE_PATHS", paths)
    for session, path in paths.items():
        payload = json.dumps(synthetic_capture(session)).encode()
        path.write_bytes(payload)
    reports, provenance = e.load_captures(paths)
    import hashlib

    assert len(reports) == 2
    for session, path in paths.items():
        data = path.read_bytes()
        assert provenance[session]["sha256"] == hashlib.sha256(data).hexdigest()
        assert provenance[session]["bytes"] == len(data)
    bad = dict(paths)
    bad["geometry-2"] = tmp_path / "alternate.json"
    with pytest.raises(ValueError, match="expected"):
        e.load_captures(bad)


def test_end_to_end_synthetic_summary_is_deterministic_and_aggregate_only():
    from experiments.gaze_representation_benchmark import evaluate as e

    reports = [synthetic_capture(), synthetic_capture("geometry-2", 0.01)]
    provenance = {r["session"]: {"sha256": "0" * 64, "bytes": 1} for r in reports}
    a = e.evaluate_reports(reports, provenance)
    b = e.evaluate_reports(reports, provenance)
    assert e.serialize(a) == e.serialize(b)

    def check(value):
        if isinstance(value, dict):
            assert not set(value) & {
                "raw_geometry",
                "landmarks",
                "samples",
                "key",
                "references",
                "frame_timestamp_ns",
            }
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(a)
    assert a["freeze_commit"] == "c4ad261b63fcce3b3998ce8335f8d81fa2118b32"
    assert set(a["holdout_gate"]) == {"R1", "R2"}
    assert all(g["overall"] in ("PROMISING", "FAIL") for g in a["holdout_gate"].values())


def test_validation_changes_cannot_change_references_or_any_maps():
    from experiments.gaze_representation_benchmark import evaluate as e

    report = synthetic_capture()
    altered = copy.deepcopy(report)
    for p in altered["trials"]:
        p["target_x"], p["target_y"] = 0.9, 0.1
        for sample in p["samples"]:
            sample["raw_geometry"] = None
    a, b = e.prepare_session(report), e.prepare_session(altered)
    assert a["reference_sha256"] == b["reference_sha256"]
    for name in ("R0", "R1", "R2"):
        assert a["data"][name]["maps"] == b["data"][name]["maps"]


def test_both_integrities_pass_before_any_fitting(monkeypatch):
    from experiments.gaze_representation_benchmark import evaluate as e

    a, b = synthetic_capture(), synthetic_capture("geometry-2")
    b["trials"].pop()
    monkeypatch.setattr(
        e, "prepare_session", lambda *args: pytest.fail("fitting before both integrity checks")
    )
    with pytest.raises(ValueError):
        e.evaluate_reports([a, b], {})


def test_freeze_source_identity_without_participant_files():
    from experiments.gaze_representation_benchmark import evaluate as e

    hashes = e.verify_frozen_sources()
    assert len(hashes) == 19
    assert all(len(h) == 64 for h in hashes.values())


def test_report_determinism_and_gate_values():
    from experiments.gaze_representation_benchmark import evaluate as e
    from experiments.gaze_representation_benchmark.report import render

    reports = [synthetic_capture(), synthetic_capture("geometry-2")]
    provenance = {r["session"]: {"sha256": "0" * 64, "bytes": 123} for r in reports}
    summary = e.evaluate_reports(reports, provenance)
    text = render(summary)
    assert text == render(summary)
    for required in (
        "DEVELOPMENT RESULT",
        "UNTOUCHED HOLDOUT RESULT",
        "R1 OVERALL",
        "R2 OVERALL",
        "SHA-256",
        "criterion | R1 value | R1 pass/fail | R2 value | R2 pass/fail",
        "All binocular ordering checks",
        "Exact common-frame",
    ):
        assert required in text


def test_one_shot_runner_seals_and_refuses_second_run(tmp_path, monkeypatch, capsys):
    import hashlib
    import subprocess

    from experiments.gaze_representation_benchmark import evaluate as e

    (tmp_path / ".venv").mkdir()
    (tmp_path / "experiments/gaze_representation_benchmark").mkdir(parents=True)
    paths = {s: tmp_path / ".venv" / f"raw-geometry-gaze-cagri-{s}.json" for s in e.CAPTURE_PATHS}
    for session, path in paths.items():
        path.write_text(json.dumps(synthetic_capture(session)))
    monkeypatch.setattr(e, "ROOT", tmp_path)
    monkeypatch.setattr(e, "CAPTURE_PATHS", paths)
    monkeypatch.setattr(e, "verify_frozen_sources", lambda: {})
    monkeypatch.setattr(
        subprocess, "check_output", lambda args, **kwargs: b"" if args[1] == "status" else "a" * 40
    )
    e.run_once()
    capsys.readouterr()
    marker = json.loads((tmp_path / ".venv/stage-b2-one-shot-evaluation.json").read_text())
    encoded = (
        tmp_path / "experiments/gaze_representation_benchmark/results_summary.json"
    ).read_bytes()
    assert marker["status"] == "complete"
    assert marker["summary_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert json.loads(encoded)["execution"]["evaluator_commit"] == "a" * 40
    with pytest.raises(ValueError, match="one-shot"):
        e.run_once()


def test_r0_preserves_logged_unavailable_binocular_frames():
    from experiments.gaze_representation_benchmark import evaluate as e

    report = synthetic_capture()
    sample = report["trials"][0]["samples"][0]
    sample.update(
        feature_status="unavailable",
        gaze_status="unavailable",
        horizontal_feature=None,
        vertical_feature=None,
        predicted_x=None,
        predicted_y=None,
        unavailable_reason="missing_features",
    )
    e.verify_capture(report, "geometry-1")
    prepared = e.prepare_session(report)
    row = prepared["data"]["R0"]["trials"]["binocular"][0]["samples"][0]
    assert row["h"] is None and row["prediction"] is None
    assert row["reason"] == "recorded production: missing_features"
    assert prepared["data"]["R0"]["trials"]["left"][0]["samples"][0]["h"] is not None


def test_r2_failed_eye_diagnostics_keep_frozen_outputs_unchanged():
    from experiments.gaze_representation_benchmark import evaluate as e
    from experiments.gaze_representation_benchmark import representations as rep

    prepared = e.prepare_session(synthetic_capture())
    record = synthetic_capture()["trials"][0]["samples"][0]["raw_geometry"]
    refs = dict(prepared["fits"]["R2"].reference)
    refs["left"] = None
    features = rep.r2(record, refs)
    assert features.left is None and features.right is not None
    assert (
        e._unavailable_reason("R2", "left", features, record, refs)
        == "R2 calibration contour reference absent"
    )
    assert e._unavailable_reason("R2", "binocular", features, record, refs).startswith("left:")
    assert features.left is None and features.right is not None
    refs = prepared["fits"]["R2"].reference
    degenerate = copy.deepcopy(record)
    for index in rep.EYES["left"]["contour"]:
        degenerate["landmarks"][str(index)]["y"] = 0.5
    features = rep.r2(degenerate, refs)
    assert features.left is None
    assert "full-rank affine" in e._unavailable_reason("R2", "left", features, degenerate, refs)


def test_common_frame_gate_failure_cannot_be_hidden_by_native_pass():
    from experiments.gaze_representation_benchmark import evaluate as e

    passing = m.gate_comparison(metric_result(), metric_result(0.1, 0.05, 0.1), True)
    failing = m.gate_comparison(metric_result(), metric_result(0.1, 0.09, 0.1), True)
    result = e.coverage_gate(
        {"native": {"primary_comparison": passing}, "common": {"primary_comparison": failing}}
    )
    assert result["overall"] == "FAIL"
    assert result["criteria"]["1"]["value"] == {"native": 0.5, "common": pytest.approx(0.9)}
    assert result["criteria"]["1"]["pass"] is False
    assert result["criteria"]["2"]["pass"] is True
