# Vertical gaze collapse diagnostics — Results

## Environment and protocol

Issue #44 uses the merged Issue #42 target layout and timing, with separate new calibration for each participant/session. Camera indices and machine conditions must be recorded for each run. Derived numerical datasets stay under ignored `.venv/`; no images or video are stored.

## Çağrı Session A

Completed on the development Mac with camera index 1 at 1920×1080; target-window image area was 1200×700. The participant followed the normal-use target protocol with natural blinking and comfortable posture. Elapsed time was 50.457 s. The run made 1,478 camera reads including settling, with 0 failed reads and 0 no-face observations. All 888 sampling attempts were usable. Nine calibration targets and 16 held-out trials completed. The derived numerical dataset is local at `.venv/vertical-collapse-cagri-A.json` and is Git-ignored.

## Çağrı Session B

Completed after the participant confirmed leaving/resetting/reseating, with a **fresh** calibration and otherwise the same normal-use instructions. Camera index 1, 1920×1080 input, and 1200×700 target-window image area were used. Elapsed time was 50.343 s. The run made 1,487 camera reads including settling, with 0 failed reads and 0 no-face observations. All 890 sampling attempts were usable. Nine calibration targets and 16 held-out trials completed. The separate derived numerical dataset is local at `.venv/vertical-collapse-cagri-B.json` and is Git-ignored. Posture/eye behavior cannot be independently verified from the numerical capture.

## Çağrı vertical diagnostics

The table shows the raw per-frame median, range, and IQR for each calibration row, followed by the median of the three **per-target aggregated medians** used by the fitter. Values are the uncalibrated binocular local-axis feature, not screen coordinates.

| Session | Calibration row | Raw median | Raw range | Raw IQR | Aggregated median |
| --- | --- | ---: | ---: | ---: | ---: |
| A | Top, y=0.20 | -0.055551 | 0.009229 | 0.002638 | -0.055572 |
| A | Center, y=0.50 | -0.049878 | 0.004093 | 0.001317 | -0.049873 |
| A | Bottom, y=0.80 | -0.042202 | 0.002936 | 0.001386 | -0.042281 |
| B | Top, y=0.20 | -0.053035 | 0.003963 | 0.001293 | -0.052835 |
| B | Center, y=0.50 | -0.045859 | 0.006761 | 0.003131 | -0.045771 |
| B | Bottom, y=0.80 | -0.039513 | 0.004017 | 0.001379 | -0.039727 |

Both raw and aggregated row medians ordered **top < center < bottom** in each session. Session A raw top/center ranges overlapped; center/bottom did not. Session B had no adjacent raw-row range overlap. Thus neither Çağrı session shows calibration-stage vertical feature collapse. Within-row spread and some overlap remain.

| Session | Fitted y slope | Fitted y intercept | Calibration-fit vertical MAE | Held-out y range | Held-out y ordering | Held-out vertical MAE | Signed y bias |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| A | 43.3410 | 2.6315 | 0.0431 | 0.0612 to 1.0951 | 21/21 | 0.1354 | -0.0087 |
| B | 43.8275 | 2.5276 | 0.0404 | -0.1247 to 0.6928 | 21/21 | 0.2161 | -0.2107 |

Predictions are deliberately unclipped; values outside `[0, 1]` expose error. Calibration-fit and held-out targets differ, so their MAEs must not be read as a controlled comparison of target difficulty. Both sessions retain held-out vertical *ordering*, unlike the earlier Fatih run reported on PR #43, but B has a pronounced negative held-out bias.

## Cross-user validation

Deferred outside Issue #44. No new Fatih diagnostic run or cross-user comparison is claimed. The earlier Fatih near-flat y predictions reported on PR #43 remain unexplained by these Çağrı-only measurements.

## Within-session and between-session comparison

The calibration-row aggregated vertical medians shifted from A to B by +0.002737 (top), +0.004103 (center), and +0.002554 (bottom). This is a measured **between-session offset** despite the same target layout. The two fitted y slopes are close (43.3410 and 43.8275), and each session was freshly calibrated.

Within Session B, the raw vertical feature median for **held-out y=0.50** targets was -0.050499, versus -0.045859 for its calibration y=0.50 row: a -0.004640 difference. Multiplying that feature difference by B's fitted y slope gives approximately -0.203 in predicted y, close to its -0.211 mean held-out signed y bias. In Session A, the corresponding medians were -0.049714 held-out and -0.049878 calibration, a much smaller +0.000163 difference. These comparisons involve different target layouts and times; they trace where a shift appears but do not establish why it occurred.

Horizontal control remained directionally useful in both sessions. Calibration-row raw horizontal medians for x=0.20/0.50/0.80 were A: 0.528227 / 0.481031 / 0.441686 and B: 0.531777 / 0.478639 / 0.441516, both in decreasing order. Left/center raw ranges overlapped in both sessions; center/right ranges did not. Fitted x slope/intercept were A: -6.7961 / 3.7496 and B: -6.6606 / 3.6857. Held-out x ordering was 21/21 in both; horizontal MAE was 0.0364 (A) and 0.0265 (B), with signed x bias -0.0364 and -0.0212 respectively. Held-out x ranges were 0.2848–0.6471 (A) and 0.3041–0.6762 (B).

The descriptive within-calibration-target correlation of vertical feature with binocular lid opening was -0.076 (A) and +0.101 (B); with the coarse face-center-y proxy it was -0.594 (A) and -0.434 (B). Session B's median lid opening at center-y targets was 0.3564 during calibration versus 0.3388 during held-out validation, while the face-center-y proxy was 0.5114 versus 0.5178. These are associations, **not causal explanations**; the proxy cannot isolate head pitch from translation. Blink blendshape scores were unavailable without changing the production observation contract.

Do not pool participants or claim statistical significance from these exploratory runs. Cross-user validation is explicitly deferred.

## Conclusion

**Final Çağrı-only assessment:** The vertical feature did **not** collapse in either session. Top/center/bottom medians remained correctly ordered before and after aggregation, and held-out y ordering was 21/21 in both sessions. The fitted vertical slopes were similar (43.34 and 43.83). Thus the current evidence does not support the linear fitter as the primary failure in these runs.

Session B's center-target vertical feature shifted by approximately **-0.00464** from calibration to held-out use. With its fitted slope of about **43.83**, this corresponds to roughly **-0.203 normalized y**, close to the observed **-0.2107 signed y bias**. Calibration-to-use vertical feature drift is therefore the strongest current hypothesis for Çağrı's instability. The measurements do **not** identify the root cause of that drift: target geometry, time, eyelid behavior, head/camera geometry, and other conditions were not independently controlled or isolated. This conclusion does **not** explain Fatih's previous near-flat vertical predictions. Cross-user validation is deferred. No corrective algorithm, threshold, or production behavior is selected.
