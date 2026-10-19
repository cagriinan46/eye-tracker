"""One-round local calibration repair policy; no camera or OS dependencies."""

import hashlib
import json
import time
from pathlib import Path

import numpy as np

POLICY = dict(
    min_pairs=20,
    min_paired_fraction=0.8,
    improvement_fraction=0.1,
    guard_tolerance_px=10,
    max_regions=2,
)


def propose(report, labels, size):
    worst = sorted(report["trials"], key=lambda t: t["filtered"]["mean_error_px"], reverse=True)[:2]
    training_positions = np.asarray(labels)[:, 0, :] * size
    indices = sorted(
        {int(np.argmin(np.linalg.norm(training_positions - t["target_px"], axis=1))) for t in worst}
    )
    return dict(
        problem_trials=[t["trial"] for t in worst],
        training_indices=indices,
        training_targets=[training_positions[i].tolist() for i in indices],
        policy=POLICY.copy(),
    )


def replace_features(original, replacements):
    result = np.array(original, copy=True)
    for index, values in replacements.items():
        values = np.asarray(values)
        if values.shape != result[index].shape or not np.isfinite(values).all():
            raise ValueError("Incomplete or invalid replacement calibration features")
        result[index] = values
    return result


def decide(rows, problem_trials):
    """Compare frozen models on paired fresh frames; no tuning on this selection set."""
    trials = []
    for trial in range(1, 7):
        group = [r for r in rows if r["trial"] == trial]
        pairs = [
            r
            for r in group
            if all(
                r.get(k) is not None and np.asarray(r[k]).shape == (2,) and np.isfinite(r[k]).all()
                for k in ("old_px", "candidate_px")
            )
        ]
        stats = dict(
            trial=trial,
            attempts=len(group),
            pairs=len(pairs),
            old_error_px=None,
            candidate_error_px=None,
        )
        if pairs:
            for name in ("old", "candidate"):
                stats[name + "_error_px"] = float(
                    np.mean(
                        [
                            np.linalg.norm(np.asarray(r[name + "_px"]) - r["target_px"])
                            for r in pairs
                        ]
                    )
                )
        trials.append(stats)
    result = dict(
        accept_candidate=False,
        reason="insufficient_paired_data",
        trials=trials,
        policy=POLICY.copy(),
        selection_only=True,
    )
    if any(
        t["pairs"] < POLICY["min_pairs"]
        or t["pairs"] < POLICY["min_paired_fraction"] * t["attempts"]
        for t in trials
    ):
        return result
    old = np.array([t["old_error_px"] for t in trials])
    new = np.array([t["candidate_error_px"] for t in trials])
    result.update(old_mean_px=float(old.mean()), candidate_mean_px=float(new.mean()))
    problems = [i - 1 for i in problem_trials]
    guards = [i for i in range(6) if i not in problems]
    if any(new[i] > old[i] + POLICY["guard_tolerance_px"] for i in guards):
        result["reason"] = "guard_regression"
    elif new.mean() >= old.mean() or new.mean() > old.mean() * (1 - POLICY["improvement_fraction"]):
        result["reason"] = "insufficient_overall_improvement"
    elif any(
        new[i] >= old[i] or new[i] > old[i] * (1 - POLICY["improvement_fraction"]) for i in problems
    ):
        result["reason"] = "insufficient_problem_improvement"
    else:
        result.update(accept_candidate=True, reason="paired_improvement")
    return result


def execute(
    *,
    folder,
    original,
    features,
    labels,
    proposal,
    targets,
    size,
    controller_factory,
    observe,
    draw,
    poll,
    wait_ready,
    usable,
    write_new,
):
    """Collect once, fit a separate model, then compare on the same new frames.

    Callbacks belong to the experiment UI. Escape exits; collection/fit failure
    retains the original. Every artifact is new and original arrays are copied.
    """
    directory = folder / "repair-1"
    directory.mkdir(exist_ok=False)
    write_new(
        directory / "proposal.json",
        dict(
            proposal, implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ),
    )
    outcome = dict(accept_candidate=False, reason="interrupted")
    try:
        c = controller_factory()
        c.new_session()
        indices = proposal["training_indices"]
        wait_ready(
            lambda: draw(
                labels[indices[0], 0], f"{len(indices)} HEDEF YENIDEN TOPLAMA | Hazirsan ENTER"
            )
        )
        replacements = {}
        for order, index in enumerate(indices, 1):
            c._current_index = index + 1
            c._n_frame_added = 0
            c.update_position()
            draw((c.x, c.y), f"YENIDEN TOPLAMA {order}/{len(indices)} | Sari noktaya bak")
            c._each_point_onset_time = time.time()
            start = time.monotonic()
            while c._current_index == index + 1:
                poll()
                if time.monotonic() - start > 15:
                    outcome["reason"] = "collection_timeout"
                    return original, outcome
                _, face, gaze, _, _ = observe()
                if not usable(face, gaze):
                    gaze.status = False
                c.add_cali_feature(gaze, face)
            replacements[index] = np.asarray(c.feature_vectors[index], dtype=np.float32)
            with (directory / f"replacement-{index + 1}.npy").open("xb") as stream:
                np.save(stream, replacements[index], allow_pickle=False)
        candidate_features = replace_features(features, replacements)
        with (directory / "candidate-calibration.npz").open("xb") as stream:
            np.savez_compressed(stream, features=candidate_features, labels=labels)
        candidate = type(original)(alpha=original.alpha)
        ok, error, _ = candidate.calibrate(
            candidate_features.reshape(-1, 258), labels.reshape(-1, 2)
        )
        if not ok or not np.isfinite(candidate.weights).all():
            outcome["reason"] = "candidate_fit_failed"
            return original, outcome
        with (directory / "candidate-weights.npy").open("xb") as stream:
            np.save(stream, candidate.weights, allow_pickle=False)
        write_new(directory / "fit.json", dict(training_error_normalized=float(error)))
        write_new(
            directory / "comparison-plan.json",
            dict(
                targets=[np.asarray(t).tolist() for t in targets],
                settle_seconds=0.8,
                sample_seconds=3.0,
                paired=True,
                metric="raw_unclipped_pixel_distance",
                selection_only=True,
            ),
        )
        wait_ready(lambda: draw(targets[0], "ESKI/YENI KARSILASTIRMA (~23 saniye) | ENTER"))
        rows = []
        with (directory / "comparison.jsonl").open("x") as stream:
            for trial, target in enumerate(targets, 1):
                draw(target, f"KARSILASTIRMA {trial}/6 | Sari noktaya bak")
                start = time.monotonic()
                while True:
                    poll()
                    _, face, gaze, _, captured_at = observe()
                    elapsed = captured_at - start
                    if elapsed >= 3.8:
                        break
                    row = dict(
                        trial=trial,
                        seconds=elapsed,
                        target_px=(np.asarray(target) * size).tolist(),
                        old_px=None,
                        candidate_px=None,
                    )
                    if usable(face, gaze):
                        for name, model in (("old", original), ("candidate", candidate)):
                            ok, point = model.predict(gaze.features, gaze.raw_gaze_coordinates)
                            if ok and np.asarray(point).shape == (2,) and np.isfinite(point).all():
                                row[name + "_px"] = (np.asarray(point) * size).tolist()
                    if elapsed >= 0.8:
                        rows.append(row)
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stream.flush()
        outcome = decide(rows, proposal["problem_trials"])
        return (candidate if outcome["accept_candidate"] else original), outcome
    except Exception as exc:
        outcome = dict(
            accept_candidate=False,
            reason="interrupted" if isinstance(exc, InterruptedError) else "failed",
            error=type(exc).__name__,
        )
        raise
    finally:
        write_new(directory / "decision.json", outcome)
