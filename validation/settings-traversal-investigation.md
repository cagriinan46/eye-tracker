# Short-lived accessibility children — 2026-10-22

Issue #123 follows the cross-application audit in #122. Baseline: `8c596eb`.
Read-only native investigation on the existing macOS windows; no camera, clicks,
typing, settings changes, new target roles or activation behavior.

## Evidence and cause

The breadth-first scanner queued descendants while enumerating other subtrees.
System Settings repeatedly returned `AXRole` error `-25202` for a child below an
`AXCell`. Re-reading that cell's children through both ranged enumeration and
full-attribute enumeration returned a readable `AXStaticText` reference that was
not native-equal to the failed reference. Refreshing the cell through its parent
returned the same cell and again a readable child. Foreground window context
remained unchanged during those comparisons.

A separate instrumented scan read each cell child immediately after enumeration.
All 41 immediate reads succeeded. Six previously readable children subsequently
failed with `-25202` when checked after another cell's children were enumerated.
This establishes a short reference lifetime across traversal, not the precise
internal macOS invalidation trigger. Native array ownership remains retained by
the existing backend throughout the scan; this was not repaired by adding retains.

An isolated depth-first experiment removed the repeatable invalid-child failure.
It does not prove references can never expire or make discovery atomic.

## Change

Consume each subtree before proceeding to later siblings, preserving native root
and sibling order. The iterative traversal still visits all reachable eligible
subtrees, deduplicates native identities and applies the existing node, child,
depth, queue and time limits. It still rejects the whole snapshot on an unreadable
node. There is no retry, skipped invalid reference, application-name condition or
relaxation of geometry, capability, enabled-state, hit-test or context checks.

Traversal changes discovery order and scan-local target IDs. Cross-scan continuity
already uses native identity tokens, not those scan-local IDs. The resolver's
ambiguity handling remains unchanged. Session/identity tests pass.

## Paired native verification

The final run alternated unchanged baseline and updated production code, with
five pairs for Settings and three pairs for each other application. Counts below
are for completed scans; failures publish no targets.

| Application | Baseline complete | Updated complete | Targets per complete scan |
| --- | --- | --- | --- |
| System Settings | 0/5 | 4/5 | Updated: 18 buttons |
| Finder | 1/3 | 2/3 | Both: 8 |
| TextEdit | 2/3 | 2/3 | Both: 3 |
| Calculator | 2/3 | 2/3 | Both: 55 |
| Normal Chrome | 2/3 | 3/3 | Both: 25 |

Settings baseline failures were one `-25204` followed by four `-25202` errors.
Its updated failure, and every failure in the other applications, was `-25204`
(messaging failure) near application activation. This separate startup/readiness
limitation remains; do not claim all scans succeed. All 34 scans preserved the
foreground application before/after scanning. Successful Settings scans took
95–109 ms with tracing overhead; these are observations, not a benchmark.

The other applications retained the same counts and role distributions in their
completed scans. This is not a full native identity-set comparison or a claim of
complete application coverage. Normal Chrome's web capability gap (#116) remains.
No published unknown-enabled preview-only targets occurred in this final run.

## Automated verification and local evidence

- Regression first failed against breadth-first traversal, then passed after the
  change: short-lived child references do not prevent collecting both branches.
- A persistent later read failure still discards already collected targets.
- Full suite: **768 passed**. Ruff lint and format checks passed; diff check clean.

Ignored local records (not uploaded):

- `validation/results/settings-invalid-child-1792663551696726000.json`: reference refreshes.
- `validation/results/settings-invalid-child-1792663571379609000.json`: first unordered depth-first experiment (4/5 complete; first failure not traced).
- `validation/results/settings-invalid-child-1792663590919035000.json`: ordered experiment, 5/5 complete, but two scans had zero hit-verified targets; not counted as successful highlighting.
- `validation/results/settings-invalid-child-1792663614705447000.json`: immediate/later role-read comparison.
- `validation/results/traversal-validation-1792663737609948000.json`: final 34 paired scans.

Two setup attempts stopped before any scan because foreground activation was not
established. Their empty records are preserved, excluded from scan totals.
Diagnostic scripts are archived locally alongside the records. Native findings
are single-device observations. Human targeting, calibration accuracy and Windows
native behavior were not tested.
