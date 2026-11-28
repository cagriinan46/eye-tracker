"""Apply the frozen #156 rule to the Issue #158 conditions; BASE winning adopts nothing."""

import argparse
import json
import sys
from pathlib import Path

from experiments.head_pointer.analysis import summarize as summarize_rule
from experiments.head_pointer_tuning.protocol import CONDITION_NAMES


def summarize(sessions: list[dict]) -> dict:
    summary = summarize_rule(sessions, CONDITION_NAMES)
    for name, values in summary["candidates"].items():
        values["comfort"] = {s["session"]: (s.get("comfort") or {}).get(name) for s in sessions}
        values["recentres"] = {
            s["session"]: (s.get("recentres") or {}).get(name, 0) for s in sessions
        }
    winner = summary["winner"]
    summary["adopted"] = winner if winner not in (None, "BASE") else None
    return summary


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
