"""Summarize separate numerical diagnostic sessions without pooling users."""

import argparse
import json
import sys
from pathlib import Path

from experiments.vertical_collapse_diagnostics.analysis import compare_sessions, summarize_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=Path, help="Derived numerical session JSON")
    args = parser.parse_args(argv)
    try:
        summaries = [
            summarize_session(json.loads(path.read_text(encoding="utf-8")))
            for path in args.datasets
        ]
        print(
            json.dumps({"sessions": summaries, "comparison": compare_sessions(summaries)}, indent=2)
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cannot summarize diagnostic dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
