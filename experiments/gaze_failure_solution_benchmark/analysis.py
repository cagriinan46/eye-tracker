"""Descriptive target-residual diagnosis; never fits a target-derived correction."""

from itertools import combinations
from math import hypot
from statistics import mean, median

from validation.real_calibration import percentile


def _summary(records: list[dict]) -> dict:
    samples = [
        row for record in records for row in record["samples"] if row["prediction"] is not None
    ]
    late = [
        row
        for record in records
        for row in record["samples"]
        if row["prediction"] is not None and row["timestamp"] >= record["target_onset"] + 3.0
    ]
    signed_x = [row["prediction"][0] - row["target_x"] for row in samples]
    signed_y = [row["prediction"][1] - row["target_y"] for row in samples]
    late_y = [row["prediction"][1] - row["target_y"] for row in late]
    spreads = []
    late_spreads = []
    for record in records:
        y_values = [
            row["prediction"][1] for row in record["samples"] if row["prediction"] is not None
        ]
        if y_values:
            spreads.append(max(0.0, percentile(y_values, 95) - percentile(y_values, 5)))
        late_values = [
            row["prediction"][1]
            for row in record["samples"]
            if row["prediction"] is not None and row["timestamp"] >= record["target_onset"] + 3.0
        ]
        if len(late_values) >= 2:
            late_spreads.append(max(0.0, percentile(late_values, 95) - percentile(late_values, 5)))
    return {
        "trials": len(records),
        "samples": len(samples),
        "median_signed_x_bias": median(signed_x) if signed_x else None,
        "median_signed_y_bias": median(signed_y) if signed_y else None,
        "x_mae": mean(abs(value) for value in signed_x) if signed_x else None,
        "y_mae": mean(abs(value) for value in signed_y) if signed_y else None,
        "late_samples": len(late),
        "late_median_signed_y_bias": median(late_y) if late_y else None,
        "median_within_trial_y_p95_p05": median(spreads) if spreads else None,
        "late_trials_with_spread": len(late_spreads),
        "median_late_within_trial_y_p95_p05": median(late_spreads) if late_spreads else None,
    }


def diagnose_records(records: list[dict]) -> dict:
    """Describe residual patterns from fixed, logged evaluation targets only."""
    repeat_x, repeat_y, repeat_e = [], [], []
    for session in sorted({record["session"] for record in records}):
        for target in sorted({record["target_id"] for record in records}):
            matching = [
                record
                for record in records
                if record["session"] == session and record["target_id"] == target
            ]
            medians = []
            for record in matching:
                predictions = [
                    row["prediction"] for row in record["samples"] if row["prediction"] is not None
                ]
                if predictions:
                    medians.append(
                        (
                            median(value[0] for value in predictions),
                            median(value[1] for value in predictions),
                        )
                    )
            for left, right in combinations(medians, 2):
                dx, dy = abs(right[0] - left[0]), abs(right[1] - left[1])
                repeat_x.append(dx)
                repeat_y.append(dy)
                repeat_e.append(hypot(dx, dy))
    return {
        "pooled": _summary(records),
        "by_session": {
            session: _summary([record for record in records if record["session"] == session])
            for session in sorted({record["session"] for record in records})
        },
        "by_row": {
            str(y): _summary([record for record in records if record["target_y"] == y])
            for y in (0.2, 0.5, 0.8)
        },
        "by_column": {
            str(x): _summary([record for record in records if record["target_x"] == x])
            for x in (0.2, 0.5, 0.8)
        },
        "by_target": {
            target: _summary([record for record in records if record["target_id"] == target])
            for target in sorted({record["target_id"] for record in records})
        },
        "repeated_target_pairs": len(repeat_y),
        "repeated_target_x_difference_median": median(repeat_x) if repeat_x else None,
        "repeated_target_y_difference_median": median(repeat_y) if repeat_y else None,
        "repeated_target_euclidean_difference_median": median(repeat_e) if repeat_e else None,
        "repeated_target_y_difference_p95": percentile(repeat_y, 95) if repeat_y else None,
    }
