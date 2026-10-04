# Offline intentional-targeting failure and solution benchmark — results

## Question and valid input

Can a causal temporal filter, a calibration-robust independent mapping, or a calibration-only affine mapping materially improve the strict intentional-targeting failures? The only input was the two valid `cagri` cue-based v2 captures: `.venv/intentional-gaze-cagri-live-1.json` and `.venv/intentional-gaze-cagri-live-2.json`. Both passed the v2 analyzer's protocol, calibration, 27-target schedule, and raw dwell checks. The reset-gated pilots, protocol-v1 data, and protocol-invalid files were excluded. No new camera data, diagnostic-label fit, or production change was made. The [README](README.md) fixes all formulas and gate rules.

## Exact production replay

Refitting M0 from each session's nine saved calibration medians reproduced every stored mapping coefficient exactly. Reconstructing all **6,105** usable target predictions from recorded horizontal/vertical features gave a maximum coordinate difference of **0.0** from the logged raw predictions. Replaying their monotonic timestamps with the original 0.10 × 0.10 half-size, 1.0 s dwell, and 5.0 s timeout gave **zero outcome or dwell-timing mismatches across 54 trials**. Thus the alternative comparisons start from the actual production baseline.

The cameras had zero failed reads and zero no-face observations; all 6,105 target observations were usable. The baseline acquired **10/27** targets in each session, **20/54 = 37.04%** pooled. The 34 timeouts are retained.

## Replay comparison

The success column means **success reached inside the recorded observation window**, not guaranteed end-to-end success in a new live run. `Censored` counts candidate trials still unacquired when a production-success recording stopped early. x/y/Euclidean MAE are sample-weighted over identical logged windows for every candidate; acquisition timing uses the candidate's observed successes only.

| Candidate | Observed success live-1 / live-2 / pooled | Censored | x MAE | y MAE | Euclidean MAE | Median confirmed latency (s) | Re-entries / interruptions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **M0+T0 production** | **10 / 10 / 20** | 0 | 0.05377 | 0.20454 | 0.22196 | 2.028 | 75 / 93 |
| M0+T1 EMA 0.35 | 1 / 0 / 1 | 19 | 0.05851 | 0.20495 | 0.22508 | 1.573* | 44 / 62 |
| M0+T2 median 5 | 2 / 0 / 2 | 19 | 0.05950 | 0.20865 | 0.22926 | 2.661* | 43 / 59 |
| M1+T0 axis medians | 4 / 7 / 11 | 13 | 0.05569 | 0.23795 | 0.25471 | 1.374* | 40 / 62 |
| M2+T0 affine | 8 / 8 / 16 | 11 | 0.05964 | 0.19629 | 0.21585 | 1.901* | 60 / 77 |

`*` Candidate latency medians are based on different and fewer successful trials than baseline and must not be read as a same-trial speed improvement. Baseline median first entry was 0.366 s and p95 confirmed acquisition was 4.716 s. The candidate median first-entry latencies were 0.527 (T1), 0.456 (T2), 0.413 (M1), and 0.386 s (M2). Pooled p95 Euclidean errors were 0.50277 (M0), 0.51606 (T1), 0.54258 (T2), 0.56767 (M1), and 0.54275 (M2).

### Temporal stabilization

T1 lowered re-entries from 75 to 44 and interruptions from 93 to 62; T2 lowered them to 43 and 59. Those counts are descriptive because a candidate can have a different acquisition stop point. T1 increased x MAE **8.81%** and y MAE **0.20%**. T2 increased x MAE **10.66%**, y MAE **2.01%**, and its observed-success median acquisition time by **0.632 s**. Neither delivered the required +5-point success gain. Among the **34 fully recorded production timeouts**, T1 rescued **0** and T2 rescued **1**; the other 19 unacquired filtered trials were censored after production success. Even granting all 19 censored trials eventual success, T1 would reach at most 20/54 and T2 at most 21/54, below the +5-point gate. The data show some smoothing of dwell interruptions but do not establish a usable interaction improvement.

### Calibration mappings

M1's axis-level medians made the fitted y slopes steeper and increased pooled target y MAE **16.33%**. M2's affine terms reduced pooled y MAE by only **4.04%** while increasing x MAE **10.92%**. M1 rescued 4 and M2 rescued 7 of the 34 fully recorded baseline timeouts, but each lost observed successes from baseline-success windows (13 and 11 censored respectively). A conservative observed-success comparison is 11/54 for M1 and 16/54 for M2. Even if all censored mapping cases later succeeded, neither meets the required **15% y-MAE reduction**. The affine in-sample calibration improvement therefore does not make it a selected interaction mapping.

## Calibration robustness and sensitivity

Coefficients below were fitted **only** from each run's nine ordinary calibration presentation medians. `LOO` refits on eight and predicts the omitted calibration target. Gains are absolute fitted coefficients for M0/M1, and the norm of the two feature coefficients for each M2 output axis; horizontal and vertical feature units differ, so the M2 norms are only descriptive.

| Mapping / session | x coefficients | y coefficients | Calibration x / y MAE | LOO x / y MAE | x / y gain norm |
| --- | --- | --- | ---: | ---: | ---: |
| M0 live-1 | −6.13376, +3.53468 | +39.17277, +1.89086 | 0.02553 / 0.06469 | 0.03375 / 0.09018 | 6.13376 / 39.17277 |
| M0 live-2 | −5.91045, +3.42707 | +18.90458, +1.31384 | 0.03109 / 0.11779 | 0.04196 / 0.14691 | 5.91045 / 18.90458 |
| M1 live-1 | −6.27032, +3.59073 | +44.83965, +2.07228 | 0.02233 / 0.06105 | 0.03463 / 0.07930 | 6.27032 / 44.83965 |
| M1 live-2 | −5.93606, +3.44509 | +26.88921, +1.65244 | 0.03035 / 0.13859 | 0.04076 / 0.18776 | 5.93606 / 26.88921 |
| M2 live-1 | h −6.23169, v +3.00489, c +3.68982 | h −0.95136, v +40.53903, c +2.41006 | 0.02122 / 0.05488 | 0.03595 / 0.09203 | 6.91833 / 40.55019 |
| M2 live-2 | h −5.50940, v −3.52537, c +3.07669 | h −3.48681, v +25.32313, c +3.31695 | 0.02378 / 0.06695 | 0.03957 / 0.10213 | 6.54077 / 25.56205 |

M0 y slope was **39.17277** in live-1 and **18.90458** in live-2, a **2.07×** change; its calibration y MAE was lower in live-1, although target y MAE was higher there (0.21570 versus 0.19191). M2 improves both in-sample calibration y fits, especially live-2, but its leave-one-out y MAE is slightly worse than M0 in live-1 (0.09203 versus 0.09018). Largest absolute calibration y residuals were 0.13067/0.34392 for M0, 0.21277/0.36760 for M1, and 0.10958/0.19500 for M2 (live-1/live-2). Calibration fit alone did not predict interaction success.

## Position-dependent residual diagnosis

The table uses raw M0 target predictions. Bias is `prediction − known target`; spread is within-trial y `p95−p05`. All-sample errors include gaze travel immediately after the cue. The late-window metric starts 3.0 s after target onset and is available only for trials lasting that long; it is a diagnostic subset, not independent fixation truth.

| Group | Median signed x bias | Median signed y bias | Median late signed y bias | x / y MAE | Median within-trial y spread |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pooled | −0.0026 | −0.0850 | −0.0551 | 0.0538 / 0.2045 | 0.2854 |
| live-1 | −0.0076 | **+0.0660** | +0.0917 | 0.0554 / 0.2157 | 0.4824 |
| live-2 | +0.0061 | **−0.1332** | −0.1344 | 0.0519 / 0.1919 | 0.1859 |
| Upper row | +0.0045 | +0.0436 | +0.1542 | 0.0519 / 0.2038 | 0.5118 |
| Center row | −0.0109 | −0.0919 | −0.0963 | 0.0506 / 0.1781 | 0.1587 |
| Lower row | −0.0057 | −0.1848 | −0.1762 | 0.0586 / 0.2299 | 0.2895 |
| Left column | +0.0264 | +0.1331 | +0.1566 | 0.0636 / 0.1845 | 0.2416 |
| Center column | −0.0048 | −0.1027 | −0.0998 | 0.0304 / 0.1911 | 0.4586 |
| Right column | −0.0172 | −0.1608 | −0.1435 | 0.0655 / 0.2340 | 0.2292 |

By individual target, median signed y bias / y MAE were: T-1-1 **+0.1598 / 0.2028**, T-1-2 −0.0652 / 0.1861, T-1-3 −0.1378 / 0.2189, T-2-1 +0.1281 / 0.1424, T-2-2 −0.1013 / 0.1863, T-2-3 −0.1248 / 0.1895, T-3-1 +0.0034 / 0.1879, T-3-2 −0.1830 / 0.2009, and T-3-3 **−0.3217 / 0.2945**. Baseline target success was 0/6 at T-1-1 and 1/6 at T-3-3. M2 changed these to 4/6 and 1/6 respectively, while T-1-2 dropped from 4/6 to 0/6: a calibration-only affine map redistributes successes by position rather than resolving all weak locations.

The median within-trial y spread in the **41** trials with at least two samples after 3.0 s was **0.1152** (live-1 0.1244 across 24 trials; live-2 0.0733 across 17). Across repeated blocks of the same target within a session, median absolute difference of trial-median y was **0.1081**; p95 was **0.4402** over 54 block pairs. These numbers include behavior and estimator changes and cannot isolate sensor jitter. The changing row and column signs, the session-bias reversal, and the T-3-3 tail argue against a single universal y offset. They are consistent with position-dependent residuals and calibration/session sensitivity, but cannot distinguish nonlinear mapping error from changes in gaze or upstream features. No target-label correction was fitted.

Specifically, the upper-to-lower signed-y trend could reflect gain/row calibration mismatch, while the left-to-right sign change indicates a column-dependent component. A three-row layout does not distinguish a nonlinear row function from calibration-to-target feature movement. T-3-3 is a corner-specific weak case, yet T-1-1 also fails despite an opposite signed bias. The late-window spread shows within-trial variation remains after some initial gaze travel; it does not establish detector jitter as its source. These diagnoses overlap and none alone explains every failure.

## Predeclared gates and decision

`PASS` requires **every** criterion in its family. Success uses the conservative observed-count denominator; timing is included for completeness but is selection-biased by censoring.

| Candidate | Success gain | Session limit | y MAE | x MAE | Stability | Latency | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T1 EMA | FAIL | — | PASS | PASS | PASS | PASS* | **FAIL** |
| T2 median 5 | FAIL | — | PASS | FAIL | PASS | FAIL* | **FAIL** |
| M1 axis medians | FAIL | FAIL | FAIL | PASS | — | PASS* | **FAIL** |
| M2 affine | FAIL | FAIL | FAIL | PASS | — | PASS* | **FAIL** |

Both families failed, so the rule prohibited a combined-candidate grid; **no combined candidate was evaluated**. No winner was selected. T1/T2 reduce observed entry interruptions but do not rescue meaningful numbers of full-window failures. M1 worsens target y error; M2 improves calibration fit without meeting the target y-error gate. The strongest measured blocker remains vertical spatial error with position and session dependence, accompanied by within-trial variation. The captures do not isolate one physical or software root cause.

## Limits and next bounded step

This is two sessions from one participant, with only the production mapping/cursor actually shown to the human. Alternative cursor paths might change human gaze behavior. Production-success recordings stop early, creating 19, 19, 13, and 11 censored T1/T2/M1/M2 cases. The same target trials provide evaluation for a small fixed candidate set, not an external holdout or cross-user validation. A 3-second late window reduces but does not eliminate gaze travel or selection bias. Camera availability was high; it does not prove fixation or estimator accuracy. Nothing here supports a production filter, replacement mapping, precise cursor, click, clinical, accessibility, or population-readiness claim.

**Next engineering step:** deliberately scope a more fundamental **offline gaze-estimation and calibration redesign**, beginning with a measurement/validation protocol that can observe the **full 5.0 s window independently of when the baseline succeeds**, and diagnose row/column residuals and calibration-to-target transfer without target-label fitting. Decide its design with the human team before implementation. Retain the current production path and the documented v1 coarse-feasibility result; do not launch another ad hoc filter, mapping, or hand-crafted vertical-feature search from these same two captures.
