import hashlib
import json

import numpy as np
import pytest


def session_fixture(root):
    path = root / "sample"
    path.mkdir()
    x = np.zeros((13, 45, 258), dtype=np.float32)
    y = np.full((13, 45, 2), 0.5, dtype=np.float32)
    y[:, :, 0] = (0.125 + np.arange(13) * 0.0625)[:, None]
    np.savez(path / "calibration.npz", features=x, labels=y)
    weights = np.zeros((259, 2))
    weights[0] = 0.5
    np.save(path / "ridge_weights.npy", weights)
    metadata = dict(
        screen_size=[100, 100], diagnostic_features_enabled=True, repeat_calibration_targets=False
    )
    targets = [[0.4, 0.5], [0.6, 0.5], [0.5, 0.4], [0.5, 0.6], [0.44, 0.42], [0.56, 0.58]]
    plan = [
        dict(target=point, target_set="unseen", target_id=i) for i, point in enumerate(targets, 1)
    ]
    evaluation, diagnostic = [], []
    for trial in range(1, 7):
        for frame in range(6):
            stamp = trial * 10 + frame
            valid = frame != 5
            evaluation.append(
                dict(
                    captured_monotonic_s=stamp,
                    trial=trial,
                    target_id=trial,
                    target_set="unseen",
                    target_px=(np.array(targets[trial - 1]) * 100).tolist(),
                    raw_px=[50, 50] if valid else None,
                )
            )
            diagnostic.append(
                dict(
                    captured_monotonic_s=stamp,
                    phase="evaluation",
                    trial=trial,
                    usable=valid,
                    features=[0.0] * 258 if valid else None,
                )
            )
    for name, value in [
        ("session.json", metadata),
        ("completion.json", {"status": "completed"}),
        ("evaluation-plan.json", {"targets": plan}),
    ]:
        (path / name).write_text(json.dumps(value))
    for name, rows in [("evaluation.jsonl", evaluation), ("diagnostic-frames.jsonl", diagnostic)]:
        (path / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path


def hashes(path):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}


def test_identical_frames_missing_denominator_and_immutable_sources(tmp_path):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    before = hashes(path)
    result = analyze(path, results_root=tmp_path)
    assert hashes(path) == before
    assert set(result["models"]) == {"0.1", "1.0", "10.0"}
    for model in result["models"].values():
        group = model["unseen"]
        assert group["sufficient_data"]
        assert group["mean_error_px_equal_target_weight"] == pytest.approx(10)
        first = group["trials"][0]
        assert first["attempts"] == 6 and first["valid"] == 5
        assert first["within_30px_fraction"] == pytest.approx(5 / 6)
        assert first["bias_px"] == pytest.approx([10, 0])
    assert result["baseline_max_difference_px"] < 0.001


@pytest.mark.parametrize("fault", ["duplicate", "missing", "trial", "raw", "feature", "incomplete"])
def test_rejects_corrupt_or_unpaired_data(tmp_path, fault):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    file = path / "diagnostic-frames.jsonl"
    rows = [json.loads(s) for s in file.read_text().splitlines()]
    if fault == "duplicate":
        rows.append(rows[0])
    if fault == "missing":
        rows.pop(0)
    if fault == "trial":
        rows[0]["trial"] = 2
    if fault == "feature":
        rows[0]["features"] = [0.0] * 257
    file.write_text("".join(json.dumps(r) + "\n" for r in rows))
    if fault == "raw":
        file = path / "evaluation.jsonl"
        rows = [json.loads(s) for s in file.read_text().splitlines()]
        rows[0]["raw_px"] = [99, 99]
        file.write_text("".join(json.dumps(r) + "\n" for r in rows))
    if fault == "incomplete":
        (path / "completion.json").write_text('{"status":"cancelled"}')
    with pytest.raises(ValueError):
        analyze(path, results_root=tmp_path)


def test_evaluation_targets_cannot_change_model_fit(tmp_path):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    plan = json.loads((path / "evaluation-plan.json").read_text())
    for row in plan["targets"]:
        row["target"] = (0.5 + 2 * (np.array(row["target"]) - 0.5)).tolist()
    (path / "evaluation-plan.json").write_text(json.dumps(plan))
    rows = [json.loads(s) for s in (path / "evaluation.jsonl").read_text().splitlines()]
    for row in rows:
        row["target_px"] = (50 + 2 * (np.array(row["target_px"]) - 50)).tolist()
    (path / "evaluation.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    result = analyze(path, results_root=tmp_path)
    for model in result["models"].values():
        assert model["unseen"]["mean_error_px_equal_target_weight"] == pytest.approx(20)


def test_rejects_symlink_session_and_missing_diagnostics(tmp_path):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(path, target_is_directory=True)
    with pytest.raises(ValueError):
        analyze(alias, results_root=tmp_path)
    (path / "diagnostic-frames.jsonl").unlink()
    with pytest.raises(ValueError, match="diagnostic"):
        analyze(path, results_root=tmp_path)


def test_trained_and_unseen_locations_remain_separate(tmp_path):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    metadata = json.loads((path / "session.json").read_text())
    metadata["repeat_calibration_targets"] = True
    (path / "session.json").write_text(json.dumps(metadata))
    with np.load(path / "calibration.npz") as data:
        trained = data["labels"][:, 0, :].tolist()
    unseen = [[0.4, 0.5], [0.6, 0.5], [0.5, 0.4], [0.5, 0.6], [0.44, 0.42], [0.56, 0.58]]
    plan, evaluation, diagnostics = [], [], []
    for trial in range(1, 20):
        repeated = trial <= 13
        group = "repeated" if repeated else "unseen"
        target = trained[trial - 1] if repeated else unseen[trial - 14]
        target_id = trial if repeated else trial - 13
        plan.append(dict(target=target, target_set=group, target_id=target_id))
        for frame in range(5):
            stamp = trial * 10 + frame
            evaluation.append(
                dict(
                    captured_monotonic_s=stamp,
                    trial=trial,
                    target_id=target_id,
                    target_set=group,
                    target_px=(np.array(target) * 100).tolist(),
                    raw_px=[50, 50],
                )
            )
            diagnostics.append(
                dict(
                    captured_monotonic_s=stamp,
                    trial=trial,
                    phase="evaluation",
                    usable=True,
                    features=[0.0] * 258,
                )
            )
    (path / "evaluation-plan.json").write_text(json.dumps(dict(targets=plan)))
    for name, rows in [("evaluation.jsonl", evaluation), ("diagnostic-frames.jsonl", diagnostics)]:
        (path / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = analyze(path, results_root=tmp_path)
    for model in report["models"].values():
        assert model["repeated"]["mean_error_px_equal_target_weight"] == pytest.approx(262.5 / 13)
        assert model["unseen"]["mean_error_px_equal_target_weight"] == pytest.approx(10)
        assert len(model["repeated"]["trials"]) == 13
        assert len(model["unseen"]["trials"]) == 6


def test_cli_creates_new_local_reports_without_overwriting_input(tmp_path, monkeypatch):
    import validation.gaze_model_replay as api

    path = session_fixture(tmp_path)
    before = hashes(path)
    monkeypatch.setattr(api, "RESULTS", tmp_path)
    monkeypatch.setattr("sys.argv", ["gaze_model_replay", str(path)])
    # The real CLI must use the configured results root, not a separate output path.
    api.main()
    api.main()
    outputs = list(tmp_path.glob("gaze-model-replay-*/report.json"))
    assert len(outputs) == 2
    assert all(json.loads(p.read_text())["attempts"] == 36 for p in outputs)
    assert hashes(path) == before


def test_insufficient_trial_does_not_publish_overall_mean(tmp_path):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    for name in ("evaluation.jsonl", "diagnostic-frames.jsonl"):
        rows = [json.loads(s) for s in (path / name).read_text().splitlines()]
        if name == "evaluation.jsonl":
            rows[0]["raw_px"] = None
        else:
            rows[0]["usable"] = False
            rows[0]["features"] = None
        (path / name).write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = analyze(path, results_root=tmp_path)
    for model in report["models"].values():
        assert model["unseen"]["sufficient_data"] is False
        assert model["unseen"]["mean_error_px_equal_target_weight"] is None
        assert model["unseen"]["trials"][0]["availability"] == pytest.approx(4 / 6)


@pytest.mark.parametrize(
    "fault", ["duplicate_location", "duplicate_id", "out_of_bounds", "trained_as_unseen"]
)
def test_plan_semantics_reject_false_unseen_accuracy(tmp_path, fault):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    plan = json.loads((path / "evaluation-plan.json").read_text())
    if fault == "duplicate_location":
        plan["targets"][1]["target"] = plan["targets"][0]["target"]
    if fault == "duplicate_id":
        plan["targets"][1]["target_id"] = 1
    if fault == "out_of_bounds":
        plan["targets"][0]["target"] = [-0.1, 0.5]
    if fault == "trained_as_unseen":
        plan["targets"][0]["target"] = [0.125, 0.5]
    (path / "evaluation-plan.json").write_text(json.dumps(plan))
    rows = [json.loads(line) for line in (path / "evaluation.jsonl").read_text().splitlines()]
    for row in rows:
        item = plan["targets"][row["trial"] - 1]
        row["target_px"] = (np.array(item["target"]) * 100).tolist()
        row["target_id"] = item["target_id"]
    (path / "evaluation.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="plan"):
        analyze(path, results_root=tmp_path)


def test_nonconstant_fit_and_replay_use_declared_alpha_without_label_leakage(tmp_path):
    from validation.gaze_model_replay import analyze

    path = session_fixture(tmp_path)
    with np.load(path / "calibration.npz") as data:
        x, y = data["features"], data["labels"]
    x[:, :, 0] = (np.arange(13) - 6)[:, None]
    np.savez(path / "calibration.npz", features=x, labels=y)
    # Sum(x^2)=45*182=8190; y=.5+x/16, so slope=511.875/(8190+alpha).
    weights = np.zeros((259, 2))
    weights[0] = 0.5
    weights[1, 0] = 511.875 / 8190.1
    np.save(path / "ridge_weights.npy", weights)
    for name in ("diagnostic-frames.jsonl", "evaluation.jsonl"):
        rows = [json.loads(s) for s in (path / name).read_text().splitlines()]
        for row in rows:
            if name.startswith("diagnostic") and row["usable"]:
                row["features"][0] = 1
            if name.startswith("evaluation") and row["raw_px"] is not None:
                row["raw_px"] = [50 + 100 * 511.875 / 8190.1, 50]
        (path / name).write_text("".join(json.dumps(r) + "\n" for r in rows))
    first = analyze(path, results_root=tmp_path)
    for alpha in (0.1, 1.0, 10.0):
        assert first["models"][str(alpha)]["unseen"]["trials"][0]["bias_px"][0] == pytest.approx(
            10 + 100 * 511.875 / (8190 + alpha)
        )
    plan = json.loads((path / "evaluation-plan.json").read_text())
    plan["targets"][0]["target"] = [0.3, 0.5]
    (path / "evaluation-plan.json").write_text(json.dumps(plan))
    rows = [json.loads(s) for s in (path / "evaluation.jsonl").read_text().splitlines()]
    for row in rows:
        if row["trial"] == 1:
            row["target_px"] = [30, 50]
    (path / "evaluation.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    second = analyze(path, results_root=tmp_path)
    for alpha in (0.1, 1.0, 10.0):
        assert second["models"][str(alpha)]["unseen"]["trials"][0]["bias_px"][0] == pytest.approx(
            20 + 100 * 511.875 / (8190 + alpha)
        )


def test_repeated_location_must_match_its_calibration_identity():
    from validation.gaze_model_replay import validate_plan

    labels = np.array([[[0.2, 0.5]], [[0.8, 0.5]]])
    with pytest.raises(ValueError, match="Repeated"):
        validate_plan(
            [dict(target=[0.8, 0.5], target_set="repeated", target_id=1)], labels, {"repeated": 2}
        )
