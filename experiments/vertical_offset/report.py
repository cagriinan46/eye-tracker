"""Print separate A/B offline one-point vertical offset results as JSON."""

import argparse
import json
from pathlib import Path

from experiments.vertical_offset.analysis import analyze_session


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", type=Path, nargs=2, help="ignored drift Session A and B JSON")
    args = parser.parse_args()
    results = [
        analyze_session(json.loads(path.read_text(encoding="utf-8"))) for path in args.sessions
    ]
    if {result["session"] for result in results} != {"A", "B"} or len(
        {result["participant"] for result in results}
    ) != 1:
        parser.error("provide distinct A/B datasets from the same participant")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
