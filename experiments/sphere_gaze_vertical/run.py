"""Collect one Issue #92 session: the Issue #77 collector plus eye-sphere head-frame numbers."""

from experiments.sphere_gaze_vertical.capture import SphereSignalExtractor
from experiments.vertical_signal_comparison import run as collector


def main(argv: list[str] | None = None) -> int:
    return collector.run(
        collector.parse_args(argv),
        signal_extractor=SphereSignalExtractor,
        experiment="issue-92-sphere-gaze-vertical",
    )


if __name__ == "__main__":
    raise SystemExit(main())
