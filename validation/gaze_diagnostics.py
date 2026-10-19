"""Read-only statistics for explicit live SVR sessions; never fit or run an evaluator.

Only named, non-symlink session directories directly under validation/results are
accepted. Output goes to a new directory. Historical captures/environments are
not searched. Associations are descriptive, not evidence of causality/accuracy.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import numpy as np

FEATURES = ("horizontal", "vertical", "head_pitch_deg", "head_yaw_deg", "head_roll_deg")
RESULTS = Path(__file__).resolve().parents[1] / "validation/results"
SETTLING = 0.8
PROBE_SAMPLE_SECONDS = 3.0


def valid_point(point):
    return (
        isinstance(point, (tuple, list))
        and len(point) == 2
        and all(isinstance(v, (int, float)) and np.isfinite(v) for v in point)
    )


def eligible(row):
    fields = (*FEATURES, "blink_left", "blink_right")
    return (
        row.get("status") == "usable"
        and all(isinstance(row.get(k), (int, float)) and np.isfinite(row[k]) for k in fields)
        and max(row["blink_left"], row["blink_right"]) <= 0.5
    )


def correlation(a, b):
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def error_summary(points, target, size):
    """Unclipped error vs displayed target, plus dispersion around mean prediction.

    Missing predictions remain in the availability/target-hit denominator.
    Centered RMS is dispersion, not an isolated physiological jitter estimate.
    """
    points = list(points)
    good = [p for p in points if valid_point(p)]
    result = dict(
        attempts=len(points),
        valid=len(good),
        bias_px=None,
        mean_distance_px=None,
        p95_distance_px=None,
        centered_rms_px=None,
        within_30px_fraction_all_attempts=None,
    )
    if not points:
        return result
    result["within_30px_fraction_all_attempts"] = 0.0
    if not good:
        return result
    errors = (np.asarray(good) - target) * size
    bias = errors.mean(axis=0)
    distances = np.linalg.norm(errors, axis=1)
    result.update(
        bias_px=bias.tolist(),
        mean_distance_px=float(distances.mean()),
        p95_distance_px=float(np.percentile(distances, 95)),
        centered_rms_px=float(np.sqrt(np.mean(np.sum((errors - bias) ** 2, axis=1)))),
        within_30px_fraction_all_attempts=float(np.sum(distances <= 30) / len(points)),
    )
    return result


def calibration_quality(rows):
    groups = defaultdict(list)
    source = [r for r in rows if r.get("phase") == "calibration" and r.get("camera") == "macbook"]
    for row in source:
        if eligible(row):
            groups[row["presentation"]].append(row)
    targets = []
    for number, group in sorted(groups.items()):
        array = np.asarray([[r[k] for k in FEATURES] for r in group])
        targets.append(
            dict(
                presentation=number,
                target=[group[0]["target_x"], group[0]["target_y"]],
                count=len(group),
                sufficient_frames=len(group) >= 5,
                median=dict(zip(FEATURES, np.median(array, axis=0).tolist())),
                iqr=dict(
                    zip(FEATURES, np.subtract(*np.percentile(array, [75, 25], axis=0)).tolist())
                ),
            )
        )
    sufficient = [t for t in targets if t["sufficient_frames"]]
    features = {}
    for key in FEATURES:
        medians = [t["median"][key] for t in sufficient]
        features[key] = dict(
            median_span=float(np.ptp(medians)) if medians else None,
            median_within_target_iqr=float(np.median([t["iqr"][key] for t in sufficient]))
            if sufficient
            else None,
            correlation_target_x=correlation(medians, [t["target"][0] for t in sufficient]),
            correlation_target_y=correlation(medians, [t["target"][1] for t in sufficient]),
            correlation_presentation_order=correlation(
                medians, [t["presentation"] for t in sufficient]
            ),
        )
    return dict(
        input_rows=len(source),
        eligible_rows=sum(t["count"] for t in targets),
        excluded_rows=len(source) - sum(t["count"] for t in targets),
        rejected_during_original_collection="unknown; not recoverable from accepted-only records",
        sufficient_targets=len(sufficient),
        targets=targets,
        features=features,
    )


def coordinate_audit(records, desktop, size):
    result = dict(
        compared=0,
        mismatches=0,
        max_error_px=None,
        drawable_region_size_matches=None,
        physical_screen_alignment_verified=False,
    )
    if desktop is None:
        return result
    left, top, width, height = desktop["region"]
    sw, sh = desktop["screen_size"]
    result["drawable_region_size_matches"] = bool(
        np.allclose([width, height], size, atol=1, rtol=0)
    )
    errors = []
    for row in records:
        point = row.get("displayed_predictions", {}).get("point")
        pixel = (row.get("desktop_action") or {}).get("pixel")
        if not valid_point(point) or not valid_point(pixel):
            continue
        expected = [
            min(sw - 1, round(left + point[0] * width)),
            min(sh - 1, round(top + point[1] * height)),
        ]
        errors.append(max(abs(a - b) for a, b in zip(expected, pixel)))
    result.update(
        compared=len(errors),
        mismatches=sum(e != 0 for e in errors),
        max_error_px=max(errors) if errors else None,
    )
    return result


def live_segments(records, size):
    groups = []
    previous = None
    for row in records:
        if not valid_point(row.get("target")):
            continue
        probe = row.get("diagnostic") or {}
        key = (tuple(row["target"]), probe.get("condition"), probe.get("trial"))
        if key != previous or row.get("target_changed"):
            groups.append([])
        groups[-1].append(row)
        previous = key
    output = []
    for group in groups:
        first = group[0]
        sampled = [
            r
            for r in group
            if (
                r["diagnostic"]["sampling"]
                if r.get("diagnostic")
                else r["seconds"] - first["seconds"] >= SETTLING
            )
        ]
        if not sampled:
            continue
        signals = [r.get("signals", {}).get("macbook", {}) for r in sampled]
        good = [s for s in signals if eligible(s)]
        output.append(
            dict(
                target=first["target"],
                condition=(first.get("diagnostic") or {}).get("condition", "uncontrolled"),
                trial=(first.get("diagnostic") or {}).get("trial"),
                start_seconds=first["seconds"],
                gaze_on_target_verified=False,
                instruction_controlled=bool(first.get("diagnostic")),
                raw=error_summary(
                    [r.get("predictions", {}).get("point") for r in sampled], first["target"], size
                ),
                smoothed=error_summary(
                    [r.get("displayed_predictions", {}).get("point") for r in sampled],
                    first["target"],
                    size,
                ),
                feature_medians={
                    k: float(np.median([s[k] for s in good])) if good else None for k in FEATURES
                },
            )
        )
    return output


def probe_schedule():
    """Same five targets twice; no fitting, target snapping or automatic retries."""
    targets = ((0.5, 0.5), (0.2, 0.2), (0.8, 0.8), (0.8, 0.2), (0.2, 0.8))
    return [
        dict(condition=condition, target=list(target), trial=i + 1)
        for condition in ("baseline", "after_position_change")
        for i, target in enumerate(targets)
    ]


def read_session(path, root=RESULTS):
    path, root = Path(path).absolute(), Path(root).resolve()
    if (
        path.parent != root
        or path.resolve() != path
        or not path.name.startswith("cagri-live-macbook-svr-")
    ):
        raise ValueError(
            "Only direct, non-symlink live MacBook SVR session directories are allowed"
        )
    payloads, hashes = {}, {}
    for name in (
        "session.json",
        "calibration.json",
        "live.jsonl",
        "desktop.json",
        "completion.json",
    ):
        file = path / name
        if file.is_symlink():
            raise ValueError("Symlink inputs are forbidden")
        if not file.exists() and name in ("desktop.json", "completion.json"):
            continue
        payload = file.read_bytes()
        hashes[name] = hashlib.sha256(payload).hexdigest()
        payloads[name] = (
            [json.loads(line) for line in payload.splitlines() if line.strip()]
            if name.endswith("jsonl")
            else json.loads(payload)
        )
    cal, records = payloads["calibration.json"], payloads["live.jsonl"]
    quality = calibration_quality(cal["rows"])
    eligible_live = [r.get("signals", {}).get("macbook", {}) for r in records]
    eligible_live = [r for r in eligible_live if eligible(r)]
    envelope = {}
    for key in FEATURES:
        values = [t["median"][key] for t in quality["targets"] if t["sufficient_frames"]]
        if values and eligible_live:
            lo, hi = min(values), max(values)
            envelope[key] = dict(
                calibration_median_range=[lo, hi],
                fraction_live_outside=float(
                    np.mean([not lo <= r[key] <= hi for r in eligible_live])
                ),
            )
    report = dict(
        session=path.name,
        metadata=payloads["session.json"],
        mapping=cal["mapping"],
        size=cal["window_image_area"],
        completion=payloads.get("completion.json"),
        live_rows=len(records),
        calibration=quality,
        live_feature_envelope=envelope,
        coordinate_audit=coordinate_audit(
            records, payloads.get("desktop.json"), cal["window_image_area"]
        ),
        segments=live_segments(records, cal["window_image_area"]),
        source_sha256=hashes,
    )
    # Detect external modification during analysis; never write to input folders.
    for name, digest in hashes.items():
        if hashlib.sha256((path / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Session changed during analysis")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", type=Path, nargs="+")
    args = parser.parse_args()
    reports = [read_session(path) for path in args.sessions]
    folder = RESULTS / ("gaze-diagnostic-audit-" + uuid4().hex)
    folder.mkdir()
    with (folder / "report.json").open("x") as file:
        json.dump(
            dict(
                analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                limitations="Descriptive only; no fits, tuning, causal claims or verified fixation. "
                "Sessions are separate; old visible-feedback logs are not controlled validation.",
                sessions=reports,
            ),
            file,
            indent=2,
            allow_nan=False,
        )
    lines = [
        "# Gaze diagnostic audit",
        "",
        "No model fitting or participant capture. Sessions remain separate.",
        "Target-relative errors from old free-viewing logs are not validated gaze accuracy.",
        "",
    ]
    for report in reports:
        c, a = report["calibration"], report["coordinate_audit"]
        lines.extend(
            [
                f"## {report['session']}",
                "",
                f"Model: {report['mapping']['kind']}; targets: {c['sufficient_targets']}",
                f"Coordinate records compared: {a['compared']}; mismatches: {a['mismatches']}.",
                "Physical window/cursor alignment remains unverified.",
                "",
                "| Feature | Median range width | Typical within-target IQR | Correlation with target Y |",
                "|---|---:|---:|---:|",
            ]
        )
        for key, stats in c["features"].items():
            lines.append(
                f"| {key} | {stats['median_span']} | {stats['median_within_target_iqr']} | {stats['correlation_target_y']} |"
            )
        lines.append("")
    with (folder / "REPORT.md").open("x") as file:
        file.write("\n".join(lines) + "\n")
    print(folder)


if __name__ == "__main__":
    main()
