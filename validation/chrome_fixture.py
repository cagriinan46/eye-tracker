"""Opt-in disposable Chrome fixture check; camera starts only with --preview."""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep

from eye_tracker.platform_adapters._macos_ax import AXBackend, AXReadError
from eye_tracker.platform_adapters.macos_accessibility import MacOSAccessibility

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
EXPECTED = Counter(
    {
        "AXButton": 1,
        "AXLink": 1,
        "AXCheckBox": 1,
        "AXRadioButton": 1,
        "AXPopUpButton": 1,
    }
)


@dataclass(frozen=True)
class Observation:
    status: str
    signature: tuple = ()  # Ephemeral role/geometry, never written to report.
    error: str | None = None


def matches_fixture(roles):
    return roles == EXPECTED


def wait_ready(observe, *, clock=monotonic, sleep=sleep, seconds=12, max_attempts=20):
    """Three consecutive matching complete observations within cooperative bounds."""
    started = clock()
    attempts = []
    previous = None
    streak = 0
    status = "attempt_limit"
    for _ in range(max_attempts):
        if clock() - started >= seconds:
            status = "timeout"
            break
        sample = observe()
        elapsed = clock() - started
        if elapsed >= seconds:
            status = "timeout"
            attempts.append(
                {"status": sample.status, "elapsed": elapsed, "streak": 0, "error": sample.error}
            )
            break
        if sample.status == "ok" and sample.signature:
            streak = streak + 1 if sample.signature == previous else 1
            previous = sample.signature
        else:
            streak, previous = 0, None
        attempts.append(
            {"status": sample.status, "elapsed": elapsed, "streak": streak, "error": sample.error}
        )
        if sample.status in {"context_changed", "unavailable", "unsupported_coordinates"}:
            status = sample.status
            break
        if streak == 3:
            status = "ready"
            break
        sleep(min(0.5, max(0, seconds - (clock() - started))))
    return {"status": status, "attempts": attempts}


def launch_preview(report, enabled, launch):
    if report["status"] == "ready" and enabled:
        return launch()
    return None


class FixtureBackend(AXBackend):
    """Track web ancestry only inside this controlled fixture's bounded traversal."""

    def __init__(self):
        super().__init__()
        self.web = set()
        self.selected = []
        self.read_error = None

    def _attr(self, node, name):
        try:
            return super()._attr(node, name)
        except AXReadError as error:
            self.read_error = f"{name}: {error}"
            raise

    def describe(self, node):
        info = super().describe(node)
        if info[0] == "AXWebArea":
            self.web.add(node)
        return info

    def children(self, node, limit):
        children, truncated = super().children(node, limit)
        if node in self.web:
            self.web.update(children)
        return children, truncated

    def identity(self, node, role, rect):
        if node in self.web:
            self.selected.append((role, rect.x, rect.y, rect.width, rect.height))
        return None

    def observe(self):
        self.web.clear()
        self.selected.clear()
        self.read_error = None
        try:
            # Prime lazy application AX data, never mutate an accessibility mode.
            app = self._own(self.create_application(self._frontmost_pid()))
            self._attr(app, "AXRole")
            if self.initial_context is not None and self.context() is None:
                return Observation("context_changed")
            snapshot = MacOSAccessibility(backend=nullcontext(self)).snapshot(
                _identity=self.identity
            )
        except AXReadError as error:
            return Observation("incomplete", error=self.read_error or str(error))
        if snapshot.status == "unavailable" and self.initial_context is None and self.trusted():
            return Observation("incomplete", error="awaiting_initial_window")
        if snapshot.status != "ok":
            return Observation(snapshot.status, error=self.read_error)
        roles = Counter(row[0] for row in self.selected)
        if not matches_fixture(roles):
            return Observation("missing_targets")
        return Observation("ok", tuple(sorted(self.selected)))


def should_restore_focus(foreground_pid, owned_pids):
    return foreground_pid is not None and foreground_pid in owned_pids


def stop_owned(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Start camera after readiness")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        parser.error("This fixture launcher currently requires macOS")
    if not CHROME.is_file():
        parser.error("Google Chrome was not found in /Applications")
    from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication, NSWorkspace
    from Foundation import NSDate, NSRunLoop

    def pump(seconds):
        until = monotonic() + seconds
        while monotonic() < until:
            NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.02))
            sleep(min(0.02, max(0, until - monotonic())))

    output_root = ROOT / "validation/results"
    output_root.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="chrome-readiness-", dir=output_root))
    profile = tempfile.mkdtemp(prefix="eye-tracker-fixture-")
    original = NSWorkspace.sharedWorkspace().frontmostApplication()
    browser = gaze = None
    report = {"status": "startup_failed", "attempts": [], "camera_started": False}
    try:
        with (output / "chrome.log").open("w") as log:
            browser = subprocess.Popen(
                [
                    str(CHROME),
                    "--user-data-dir=" + profile,
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    "--disable-sync",
                    "--disable-extensions",
                    "--force-renderer-accessibility",
                    (ROOT / "validation/fixtures/semantic-controls.html").as_uri(),
                ],
                stdout=log,
                stderr=log,
            )
            report["owned_pid"] = browser.pid
            report["profile"] = profile
            app = None
            for _ in range(50):
                pump(0.1)
                if browser.poll() is not None:
                    raise RuntimeError("owned_browser_exited")
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(browser.pid)
                if app is not None and str(app.bundleIdentifier()) == "com.google.Chrome":
                    break
            else:
                raise RuntimeError("owned_browser_not_registered")
            app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            for _ in range(30):
                pump(0.1)
                front = NSWorkspace.sharedWorkspace().frontmostApplication()
                if front is not None and int(front.processIdentifier()) == browser.pid:
                    break
            else:
                raise RuntimeError("owned_browser_not_foreground")
            with FixtureBackend() as backend:

                def observe():
                    pump(0.01)
                    if browser.poll() is not None or backend._frontmost_pid() != browser.pid:
                        return Observation("context_changed")
                    if not backend.trusted():
                        return Observation("unavailable")
                    return backend.observe()

                report.update(wait_ready(observe, sleep=pump))
                (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
                print("READINESS:", report["status"], "REPORT:", output / "report.json", flush=True)

                def launch():
                    nonlocal gaze
                    if browser.poll() is not None or backend._frontmost_pid() != browser.pid:
                        raise RuntimeError("context_changed_before_camera")
                    if backend.context() is None:
                        raise RuntimeError("window_changed_before_camera")
                    gaze = subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "experiments.gazefollower_baseline.run",
                            "--semantic-preview",
                        ],
                        cwd=ROOT,
                    )
                    report["camera_started"] = True
                    return gaze.wait()

                report["preview_exit"] = launch_preview(report, args.preview, launch)
            return 0 if report["status"] == "ready" and report["preview_exit"] in (None, 0) else 2
    except KeyboardInterrupt:
        report["status"] = "cancelled"
        return 130
    except (OSError, RuntimeError) as error:
        report["status"] = "failed"
        report["error"] = type(error).__name__ + ": " + str(error)
        return 2
    finally:
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        restore = should_restore_focus(
            int(front.processIdentifier()) if front is not None else None,
            (browser.pid if browser is not None else None, gaze.pid if gaze is not None else None),
        )
        if gaze is not None:
            stop_owned(gaze)
        if browser is not None:
            stop_owned(browser)
            report["owned_browser_exited"] = browser.poll() is not None
        if restore and original is not None:
            original.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("REPORT:", output / "report.json", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
