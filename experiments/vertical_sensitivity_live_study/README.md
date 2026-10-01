# Controlled live vertical sensitivity diagnostic

## Question

Across exactly three fresh sessions from Çağrı, how do 3×3 calibration vertical-feature geometry, fitted independent-linear y sensitivity, and repeated identical-target feature variability relate descriptively? In particular, does a session with compressed calibration feature separation and a steep y slope map observed repeat differences to larger normalized-y differences? This is a diagnostic study, not a correction or a production change.

The prior [offline sensitivity report](../vertical_mapping_sensitivity/RESULTS.md) found a calibration feature span of about 0.00875 and y slope 61.96 in fixed-CENTER live-1, versus span 0.03368 and slope 20.07 in live-2. Those prior reports lacked enough per-presentation held-out feature medians to connect their feature movement to output movement directly.

## Predeclared human data plan

The participant performs **cagri/live-1**, **cagri/live-2**, and **cagri/live-3** once each. All three complete valid sessions will be included, regardless of result. A run may be repeated only after a technical invalidation such as cancellation, insufficient usable frames, camera failure, corrupted output, or documented protocol failure. Preserve the invalid-attempt marker and use a distinct filename for a justified retry; never silently replace a run because its metrics look unfavorable.

The three sessions are now complete; measured findings are in [RESULTS.md](RESULTS.md). This plan records the protocol declared before capture.

## Capture protocol and commands

Run from the repository root with the active virtual environment and Face Landmarker model already installed. Camera index `1` matches the earlier Çağrı sessions; change it only if the actual camera enumeration differs, and record that change. Each command saves derived numerical data in ignored `.venv`; it refuses to overwrite an existing report or invalid-attempt marker.

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_sensitivity_live_study.run --participant cagri --session live-1 --camera-index 1 --output .venv/vertical-sensitivity-cagri-live-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_sensitivity_live_study.run --participant cagri --session live-2 --camera-index 1 --output .venv/vertical-sensitivity-cagri-live-2.json
PYTHONPATH=src:. .venv/bin/python -m experiments.vertical_sensitivity_live_study.run --participant cagri --session live-3 --camera-index 1 --output .venv/vertical-sensitivity-cagri-live-3.json
```

The full-screen window presents 27 dots: the production-path 3×3 calibration in row-major order, then the same 9 coordinates in row-major order (pass A), then the exact reverse order (pass B). It shows target number and settling/sampling status, never predictions. Look naturally at each dot with comfortable posture, natural eye opening, and natural blinking. Press `q` or Esc to cancel. The existing timing is 0.8 seconds settling plus 1.2 seconds sampling per target, with at least five usable samples required, so target presentation takes about 54 seconds plus setup and processing time. The inherited UI labels both diagnostic passes `DIAGNOSTIC`; targets 10–18 are A and 19–27 are B. This is a display-label reuse, not a protocol change.

The runner reuses the Issue #52 controlled capture and the existing production camera, face landmark, eye-feature, and independent-linear calibration components. It saves the original derived numerical sampling rows plus all 27 per-presentation **actual recorded median** horizontal/vertical features, pass and order, target coordinates, baseline unclipped x/y predictions, and usable/unavailable attempt counts. The report retains mapping coefficients, timing, resolution, elapsed time, camera reads/failures, and no-face counts. It saves no camera frames or video. A technically invalid attempt produces a separate `.invalid.json` reason marker; the reused collector cannot retain partial measurements after an exception, so the marker explicitly states that limitation.

## Predeclared analysis

For each session, report the fitted y slope/intercept; all nine calibration vertical-feature medians; full calibration feature span; top, center, and bottom row medians; top-to-center, center-to-bottom, and minimum adjacent-row separation; within-row spread across x; calibration y MAE and repository-standard y ordering. Exact-coordinate matches compare calibration→A, calibration→B, and A→B, with signed and absolute vertical-feature differences and the corresponding signed and absolute `y_slope × feature_difference`. Summarize median, p95, and maximum absolute differences over all 27 comparisons, with the same summaries separately per comparison type in the final report. Report fixed sensitivity examples for feature changes 0.001, 0.003, and 0.005 using `abs(y_slope × change)`.

The [cross-session table](RESULTS.md#cross-session-comparison-and-fixed-sensitivity-examples) retains all three valid sessions and includes calibration span, minimum adjacent-row separation, slope, calibration y MAE, and median/p95/max repeated-target feature and slope-amplified y differences. The three sessions are descriptive observations from one participant; no correlation coefficient or causal inference is used. The analysis uses saved feature medians directly, with no feature reconstruction from predictions.

**Feature instability** is movement in the measured vertical feature. **Mapping sensitivity** is how the fitted slope converts a given movement to predicted y. A steep slope can amplify movement but cannot cause the feature itself to move. Compressed calibration geometry, head pose, eyelids, glasses, time, camera position, gaze history, and physiology are not established causes by this protocol. This study does not test cross-user reliability, cursor usability, or production readiness. It applies no CENTER offset, smoothing, blink gate, clipping, mapping-family change, or ML.
