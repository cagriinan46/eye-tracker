# Bounded gaze diagnosis — 2026-10-19

User-approved scope: one diagnosis round and at most one evidence-led correction
round; maximum two short human sessions. This change prepares the first round.
It does not fix accuracy, change the model, or authorize automatic human capture.

## Preserved baseline

Single MacBook camera, 25-target seed-77 calibration, 0.8 s settling + 1.2 s
sampling, five medians (horizontal, vertical, pitch, yaw, roll), input-only
StandardScaler, independent RBF SVRs (C=1000, gamma=0.1, epsilon=1), EMA=0.50.
The existing blink filter and minimum 20 usable calibration targets are unchanged.
No parameter search, refitting of historical sessions, outlier removal, offset
correction or hardware/environment change is part of this diagnostic PR.

## Offline report: no cameras or model fitting

From the repository root, with the dedicated Python environment:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
/Users/cagri/.virtualenvs/eye-tracker-cagri-20261018/bin/python \
-m validation.gaze_diagnostics \
validation/results/cagri-live-macbook-svr-20261019-c7f95f8d
```

Only explicit `cagri-live-macbook-svr-*` directories directly under
`validation/results` are accepted. Symlink sessions/files are rejected. Source
files are hashed before and after analysis. No archived environment is searched.
Each invocation writes JSON and Markdown to a new ignored audit directory.
Do not commit the participant report, raw rows or session outputs.

Statistics include per-target median/IQR/count, feature/target/order correlations,
live values outside the calibration *median* envelope, and expected-vs-logged
desktop coordinates. Envelope violations are descriptive, not a confidence gate.
Rows already rejected during historical collection cannot be recovered or counted.

Consecutive target visits stay separate. For legacy logs the first 0.8 s of each
visit is excluded, but fixation is unverified and blue feedback was visible.
Those errors are descriptive distances to the displayed target, not validated
accuracy, and must not rank different sessions/models as a controlled experiment.

Coordinate tests exercise the real controller with an inert endpoint, including
the 33-point window offset, center/endpoints and offscreen rejection. The audit
checks logged commands. Neither proves the observed physical cursor position,
actual OS delivery, or current display alignment. Existing native-window bounds
checks still run when a human session is explicitly started.

## Prospective observation-only probe (not started by this change)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" \
/Users/cagri/.virtualenvs/eye-tracker-cagri-20261018/bin/python \
live_svr_demo.py --diagnostic
```

Do not combine this flag with `--control-pointer`; the parser rejects it, and
the runner also guards against direct incompatible calls before camera imports.

1. Camera preview: adjust placement; Enter only when ready.
2. Actual calibration screen: separate Enter starts the unchanged 25 targets (~50 s).
3. Baseline prompt: sit comfortably and naturally; Enter starts five targets.
4. Position-change prompt: make a small comfortable adjustment and settle; separate
   Enter starts the same five targets. Do not deliberately chase the cursor.
5. Ends automatically. Escape aborts and preserves partial JSONL rows.

Each target is displayed before its timer starts, with 0.8 s settling and 3 s
sampling. Ten targets total: ~38 s of observation, in addition to calibration
and user-paced gates. There is no automatic repeat or second calibration.
Blue prediction feedback is hidden throughout observation. Both raw and EMA
predictions are logged, but no OS pointer adapter is created and no click fires.
This does not switch the interface to a grid launcher; only fixation targets appear.

`diagnostic-summary.json` is written only after all trials complete. The summary
contains per-visit mean signed bias, mean/p95 radial error, centered RMS
dispersion, feature medians, availability and fraction within 30 logical pixels.
Missing predictions remain in the target-hit denominator; this is not a dwell
success measure. Dispersion includes measurement noise, drift and real movement.
An insufficient/absent prediction is not evidence of a successful fixation.

The second condition also occurs later in time: changes cannot be causally
attributed to head movement alone. Looking at the target is instructed, not
independently verified. Head translation is not fully measured by the five inputs.

## Decision and stop rule

Review the first session and select at most one justified correction. If no
specific issue can be identified, stop this approach rather than tune blindly.
If a correction is justified, use a second fresh session with the same protocol.
Do not optimize using its outcome labels. Primary comparison is equal-weight
mean of per-target **smoothed** mean radial errors, reported separately for both
conditions; raw errors, centered RMS, p95 errors and availability accompany it.
Require all ten trials to have at least five valid predictions before comparison;
otherwise report insufficient evidence, not success or an automatic rerun.

The proposed improvement gate is >=25% lower mean error in both conditions,
without higher mean per-target centered RMS/p95 error or lower availability.
These are engineering decision thresholds, not population validation. Passing
does not establish usable pointer selection; that needs a separate task outcome.
Failure closes this round; no third hyperparameter trial is automatically added.

Future PR merges remain human-controlled. Stage B2's consumed one-shot marker,
archival environments and past participant records must never be modified/rerun.
