"""Print the offline Issue #50 A/B model comparison as derived-numerical JSON."""

import argparse
import json
from pathlib import Path

from experiments.vertical_mapping_evaluation.analysis import analyze_session


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", type=Path, nargs=2, help="ignored Session A and B JSON files")
    args = parser.parse_args()
    results = [
        analyze_session(json.loads(path.read_text(encoding="utf-8"))) for path in args.sessions
    ]
    if {result["session"] for result in results} != {"A", "B"} or len(
        {result["participant"] for result in results}
    ) != 1:
        parser.error("provide separate A and B datasets from the same participant")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
