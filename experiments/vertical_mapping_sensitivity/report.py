"""Print per-session sensitivity diagnostics from local derived-numerical reports."""

import argparse
import json
from pathlib import Path

from experiments.vertical_mapping_sensitivity.analysis import analyze_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path, help="Local JSON session reports")
    args = parser.parse_args(argv)
    results = [
        {"source": str(path), **analyze_session(json.loads(path.read_text(encoding="utf-8")))}
        for path in args.reports
    ]
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
