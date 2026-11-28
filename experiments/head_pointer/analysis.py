"""Apply the frozen Issue #156 winner rule to one or more session files."""

import argparse
import json
import sys
from pathlib import Path
from statistics import median

from experiments.head_pointer.protocol import MAX_TIMEOUTS_PER_SESSION, TIE_FRACTION
from experiments.head_pointer.signals import CANDIDATES


def _median(values: list[float]) -> float | None:
    return median(values) if values else None


def summarize(sessions: list[dict]) -> dict:
    """Per-candidate descriptive numbers and the frozen pass/winner decision."""
    candidates: dict[str, dict] = {}
    for candidate in CANDIDATES:
        per_session: dict[str, dict] = {}
        times: list[float] = []
        jitters: list[float] = []
        for session in sessions:
            scored = [
                t
                for t in session.get("trials", [])
                if t["candidate"] == candidate and not t["practice"]
            ]
            selected = [t for t in scored if t["outcome"] == "selected"]
            timeouts = sum(t["outcome"] != "selected" for t in scored)
            session_times = [t["elapsed"] for t in selected]
            session_jitter = [
                t["hold_jitter_px"] for t in selected if t["hold_jitter_px"] is not None
            ]
            by_size: dict[str, float | None] = {}
            for diameter in sorted({t["diameter"] for t in scored}):
                sized = [t["elapsed"] for t in selected if t["diameter"] == diameter]
                by_size[str(diameter)] = _median(sized)
            per_session[session["session"]] = {
                "calibrated": candidate in (session.get("mappings") or {}),
                "scored": len(scored),
                "selected": len(selected),
                "timeouts": timeouts,
                "median_time_s": _median(session_times),
                "median_time_by_diameter_s": by_size,
                "median_hold_jitter_px": _median(session_jitter),
                "median_entries": _median([t["entries"] for t in selected]),
            }
            times.extend(session_times)
            jitters.extend(session_jitter)
        passes = bool(per_session) and all(
            s["scored"] > 0 and s["timeouts"] <= MAX_TIMEOUTS_PER_SESSION
            for s in per_session.values()
        )
        candidates[candidate] = {
            "sessions": per_session,
            "passes": passes,
            "median_time_s": _median(times),
            "median_hold_jitter_px": _median(jitters),
        }
    return {"candidates": candidates, "winner": winner(candidates)}


def winner(candidates: dict[str, dict]) -> str | None:
    passing = [
        (c["median_time_s"], c["median_hold_jitter_px"] or float("inf"), name)
        for name, c in candidates.items()
        if c["passes"] and c["median_time_s"] is not None
    ]
    if not passing:
        return None
    passing.sort()
    best = passing[0]
    tied = [p for p in passing if p[0] <= best[0] * (1 + TIE_FRACTION)]
    return min(tied, key=lambda p: (p[1], p[0]))[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", nargs="+", type=Path)
    args = parser.parse_args(argv)
    sessions = [json.loads(path.read_text()) for path in args.sessions]
    incomplete = [s.get("session") for s in sessions if not s.get("completed")]
    if incomplete:
        print(f"Warning: incomplete session(s) {incomplete}", file=sys.stderr)
    print(json.dumps(summarize(sessions), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
