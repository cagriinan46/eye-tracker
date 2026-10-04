# Coarse gaze-target acquisition, protocol v1

## Question and frozen protocol

Can the unchanged production gaze estimate acquire coarse on-screen regions in the participant's normal-use setup, despite known vertical error? This experiment did **not** move the OS pointer or test clicking. The preregistered [protocol](README.md) used ordinary nine-point calibration, all nine targeting centers at x/y `{0.2, 0.5, 0.8}`, three balanced blocks (27 trials/session), and a centered rectangle with half-width/half-height `0.14`. A raw, unclipped prediction had to remain inside for at least `0.300` s by monotonic time; otherwise the trial timed out at `4.0` s. The displayed gaze dot was feedback only. No smoothing or feature change was used. These v1 parameters were not changed after capture.

All figures below were recomputed from the ignored local numerical JSON files with `analysis.py`. Spatial errors aggregate **all usable targeting samples**, including early transition samples and timeouts; they are not restricted to successful-dwell samples. Euclidean error is `hypot(predicted_x − target_x, predicted_y − target_y)`. P95 uses linear interpolation. Acquisition times include user response and estimator behavior, not camera-to-photon latency. The local files remain untracked; no images or video are in this PR.

## Capture validity and analysis sets

All five files identify participant `cagri`, protocol `coarse_gaze_targeting` version `1`, seed `20261006`, both READY screens, camera index `1` at `1920×1080`, calibration settle/sample `0.8/1.2` s, target half-width/height `0.14/0.14`, dwell `0.300` s, and timeout `4.0` s. Every file has nine correctly ordered calibration presentations with at least five usable samples each, 27 correctly scheduled target/block trials, matching sample counts, and zero failed camera reads and no-face observations. All targeting predictions were usable. The session times are measured seconds after the first READY gate and include the second READY wait; they are not a standardized task-duration comparison.

| File | Role | Calibration / trials | Targeting samples | Elapsed s | Capture/behavioral interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| `.venv/coarse-gaze-cagri-live-1.json` | Secondary | 9 / 27 | 2,816 | 134.61 | Technically complete, natural opening; different physical setup. Excluded from primary repeatability. |
| `.venv/coarse-gaze-cagri-live-2.json` | Exploratory | 9 / 27 | 1,361 | 82.36 | Technically complete; participant deliberately varied eye opening without per-trial condition labels. **Protocol-invalid for primary inference.** |
| `.venv/coarse-gaze-cagri-live-3.json` | Primary | 9 / 27 | 916 | 66.28 | Normal-use setup, natural opening. |
| `.venv/coarse-gaze-cagri-live-4.json` | Primary | 9 / 27 | 1,092 | 73.68 | Normal-use setup, natural opening. |
| `.venv/coarse-gaze-cagri-live-5.json` | Primary | 9 / 27 | 1,066 | 74.49 | Normal-use setup, natural opening. |

The primary set is exactly live-3/4/5. No trial was excluded because it timed out. Live-1 and live-2 are preserved but are not pooled into primary results.

## Primary per-session and pooled results

| Set | Success | Timeout | Successful-entry median / p95 s | Confirmed-acquisition median / p95 s | x MAE | y MAE | Euclidean mean / median / p95 | Usable samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| live-3 | 25/27 (92.59%) | 2/27 | 0.364 / 2.494 | 0.684 / 2.812 | 0.1188 | 0.2163 | 0.2721 / 0.2065 / 0.6002 | 916/916 |
| live-4 | 23/27 (85.19%) | 4/27 | 0.357 / 2.236 | 0.678 / 2.552 | 0.0744 | 0.2231 | 0.2459 / 0.2194 / 0.4686 | 1,092/1,092 |
| live-5 | 22/27 (81.48%) | 5/27 | 0.311 / 1.942 | 0.628 / 2.258 | 0.0718 | 0.2387 | 0.2606 / 0.2741 / 0.4430 | 1,066/1,066 |
| **Primary pooled** | **70/81 (86.42%)** | **11/81 (13.58%)** | **0.340 / 2.499** | **0.659 / 2.816** | **0.0867** | **0.2265** | **0.2588 / 0.2354 / 0.4970** | **3,074/3,074** |

Latency distributions include only successful trials; the 11 timeouts have no acquisition latency. Spatial values are pooled by usable sample, so longer trials contribute more samples. This explains why coarse success can coexist with large all-sample y error and tails. The primary set had **0 unavailable targeting predictions**, **0 failed camera reads**, and **0 no-face observations**. Capture availability did not explain its timeouts.

Stability remained imperfect: live-3/4/5 had 10/3/2 target re-entries and 11/4/3 dwell interruptions, respectively; pooled totals were **15 re-entries and 18 interruptions**. Median longest observed dwell per trial was 0.3169/0.3176/0.3163 s (pooled 0.3169 s). For each session, each target had three block presentations; comparing their median raw predictions gives 27 within-session block pairs. Median Euclidean differences were **0.1258, 0.0804, 0.1180** for live-3/4/5. Across the 81 within-session pairs, median/p95/maximum were **0.1074/0.2927/0.4540** normalized units. These are repeatability descriptors, not independent-user estimates.

## Target position

Success counts pool nine trials per target (three blocks × three primary sessions). Spatial errors again use all usable samples, including timeouts.

| Row | Success | x MAE | y MAE | Euclidean mean |
| --- | ---: | ---: | ---: | ---: |
| Upper | 23/27 | 0.0953 | 0.2112 | 0.2487 |
| Center | 25/27 | 0.0667 | 0.1802 | 0.2157 |
| Lower | 22/27 | 0.0899 | 0.2693 | 0.2945 |

| Column | Success | x MAE | y MAE | Euclidean mean |
| --- | ---: | ---: | ---: | ---: |
| Left | 23/27 | 0.1146 | 0.2171 | 0.2703 |
| Center | 27/27 | 0.0421 | 0.1997 | 0.2112 |
| Right | 20/27 | 0.0875 | 0.2469 | 0.2736 |

| Target (x, y) | Success live-3 / 4 / 5 | Pooled success | x MAE | y MAE | Euclidean mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| T-1-1 (0.2, 0.2) | 2 / 3 / 2 | 7/9 | 0.1321 | 0.2220 | 0.2810 |
| T-1-2 (0.5, 0.2) | 3 / 3 / 3 | 9/9 | 0.0491 | 0.1860 | 0.2029 |
| T-1-3 (0.8, 0.2) | 3 / 2 / 2 | 7/9 | 0.0706 | 0.2091 | 0.2294 |
| T-2-1 (0.2, 0.5) | 2 / 3 / 2 | 7/9 | 0.0825 | 0.2279 | 0.2745 |
| T-2-2 (0.5, 0.5) | 3 / 3 / 3 | 9/9 | 0.0255 | 0.1294 | 0.1398 |
| T-2-3 (0.8, 0.5) | 3 / 3 / 3 | 9/9 | 0.0802 | 0.1434 | 0.1843 |
| T-3-1 (0.2, 0.8) | 3 / 3 / 3 | 9/9 | 0.1223 | 0.1763 | 0.2231 |
| T-3-2 (0.5, 0.8) | 3 / 3 / 3 | 9/9 | 0.0481 | 0.2545 | 0.2631 |
| **T-3-3 (0.8, 0.8)** | **3 / 0 / 1** | **4/9** | **0.0994** | **0.2945** | **0.3217** |

T-3-3 was the weakest pooled target and failed in 5/9 trials, including all three live-4 trials. It was **not uniformly weak**: live-3 acquired it 3/3. In live-4 and live-5 its sample-median raw y was 0.516 and 0.455 against target y 0.8, consistent with a large upward output bias in those sessions; the median raw x was 0.730 and 0.723. Those observations describe the failure, not its physical cause. The center column acquired all 27 trials; the lower row had the highest y MAE and Euclidean mean.

## Timing and the permissive-region concern

First entry means target onset to the first observed in-region sample, whether or not a successful dwell followed. Successful entry is the start of the dwell that actually led to acquisition. Confirmed acquisition is its completion. In the primary set, first entry was observed in **73/81** trials (median/p95 **0.319/2.111 s**, range 0.042–3.397); successful-entry median/p95 among 70 successes were **0.340/2.499 s** (range 0.042–3.397); confirmed-acquisition median/p95 were **0.659/2.816 s** (range 0.358–3.714). The median observed dwell from successful entry to confirmation was **0.318 s** (p95 0.323 s). The small amount beyond 0.300 s reflects sample timing.

The **first usable prediction was already inside** in 1/27 live-3, 2/27 live-4, and 5/27 live-5 trials: **8/81 (9.88%)** pooled. Confirmed acquisition occurred by **0.50 s in 7/70 successes (10.00%)** or 7/81 total trials (8.64%); by **0.75 s in 45/70 (64.29%)** or 45/81 (55.56%); and by **1.00 s in 54/70 (77.14%)** or 54/81 (66.67%). Thus many successes followed soon after target onset, although most did not begin inside on the first usable sample.

Adjacent target centers are `0.30` normalized units apart. The full target width and height are `0.28`, leaving only a **0.02 normalized gap** between neighboring acceptance regions. This deliberately coarse geometry is useful for asking whether any region can be acquired. Combined with a 300 ms dwell and no neutral/reset fixation before each trial, it is permissive evidence for **intentional selection**: a cursor can enter quickly or carry over from the preceding gaze location. The data do not identify any particular valid v1 success as a false positive. Coarse acquisition and deliberate precise selection are distinct questions.

## Separate sessions and setup sensitivity

Live-1 was technically complete but used a different physical setup. It succeeded **4/27 (14.81%)**, versus **70/81 (86.42%)** in the primary normal-use set. Its x/y MAE were **0.0682/0.2739**, versus primary **0.0867/0.2265**: x error was actually lower, while y error was higher by about **0.0474**. Its successful confirmed-acquisition median/p95 were **1.812/3.461 s**, versus primary **0.659/2.816 s**. The calibration mapping varied:

| Session | x slope | x intercept | y slope | y intercept |
| --- | ---: | ---: | ---: | ---: |
| live-1, different setup | −9.2087 | 5.1302 | 25.7705 | 1.6353 |
| live-3 | −7.8990 | 4.3486 | 30.1038 | 1.5917 |
| live-4 | −6.6930 | 3.7509 | 28.3705 | 1.5955 |
| live-5 | −6.8348 | 3.8572 | 24.0481 | 1.4769 |

Live-1's x slope lay outside the primary range, while its y slope lay within the primary range. The broad performance difference shows session/setup sensitivity; the data do not isolate which physical difference caused it. Live-1 remains available as separate evidence.

Live-2 was also technically complete, but the participant deliberately alternated narrow/natural/wide eye opening during targeting. The JSON has no controlled condition labels, so it is **protocol-invalid for primary natural-use inference** and cannot support condition-specific eye-opening estimates. Its exploratory totals were **21/27 successes**, x/y MAE **0.0966/0.2439**, and successful confirmed-acquisition median **0.648 s**. These figures are not pooled with primary results and do not validate an eye-opening effect.

## Decision, limits, and next step

**Bounded decision:** In this participant's normal-use setup, the current production pipeline acquired the deliberately coarse v1 regions in **70/81** trials across three sessions. This supports coarse gaze-region feasibility. Eleven timeouts, the weak T-3-3 result, substantial y error/tails, and the permissive geometry prevent a claim of reliable precise selection or cursor readiness. No production feature, mapping, smoothing, OS input, or click behavior is selected from this study.

This is one participant on one camera/computer environment for the primary set. The first two captures have explicitly different behavioral/setup status. The cursor was visual feedback, so the test cannot separate pure gaze behavior from feedback-driven adaptation. Fixation was not independently measured. Raw errors include initial target transitions, and first-entry times are observed at camera-sample resolution. Full capture availability does not imply accurate gaze. The 0.02 gap, short dwell, and missing reset phase limit intentional-selection interpretation. There is no cross-user, small-target, click, actual OS-cursor, or production-readiness evidence.

**Next bounded experiment, to design separately:** `coarse_gaze_targeting` protocol **v2** should test intentional targeting using the same production pipeline and initially the same nine target centers, but half-width/half-height **0.10** (full region **0.20 × 0.20**), dwell **500 ms**, timeout **4.0 s**, and a trial-start **neutral/reset fixation phase** that prevents a new trial starting with an already-acquired target through carryover. Use natural relaxed eye opening; instruct the participant not to chase the gaze dot or deliberately steer with the head. Keep raw, unclipped metrics and no smoothing. The exact reset timing/UI belongs to v2 design, not this frozen v1 analysis. **V2 is an interaction-selection test, not another vertical-feature experiment.**
