# Vertical signal vs drift diagnosis — Issue #75

Preregistered **2026-10-08, Europe/Istanbul**, before any Fatih A/B session was
collected. Approved by Fatih in chat; vertical accuracy is the team's priority
before Phase 2. This is a diagnostic experiment, not a production change.

## Question

Fatih's production-path validation on 2026-10-08 (see
[WORK_LOG](../../docs/handoff/WORK_LOG.md)) gave held-out x MAE 0.048 with 21/21
ordering, but y MAE 0.249, y ordering 7/21 and y bias +0.25. That report holds
no feature values. **Is the vertical failure already present in the calibration
feature (signal inadequacy), or does a usable calibration signal later shift
(drift) or lose its order (instability)?** The answer selects which kind of fix
to try next; it does not select a fix.

## Protocol and data

Collection reuses the merged Issue #44 collector unchanged; read its
[README](../vertical_collapse_diagnostics/README.md) for the 9 calibration +
16 held-out presentation protocol, per-frame derived fields and privacy rules.
Fatih completes Session A in a normal comfortable posture, stands up and
reseats, then completes Session B with a new calibration. Built-in camera
index 0 on Fatih's Mac, normal glasses use, natural blinking, no deliberate
changes to eye opening or posture. From the repository root:

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_collapse_diagnostics.run \
  --participant fatih --session A --camera-index 0 --screen-size 1512x982 \
  --output .venv/vertical-collapse-fatih-A.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_collapse_diagnostics.run \
  --participant fatih --session B --camera-index 0 --screen-size 1512x982 \
  --output .venv/vertical-collapse-fatih-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_signal_drift_diagnosis.analysis \
  .venv/vertical-collapse-fatih-A.json .venv/vertical-collapse-fatih-B.json
```

Outputs are new, Git-ignored files; the collector refuses to overwrite. No other
local dataset (Çağrı's captures, geometry-1/2, B2 marker) is read. A cancelled or
failed session is recorded as such; a retry uses a new filename and is reported.

### Protocol amendment before data collection (2026-10-08)

After the preregistration commit `6b43f0f` and **before any session**, Fatih
reported that the 16:00 validation targets did not fill the screen. Probing
showed macOS OpenCV makes the window full screen but shows the historical
1200×700 canvas centered at its own size; Fatih's logical display is 1512×982
points, so targets covered about 79%×71% of the screen. All historical reports
also record 1200×700. A new opt-in `--screen-size WIDTHxHEIGHT` option on the
collector and the validation harness draws the canvas at display size and
refuses to run if the measured image area differs; the default path is
unchanged. Fatih visually confirmed a full-screen test pattern. A/B use
`--screen-size 1512x982`. Target coordinates, timing, the classification rule
and all thresholds are unchanged. Consequence: these sessions differ from the
16:00 session and from historical runs in on-screen target span, so any
`NOT_REPRODUCED` result must consider display size as an explanation.

## Frozen classification rule

Let `v` be the binocular production vertical feature. Per session:

1. **Calibration line.** Using the nine per-target medians that the production
   fitter received (`calibration_samples`), fit ordinary least squares
   `v = α + β·target_y` and report R². The fitted direction is `sign(β)`.
2. **Column ordering.** Within each of the three calibration columns, count the
   three row pairs whose `v` difference has the fitted direction (9 pairs).
3. **Held-out feature ordering.** Median `v` of each held-out trial's usable rows
   (at least five), then median of each target's two trials. Count the 21 target
   pairs whose target-y difference is at least 0.05 and whose `v` difference has
   the fitted direction.
4. **Held-out shift.** `shift_y = mean over 16 trials of (v_trial − α − β·y) / β`,
   in normalized screen-y units relative to the calibration feature line.

Categories, applied in this order:

| Category | Condition |
| --- | --- |
| `SIGNAL` | β = 0, or calibration R² < **0.80**, or column ordering < **8/9** |
| `INSTABILITY` | otherwise, held-out feature ordering < **17/21** |
| `DRIFT` | otherwise, \|shift_y\| > **0.10** |
| `NOT_REPRODUCED` | otherwise |

The overall result is a category only if **both** sessions agree; otherwise it
is `MIXED` and both are reported. The thresholds are constants in
[analysis.py](analysis.py) and are asserted by tests; they must not change after
data collection. Transparency note: they were chosen after seeing the
2026-10-08 validation session's *prediction-level* summary, but before any
feature-level data from Fatih existed.

Descriptive only (no decision role): per-eye calibration fits and column
ordering, eye-opening vs target-y fit, head-center-y proxy change from
calibration to validation, the Issue #44 within-target associations and the
held-out prediction metrics.

## What each outcome would suggest (proposal, not authorization)

- `SIGNAL`: the current feature cannot represent Fatih's vertical gaze; next
  work is a new vertical signal (for example eye opening, head pose or an
  appearance-based estimate), compared against this baseline.
- `DRIFT`: the signal exists but moves after calibration; next work is drift
  compensation or recentering.
- `INSTABILITY`: the signal exists in calibration but is not reproducible;
  next work is stability/sampling investigation.
- `NOT_REPRODUCED`: the failure did not recur; compare conditions with the
  2026-10-08 validation session before choosing any fix.
- `MIXED`: report both sessions; humans decide whether to collect more.

## Limitations

One participant, one day, one Mac and camera. Linear fit on nine points; R²
and pair counts are descriptive engineering thresholds, not statistical tests.
The head-center proxy cannot separate translation from pitch. Eye opening and
the vertical feature share landmarks. No physical cause can be established.
Results apply to Fatih only and are never pooled with Çağrı's sessions.
