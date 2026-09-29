"""Compare two locally stored numerical diagnostic sessions."""

import argparse
import json
from pathlib import Path

from experiments.vertical_drift_diagnostics.analysis import compare_sessions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_a", type=Path)
    parser.add_argument("session_b", type=Path)
    args = parser.parse_args(argv)
    for path in (args.session_a, args.session_b):
        if not path.resolve().is_relative_to(Path(".venv").resolve()):
            parser.error("numerical datasets must be inside Git-ignored .venv")
    reports = [
        json.loads(path.read_text(encoding="utf-8")) for path in (args.session_a, args.session_b)
    ]
    print(json.dumps(compare_sessions(reports), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
