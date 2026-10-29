# UniGaze desktop integration plan

Issue #139; user explicitly requests implementation now, before design discussion.
Spec: ADR-006 and existing desktop prototype behavior.

Goal: default UniGaze desktop runtime, explicit --model mgaze rollback; no redesign.
Architecture: preserve MGaze adapter; run the measured UniGaze pipeline in its
prepared Python environment via bounded local socket messages. Promote research
Python sources into experiments/unigaze; weights/intrinsics remain external local
assets. No production contracts or OS/hardware actions change.

- [x] Add model-specific protocol tests: 2 vs258 features,13x20 vs13x45 calibration,
  held-out checks, invalid/stale behavior and raw/filtered check reporting.
- [x] Promote pinned geometry/paired extraction/filter/mapping code with configurable
  local asset paths, isolated process, graceful shutdown and missing-asset errors.
- [x] Connect default UniGaze and explicit MGaze to desktop lifecycle and records.
  Keep UI camera-off startup; add model identification only. Keep MGaze behavior.
- [x] Camera-free tests and actual-model public-fixture smoke; native camera-off UI
  smoke; relevant lint/full tests. Review, commit, push and PR; human merge.

Constraints: no startup downloads, images only RAM/local IPC; no human test launched;
research comparisons remain unchanged. Use existing macOS environment; Windows
UniGaze worker transport is not validated and must report unsupported execution
rather than silently choose MGaze. Record this limit; Windows remains project target.

Review focus: process exit during capture, malformed worker packet, model-switch
calibration mismatch, missing camera calibration, stale UI/observations. Existing
300ms freshness and800ms heartbeat limits remain; do not hide slow frames.

Calibration: reuse UniGaze13 normalized research targets,1.5ssettling and6s sampling,
select20 evenly-spaced valid samples; fail insufficient data. MGaze retains its
existing13x45 protocol. Independent UI5point check and12selection trials remain.
Filter: pinned HeuristicFilter look_ahead3; invalid tracking resets; report raw and
filtered independent errors and filter-history age separately from capture age.

## Execution and review evidence

Implemented inline on feature/unigaze-desktop from synchronized main a07327e.
The user explicitly requested execution before a separate UI design discussion.

- Promoted all runtime Python code into tracked experiments/unigaze; local assets
  remain external. No research kit Python imports. No new dependency installed.
- Actual-model public-fixture smoke: valid angles, blank rejection, memory-only
  preview. Recorded session replay:976 valid predictions; fit/raw/filter max error0.
- Native macOS UI:1280x772 drawable viewport, UniGaze selected, camera off; no worker
  started. Actual proxy/worker fixture test covers calibration/read/reset/cleanup.
- Final review via requesting-code-review found two important lifecycle issues.
  Fixed cancellation with stop-event-aware socket polling and owned subprocess-group
  termination; fixed resume filter reset and rejection of in-flight pre-reset frames.
  Regression tests first failed, then passed; blocked startup/nested child and
  pause/resume tests exercise the fixes without camera access.
- Deferred minor: filter hashes are recorded, not enforced against a separate
  expected manifest. Baseline commit is checked and provenance is retained; no
  claim that recorded filter hashes alone prevent local source edits.
- Ruling: retain the measured paired extractor's MGaze eligibility branch rather
  than replace its face/eye gates while integrating. Cost: extra runtime work and
  retained baseline environment dependency; avoids changing the evaluated pipeline.
- Ruling: keep macOS-only inherited-socket transport for this local integration;
  fail explicitly elsewhere. Cost: Windows UniGaze transport remains follow-up work.

No human gaze session run; selection accuracy in the desktop viewport remains
unverified. Existing research accuracy is not reported as desktop success.
