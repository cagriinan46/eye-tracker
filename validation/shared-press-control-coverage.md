# Shared menu-button and text-field discovery — 2026-10-22

Issue #125, baseline `8561c26` (after #124). The cross-application audit identified
press-capable menu-opening buttons and text fields excluded by the initial role
set. Add `AXMenuButton` and `AXTextField` to the existing discovery path. There is
no application-specific resolver or new activation behavior.

## Eligibility remains unchanged

A role nominates a possible target; `AXPress`, usable geometry, center-hit
visibility, complete traversal, current context and all budgets remain required.
Known-disabled controls are excluded. Unknown enabled state retains the existing
`None` / `preview_only` contract; only the preview coordinator opts into those.
`AXConfirm` and `AXShowMenu` alone do not establish press capability. Closed
`AXMenu` contents remain excluded. Menu opening, item selection, focus execution,
typing, scrolling and clicks are not implemented by this change.

Native geometry/state/action reads now apply to these two roles too. Consequently
invalid required data or a native read failure can conservatively reject a scan
that previously ignored that role's metadata. Unsupported capability is not
inferred from a role or an application's name.

## Native comparison

Existing windows, camera-free, no clicks/typing/navigation/settings changes.
The diagnostic loaded both baseline scanner and baseline native backend from
Git alongside the updated implementation, including each backend's exception
classes. Five Settings pairs and three pairs per other application: 34 scans.
All recorded scans preserved the foreground application before and after reading.

| Context | Baseline complete | Expanded complete | Targets in completed scans |
| --- | --- | --- | --- |
| System Settings | 4/5 | 5/5 | 18 → 18 |
| Finder | 1/3 | 1/3 | 8 → 10: two menu buttons |
| TextEdit | 2/3 | 2/3 | 3 → 3 |
| Calculator | 1/3 | 2/3 | 55 → 56: one menu button |
| Normal Chrome | 2/3 | 3/3 | 25 → 26: one text field |

For all ten pairs in which both scans completed, the diagnostic compared sets of
(role, rectangle, enabled state, category) in memory. No baseline signatures were
removed; additions were exactly the roles listed above. Only aggregate role counts
were stored, not coordinates, UI labels or page content. This comparison does not
prove native object identity, detect duplicate identical signatures, or establish
coverage across other windows/states.

All 11 failed scans reported `-25204` near application activation. This pre-existing
messaging/readiness limitation remains; differences in completion counts are not
attributed to role expansion. Settings and TextEdit produced no new hit-verified
candidates in these windows. The run does not identify each rejected control's
reason. No unknown-enabled candidates were published in this sample.

Normal Chrome's missing web `AXPress` metadata (#116) is still unresolved. TextEdit
text-area editing and Finder file selection remain separate gaps. The increased
counts are discovery coverage, not gaze accuracy or end-to-end usability results.

## Verification

- Eight new regression cases failed before the role expansion (eligible targets,
  unknown-enabled candidates, required geometry and native description behavior).
- State/capability/visibility tests and nested-control ambiguity tests pass.
- Full suite: **790 passed**. Ruff lint/format and `git diff --check` passed.
- Native result: `validation/results/press-coverage-1792666672183659000.json`.
- Harness: `validation/results/shared-press-coverage-harness.py` (local experimental
  script pinned to baseline `8561c26`).

Two preliminary harness runs aborted without recorded scans because separately
loading the baseline backend introduced mismatched exception classes, allowing a
startup messaging error to escape its handler. This diagnostic defect was fixed
before the comparison above. Their empty records remain local and are excluded
from scan totals. Raw diagnostics are ignored and not uploaded. No Windows-native
or human gaze testing was performed.
