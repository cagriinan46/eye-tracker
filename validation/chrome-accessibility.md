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
