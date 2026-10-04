# Intentional gaze targeting v2 — results

## Engineering question and final protocol

Can the unchanged production gaze estimator deliberately acquire 0.20 × 0.20 normalized targets with a 1.0 s continuous dwell? The final cue-based protocol uses a fixed 0.75 s fixation cue at the opposite point (center-target cue: `(0.2, 0.2)`), then presents the target regardless of cue gaze. Each session has its own standard nine-point calibration, the nine v1 target centers once in each of three balanced blocks, raw unclipped production predictions, a target half-width/height of 0.10, a 5.0 s target timeout, and 0.5 s feedback. No smoothing, OS cursor movement, or clicking was used. The [README](README.md) records the complete protocol and the predeclared engineering bands.

## Capture validity and early stop

Only `.venv/intentional-gaze-cagri-live-1.json` and `.venv/intentional-gaze-cagri-live-2.json` contribute to these statistics. Both identify participant `cagri`, protocol `intentional_gaze_targeting` version `2`, seed `20261006`, a 0.75 s non-gated cue, 0.10 target half-width/height, 1.0 s target dwell, and 5.0 s timeout. Each records two READY screens, camera index 1 at 1920 × 1080, 9 ordered calibration presentations, all 27 expected target cells, a target attempt for every cell, and no failed camera reads or no-face observations. Calibration presentations had 33–34 usable samples each. Recorded cue display durations were 0.7506–0.7659 s in live-1 and 0.7501–0.7654 s in live-2; target onset followed cue end by about 0.015–0.018 s. The analyzer accepted both complete captures. Target timeouts are retained as results.

The two preserved `live-1-reset-gated-pilot.invalid.json` and `live-2-reset-gated-pilot.invalid.json` files are incomplete implementation pilots from the earlier gaze-gated design. They are excluded. Their design did not guarantee target presentation, and they cannot be pooled with the cue-based sessions. No raw captures are committed.

Three valid sessions were originally prepared. Collection stopped after **two** because the predeclared **<60%** engineering band was mathematically locked: 20 successes in 54 trials, plus a hypothetical perfect 27/27 third run, would be **47/81 = 58.02%**. This engineering early-stop decision was made after the first two valid sessions; the early-stop rule itself was not preregistered. It does **not** complete the planned three-session repeatability study or characterize session-to-session variability fully. No live-3 capture was collected for this decision.

## Success, latency, and spatial error

| Metric | live-1 | live-2 | Pooled |
| --- | ---: | ---: | ---: |
| Success / targets | 10/27 (37.04%) | 10/27 (37.04%) | **20/54 (37.04%)** |
| Target timeouts | 17/27 (62.96%) | 17/27 (62.96%) | **34/54 (62.96%)** |
| First-entry latency, median / p95 (s) | 0.414 / 3.408 | 0.302 / 3.895 | 0.366 / 3.847 |
| Successful-entry latency, median / p95 (s) | 2.318 / 3.770 | 0.423 / 1.833 | 1.004 / 3.692 |
| Confirmed-acquisition latency, median / p95 (s) | 3.341 / 4.795 | 1.450 / 2.861 | 2.028 / 4.716 |
| Raw x MAE | 0.05543 | 0.05189 | 0.05377 |
| Raw y MAE | 0.21570 | 0.19191 | **0.20454** |
| Mean / median Euclidean error | 0.23356 / 0.19362 | 0.20882 / 0.16601 | 0.22196 / 0.18382 |
| p95 Euclidean error | 0.54369 | 0.43151 | 0.50277 |
| Usable / unavailable predictions | 3,242 / 0 | 2,863 / 0 | **6,105 / 0** |

First-entry latency uses trials that entered the target at least once (23 in live-1, 20 in live-2, 43 pooled), including later timeouts. Successful-entry and confirmed-acquisition latencies use the 10 successful trials per session. Confirmed latency starts at target onset and ends at the observation confirming a full 1.0 s dwell; cue time is excluded. Percentiles use the project's interpolated percentile convention. Spatial errors pool **all usable raw target-phase samples**, including gaze travel immediately after cue removal and values outside the visible screen. They are sample-weighted: longer trials contribute more samples. They are not camera-to-photon latency or a stationary-fixation accuracy test.

## Dwell behavior and availability

| Timeout diagnostic | live-1 (17) | live-2 (17) | Pooled (34) |
| --- | ---: | ---: | ---: |
| Entered target at least once | 13 | 10 | **23** |
| Never entered target | 4 | 7 | **11** |
| Had at least one dwell interruption | 12 | 10 | 22 |
| Longest dwell ≥0.50 s | 7 | 3 | 10 |
| Longest dwell ≥0.75 s | 5 | 1 | 6 |
| Longest dwell ≥0.90 s | 2 | 0 | 2 |
| Longest dwell ≥0.95 s | 2 | 0 | 2 |
| Median / p95 longest dwell (s) | 0.248 / 0.989 | 0.176 / 0.750 | 0.246 / 0.897 |

Across **all** 27 trials per session, live-1 had 47 target re-entries and 57 dwell interruptions; live-2 had 28 and 36. Pooled totals were **75 re-entries** and **93 interruptions**. Median longest dwell across all trials was 0.811 s in live-1, 0.461 s in live-2, and 0.742 s pooled. Repeated same-target median prediction differences across blocks had median/p95/maximum Euclidean magnitudes of 0.17218/0.49285/0.66388 in live-1 and 0.07347/0.22827/0.31314 in live-2 (27 block pairs per session). These pairs describe repeatability; they do not isolate the cause of change.

Prediction availability was **100% of recorded target samples** in both sessions, with zero failed camera reads and zero no-face observations across calibration and targeting. The failures therefore cannot be attributed to a recorded loss of face detection or unavailable predictions. Availability does not establish spatial accuracy.

## Position dependence

| Row or column | live-1 successes | live-2 successes | Pooled |
| --- | ---: | ---: | ---: |
| Upper row | 3/9 | 4/9 | 7/18 |
| Center row | 3/9 | 4/9 | 7/18 |
| Lower row | 4/9 | 2/9 | 6/18 |
| Left column | 4/9 | 4/9 | 8/18 |
| Center column | 2/9 | 5/9 | 7/18 |
| Right column | 4/9 | 1/9 | 5/18 |

| Target | live-1 | live-2 | Pooled | Pooled y MAE |
| --- | ---: | ---: | ---: | ---: |
| T-1-1 (upper left) | 0/3 | 0/3 | **0/6** | 0.2028 |
| T-1-2 | 1/3 | 3/3 | 4/6 | 0.1861 |
| T-1-3 | 2/3 | 1/3 | 3/6 | 0.2189 |
| T-2-1 | 2/3 | 3/3 | 5/6 | 0.1424 |
| T-2-2 | 0/3 | 1/3 | 1/6 | 0.1863 |
| T-2-3 | 1/3 | 0/3 | 1/6 | 0.1895 |
| T-3-1 | 2/3 | 1/3 | 3/6 | 0.1879 |
| T-3-2 | 1/3 | 1/3 | 2/6 | 0.2009 |
| T-3-3 (lower right) | 1/3 | 0/3 | **1/6** | **0.2945** |

T-1-1 failed in both sessions. T-3-3 was also weak, with the largest pooled target y MAE. T-2-2 and T-2-3 each succeeded only 1/6. The small per-target counts do not support a general position model, but a single global success rate hides these differences.

## Calibration and session sensitivity

Using each session's saved mapping coefficients and the median feature recorded at each of its **nine calibration presentations**, we reconstructed fitted predictions without clipping. The errors below are calibration-median residuals, not held-out target-phase errors.

| Calibration metric | live-1 | live-2 |
| --- | ---: | ---: |
| x slope / intercept | −6.133759 / 3.534678 | −5.910451 / 3.427074 |
| y slope / intercept | **39.172769 / 1.890864** | **18.904582 / 1.313838** |
| Horizontal feature span | 0.109437 | 0.112156 |
| Vertical feature span | 0.017787 | 0.034857 |
| Calibration x MAE | 0.025532 | 0.031095 |
| Calibration y MAE | 0.064688 | 0.117789 |
| C-3-3 signed calibration y residual | −0.033911 | **−0.343916** |

The signed fitted residuals (`prediction − target`) at each calibration presentation median were:

| Calibration target | live-1 x / y | live-2 x / y |
| --- | ---: | ---: |
| C-1-1 | −0.025845 / +0.109969 | −0.074555 / +0.220880 |
| C-1-2 | +0.016896 / +0.039124 | +0.004594 / +0.078732 |
| C-1-3 | +0.045413 / −0.130670 | −0.011660 / +0.014672 |
| C-2-1 | +0.017644 / +0.081762 | −0.013320 / +0.099449 |
| C-2-2 | +0.011567 / −0.017001 | +0.015475 / +0.042697 |
| C-2-3 | +0.004576 / +0.060240 | −0.018085 / −0.075542 |
| C-3-1 | +0.018797 / −0.047482 | +0.088336 / +0.073623 |
| C-3-2 | −0.019470 / −0.062031 | +0.031521 / −0.110594 |
| C-3-3 | −0.069579 / −0.033911 | −0.022307 / −0.343916 |

The live-1 y slope magnitude was **2.07×** live-2's. A hypothetical raw vertical-feature change of 0.005 would map to 0.19586 normalized y in live-1 versus 0.09452 in live-2. The live-2 vertical calibration feature span was almost twice live-1's. These show substantial session-specific mapping sensitivity. They do not show that slope caused feature movement or that the slope difference alone caused target failures. In particular, live-1 had lower calibration y MAE yet higher target-phase y MAE (0.21570 versus 0.19191). The high C-3-3 calibration residual in live-2 is evidence of imperfect fit even during calibration.

## Failure decomposition

The categories below **overlap** and are descriptive, not exclusive diagnoses.

- **Spatial error:** For each of the 34 timeout trials, the median raw x prediction across that trial's usable samples was inside the target's x interval, while the median raw y prediction was outside its y interval. Among the 4,735 usable samples in timeout trials, 4,370 (92.29%) were inside the horizontal interval, 569 (12.02%) inside the vertical interval, and 525 (11.09%) inside both. As a secondary check against initial cue-to-target travel, the median prediction from 3.0 s after target onset onward remained vertically outside in **32/34** timeout trials and horizontally inside in **34/34**. This late-window check was added for diagnosis after collection; it is not a preregistered success metric.
- **Temporal stability:** 23/34 timeout trials entered the full region, and 22/34 had an interrupted dwell. Only 10 reached a longest dwell of 0.50 s; 2 reached at least 0.95 s. Thus many failures include brief target entries, while most were not near the full 1.0 s requirement. Entry or interruption alone cannot distinguish estimator jitter from natural gaze motion.
- **Mapping/session sensitivity:** The fitted y slopes were 39.17 and 18.90 and calibration y MAE rose from 0.06469 to 0.11779, yet both sessions succeeded 10/27. Mapping sensitivity is a plausible contributor to output error, not an isolated cause.
- **Position dependence:** T-1-1 was 0/6 and T-3-3 was 1/6; row and column success varied as shown above.
- **Tracking availability:** All 6,105 targeting observations were usable, with zero camera-read failures or no-face observations. Recorded availability was not the primary limitation.

## Decision, limits, and next step

**Decision:** The observed pooled success was **20/54 = 37.04%**, in the predeclared **<60%** band. For this participant and 0.20 × 0.20 targets with a 1.0 s dwell, the current production gaze estimator is **not adequate for stricter intentional selection**. This does not negate [v1 coarse-region feasibility](../coarse_gaze_targeting_validation/RESULTS.md); it identifies a more demanding interaction geometry that the present output did not support.

Evidence is limited to two same-participant sessions on one local setup. The preplanned third repeat was not collected, so full session-to-session repeatability is unknown. The moving gaze cursor was visible during target trials, fixation was not independently measured, and target-phase errors include gaze travel. The observed vertical error, dwell breaks, calibration fit residuals, and mapping slope differences cannot distinguish physical gaze movement from landmark/feature movement, mapping bias, or estimator jitter. No cross-user, production, clinical, accessibility, click, or OS-cursor readiness claim follows.

**Next bounded task:** On a new branch, run an **offline diagnostic and solution benchmark using only the two valid v2 captures**. First separate late-trial spatial bias from short-window variation, then compare a small preregistered set of interpretable interventions: (1) simple temporal stabilization with its latency cost, (2) justified calibration/gain-bias robustness alternatives, and (3) whether independent-linear mapping leaves position-dependent residuals. Evaluate on held-out trials/blocks without tuning to their labels; retain raw baseline metrics. Do not implement a production change, collect new camera data, add ML, reopen arbitrary hand-crafted vertical-feature search, or start OS cursor control in that task.
