"""Compare single-camera and fused vertical candidates (Issue #90); see README.md.

Both cameras are scored on the same presentations: those with enough common
frames in **both** cameras. Single-camera candidates are the frozen Issue #77
candidates, unchanged. Fusion candidates and the decision margins below are
preregistered before any Issue #90 session.
"""

import argparse
import json
import sys
from collections import defaultdict
from statistics import fmean

from experiments.vertical_signal_comparison import analysis as frozen

CAMERAS = ("top", "bottom")
# Preregistered for Issue #90 before any session; do not tune.
FUSION_BETTER_MARGIN = 0.01
BOTTOM_BETTER_MARGIN = 0.02  # Issue #88 rule, replicated with simultaneous frames
LATE_SOURCE = "COMBO"
SPLIT_FEATURES = ("top_opening", "bottom_vertical", "bottom_blend", "top_pitch")


def camera_report(report: dict, camera: str, keep: set[int] | None = None) -> dict:
    """One camera's rows in Issue #77 report shape, optionally limited to presentations."""
    rows = [
        row
        for row in report["rows"]
        if row["camera"] == camera and (keep is None or row["presentation"] in keep)
    ]
    return {"participant": report["participant"], "session": report["session"], "rows": rows}


def common_presentations(report: dict) -> set[int]:
    """Presentations with at least the frozen minimum of common frames in every camera."""
    available = [
        {
            record["presentation"]
            for record in frozen.presentation_medians(camera_report(report, camera)["rows"])
            if record["available"]
        }
        for camera in CAMERAS
    ]
    return set.intersection(*available)


def _joined_records(per_camera: dict[str, list[dict]]) -> list[dict]:
    """Per-presentation records carrying both cameras' medians under prefixed names."""
    by_presentation: dict[int, dict] = defaultdict(dict)
    for camera, records in per_camera.items():
        for record in records:
            joined = by_presentation[record["presentation"]]
            for key in ("presentation", "phase", "target_id", "target_x", "target_y"):
                joined[key] = record[key]
            joined["trial_number"] = record["trial_number"]
            for name in (*frozen.BASE_FEATURES, "opening_squared"):
                joined[f"{camera}_{name}"] = record[name]
            joined.setdefault("_cameras", set()).add(camera)
    return [
        {key: value for key, value in record.items() if key != "_cameras"}
        for _, record in sorted(by_presentation.items())
        if record["_cameras"] == set(CAMERAS)
    ]


def _prefixed(camera: str, features: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{camera}_{name}" for name in features)


def _metrics(calibration, validation, checkpoints, predict_one) -> dict:
    metrics = frozen.score([(r, predict_one(r)) for r in validation], "target_y")
    drift = defaultdict(dict)
    for record in checkpoints:
        drift[record["target_id"]][record["trial_number"]] = predict_one(record)
    per_target = {
        target: blocks[3] - blocks[1] if 1 in blocks and 3 in blocks else None
        for target, blocks in sorted(drift.items())
    }
    values = [r["target_y"] for r in calibration]
    mean_value = fmean(values)
    total = sum((value - mean_value) ** 2 for value in values)
    residual = sum((r["target_y"] - predict_one(r)) ** 2 for r in calibration)
    return {
        "available": True,
        "calibration_r_squared": 1 - residual / total if total > 0 else 0.0,
        **metrics,
        "passes": frozen.passes(metrics),
        "checkpoint_last_minus_first": per_target,
    }


def fusion_candidates(joined: list[dict]) -> dict:
    """LATE: mean of each camera's own COMBO prediction. SPLIT: one OLS on mixed inputs."""
    calibration = [r for r in joined if r["phase"] == "calibration"]
    validation = [r for r in joined if r["phase"] == "validation"]
    checkpoints = [r for r in joined if r["phase"] == "checkpoint"]
    combo = frozen.CANDIDATES[LATE_SOURCE]
    fits = {
        camera: frozen.fit(calibration, _prefixed(camera, combo), "target_y") for camera in CAMERAS
    }
    results: dict[str, dict] = {}
    if any(coefficients is None for coefficients in fits.values()):
        results["LATE"] = {"available": False, "passes": False}
    else:

        def late(record: dict) -> float:
            return fmean(
                frozen.predict(fits[camera], record, _prefixed(camera, combo)) for camera in CAMERAS
            )

        results["LATE"] = _metrics(calibration, validation, checkpoints, late)
    split = frozen.fit(calibration, SPLIT_FEATURES, "target_y")
    if split is None:
        results["SPLIT"] = {"available": False, "passes": False}
    else:
        results["SPLIT"] = {
            "coefficients": split,
            **_metrics(
                calibration,
                validation,
                checkpoints,
                lambda record: frozen.predict(split, record, SPLIT_FEATURES),
            ),
        }
    return results


def analyze_session(report: dict) -> dict:
    """Score both cameras and the fusions on the same common presentations."""
    keep = common_presentations(report)
    cameras = {
        camera: frozen.analyze_session(camera_report(report, camera, keep)) for camera in CAMERAS
    }
    summary = {
        "participant": report["participant"],
        "session": report["session"],
        "common_presentations": len(keep),
        "valid": all(result["valid"] for result in cameras.values()),
        "cameras": cameras,
        "inter_camera_gap_ms": _inter_camera_gap_ms(report["rows"]),
    }
    if not summary["valid"]:
        return {**summary, "fusion": {}}
    per_camera = {
        camera: [
            record
            for record in frozen.presentation_medians(camera_report(report, camera, keep)["rows"])
            if record["available"]
        ]
        for camera in CAMERAS
    }
    return {**summary, "fusion": fusion_candidates(_joined_records(per_camera))}


def _inter_camera_gap_ms(rows: list[dict]) -> dict | None:
    """Descriptive: bottom minus top frame timestamp within each loop."""
    stamps: dict[int, dict[str, int]] = defaultdict(dict)
    for row in rows:
        if row.get("timestamp_ns") is not None and "loop" in row:
            stamps[row["loop"]][row["camera"]] = row["timestamp_ns"]
    gaps = sorted(
        (pair["bottom"] - pair["top"]) / 1e6
        for pair in stamps.values()
        if "top" in pair and "bottom" in pair
    )
    if not gaps:
        return None
    return {"loops": len(gaps), "median": gaps[len(gaps) // 2], "max": gaps[-1]}


def method_results(session: dict) -> dict[str, dict]:
    """Flat view: TOP:<candidate>, BOTTOM:<candidate>, LATE, SPLIT."""
    flat = {}
    for camera in CAMERAS:
        for name, result in session["cameras"][camera]["candidates"].items():
            flat[f"{camera.upper()}:{name}"] = result
    flat.update(session["fusion"])
    return flat


def combine(sessions: list[dict]) -> dict:
    """Apply the preregistered Issue #90 decision rule across sessions of one participant."""
    keys = [(s["participant"], s["session"]) for s in sessions]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate participant/session")
    if len({s["participant"] for s in sessions}) != 1:
        raise ValueError("combine one participant at a time")
    complete = len(sessions) >= 2 and all(s["valid"] for s in sessions)
    ranking = []
    if complete:
        flats = [method_results(s) for s in sessions]
        for method in flats[0]:
            results = [flat.get(method, {}) for flat in flats]
            if all(result.get("available") for result in results):
                ranking.append(
                    {
                        "method": method,
                        "mean_y_mae": fmean(result["mae"] for result in results),
                        "passes_all_sessions": all(result["passes"] for result in results),
                    }
                )
        ranking.sort(key=lambda item: item["mean_y_mae"])

    def best(prefix: str) -> dict | None:
        matches = [item for item in ranking if item["method"].startswith(prefix)]
        return matches[0] if matches else None

    def mae(method: str) -> float | None:
        return next((i["mean_y_mae"] for i in ranking if i["method"] == method), None)

    best_top, best_bottom = best("TOP:"), best("BOTTOM:")
    singles = [item for item in (best_top, best_bottom) if item is not None]
    best_single = min(singles, key=lambda item: item["mean_y_mae"]) if singles else None

    def beats(value: float | None, reference: dict | None, margin: float) -> bool | None:
        if not complete or value is None or reference is None:
            return None
        return value <= reference["mean_y_mae"] - margin

    return {
        "participant": sessions[0]["participant"],
        "sessions": [s["session"] for s in sessions],
        "complete": complete,
        "best_top": best_top,
        "best_bottom": best_bottom,
        "best_single": best_single,
        "fusion_better_primary_late": beats(mae("LATE"), best_single, FUSION_BETTER_MARGIN),
        "fusion_better_secondary_split": beats(mae("SPLIT"), best_single, FUSION_BETTER_MARGIN),
        "bottom_better_than_top": beats(
            best_bottom and best_bottom["mean_y_mae"], best_top, BOTTOM_BETTER_MARGIN
        ),
        "vertical_solved_by_fusion": (
            any(i["passes_all_sessions"] for i in ranking if i["method"] in ("LATE", "SPLIT"))
            if complete
            else None
        ),
        "methods_passing_all_sessions": [i["method"] for i in ranking if i["passes_all_sessions"]],
        "ranking": ranking,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=argparse.FileType("r", encoding="utf-8"))
    args = parser.parse_args(argv)
    try:
        sessions = [analyze_session(json.load(handle)) for handle in args.datasets]
        output = {"sessions": sessions, "combined": combine(sessions)}
        print(json.dumps(output, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError) as error:
        print(f"Cannot analyze dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
