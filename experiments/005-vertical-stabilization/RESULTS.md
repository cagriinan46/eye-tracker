# Experiment 005 — Results

## Environment

Offline analysis was run locally on the development Mac with Python 3.12.13 and macOS 26.2. The input CSVs were produced by the Experiment 004 human camera runs; this stage did **not** access the camera or re-run Face Landmarker. The exact capture-time Python patch and OpenCV versions were not supplied. No new dependency or production framework decision was made.

## Input Datasets

All three local, Git-ignored Experiment 004 numerical CSVs were available and analyzed. They were **not** committed. Run 1: no glasses, natural opening, manually better-centered camera. Run 2: glasses and intentionally slightly wider opening (**diagnostic**, not normal use). Run 3: glasses and natural opening (most relevant normal-use repeat with glasses). All runs used stable-head instructions and natural blinking without intentional winks. Camera/face geometry differed across runs; they are not an isolated glasses comparison.

| Run | Local input | Rows | Valid raw rows | Median sample interval | Observed within-trial rate |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | `.venv/vertical-gaze-stable.csv` | 894 | 894 | 33.471 ms | 29.88 FPS |
| 2 — diagnostic | `.venv/vertical-gaze-stable2.csv` | 894 | 894 | 33.289 ms | 30.04 FPS |
| 3 — natural opening | `.venv/vertical-gaze-stable3.csv` | 897 | 897 | 33.462 ms | 29.88 FPS |

The rates above are from median intervals between adjacent sampling frames, omitting unsampled trial-transition gaps. They are **not** full-run effective FPS or camera acquisition metrics. No face/geometry-invalid rows occurred in these CSVs; Experiment 004 separately reported no camera-read or tracking-loss failures during capture.

## Baseline

The unmodified `binocular_vertical_local_axis` is the baseline. Raw means reproduced Experiment 004's UP < CENTER < DOWN ordering. Raw frame ranges overlapped for all three pairwise direction comparisons in every run. The raw CENTER means shifted from `-0.04707` to `-0.04088` to `-0.03474` across sessions; no temporal method can be expected to remove this absolute session offset.

## Candidate Methods

The predeclared compact set is raw; trailing 120/240 ms medians; trailing 120 ms mean; EWMA with current-sample weight `0.45`; and 120 ms median after conservative blink rejection. All windows use observed timestamps and only past/current data. At these measured rates, 120 ms contains approximately four samples and 240 ms approximately seven. No per-run or direction-specific method tuning was performed. See [README.md](README.md) for exact rules.

## Blink / Outlier Handling

The experimental gate requires both a blink score at least `0.65` in either eye **and** binocular opening at most `70%` of a recent accepted-opening median. Low opening alone is retained. It excluded 14/894 frames in Run 1 (UP 9, CENTER 1, DOWN 4), 3/894 in Run 2 (UP 1, CENTER 2, DOWN 0), and 6/897 in Run 3 (UP 3, CENTER 0, DOWN 3). Rejection is not a demonstrated gesture classifier and its parameters are not production thresholds.

For a consistent descriptive transient measure, each run's raw within-segment adjacent absolute-difference p95 was used as a *common evaluation cutoff* for that run, never as a filtering rule. The cutoffs were approximately `0.00493`, `0.00281`, and `0.00353` for Runs 1–3. Missing/rejected outputs cannot form adjacent pairs, so lower counts for the blink method partly reflect reduced availability. No samples were manually deleted or selected based on target labels.

## Measurements

The compact table gives sample standard deviation for UP/CENTER/DOWN and jump counts above each run's raw p95 cutoff. Full per-label **count, mean, standard deviation, median, MAD, min/max, p10/p90, and every trial mean/median** are printed by the script or available via `--json`; the CSVs are not necessary to read this bounded interpretation. The blink method retained 880, 891, and 891 outputs respectively; all other methods retained all 894, 894, and 897 valid frames.

| Run | Method | UP std | CENTER std | DOWN std | Large adjacent jumps |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | Raw | 0.01408 | 0.00588 | 0.00764 | 44 |
| 1 | Median 120 ms | 0.01403 | 0.00574 | 0.00767 | 38 |
| 1 | Median 240 ms | 0.01313 | 0.00527 | 0.00754 | 32 |
| 1 | Mean 120 ms | 0.01362 | 0.00553 | 0.00744 | 52 |
| 1 | EWMA 0.45 | 0.01316 | 0.00539 | 0.00726 | 40 |
| 1 | Blink + median 120 ms | 0.01244 | 0.00552 | 0.00643 | 25 |
| 2 | Raw | 0.00557 | 0.00502 | 0.00287 | 44 |
| 2 | Median 120 ms | 0.00530 | 0.00474 | 0.00277 | 22 |
| 2 | Median 240 ms | 0.00446 | 0.00373 | 0.00269 | 14 |
| 2 | Mean 120 ms | 0.00517 | 0.00457 | 0.00275 | 28 |
| 2 | EWMA 0.45 | 0.00503 | 0.00441 | 0.00274 | 24 |
| 2 | Blink + median 120 ms | 0.00493 | 0.00426 | 0.00277 | 18 |
| 3 | Raw | 0.01292 | 0.00800 | 0.00868 | 45 |
| 3 | Median 120 ms | 0.01302 | 0.00877 | 0.00922 | 42 |
| 3 | Median 240 ms | 0.01243 | 0.00943 | 0.00988 | 37 |
| 3 | Mean 120 ms | 0.01261 | 0.00868 | 0.00906 | 46 |
| 3 | EWMA 0.45 | 0.01228 | 0.00844 | 0.00874 | 46 |
| 3 | Blink + median 120 ms | 0.01213 | 0.00877 | 0.00900 | 37 |

Median absolute deviation (MAD) did not consistently decrease. For example, CENTER MAD in Run 3 was `0.00451` raw, `0.00463` with 240 ms median, and `0.00461` with blink + 120 ms median. Thus improvements in some standard deviations must not be interpreted as universal spread reduction.

## Per-Run Results

| Run | Raw UP / CENTER / DOWN mean | Blink + median 120 ms mean | Raw trial-mean spans (UP / CENTER / DOWN) | Blink + median spans |
| --- | --- | --- | --- | --- |
| 1 | -0.05189 / -0.04707 / -0.03968 | -0.05270 / -0.04714 / -0.04009 | 0.00890 / 0.00654 / 0.01238 | 0.00721 / 0.00652 / 0.01057 |
| 2 — diagnostic | -0.05085 / -0.04088 / -0.03262 | -0.05093 / -0.04105 / -0.03258 | 0.00586 / 0.00502 / 0.00641 | 0.00577 / 0.00422 / 0.00643 |
| 3 — natural opening | -0.04539 / -0.03474 / -0.02466 | -0.04556 / -0.03436 / -0.02456 | 0.01518 / 0.00833 / 0.00937 | 0.01629 / 0.00835 / 0.01066 |

Each span is the maximum minus minimum of the five within-label trial means; smaller is more repeatable by this descriptive measure. The blink method improved all three Run 1 spans, two Run 2 spans slightly, but **worsened all three Run 3 spans**. The 240 ms median similarly worsened Run 3 trial-mean spans (UP `0.01780`, CENTER `0.00849`, DOWN `0.01226`). Per-trial means and medians for every candidate are reproducible from the script's text/JSON output; no significance test is claimed.

## Cross-Run Comparison

All six methods retained UP < CENTER < DOWN **aggregate mean ordering** in each run. None removed raw-range overlap in any run. The p10–p90 ranges overlapped for every pair in Run 1, for UP/CENTER and CENTER/DOWN in Run 3, and for no pair in diagnostic Run 2; this pattern was unchanged by the tested methods. Pairwise mean deltas were broadly similar to raw values, so filters did not simply flatten the directional means, but they also did not establish robust frame-level separation. The session-level CENTER offset remained materially larger than many within-run UP–CENTER differences.

## Latency Considerations

A 120 ms trailing window uses values up to 120 ms old (rough centered-response intuition about 60 ms); a 240 ms window uses up to 240 ms old (rough intuition about 120 ms). EWMA 0.45 has an approximate mean sample age of 40 ms at the observed ~33 ms interval, with a longer tail. Blink rejection can produce a missing estimate during the event. Actual visual-target transition latency and interactive comfort were **not measured** in these CSVs because the protocol omitted one-second transitions from sampling; jump reduction alone cannot prove true gaze transitions are preserved.

## Observations

Short temporal methods generally lowered single-frame jump counts, especially median 240 ms in diagnostic Run 2 (44 to 14). The mean 120 ms raised counts in Run 1 (44 to 52), showing that the transient metric is method-sensitive. Blink rejection reduced apparent variance in some run/label combinations but also removed direction-dependent numbers of frames. Strong prior blink/eye-opening correlations from Experiment 004 remain a caution; the present analysis does not establish which deviations were caused by blinks. No genuine target-transition preservation could be checked from the sampling-only CSVs.

## Limitations

Single user, three short runs, no statistical significance. Run 2 intentionally widened eye opening and is diagnostic; glasses and camera/face geometry also changed. Correlation does not establish causation. Raw visual data was not stored. The blink gate's numerical parameters are exploratory and were not validated as safe for diverse users or normal gaze; dropped samples may hide rather than solve difficulty. Resetting at the known unsampled trial gaps avoids contamination in this offline protocol, but continuous live transitions are untested. The analysis neither calibrates screen coordinates nor fixes between-session offsets. MediaPipe/OpenCV remain experiment-specific candidates, not production decisions.

## Conclusion

The offline comparison is **inconclusive for selecting a stabilization method**. Causal short-window methods reduced some transient jumps and generally preserved aggregate UP/CENTER/DOWN ordering, but raw direction ranges still overlapped, robust/trial spread did not improve consistently across all runs, and the natural-opening Run 3 often became less repeatable. Conservative blink rejection incurred missing outputs and has not been shown to preserve genuine gaze transitions. No method is approved as a live/production gaze filter, and full 2D calibration remains unvalidated. Between-session offset remains a separate future calibration question.

## Human Validation Status

The three existing human capture runs were reused; **no additional camera run was performed or requested**. Given the mixed offline evidence, asking for another repeated run now is not justified. A future live normal-use validation should be considered only after the team identifies a better-supported candidate and a way to measure transition delay while retaining the Experiment 004 UP/CENTER/DOWN protocol. This document does not claim the Experiment #18 hypothesis is confirmed.
