"""Deterministic development scenarios, never a human-accuracy benchmark."""

import json
from dataclasses import asdict

from eye_tracker.intent.targeting import (
    GazePoint,
    TargetingConfig,
    TargetResolver,
    select_target,
)
from eye_tracker.intent.targets import TargetRect, UISnapshot, UITarget

CONFIG = TargetingConfig(
    radius=50,
    separation=10,
    stable_seconds=0.1,
    max_sample_gap=0.08,
    max_snapshot_age=0.5,
    max_gaze_age=0.05,
)


def run_comparison() -> dict:
    screen = TargetRect(0, 0, 500, 500)
    a = UITarget("a", "button", TargetRect(100, 100, 20, 20), True, "press")
    b = UITarget("b", "button", TargetRect(130, 100, 20, 20), True, "press")
    parent = UITarget("parent", "button", TargetRect(90, 90, 50, 50), True, "press")
    # Intended labels are specified independently of predictions. The dense case
    # intentionally alternates around the midpoint while intended target stays a.
    scenarios = {
        "isolated_offset": ((a,), "a", [(125, True)] * 5),
        "dense_boundary": (
            (a, b),
            "a",
            [(124, True), (126, True), (124, True), (126, True), (124, True)],
        ),
        "nested_overlap": ((a, parent), "a", [(110, True)] * 5),
        "tracking_loss": ((a,), "a", [(125, True)] * 3 + [(125, False), (125, True)]),
    }
    report = {"synthetic_only": True, "config": asdict(CONFIG), "scenarios": {}}
    for name, (targets, intended, samples) in scenarios.items():
        snapshot = UISnapshot(name, 1, "synthetic", screen, targets, "ok")
        methods = {}
        for method in ("coordinate", "nearest", "conservative"):
            resolver = TargetResolver(CONFIG)
            metrics = dict(
                correct=0, wrong=0, abstentions=0, switches=0, first_correct_seconds=None
            )
            previous_candidate = None
            for index, (x, valid) in enumerate(samples):
                now = 1 + index * 0.06
                gaze = GazePoint(x, 110, now, valid)
                kwargs = dict(now=now, context_id="synthetic")
                decision = (
                    resolver.update(gaze, snapshot, **kwargs)
                    if method == "conservative"
                    else select_target(gaze, snapshot, config=CONFIG, method=method, **kwargs)
                )
                if decision.target is None:
                    metrics["abstentions"] += 1
                    continue
                target_id = decision.target.target_id
                if previous_candidate is not None and target_id != previous_candidate:
                    metrics["switches"] += 1
                previous_candidate = target_id
                if target_id == intended:
                    metrics["correct"] += 1
                    if metrics["first_correct_seconds"] is None:
                        metrics["first_correct_seconds"] = round(now - 1, 6)
                else:
                    metrics["wrong"] += 1
            methods[method] = metrics
        report["scenarios"][name] = {"samples": len(samples), "methods": methods}
    return report


def main() -> int:
    print(json.dumps(run_comparison(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
