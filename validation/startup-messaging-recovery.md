# Initial-window messaging recovery — 2026-10-22

Issue #127; baseline `97bb62f` (after #126). Camera-free, read-only investigation
of transient `-25204` failures following application activation.

## Diagnosis

Five scans each of Settings, Finder, TextEdit, Calculator and Chrome completed
21/25 times on baseline. All four failures occurred in the **initial
`AXFocusedWindow` read**, before a window context or target traversal existed.
Each affected application subsequently returned complete snapshots. This differs
from invalid child references (`-25202`) and missing target metadata.

`PreviewFeed` already opens another session after an incomplete snapshot. The
problem was an unnecessarily abandoned first attempt, not a permanently stuck
preview worker. Broad retries in the feed or target traversal are unnecessary.

## Bounded correction

The private native bridge distinguishes messaging error `-25204` as a subclass
of `AXReadError`. Only `context()`'s first focused-window read may retry it:

- Retry once, only when no initial context has been established.
- Before retry, confirm the original foreground PID and accessibility permission.
- Reuse the same application reference and existing per-message timeout.
- After retry, verify permission and foreground PID before adopting the window.
- Also verify foreground PID after a successful first read.
- An established session's failed context check still invalidates immediately.

Persistent errors, invalid references and malformed data still propagate to the
existing fail-closed handling. No retries are added to geometry, target reads,
children, hit tests or already-established context checks. No sleep, dependency,
application-name rule, role expansion, action or permission prompt is introduced.

Snapshot timestamps and the 0.5-second discovery budget are not renewed. The
extra read has the existing 0.05-second native timeout by default. Native timeouts
remain cooperative, not hard wall-clock guarantees. A slow read can overshoot a
budget before the next check; an expired snapshot is not published as complete.
Before the first successful read there is no known window to compare; the first
success establishes it. Subsequent checks retain native window equality.

## Native evidence

1. **Baseline diagnosis:** 21/25 scans complete, four initial-window messaging
   failures. Record: `startup-probe-1792667000152728000.json`.
2. **Separate activation comparison:** baseline 8/10 and updated 10/10 complete.
   Each scan followed a separate app activation; order reversed in the second
   round. No updated read needed a retry in this run, so these rates alone do not
   demonstrate recovery. Applications were already warmed; observed target counts
   also varied slightly during activation. Record:
   `startup-recovery-1792667088770345000.json`.
3. **Updated diagnosis:** 25/25 scans complete. Calculator's first focused-window
   read returned `-25204`; the retry succeeded and the full scan returned 56 targets
   in about 155 ms including diagnostic overhead. The other 24 scans did not need
   recovery. Record: `startup-probe-1792667100732826000.json`.

All recorded scans preserved the foreground application before/after scanning.
These are small, single-device observations, not a statistically controlled error
rate comparison or proof that arbitrary messaging failures always recover. The
single directly observed recovery supports the narrowly scoped remedy.

Raw files are local under `validation/results/`. The reused diagnosis harness's
`method: baseline` label remains in the third record, but **that run used the
updated working tree**, as distinguished above; its `baseline` field identifies
the base commit, not the implementation under test. Harness copies are archived
under `validation/results/startup-messaging-harness/` with run notes. No UI labels,
page content, coordinates or imagery were logged.

## Automated verification

- Tests cover recovery, at most two initial reads, persistent failure, invalid
  reference exclusion, established-session failure, foreground/permission changes
  before and during retry, and unchanged overall snapshot time budget.
- Regression run before the behavior change: six failures; all pass afterward.
- Full suite: **801 passed**. Ruff lint and format checks passed; diff check clean.

No camera, clicks, settings writes, human targeting or Windows-native tests were
performed. The resolver, preview coordinator and public snapshot contract are
unchanged. Persistent failures still abstain and may recover in a later feed
session; this change does not guarantee immediate readiness of every application.
