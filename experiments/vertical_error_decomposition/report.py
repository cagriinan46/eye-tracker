"""Analyze local ignored derived-numerical A/B session reports."""

import argparse
import json
from pathlib import Path

from experiments.vertical_error_decomposition.analysis import analyze_session


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sessions", type=Path, nargs=2, help="ignored Session A and B JSON files")
    args = parser.parse_args()
    reports = [analyze_session(json.loads(path.read_text())) for path in args.sessions]
    if {report["session"] for report in reports} != {"A", "B"} or len(
        {report["participant"] for report in reports}
    ) != 1:
        parser.error("provide A and B from the same participant")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
