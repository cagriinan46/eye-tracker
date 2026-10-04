# Offline gaze failure and solution benchmark

## Question and input boundary

Which small, interpretable intervention family could improve intentional targeting before another live capture? This is an offline comparison of **only** the two completed, cue-based `intentional_gaze_targeting` protocol-v2 captures for `cagri`: `.venv/intentional-gaze-cagri-live-1.json` and `live-2.json`. The analyzer validates protocol identity, schedule, calibration, target observations, and saved dwell outcomes. It excludes v1 and the reset-gated pilot files. Raw captures remain ignored under `.venv/`; no camera or production code is changed.

Run from the repository root with:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.gaze_failure_solution_benchmark.benchmark > .venv/gaze-failure-benchmark-summary.json
```

The output is derived numerical JSON containing candidate metrics, calibration diagnostics, residual groups, gate results, and exact replay checks. It does not contain images. The code has no NumPy dependency so the deterministic tests run in the repository's minimal CI environment.

## Frozen candidates and calibration

Every mapping is fitted separately for each session from its **nine ordinary calibration presentation medians**. Diagnostic target rows, trial labels, outcomes, and future observations never enter a fit. All mapped predictions remain unclipped.

| ID | Formula / operation |
| --- | --- |
| M0 | Unchanged production `IndependentLinearMapping`: `x = x_slope*h + x_intercept`, `y = y_slope*v + y_intercept`; fit by production ordinary least squares. |
| M1 | At each calibration x level, median the three horizontal features; at each y level, median the three vertical features. Fit ordinary independent linear mappings through the resulting three level medians per axis. |
| M2 | Calibration-only ordinary least-squares 2D affine map: `x = a*h + b*v + c`, `y = d*h + e*v + f`. A pivoted 3×3 normal-equation solve rejects rank-deficient geometry. |

For each mapping, report the nine calibration-median residuals, x/y MAE, leave-one-calibration-target-out MAE, and per-axis coefficient norm as a gain diagnostic. Leave-one-out refits using the other eight calibration targets only. M2's gain norms combine horizontal and vertical feature coefficients, whose feature units differ, so compare them descriptively with the coefficients rather than treating them as a physical sensitivity unit.

Temporal filters act on the mapped x/y predictions independently in each trial:

| ID | Causal rule |
| --- | --- |
| T0 | Raw mapping output, no filter. |
| T1 | EMA with `alpha = 0.35`; first usable sample initializes the state. |
| T2 | Rolling median of the latest five usable samples, including the current sample. |

Unavailable samples yield no prediction, interrupt dwell, and clear filter state. No values are interpolated across unavailability. No filter parameter is tuned from targeting outcomes.

## Replay, comparability, and gates

M0+T0 must first reproduce **every** saved prediction, target outcome, and dwell timing at original monotonic timestamps. Otherwise the benchmark stops. Candidates use the same inclusive 0.10 half-width/height, 1.0 s continuous dwell, and 5.0 s timeout. Spatial errors use the same fixed logged target-sample windows for all candidates, including cue-to-target gaze travel. For candidate acquisition, replay stops at the first observed successful dwell.

The recording itself stops when **production** succeeds. If a candidate has not succeeded by that early recording end, its outcome is **censored**, not a proven timeout. Observed-success counts use all 54 trials as a conservative denominator; candidate success could be underestimated. Such censored cases are counted separately, and latency medians compare different subsets of successful trials. The 34 production timeout trials have full target windows and can show whether a candidate rescues a recorded failure. Entries and interruptions may also be affected by differing observed success times. This replay cannot simulate gaze behavior after the recorded stop or human adaptation to a differently moving cursor.

The predeclared gates are applied to observed-success counts, pooled sample-weighted x/y MAE, and median confirmed-acquisition latency. Mapping: at least +10 percentage points success, no session losing >5 points, y MAE at least 15% lower, x MAE no more than 15% higher, median latency no more than 0.50 s higher, calibration-only fit. Temporal: at least +5 points success, interruptions **or** re-entries at least 20% lower, x/y MAE no more than 10% higher, latency no more than 0.50 s higher. If both families pass, exactly one selected mapping/filter combination is replayed; it must improve both sessions, pooled success by at least 15 points, y MAE by at least 15%, and respect the x/latency limits. No large candidate grid is run.

Target labels are used only for evaluation and residual diagnosis. The diagnostic groups signed x/y bias, absolute errors, a within-trial y `p95−p05` spread, and repeated-target block differences by row, column, and target. A secondary spread from samples at least 3 s after onset reduces initial gaze-travel influence but selects longer trials; it is not a stationary-fixation measurement. No target-specific correction is fitted.

See [RESULTS.md](RESULTS.md) for the measured decision.
