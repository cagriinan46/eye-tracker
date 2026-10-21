"""One read-only discovery pass, without camera, focus changes or activation."""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from time import monotonic

from eye_tracker.platform_adapters.macos_accessibility import DiscoveryLimits, MacOSAccessibility


def main(argv=None, *, provider=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    limits = DiscoveryLimits()
    provider = provider if provider is not None else MacOSAccessibility(limits=limits)
    started = monotonic()
    snapshot = provider.snapshot()
    print(
        json.dumps(
            {
                "status": snapshot.status,
                "target_count": len(snapshot.targets),
                "roles": dict(Counter(t.role for t in snapshot.targets)),
                "elapsed_seconds": round(monotonic() - started, 6),
                "limits": asdict(getattr(provider, "limits", limits)),
                "coverage": "foreground_window_supported_press_roles_single_display",
            },
            sort_keys=True,
        )
    )
    return 0 if snapshot.status == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
