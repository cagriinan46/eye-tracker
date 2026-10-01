"""Capture one of three predeclared human sensitivity sessions."""

import argparse
import json
import sys
from pathlib import Path

from experiments.vertical_position_variability.run import collect_session
from experiments.vertical_sensitivity_live_study.analysis import prepare_report
from experiments.vertical_sensitivity_live_study.protocol import schedule


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participant", choices=("cagri",), required=True)
    parser.add_argument("--session", choices=("live-1", "live-2", "live-3"), required=True)
    parser.add_argument("--camera-index", type=int, required=True)
    parser.add_argument("--model", type=Path, default=Path(".venv/models/face_landmarker.task"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.camera_index < 0:
        parser.error("camera index must be nonnegative")
    if not args.output.resolve().is_relative_to(Path(".venv").resolve()):
        parser.error("derived numerical output must be inside Git-ignored .venv")
    if args.output.suffix != ".json":
        parser.error("output must be a JSON path")
    return args


def _invalid_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.invalid.json")


def run(args: argparse.Namespace) -> int:
    """Write one complete report, or a separate reason marker for an invalid attempt."""
    if not args.model.is_file():
        print(f"Face Landmarker model not found: {args.model}", file=sys.stderr)
        return 1
    invalid_path = _invalid_path(args.output)
    if args.output.exists() or invalid_path.exists():
        print("Refusing to overwrite an existing result or invalid-attempt marker", file=sys.stderr)
        return 1
    try:
        report = prepare_report(collect_session(args))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as destination:
            json.dump(report, destination, indent=2)
            destination.write("\n")
        print(f"Completed {len(schedule())} presentations; derived data: {args.output}")
        return 0
    except (KeyboardInterrupt, InterruptedError, RuntimeError, ValueError, OSError) as error:
        # The reused collector discards partial rows on failure. Keep a durable
        # invalidation record; any justified retry must use a distinct filename.
        invalid_path.parent.mkdir(parents=True, exist_ok=True)
        marker = {
            "participant": args.participant,
            "session": args.session,
            "camera_index": args.camera_index,
            "status": "invalid_incomplete_run",
            "reason": str(error) or type(error).__name__,
            "planned_presentations": len(schedule()),
            "partial_measurements_available": False,
        }
        with invalid_path.open("x", encoding="utf-8") as destination:
            json.dump(marker, destination, indent=2)
            destination.write("\n")
        print(f"Run invalid; reason saved: {invalid_path}: {marker['reason']}", file=sys.stderr)
        return 130 if isinstance(error, (KeyboardInterrupt, InterruptedError)) else 1


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
