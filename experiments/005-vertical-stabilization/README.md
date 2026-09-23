# Experiment 005 — Vertical gaze signal stabilization

Experiment #16 found that `binocular_vertical_local_axis` retained UP < CENTER < DOWN mean ordering in three human runs, including natural eye opening with glasses. Raw frame ranges overlapped, blink/eyelid measures were strongly associated with local-axis variation, and the absolute signal shifted between sessions. The original eye geometry remains unchanged here.

## Question and hypothesis

Can conservative temporal aggregation and blink/outlier handling reduce frame-level vertical gaze noise while preserving UP/CENTER/DOWN directional separation? We hypothesize that short causal windows and rejection of *obvious* blink-contaminated frames will reduce transient outliers and improve repeatability. This is feature exploration, not a production estimator, screen calibration, or a permanent blink threshold.

## Inputs and setup

This analysis uses the **derived numerical** CSVs from Experiment 004, not camera frames. It runs locally on Python 3.12 with the standard library; `requirements.txt` adds no packages. From the repository root:

```bash
.venv/bin/python experiments/005-vertical-stabilization/analyze_temporal_stability.py
```

By default it reads `.venv/vertical-gaze-stable.csv`, `.venv/vertical-gaze-stable2.csv`, and `.venv/vertical-gaze-stable3.csv`. Supply one or more CSV paths as positional arguments to analyze other Experiment 004 runs. `--json` prints complete machine-readable descriptive results, including per-label and per-trial statistics. The CSVs remain ignored and must not be committed without deliberate review.

## Methods

All methods process the unchanged `binocular_vertical_local_axis` in timestamp order, use only current/past samples, and reset state when the gap between sampled frames exceeds 0.5 seconds. The reset separates the one-second unsampled trial transitions in Experiment 004; it is not direction-specific correction. Target labels and trial numbers are used **only after processing** to evaluate outputs. There is no label-derived normalization, UP/CENTER/DOWN threshold, or parameter search across runs.

| Method | Rule | Nominal history |
| --- | --- | --- |
| `raw` | Valid frame's local-axis value. | None |
| `median_120` | Median of current and preceding valid values within 120 ms. | 120 ms |
| `median_240` | Same within 240 ms. | 240 ms |
| `mean_120` | Arithmetic mean within 120 ms. | 120 ms |
| `ewma_045` | `s_t = 0.45 x_t + 0.55 s_(t-1)`; reset at sampling gaps. | Decaying, no hard window |
| `blink_median_120` | Conservative blink/near-closure rejection before the 120 ms median. | 120 ms plus 250 ms opening context |

The experimental blink gate rejects a geometrically valid frame only when **both** (1) the larger of `eyeBlinkLeft` and `eyeBlinkRight` is at least `0.65`, and (2) binocular eye opening is at most `70%` of the median of at least three previously accepted opening samples from the preceding 250 ms. These numbers are exploratory rejection parameters, **not production or command thresholds**. Low opening alone is never rejected: vertical gaze itself can change eyelid opening. Missing blink/opening data means no blink-based rejection. Face/geometry-invalid frames are unavailable for every method. Rejected frames return no estimate and do not enter the filter; the script does not conceal their availability cost by filling or interpolating them.

The implementation uses timestamps to form windows, not an assumed fixed FPS. It also reports the observed within-trial median sample interval and approximate samples in each window. At roughly 30 FPS, a 120 ms window covers about four recent frames and a 240 ms window about seven; these counts are measured anew for each run.

## Measurements and interpretation

For every method and run, the script reports available/excluded counts; UP/CENTER/DOWN count, mean, sample standard deviation, median, median absolute deviation (MAD), minimum/maximum, and p10/p90; all trial means and medians; trial mean/median spans; pairwise mean differences and raw-range/p10–p90 overlap. An additional descriptive jump count uses each run's raw adjacent-difference p95 as a common *evaluation* cutoff. It is not used to reject or smooth samples. Adjacent differences across unsampled trial gaps are excluded. A smaller jump count is not proof that genuine gaze changes were preserved.

The previous three runs were single-user, approximately stable-head experiments: Run 1 used no glasses and natural eye opening; Run 2 used glasses and intentionally slightly wider opening as a **diagnostic** condition; Run 3 used glasses and natural opening. Conditions also differed in camera/face geometry. Neither glasses nor wider opening can be identified as the cause of any difference. Short-term noise and between-session offset are separate problems: temporal filtering is not expected to fix calibration drift.

Approximate algorithmic delay: causal 120/240 ms windows can retain values from up to 120/240 ms in the past; a centered-response intuition is roughly half that, but median response depends on signal shape. EWMA's average age at a 33 ms interval is about `(0.55/0.45) × 33 ≈ 40 ms`, with a longer decaying tail. Blink rejection may temporarily provide **no output**. Actual user-perceived transition latency was not measured because these CSVs omit the one-second transition periods. No method should be chosen from smoothness alone.

## Privacy and limitations

No camera, MediaPipe, network, frames, face images, or video are used by this offline script. It reads only local derived values; it does not write any output file unless the user redirects its text. The numerical CSVs may still be sensitive and remain local/ignored. The source runs involve one user and three short sessions, not a representative sample. This analysis cannot establish live transition preservation, screen-coordinate accuracy, cross-user performance, or a production filter. No statistical significance is claimed. Correlation with blink/opening does not establish causation.

The bounded measured outcome and human-validation decision are in [RESULTS.md](RESULTS.md).
