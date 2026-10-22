# Chrome web-control discovery: bounded diagnostic

Issue #116, macOS, 2026-10-21. This is an opt-in browser test preparation,
not an automatic application-setting change or a production coverage fix.

## Reproduction and findings

The existing Chrome 156.0.8078.47 process exposed the local
[`semantic-controls.html`](fixtures/semantic-controls.html) page's roles and geometry,
but its web controls advertised only `AXShowMenu` and `AXScrollToVisible`.
No web targets passed the production `AXPress` requirement. The browser's own
controls did advertise `AXPress`. Three foreground scans completed successfully.
This reproduces the failure without a camera, gaze estimates or a third-party site.

Fresh isolated Chrome processes with `--force-renderer-accessibility` exposed
`AXPress` for the five enabled controls: button, link, checkbox, radio and select.
Both the default API configuration and a comparison with
`--disable-features=MacAccessibilityAPIMigration` exposed those actions. Thus the
API-migration hypothesis did not explain the difference in these forced-mode tests.
The existing profile versus a fresh profile is still a confound; this does not
identify the precise mode/setting responsible in the existing process.

In a subsequent **foreground** forced-accessibility test, the unchanged production
scanner accepted all five enabled web controls in each of three complete scans.
The disabled button and hidden button were not selected. Total targets were 15
(10 browser/window controls plus 5 page controls); elapsed times were approximately
91, 17 and 43 ms. No action was performed. Earlier background metadata probes
cannot establish foreground visibility and are not counted as coverage results.
Fresh processes without forced accessibility exposed no web tree during their
short startup probes; those are inconclusive for steady-state default behavior.

The missing capability signal can therefore be restored in a controlled browser
test environment without weakening the resolver or discovery checks. Arbitrary
sites, existing user profiles and normal startup still need separate validation.
macOS menu items remain outside the current discovery scope.

## Repeat the camera-free check

Run from the repository root only when ready to open a separate Chrome test window.
These commands create a disposable browser profile, not a copy of the user's
profile. They do not restart the existing browser or change its settings.

```sh
semantic_chrome_profile="$(mktemp -d "${TMPDIR:-/tmp}/eye-tracker-chrome.XXXXXX")"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$semantic_chrome_profile" \
  --no-first-run --no-default-browser-check \
  --disable-background-networking --disable-sync --disable-extensions \
  --force-renderer-accessibility \
  "file://$PWD/validation/fixtures/semantic-controls.html"
```

Keep the separate test window in the foreground, with all five enabled controls
visible. Start the following command from another terminal with a short delay,
then switch back to that test window before the scan begins:

```sh
sleep 5
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
  ~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
  -m validation.semantic_targets
```

The CLI reports aggregate counts, including browser chrome. Counts alone do not
identify which page controls were accepted; the diagnostic measurements above
additionally tracked traversal into `AXWebArea`. Do not treat a matching total as
proof of exact target coverage. An `incomplete` result is not selectable evidence.
No camera starts; green highlighting requires the separately authorized live
preview flow. Close only the test browser when finished. Keep or remove its
disposable profile separately; never remove the normal Chrome profile or project
experiment records as cleanup.

## Follow-up boundary

Do not substitute `AXShowMenu` or `AXScrollToVisible` for `AXPress`. Do not infer
activation capability from geometry or role alone. Automatic browser accessibility
mode requests would write application state and need a separately reviewed design
under ADR-005's read-only discovery boundary. This document does not authorize
such a change. Issue #116 remains open for normal-profile integration.

Chromium documents `--force-renderer-accessibility` for its accessibility inspection
tools: [official inspection guide](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/tools/accessibility/inspect).
Apple defines [AXUIElementCopyActionNames](https://developer.apple.com/documentation/applicationservices/1462053-axuielementcopyactionnames)
as the list of actions an element supports. The earlier API-migration hypothesis
came from [Chromium's Cocoa adapter](https://raw.githubusercontent.com/chromium/chromium/main/ui/accessibility/platform/ax_platform_node_cocoa.mm);
source inspection alone is not proof of the installed browser's feature state.

## Checked fixture launcher

The bounded launcher combines disposable-profile preparation and foreground
readiness checks. From the repository root, with the prepared experiment Python:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
  ~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
  -m validation.chrome_fixture
```

This explicitly opens and foregrounds a new Chrome process with the documented
`--force-renderer-accessibility` flag. It never sends a runtime accessibility-mode
setter to an existing browser. It closes its owned browser after the check and
restores the previously foreground application only if an owned test process
still had focus at cleanup; a deliberate user focus change is preserved. Disposable profiles and a new
`validation/results/chrome-readiness-*/report.json` are preserved.

The default is camera-free. Add `--preview` only for an authorized, ready human
session. That starts the existing GazeFollower semantic preview after readiness;
calibration, quality review, Enter and Tab remain unchanged. Escape ends preview.
Closing the launcher terminates only its owned gaze/browser processes. It does
not remove profiles, guarantee descendant-process teardown or modify the normal
Chrome session. This launcher is currently macOS-only; the shared resolver is
unchanged.

Readiness requires three consecutive complete scans with the same role/geometry
set for the five enabled page controls. Toolbar controls do not count. Incomplete
scans, missing controls and changed geometry reset the streak; context changes,
permission failure and unsupported display coordinates stop the check. At most
20 attempts and 12 seconds of cooperative discovery are allowed, with 0.5-second
spacing. Startup activation has a separate bounded wait. Native calls can exceed
cooperative IPC budgets; no replacement workers are spawned. Late scans cannot
report readiness. A failed check never starts the camera and exits nonzero.

Reports contain scan status, elapsed time, streak and available attribute-read
errors, not UI text or rectangles. Native errors outside attribute reads may only
appear as `incomplete`. A ready result describes that fixture at that instant,
not arbitrary sites or guaranteed coverage after calibration. Existing runtime
freshness/context checks still suppress invalid outlines. Issue #116 remains
open: this is a controlled test preparation path, not a normal-session fix or a
resolution of the intermittent native startup error.

Camera-free validation on 2026-10-22: the first launcher run encountered three
`AXRole` reads failing with `-25204`, then three matching complete scans and
readiness at 2.81 seconds. A second run after the lifecycle review also reached
readiness. Both reports recorded `camera_started: false` and owned-browser exit.
These observations validate recovery from a transient read failure in the test
launcher, not the root cause of Chrome's native failure or human gaze accuracy.
