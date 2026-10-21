# Desktop-wide semantic gaze: proposed first slice

Status: **Proposed — awaiting human architectural review.**

Related preparation issue: [#98](https://github.com/cagriinan46/eye-tracker/issues/98).
The user approved the Phase 2 priority and desktop-wide goal on 2026-10-21.
This document proposes the persistent architecture; it does not accept an ADR or
claim implementation approval for that architecture.

## Intent and scope

Help a person with severe upper-limb motor impairment target an actionable desktop
element despite approximate webcam gaze. Chrome's back button is an example, not
the feature boundary. Finder, native dialogs, application toolbars and accessible
web content belong to the eventual coverage matrix.

First slice: macOS read-only target discovery and an independently testable target
resolver, followed by an explicitly enabled preview. Resolve a probable target;
do not equate looking with activation. Preserve the existing calibration, gaze
model, filters and coordinate-only mode. Windows remains a later platform adapter.

No promise of support for every control in every application: custom-rendered
content, inaccessible UI and unsupported roles must return an explicit unavailable
or no-target result. Free pointing and later gestures/text entry still have roles.

## Approaches considered

1. **Native accessibility plus a small deterministic resolver (recommended).**
   Reads OS-exposed geometry and actionability across applications. Fits local-first
   operation and requires no new model. Coverage and latency must be measured.
2. **Browser DOM integration.** Strong information for page content, but cannot by
   itself cover browser chrome, Finder or other native applications. Not the primary
   solution for the approved desktop-wide goal.
3. **Screenshot/OCR/model-based detection.** Could later help inaccessible content,
   but introduces extra inference, privacy and validation work. Excluded from this
   first slice; no new dependency or model is justified yet.

## Proposed architecture for review

Follow ADR-003. OS accessibility inspection belongs to a read-only platform
adapter. Target ranking belongs to `intent` as contextual target resolution; it
does not generate a click intent. The app coordinates the two through data values:

```text
gaze result -------------------------------> target resolver (intent)
                                                ^
macOS accessibility adapter -> UI snapshot ------|
                                                |
                                     target candidate / abstention
                                                |
                                         preview feedback

later: target candidate + intentional confirmation -> intent -> actions -> platform
```

Proposed ownership: shared target/snapshot value contracts in `intent`, pure resolver
in `intent/targeting.py`, OS discovery in `platform_adapters/macos_accessibility.py`.
The application supplies snapshots; intent never imports an OS framework. The
platform adapter can return the shared values without depending on the resolver.
No new generic AI subsystem, and no OS action inside gaze or gesture modules.

This placement resolves the open question in architecture section 20 only after
human review. Then update architecture and record the accepted decision before
implementing the persistent modules.

## Read-only discovery contract

- A snapshot carries capture time, application/window context, logical screen
  coordinate space, eligible targets, and explicit completeness/error status.
- A target carries snapshot-local identity, role, logical rectangle, enabled state
  and supported interaction category. Do not identify elements only by screen
  coordinates; a window can move or replace a control.
- Avoid reading titles, URLs, document text, input values or password contents.
  Titles are unnecessary for geometric selection. Do not persist native AX handles.
- Restrict discovery to visible interaction context. An advertised AX action is
  insufficient: hidden menu items can also advertise actions.
- Check rectangle validity, enabled state, window/screen intersection and native
  hit-testing at the proposed target point, accepting a verified descendant only
  after bounded ancestry validation. If visibility cannot be established, abstain.
- Traverse with explicit node/depth/child/time limits and AX per-message timeouts.
  A truncated, errored or stale neighborhood cannot be treated as complete evidence
  that a competing target is absent. Return incomplete/unavailable and abstain.
- Run discovery outside the gaze inference loop. Cache only within a bounded
  lifetime; invalidate on context changes and revalidate before any later action.
  Choose measured budgets during the discovery implementation task, not from the
  one-off probe timings below.

## Target resolution and preview

The deterministic resolver receives gaze/time, a snapshot and explicit configuration.
Compare a coordinate-only baseline, a nearest-eligible-target baseline and a
conservative temporal resolver. Use distance to target rectangles, competition
between nearby candidates and sustained evidence. Do not claim a heuristic score
is a calibrated probability.

Explicit outcomes include candidate, ambiguous, no nearby target, invalid gaze,
stale snapshot and unavailable context. A candidate needs a bounded attraction
radius and a separation margin against its runner-up. Stability may retain a target
only while it remains eligible; tracking loss, context changes and stale information
clear it. All thresholds stay configurable and are tuned on development scenarios,
not silently selected on held-out evaluation results.

First live integration, after review: an opt-in non-activating highlight. Preserve
raw gaze separately from the candidate and any proposed corrected coordinate.
Do not move OS keyboard focus, click, scroll, type or add a dwell timer. Later
pointer snapping must have its own explicit activation and Escape/invalid-gaze
guards; baseline mode remains available.

The overlay must not steal focus or become an accessible target itself. If the
display and snapshot coordinate spaces cannot be reconciled, report unsupported
context rather than applying guessed Retina or multi-monitor offsets.

## Evaluation and acceptance

Before human testing:

- Use synthetic snapshots and declared intended targets to test isolated/dense
  controls, equal-distance ambiguity, nested controls, disabled/hidden controls,
  invalid gaze, stale snapshots, window changes and bounded traversal failure.
- Inspect supported roles in multiple application categories using read-only native
  probes. Record what is actually covered; do not infer browser-page coverage from
  browser-toolbar coverage.
- Test that the preview path cannot invoke pointer/action methods, read sensitive
  values or silently modify calibration. Native tests stay opt-in, outside CI.
- Measure discovery latency and effect on gaze processing before enabling live
  integration. A small synthetic benchmark is not evidence of human success.

For later authorized human evaluation, predeclare task targets and compare the same
layouts under the three methods. Report correct target rate, wrong target rate,
abstention/coverage, target-switching frequency and time to a stable target. Include
dense neighboring controls. Preserve raw gaze error as a separate metric.

Target labels must be independent of the resolver's predictions. Existing free-view
live traces have no ground-truth intended target and cannot establish improvement.
Do not train or recalibrate using the system's own guessed target as truth.

Phase 2 does not pass merely because a rectangle is readable or a highlight appears.
Broad coverage and measurable selection improvement remain to be established.

## Read-only feasibility evidence — 2026-10-21

A throwaway Python/ctypes probe ran in the existing isolated GazeFollower environment.
No dependencies were installed. It used ApplicationServices/CoreFoundation and the
already installed AppKit bridge. Context7 was unavailable in the session; native API
signatures were checked against Apple's documentation. The probe was kept outside
the repository and is not a production adapter.

- `AXIsProcessTrusted` returned true without showing a permission prompt.
- Finder and Chrome were already running; no app was launched or activated.
- Per app: at most 150 visited nodes, depth 10, 40 children per node, queue 300,
  a two-second traversal budget and 50 ms per-message timeout. A sequence of native
  calls can exceed the loop budget; this is not a hard deadline implementation.
- Finder: 150 nodes, 147 advertising actions, 50 with positive-size bounds.
- Chrome: 150 nodes, 145 advertising actions, 17 with positive-size bounds.
- These categories are **not** counts of visible valid targets. Traversal included
  menu entries; visibility, occlusion, nearby-target completeness and hit-testing
  were not established. The scan was deliberately partial.
- Observed single-run traversal durations were about 0.270 s and 0.155 s respectively;
  these are not realtime latency guarantees or gaze-loop benchmarks.
- Read only roles, action names, geometry, enabled flags and child relationships.
  No UI titles/values, screenshots, camera frames, pointer motion or AX actions.

Conclusion: native cross-application inspection is feasible on this machine with
existing access. Reliable visible-target discovery remains an implementation task.

## Research basis

- [Apple Snap to Item](https://support.apple.com/en-ca/guide/ipad/ipad2cd35723/ipados):
  target assistance exists in a shipping accessibility product; different hardware
  and closed implementation do not establish webcam accuracy here.
- [GazeTheWeb](https://github.com/MAMEM/GazeTheWeb): interface introspection and
  target correction precedent. Old separate-browser implementation, not a dependency.
- [BayesGaze, 2021](https://graphicsinterface.org/wp-content/uploads/gi2021-35.pdf):
  temporal target evidence; controlled iPad/TrueDepth experiment, not a guarantee
  for dense desktop controls on this webcam.
- [Toward Everyday Gaze Input](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/01/everyday_eyetracking.pdf):
  account for variation across people and screen regions.
- [Apple AXUIElement APIs](https://developer.apple.com/documentation/applicationservices/axuielement_h)
  and [messaging timeout](https://developer.apple.com/documentation/applicationservices/1459345-axuielementsetmessagingtimeout).

## Proposed implementation sequence after design review

1. Record the approved placement and open a bounded adapter/contracts issue.
2. Implement and test read-only visible-target discovery and unavailable states.
3. Implement the pure resolver and synthetic comparison harness.
4. Add opt-in preview, then benchmark native coverage and latency.
5. Define and run a short human target-selection comparison only when the user is
   ready. Consider pointer snapping separately from confirmation/activation.

Each task uses a fresh branch from synchronized main. Live-trace PR #97 must be
merged by a human before an integration task relies on its diagnostics. Preserve
the [pre-semantic checkpoint](../../recovery/pre-semantic-2026-10-21.md).
