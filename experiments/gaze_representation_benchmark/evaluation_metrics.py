"""Frozen aggregate windows/metrics/gates; no representation or fitting calls."""

from itertools import combinations
from math import hypot, isfinite
from statistics import fmean, median

from experiments.fixed_window_gaze_diagnostic.analysis import robust
from validation.real_calibration import percentile

AXES = {"horizontal": ("h", "target_x", "target_y"), "vertical": ("v", "target_y", "target_x")}
LEVELS = (0.2, 0.5, 0.8)


def ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator <= 0:
        return None
    result = numerator / denominator
    return result if isfinite(result) else None


def _complete_median(values):
    return median(values) if values and all(v is not None for v in values) else None


def _delta(a, b):
    return b - a if a is not None and b is not None else None


def _absolute(value):
    return abs(value) if value is not None else None


def _values(presentation, key, half=None):
    return [
        r[key]
        for r in presentation["samples"]
        if r[key] is not None and (half is None or (r["t"] >= 1.5) == (half == "second"))
    ]


def _medians(presentations, key):
    return [_complete_median(_values(p, key)) for p in presentations]


def _ordering(presentations, key, coordinate, direction):
    levels = [
        _complete_median(_medians([p for p in presentations if p[coordinate] == level], key))
        for level in LEVELS
    ]
    steps = [_delta(levels[k], levels[k + 1]) for k in (0, 1)]
    complete = all(v is not None for v in steps)
    return {
        "level_medians": levels,
        "signed_adjacent_separations": steps,
        "minimum_separation": min(abs(v) for v in steps) if complete else None,
        "ordered": all(v * direction > 0 for v in steps) if complete and direction else None,
    }


def axis_diagnostics(calibration, trials, axis, slope=None):
    key, coordinate, orthogonal = AXES[axis]
    cal_levels = [
        _complete_median(_medians([p for p in calibration if p[coordinate] == level], key))
        for level in LEVELS
    ]
    steps = [_delta(cal_levels[k], cal_levels[k + 1]) for k in (0, 1)]
    direction = None
    if all(v is not None for v in steps):
        direction = 1 if all(v > 0 for v in steps) else -1 if all(v < 0 for v in steps) else None
    cal_separation = min(abs(v) for v in steps) if all(v is not None for v in steps) else None
    ordering = {}
    for block in ("pooled", 1, 2, 3):
        subset = [p for p in trials if block == "pooled" or p["block"] == block]
        name = "pooled" if block == "pooled" else f"block-{block}"
        ordering[name] = _ordering(subset, key, coordinate, direction)
        for fixed in LEVELS:
            conditional = [p for p in subset if p[orthogonal] == fixed]
            prefix = "column" if axis == "vertical" else "row"
            ordering[f"{prefix}-{fixed:g}/{name}"] = _ordering(
                conditional, key, coordinate, direction
            )
    separation = ordering["pooled"]["minimum_separation"]
    within = []
    for p in trials:
        stats = robust(_values(p, key))
        first, second = (robust(_values(p, key, h)) for h in ("first", "second"))
        half_shift = _delta(first["median"], second["median"])
        within.append(
            {
                "order": p["order"],
                "target_id": p["target_id"],
                "block": p["block"],
                **stats,
                "mad_over_separation": ratio(stats["mad"], separation),
                "iqr_over_separation": ratio(stats["iqr"], separation),
                "first_half": first,
                "second_half": second,
                "half_shift": half_shift,
                "absolute_half_shift": _absolute(half_shift),
            }
        )
    targets = []
    for cal in calibration:
        target_trials = [
            p
            for p in trials
            if (p["target_x"], p["target_y"]) == (cal["target_x"], cal["target_y"])
        ]
        target_trials.sort(key=lambda p: p["block"])
        cal_median = _complete_median(_values(cal, key))
        block_medians = _medians(target_trials, key)
        val_median = _complete_median(block_medians) if len(block_medians) == 3 else None
        signed = _delta(cal_median, val_median)
        pairwise = [_delta(a, b) for a, b in combinations(block_medians, 2)]
        complete_blocks = len(block_medians) == 3 and all(v is not None for v in block_medians)
        distribution = robust([v for p in target_trials for v in _values(p, key)])
        half_medians = {
            h: _complete_median([_complete_median(_values(p, key, h)) for p in target_trials])
            if len(target_trials) == 3
            else None
            for h in ("first", "second")
        }
        first_transfer, second_transfer = (
            _delta(cal_median, half_medians[h]) for h in ("first", "second")
        )
        targets.append(
            {
                "target_id": cal["target_id"],
                "target_x": cal["target_x"],
                "target_y": cal["target_y"],
                "calibration_median": cal_median,
                "validation_median": val_median,
                "signed_transfer": signed,
                "absolute_transfer": _absolute(signed),
                "transfer_over_validation_separation": ratio(_absolute(signed), separation),
                "transfer_over_calibration_separation": ratio(_absolute(signed), cal_separation),
                "mapped_transfer": signed * slope
                if signed is not None and slope is not None
                else None,
                "block_medians": block_medians,
                "pairwise_block_changes": pairwise,
                "mapped_pairwise_changes": [
                    v * slope if v is not None and slope is not None else None for v in pairwise
                ],
                "block_range": max(block_medians) - min(block_medians) if complete_blocks else None,
                "distribution": distribution,
                "mad_over_separation": ratio(distribution["mad"], separation),
                "iqr_over_separation": ratio(distribution["iqr"], separation),
                "first_half_validation_median": half_medians["first"],
                "second_half_validation_median": half_medians["second"],
                "first_half_transfer": first_transfer,
                "second_half_transfer": second_transfer,
                "absolute_first_half_transfer": _absolute(first_transfer),
                "absolute_second_half_transfer": _absolute(second_transfer),
            }
        )
    shifts = [t["absolute_transfer"] for t in targets]
    complete_transfer = len(shifts) == 9 and all(v is not None for v in shifts)
    transfer = median(shifts) if complete_transfer else None
    ranges = [t["block_range"] for t in targets]
    complete_ranges = len(ranges) == 9 and all(v is not None for v in ranges)
    summaries = {}
    for grouping in ("target_x", "target_y"):
        summaries[grouping] = [
            {
                "level": level,
                "signed_shift": robust(
                    [
                        t["signed_transfer"]
                        for t in targets
                        if t[grouping] == level and t["signed_transfer"] is not None
                    ]
                ),
                "absolute_shift": robust(
                    [
                        t["absolute_transfer"]
                        for t in targets
                        if t[grouping] == level and t["absolute_transfer"] is not None
                    ]
                ),
                "complete_targets": all(
                    t["absolute_transfer"] is not None for t in targets if t[grouping] == level
                ),
            }
            for level in LEVELS
        ]
    group_medians = {}
    for phase, presentations in (("calibration", calibration), ("validation", trials)):
        group_medians[phase] = {
            grouping: [
                {
                    "level": level,
                    "median": _complete_median(
                        _medians([p for p in presentations if p[grouping] == level], key)
                    ),
                }
                for level in LEVELS
            ]
            for grouping in ("target_x", "target_y")
        }
    return {
        "calibration_level_medians": cal_levels,
        "calibration_adjacent_separations": steps,
        "calibration_minimum_separation": cal_separation,
        "direction": direction,
        "calibration_group_medians": group_medians["calibration"],
        "validation_group_medians": group_medians["validation"],
        "ordering": ordering,
        "targets": targets,
        "transfer_by_level": summaries,
        "median_absolute_transfer": transfer,
        "normalized_transfer": ratio(transfer, separation),
        "normalized_transfer_calibration_separation": ratio(transfer, cal_separation),
        "median_block_range": median(ranges) if complete_ranges else None,
        "maximum_block_range": max(ranges) if complete_ranges else None,
        "within_presentations": within,
        "within_mad_summary": robust([p["mad"] for p in within if p["mad"] is not None]),
        "within_iqr_summary": robust([p["iqr"] for p in within if p["iqr"] is not None]),
        "absolute_half_shift_summary": robust(
            [p["absolute_half_shift"] for p in within if p["absolute_half_shift"] is not None]
        ),
    }


def screen_summary(rows):
    dx, dy = [r["dx"] for r in rows], [r["dy"] for r in rows]
    errors = [hypot(x, y) for x, y in zip(dx, dy, strict=True)]
    return {
        "count": len(rows),
        "x_mae": fmean(abs(v) for v in dx) if dx else None,
        "y_mae": fmean(abs(v) for v in dy) if dy else None,
        "x_bias": fmean(dx) if dx else None,
        "y_bias": fmean(dy) if dy else None,
        "mean_euclidean": fmean(errors) if errors else None,
        "median_euclidean": median(errors) if errors else None,
        "p95_euclidean": percentile(errors, 95) if errors else None,
        "x_residuals": robust(dx),
        "y_residuals": robust(dy),
        "x_absolute_errors": robust([abs(v) for v in dx]),
        "y_absolute_errors": robust([abs(v) for v in dy]),
    }


def _screen_rows(presentations):
    return [
        {"dx": r["prediction"][0] - p["target_x"], "dy": r["prediction"][1] - p["target_y"]}
        for p in presentations
        for r in p["samples"]
        if r["prediction"] is not None
    ]


def availability(presentations):
    rows = [r for p in presentations for r in p["samples"]]
    valid = [r for r in rows if r["h"] is not None and r["v"] is not None]
    reasons = {}
    for r in rows:
        if r["h"] is None or r["v"] is None:
            reason = r["reason"] or "unavailable feature geometry"
            reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "attempts": len(rows),
        "usable": len(valid),
        "usable_fraction": len(valid) / len(rows) if rows else None,
        "mapped": sum(r["prediction"] is not None for r in rows),
        "unavailable_reasons": reasons,
    }


def window_diagnostics(calibration, trials, mapping, start, end):
    selected = [
        {**p, "samples": [r for r in p["samples"] if start <= r["t"] < end]} for p in trials
    ]
    presentations = []
    for p in selected:
        halves = {}
        for axis, (key, _, _) in AXES.items():
            first, second = (robust(_values(p, key, h)) for h in ("first", "second"))
            shift = _delta(first["median"], second["median"])
            halves[axis] = {
                "first": first,
                "second": second,
                "signed_shift": shift,
                "absolute_shift": _absolute(shift),
            }
        presentations.append(
            {k: p[k] for k in ("target_id", "target_x", "target_y", "block", "order")}
            | {
                "horizontal": robust(_values(p, "h")),
                "vertical": robust(_values(p, "v")),
                "halves": halves,
                "screen": screen_summary(_screen_rows([p])),
                "availability": availability([p]),
            }
        )
    screen = {"all": screen_summary(_screen_rows(selected))}
    coverage = {"all": availability(selected)}
    for grouping in ("target_id", "target_x", "target_y", "block"):
        groups = sorted({p[grouping] for p in selected})
        screen[grouping] = [
            {"value": g, **screen_summary(_screen_rows([p for p in selected if p[grouping] == g]))}
            for g in groups
        ]
        coverage[grouping] = [
            {"value": g, **availability([p for p in selected if p[grouping] == g])} for g in groups
        ]
    features = {
        axis: axis_diagnostics(
            calibration,
            selected,
            axis,
            getattr(mapping, "x_slope" if axis == "horizontal" else "y_slope") if mapping else None,
        )
        for axis in AXES
    }
    return {
        "window_seconds": [start, end],
        "presentations": presentations,
        "features": features,
        "screen": screen,
        "availability": coverage,
    }


def common_frames(baseline, candidate):
    if len(baseline) != len(candidate):
        raise ValueError("common-frame comparisons require identical presentation schedules")
    shared_baseline, shared_candidate = [], []
    for a, b in zip(baseline, candidate, strict=True):
        if any(a[k] != b[k] for k in ("target_id", "target_x", "target_y", "block", "order")):
            raise ValueError("common-frame presentation identity mismatch")
        ka = {tuple(r["key"]) for r in a["samples"] if r["h"] is not None and r["v"] is not None}
        kb = {tuple(r["key"]) for r in b["samples"] if r["h"] is not None and r["v"] is not None}
        shared = ka & kb
        shared_baseline.append(
            {**a, "samples": [r for r in a["samples"] if tuple(r["key"]) in shared]}
        )
        shared_candidate.append(
            {**b, "samples": [r for r in b["samples"] if tuple(r["key"]) in shared]}
        )
    return shared_baseline, shared_candidate


def gate_comparison(baseline, candidate, provenance):
    base_screen, cand_screen = baseline["screen"]["all"], candidate["screen"]["all"]
    base_feature, cand_feature = baseline["features"]["vertical"], candidate["features"]["vertical"]
    y_ratio = ratio(cand_screen["y_mae"], base_screen["y_mae"])
    transfer_ratio = ratio(cand_feature["normalized_transfer"], base_feature["normalized_transfer"])
    x_ratio = ratio(cand_screen["x_mae"], base_screen["x_mae"])
    checks = base_feature["ordering"]
    candidate_checks = cand_feature["ordering"]
    correct = [k for k, v in checks.items() if v["ordered"] is True]
    lost = [
        k
        for k in correct
        if k not in candidate_checks or candidate_checks[k]["ordered"] is not True
    ]
    criteria = {
        "1": {"value": y_ratio, "threshold": 0.80, "pass": y_ratio is not None and y_ratio <= 0.80},
        "2": {
            "value": transfer_ratio,
            "threshold": 0.75,
            "pass": transfer_ratio is not None and transfer_ratio <= 0.75,
        },
        "3": {
            "value": {
                "r0_correct": len(correct),
                "candidate_correct": sum(v["ordered"] is True for v in candidate_checks.values()),
                "lost_checks": lost,
            },
            "pass": bool(checks)
            and set(checks) <= set(candidate_checks)
            and all(v["ordered"] is not None for v in checks.values())
            and all(v["ordered"] is not None for v in candidate_checks.values())
            and not lost,
        },
        "4": {"value": x_ratio, "threshold": 1.15, "pass": x_ratio is not None and x_ratio <= 1.15},
        "5": {"value": bool(provenance), "pass": bool(provenance)},
    }
    return {
        "criteria": criteria,
        "overall": "PROMISING" if all(c["pass"] for c in criteria.values()) else "FAIL",
    }
