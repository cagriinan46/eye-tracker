# Verified semantic continuity — issue #114

User approved this bounded improvement after preview session `acd74fbf877b`.
No calibration change, threshold widening, pointer action or new human test.
ADR-005 placement and macOS-first / shared portable resolver remain unchanged.
This supersedes the earlier feed plan's no-cross-snapshot-evidence restriction only
for explicit native-verified continuity, not for snapshot-local target IDs.

## Implementation

- Preserve the last complete checked snapshot during an early in-session refresh.
  Neither capture nor context-check time advances during traversal. Existing age
  checks continue to reject old evidence; failure/context change/closure clears it.
- Limit native sessions to four scan attempts and two seconds of validity. Native
  calls have cooperative timeouts; references are released on worker session exit,
  not forcibly while a call is blocked.
- Retain optional opaque tokens only for native-equal controls with unchanged
  visible geometry, role and enabled press eligibility in consecutive complete scans.
  Every refresh repeats complete discovery and hit-testing. Native references stay
  private; one-shot discovery issues no continuity tokens.
- Resolver preserves evidence only with token/context/screen/properties agreement.
  Missing tokens retain snapshot-local behavior. Ranking and ambiguity run every
  update; invalid inputs, reversed time and timing gaps still reset acquisition.
- Session boundaries intentionally reacquire; Windows can omit tokens until its
  native adapter can meet the same contract. No Windows-native support is claimed.

## Validation

Regression tests cover replacement at identical coordinates, hash collisions,
native aliases, disappearance/reappearance, geometry/role/eligibility/context changes,
scan/time bounds, failed and blocked refresh, context/snapshot expiry and shutdown.
A deterministic 32-sample, four-scan unchanged-control stream emits 16 candidates
without tokens and 28 with verified continuity (same gaze and thresholds). This
measures avoided reacquisition in a synthetic case, not human targeting accuracy.
The initial acquisition remains mandatory. The later labeled user comparison must
separately measure intended-target correctness, coverage and stability.

Full suite: 740 passed. Independent code review found no important actionable
issues. No camera, native desktop interaction or human test was started for this task.
