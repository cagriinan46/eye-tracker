# Issue #52 — Vertical position and repeat variability results

## Input datasets and condition

Offline analysis used four existing local, Git-ignored derived-numerical JSON files: `.venv/vertical-collapse-cagri-{A,B}.json` and `.venv/vertical-drift-cagri-{A,B}.json`. All four were from Çağrı on the development Mac using camera index 1, normal comfortable posture and natural blinking. The collapse runs each had nine calibration targets and 16 held-out presentations; the drift runs added five exact-CENTER checkpoints. The successful Experiment 006 CSV was inspected for comparable fields but not pooled because it used a separate experimental blink gate. No new camera data was used for the offline measurements below. No raw visual data was stored by these harnesses.

## Same-Y horizontal-position comparisons — offline

The table reports the span between per-target (or, for repeated held-out targets, per-target-across-trials) **vertical feature medians**. The illustrative normalized-Y span multiplies this by that session's existing fitted `abs(y_slope)`; it is not an accuracy score or correction. Values are rounded, while the local analyzer retains full precision.

| Session | Calibration Y=0.20 / 0.50 / 0.80 feature spans | Held-out Y=0.35 / 0.50 / 0.65 feature spans | Illustrative mapped-Y spans, calibration / held-out |
| --- | --- | --- | --- |
| Collapse A | 0.00347 / 0.00126 / 0.00164 | 0.00501 / 0.00083 / 0.00373 | 0.150 / 0.054 / 0.071 ; 0.217 / 0.036 / 0.162 |
| Collapse B | 0.00170 / 0.00366 / 0.00187 | 0.00448 / 0.00180 / 0.00309 | 0.074 / 0.161 / 0.082 ; 0.196 / 0.079 / 0.136 |
| Drift A | 0.00728 / 0.00915 / 0.01010 | 0.00409 / 0.00114 / 0.00293 | 0.208 / 0.262 / 0.289 ; 0.117 / 0.033 / 0.084 |
| Drift B | 0.00156 / 0.00939 / 0.00713 | 0.00425 / 0.00408 / 0.00999 | 0.050 / 0.300 / 0.228 ; 0.136 / 0.130 / 0.320 |

Vertical medians differed across X at fixed Y, but **the direction and size were inconsistent** across rows and sessions. For example, calibration-center-row left/center/right medians were approximately `-0.03647/-0.04562/-0.04491` in Drift A, `-0.03963/-0.04817/-0.04902` in Drift B, and `-0.04985/-0.04987/-0.05110` in Collapse A. The row-major calibration order ties X to elapsed time. The prior held-out sequence contains two presentations per location, but the same shuffled order was reused in all sessions; several same-Y X groups also remain time-ordered. These observations are compatible with a positional association but do **not** isolate one from collection order, changes after previous targets, or other session variation. The earlier mapping's row-anchor calibration improvement does not resolve this confounding.

## Repeated identical targets — offline

Each held-out location appeared twice. The table gives the median and largest absolute difference between its two presentation-level vertical medians, across the eight held-out targets in each session. CENTER checkpoint span is from five repeats and is not directly comparable to a two-repeat statistic.

| Session | Median absolute held-out repeat difference | Largest held-out repeat difference | Five-CENTER median span, if present |
| --- | ---: | ---: | ---: |
| Collapse A | 0.00230 | 0.00995 | N/A |
| Collapse B | 0.00150 | 0.00359 | N/A |
| Drift A | 0.00170 | 0.00304 | 0.00594 |
| Drift B | 0.00141 | 0.00718 | 0.00210 |

These are **identical-coordinate** comparisons, so target position alone cannot explain their differences. The changes are not uniform in sign, and elapsed time is coupled with intervening gaze movements. The four sessions show descriptive repeat variability, but neither a smooth time drift nor its physical mechanism is established. Some repeated-target differences are comparable to or larger than same-Y between-X spans. Horizontal remains a reference rather than a correction input: the median absolute repeated-target binocular horizontal change across the eight held-out targets was 0.00133 / 0.00279 / 0.00146 / 0.00161 in Collapse A/B and Drift A/B, respectively.

## Per-eye and diagnostic observations

The median absolute repeated-target left/right vertical changes were respectively `0.00250/0.00209` (Collapse A), `0.00142/0.00202` (Collapse B), `0.00231/0.00172` (Drift A), and `0.00177/0.00120` (Drift B). Both eyes contribute numerically; no consistent one-eye dominance follows. Eye-opening and coarse face-center-Y values also changed between repeated presentations, but their shifts were not independently controlled. The prior [Issue #46 checkpoint analysis](../vertical_drift_diagnostics/RESULTS.md) found session-dependent opening associations and a descriptive coarse face-position association; correlation is not causation. Blink blendshape scores are unavailable through the current production observation contract, and that contract was not changed.

## Need for a controlled run

The offline data support **repeated identical-target variability**. They do not distinguish a horizontal-position association from target order/time or other co-varying behavior. The conditional short, reversed-order protocol in [README.md](README.md) is therefore justified to test whether same-Y positional patterns recur when X order reverses. It is not a new calibration-model competition.

## Controlled run

Çağrı completed one on-screen session on the development Mac, using camera index 1, 1920×1080 camera input, and the 1200×700 target-window image area. The derived numerical file is local and Git-ignored at `.venv/vertical-position-cagri-controlled-1.json`. It has 27 completed presentations: nine fresh-calibration targets and two diagnostic passes over the same nine coordinates, the second in exactly reversed order. Existing production feature extraction, median aggregation, and independent-linear fitting were reused; no gaze model or feature formula was changed. The instructed condition was normal comfortable posture, natural eye opening/blinking, and no deliberate camera/head/glasses manipulation; compliance cannot be independently verified from numerical output. The Experiment 006 experimental blink gate was absent, as in the current production path.

| Acquisition / mapping | Measured value |
| --- | ---: |
| Elapsed | 54.421 s |
| Camera reads including settling | 1,559 |
| Failed camera reads / no-face observations | 0 / 0 |
| Sampling frames / usable | 933 / 933 |
| Vertical mapping slope | 22.69249 normalized Y per feature unit |

The table gives each diagnostic presentation's **binocular vertical median** at X=0.20, 0.50, 0.80. Values are uncalibrated features. The second pass reverses both row and X order, so its X-time order is opposite the first pass within each Y row.

| Y row | Pass 1: left / center / right | Pass 2: left / center / right | Between-X span: pass 1 / pass 2 |
| --- | --- | --- | ---: |
| Top 0.20 | -0.05794 / -0.06411 / -0.05900 | -0.05583 / -0.06153 / -0.05953 | 0.00617 / 0.00570 |
| Center 0.50 | -0.04856 / -0.04170 / -0.04633 | -0.05180 / -0.05059 / -0.04961 | 0.00686 / 0.00220 |
| Bottom 0.80 | -0.03510 / -0.03735 / -0.02547 | -0.04246 / -0.03306 / -0.03522 | 0.01188 / 0.00940 |

The analyzer preserved each pass and confirmed the X order was left→right in pass 1 and right→left in pass 2. The top-row CENTER value was more negative than both sides in **both** order directions. The center and bottom rows did **not** reproduce a stable left/center/right pattern: center-row ordering changed, and bottom-row values shifted strongly between passes. Thus one top-row association is visible, but this single session does not establish a general X-dependent vertical feature across Y regions. The already-fitted mapping converts each pass's between-X spans to illustrative normalized-Y spans of 0.140/0.129 (top), 0.156/0.050 (center), and 0.270/0.213 (bottom). These are not held-out accuracy metrics. Within-presentation vertical IQR reached 0.00936 at the first center target, so frame-level spread sometimes rivals a between-X difference.

The same nine coordinates were revisited after approximately 2.03–34.25 seconds, depending on order. Across their two presentation medians, the median absolute vertical difference was **0.00327** and the largest was **0.00975**. The corresponding median and largest absolute mapped-Y changes were approximately **0.074** and **0.221** using the run's fitted slope. The exact CENTER target changed by **-0.00889** in vertical feature (about **-0.202 normalized Y** under that mapping). The bottom-right target changed by **-0.00975** despite its two presentations being only about **2.03 s** apart. These signs and intervals do not show a smooth monotonic time drift; elapsed time, prior gaze target, and ordinary eye/head behavior remain coupled.

Horizontal feature medians separated left/center/right diagnostic targets in the expected order within both passes: for example, the center row's first pass was 0.55230 / 0.48673 / 0.43795 and its reverse pass was 0.54323 / 0.49184 / 0.43783. This is a reference that the presented X positions affected the observed horizontal signal; it does not prove exact fixation or eliminate other confounds.

The left/right vertical medians both changed across identical-target repeats. Their median absolute changes over nine targets were approximately **0.00541** and **0.00200**, respectively, but per-target contributions varied and this single run does not establish one-eye dominance. For the top row, the left-eye vertical feature generally became more negative from left to right while the right-eye feature generally became less negative, yielding a binocular pattern that is not a simple monotonic X trend. Binocular eye-opening and coarse face-center-Y also changed between presentations (for exact CENTER, opening changed by about **-0.03337** and face-center-Y by **+0.00758**); these are descriptive co-movements, not causes. The face proxy cannot separate head pitch from translation. No blink blendshape value was added to the production contract.

## Limitations and bounded conclusion

**Classification B — repeated identical-target observations show material variability.** The controlled, reverse-order session reproduced same-coordinate vertical changes; some were comparable to or larger than between-X differences in the same Y row. A top-row position-associated pattern appeared in both passes, but it did not generalize consistently to center/bottom rows. The evidence therefore does **not** support a general horizontal-position law or establish that X position physically causes the vertical change. It also does not establish that time itself is the cause of repeat variability. No hard threshold or statistical significance is claimed from one person and one controlled run.

The earlier fixed-order calibration rows remain time-confounded, and even the reversed-order session cannot independently hold eyelid state, face geometry, or gaze history constant. Presentation medians are descriptive aggregation, not a validated production smoother. The slope-scaled values illustrate sensitivity of the *existing* mapping, not a corrective model. No production behavior, feature formula, mapping, filter, or threshold was changed or selected.

The smallest justified next step, if the team needs to resolve the weaker position hypothesis, is an independently repeated balanced session with the same targets and separately recorded condition, then compare whether the top-row pattern and repeat magnitudes recur. Do not change the mapping based on this one run. Cross-user behavior remains untested by Issue #52.

The capture code stored only derived numerical data and no raw visual media. MediaPipe logged a `portable_clearcut_uploader` **failed send** during the controlled run. The log does not reveal the attempted payload; the separate third-party telemetry/privacy question remains unresolved, and this experiment cannot claim that outbound data has been ruled out.
