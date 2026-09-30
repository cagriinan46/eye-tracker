"""Print Issue #52's per-session, derived-numerical offline summaries."""

import argparse
import json
from pathlib import Path

from experiments.vertical_position_variability.analysis import analyze_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", type=Path, help="local Git-ignored numerical JSON")
    args = parser.parse_args(argv)
    for path in args.datasets:
        with path.open(encoding="utf-8") as stream:
            summary = analyze_session(json.load(stream))
        # No input data or generated artifact is written to disk.
        print(json.dumps({"source": str(path), **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
