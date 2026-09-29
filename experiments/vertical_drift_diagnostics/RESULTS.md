# Calibration-to-use vertical-feature drift — Results

## Environment and protocol

Çağrı completed two separate controlled runs on the development Mac with camera index 1, 1920 × 1080 camera input, and a 1200 × 700 target-window image area. Session A used a normal comfortable posture; before Session B, the participant reported leaving/resetting/reseating normally. Each run fitted a **fresh** session-local calibration. The participant was instructed to use natural eye opening and blinking, not to wink intentionally or adjust posture/camera for a desired result. Those behaviors cannot be independently verified from numerical data.

The [planned protocol](README.md) was used unchanged: nine calibration targets, the same 16 held-out trials, and CENTER checkpoints 0–4 immediately after calibration and after each block of four held-out trials. Seed 42, 0.8 s settling, 1.2 s sampling, and a minimum of five usable samples per presentation were used. The only addition to the merged validation protocol was the five repeated CENTER presentations; the experimental Experiment 006 blink gate remained absent. Derived numerical data are local and Git-ignored at `.venv/vertical-drift-cagri-A.json` and `.venv/vertical-drift-cagri-B.json`. Neither the harness nor these files save camera frames, photographs, or video.

| Acquisition | Session A | Session B |
| --- | ---: | ---: |
| Elapsed | 60.483 s | 60.371 s |
| Camera reads including settling | 1,778 | 1,774 |
| Failed camera reads | 0 | 0 |
| No-face observations including settling | 0 | 0 |
| Sampling attempts / usable | 1,066 / 1,066 | 1,067 / 1,067 |
| Calibration targets / held-out trials / CENTER checkpoints | 9 / 16 / 5 | 9 / 16 / 5 |
| Calibration-center vertical median | -0.045623 | -0.048167 |
| Fitted vertical slope / intercept | 28.6059 / 1.7161 | 31.9928 / 1.9099 |

## CENTER checkpoint measurements

All values are derived numerical features. Time is the median elapsed monotonic time of each checkpoint's sampling attempts. `Δcal` compares the checkpoint's vertical median with the **same session's exact C-2-2 calibration-target median**; `Δ0` compares with checkpoint 0. The per-eye, lid-opening, and face-center-y entries are medians, not inputs to any correction. Every checkpoint had 35–36 usable frames and no unavailable sampling attempts.

| Session | Checkpoint | Time (s) | Vertical median | IQR | Δcal | Δ0 | Left / right vertical medians | Binocular opening | Face-center y |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| A | 0 | 19.575 | -0.046198 | 0.006331 | -0.000575 | 0 | -0.048572 / -0.044135 | 0.327653 | 0.450912 |
| A | 1 | 29.678 | -0.045032 | 0.001501 | +0.000591 | +0.001167 | -0.048254 / -0.041885 | 0.338177 | 0.438207 |
| A | 2 | 39.773 | -0.049362 | 0.002630 | -0.003739 | -0.003163 | -0.052961 / -0.045907 | 0.340488 | 0.450666 |
| A | 3 | 49.844 | -0.046862 | 0.003090 | -0.001239 | -0.000664 | -0.050194 / -0.043559 | 0.324495 | 0.440669 |
| A | 4 | 59.915 | -0.050970 | 0.002072 | -0.005347 | -0.004771 | -0.054731 / -0.046955 | 0.333451 | 0.453649 |
| B | 0 | 19.553 | -0.049271 | 0.001706 | -0.001103 | 0 | -0.053340 / -0.045217 | 0.315073 | 0.465233 |
| B | 1 | 29.623 | -0.051190 | 0.004291 | -0.003023 | -0.001919 | -0.055311 / -0.047124 | 0.336748 | 0.479946 |
| B | 2 | 39.680 | -0.050562 | 0.002461 | -0.002395 | -0.001292 | -0.054663 / -0.046420 | 0.314067 | 0.473566 |
| B | 3 | 49.732 | -0.051096 | 0.003332 | -0.002929 | -0.001825 | -0.055143 / -0.046536 | 0.333826 | 0.467411 |
| B | 4 | 59.803 | -0.051373 | 0.002220 | -0.003206 | -0.002102 | -0.054954 / -0.047704 | 0.333041 | 0.480437 |

Session A's checkpoint medians span -0.050970 to -0.045032; B's span -0.051373 to -0.049271. Checkpoint 0 was only -0.000575 (A) and -0.001103 (B) below each calibration-center median. By checkpoint 4, those differences were -0.005347 and -0.003206, respectively. The A sequence rises, falls, partly recovers, then falls again; B shifts down after checkpoint 0 but also fluctuates. These are **not** clean monotonic time trends or evidence for a single immediate jump.

From checkpoint 0 to 4, A's left/right vertical medians changed by -0.006159 / -0.002821; B's changed by -0.001614 / -0.002486. Both eyes moved numerically in each session, but the relative per-eye contribution differed, so consistent one-eye dominance is **not** established. Binocular opening changed by +0.005798 (A) and +0.017969 (B), and face-center y by +0.002737 (A) and +0.015204 (B). Across the five checkpoint medians, the descriptive vertical/opening correlations were -0.232 (A) and -0.807 (B); vertical/face-center-y correlations were -0.758 and -0.723. Five non-independent checkpoint summaries are insufficient for a causal or statistically significant claim. The opening association did not have similar magnitude across A/B; the coarse face-position association reproduced descriptively but cannot distinguish translation from pitch or other geometry changes.

## Held-out mapping context

| Held-out metric | Session A | Session B |
| --- | ---: | ---: |
| Horizontal MAE | 0.0657 | 0.0441 |
| Vertical MAE | 0.1869 | 0.1796 |
| Signed x / y bias | -0.0657 / -0.1869 | -0.0441 / -0.1678 |
| Spatial ordering, x / y | 21/21 / 21/21 | 21/21 / 20/21 |

The post-calibration CENTER shift has the same negative direction as held-out y bias. The fitted mapping predicts y≈0.411 (A) and y≈0.369 (B) **at the calibration-center feature itself**, already below the center target's y=0.50. Thus the held-out bias cannot be attributed to checkpoint drift alone. The checkpoint-4 shifts correspond illustratively to approximately -0.153 (A) and -0.103 (B) normalized y using each fitted slope, but a final CENTER checkpoint is not the mean of the 16 held-out trials. No offset was applied.

## Limitations and runtime observation

This is a short, single-user, two-session exploratory diagnostic; no statistical significance or cross-user result is claimed. Time and gaze excursions occurred together between checkpoints, so the protocol cannot separate elapsed-time drift from changes after looking away and returning. The identical CENTER target limits target-position confounding at checkpoints, but does not measure head pitch, camera distance, lighting, glasses position, or physiological causes. Per-eye and opening measures are derived proxies, not independent causal measurements. The current observation contract does not provide blink blendshape scores. Fatih's previous near-flat y behavior remains unexplained.

MediaPipe logged a `portable_clearcut_uploader` **failed send** message near the end of both runs. The harness itself has no upload path and saved only derived numerical JSON, but the log does not reveal the attempted telemetry payload. This third-party behavior needs separate privacy review; these runs alone cannot establish that the library never attempts network communication. No production Vision/Gaze behavior was changed here.

## Conclusion

Both controlled sessions measured a small calibration-to-checkpoint-0 shift and larger negative vertical-feature offsets at later identical CENTER checkpoints. The effect is therefore **observable after calibration in both sessions**, but it was non-monotonic in A and only modestly variable after checkpoint 1 in B; neither an immediate jump nor smooth progressive time drift is established. Both eyes contributed numerically, while eye opening and the coarse face-center-y proxy showed descriptive, session-dependent associations. The **cause remains inconclusive** because time, intervening gaze movement, and face/eyelid geometry were not independently controlled. The feature shifts can contribute to negative mapped y predictions, but calibration-fit center offset also matters. No correction, filter, threshold, or production algorithm is validated or implemented. Cross-user validation remains deferred.
