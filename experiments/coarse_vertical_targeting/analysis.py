"""Score Issue #81 zone-targeting sessions with the preregistered rule (see README.md)."""

import argparse
import json
import sys
from collections import defaultdict
from statistics import median

from experiments.coarse_vertical_targeting.protocol import LAYOUTS, trial_schedule

# Preregistered on 2026-10-08 before any Issue #81 session; do not tune.
PASS_SUCCESS_RATE = 0.80
PASS_MAX_WRONG_RATE = 0.10


def _validate(report: dict) -> list[dict]:
    expected = trial_schedule(report["session"], report["seed"])
    outcomes = report["outcomes"]
    if len(outcomes) != len(expected):
        raise ValueError("session does not contain every planned trial")
    for outcome, trial in zip(outcomes, expected, strict=True):
        if outcome["layout"] != trial.layout or tuple(outcome["target"]) != trial.target:
            raise ValueError("trial order does not match the frozen schedule")
        if outcome["result"] not in {"success", "wrong", "timeout"}:
            raise ValueError("unknown trial result")
    return outcomes


def summarize_layout(outcomes: list[dict]) -> dict:
    total = len(outcomes)
    counts = {
        name: sum(o["result"] == name for o in outcomes) for name in ("success", "wrong", "timeout")
    }
    by_row: dict[int, list[dict]] = defaultdict(list)
    for outcome in outcomes:
        by_row[outcome["target"][0]].append(outcome)
    times = [o["selection_seconds"] for o in outcomes if o["result"] == "success"]
    success_rate = counts["success"] / total
    wrong_rate = counts["wrong"] / total
    return {
        "trials": total,
        **counts,
        "success_rate": success_rate,
        "wrong_rate": wrong_rate,
        "timeout_rate": counts["timeout"] / total,
        "median_success_seconds": median(times) if times else None,
        "success_by_target_row": {
            str(row): sum(o["result"] == "success" for o in items) / len(items)
            for row, items in sorted(by_row.items())
        },
        "wrong_selected_row_offsets": sorted(
            o["selected"][0] - o["target"][0] for o in outcomes if o["result"] == "wrong"
        ),
        "passes": success_rate >= PASS_SUCCESS_RATE and wrong_rate <= PASS_MAX_WRONG_RATE,
    }


def analyze_session(report: dict) -> dict:
    outcomes = _validate(report)
    return {
        "participant": report["participant"],
        "session": report["session"],
        "window_image_area": report.get("window_image_area"),
        "layouts": {
            layout: summarize_layout([o for o in outcomes if o["layout"] == layout])
            for layout in LAYOUTS
        },
    }


def combine(sessions: list[dict]) -> dict:
    keys = [(s["participant"], s["session"]) for s in sessions]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate participant/session")
    if len({s["participant"] for s in sessions}) != 1:
        raise ValueError("combine one participant at a time")
    enough = len(sessions) >= 2
    return {
        "participant": sessions[0]["participant"],
        "sessions": [s["session"] for s in sessions],
        "layout_passes": {
            layout: enough and all(s["layouts"][layout]["passes"] for s in sessions)
            for layout in LAYOUTS
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=argparse.FileType("r", encoding="utf-8"))
    args = parser.parse_args(argv)
    try:
        sessions = [analyze_session(json.load(handle)) for handle in args.datasets]
        print(json.dumps({"sessions": sessions, "combined": combine(sessions)}, indent=2))
    except (ValueError, KeyError, TypeError) as error:
        print(f"Cannot analyze dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
