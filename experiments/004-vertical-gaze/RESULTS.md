# Experiment 004 — Results

## Environment

Three human runs were completed on the development Mac. The exact macOS/Python patch versions, camera index, input resolution, installed OpenCV version, model checksum for these runs, lighting, and seating distances were not supplied with the measurements. MediaPipe 0.10.35 remains an experiment-only pin; MediaPipe 1.0.1 previously produced a native SIGABRT during model initialization on the tested macOS ARM64 / Python 3.12 setup. No raw camera images or video were stored by the experiment script.

## Configuration

All three runs used the `stable` condition, with five reported trials per UP/CENTER/DOWN target. The script defaults to camera index 1, the official float16 Face Landmarker model, a one-second transition, two-second sampling, and shuffled order with seed 42; the exact command and option overrides for each run were not supplied. Run conditions differed in glasses, eye opening, and camera/face geometry, so the runs are not a controlled comparison of glasses alone.

## Previous Baseline

Experiment #14's combined vertical means were UP `0.4107`, CENTER `0.4094`, DOWN `0.4019`; raw ranges overlapped and repeated UP/DOWN trial means varied substantially. Its horizontal LEFT/CENTER/RIGHT separation was clear and repeatable. All 896 sampling frames were usable, with zero no-face frames, invalid geometry, failed reads, or tracking loss. The current study must compare new features against that measured vertical weakness, without assuming face-tracking failure caused it.

## Protocol

The human followed the guided UP/CENTER/DOWN targets in three stable-head runs. All runs included natural blinking and **no intentional winks**:

| Run | Glasses | Eye opening | Camera / condition note |
| --- | --- | --- | --- |
| 1 | No | Normal/natural | Camera manually centered and positioned more appropriately. |
| 2 | Yes | Intentionally slightly wider than normal | Diagnostic condition, **not** the primary normal-use condition. |
| 3 | Yes | Normal/natural | Most relevant normal-use repeat with glasses. |

The optional `small-head-motion` condition was not reported. Head pose was not independently measured.

## Candidate Features

The script evaluates left/right/binocular versions of `vertical_bbox` (Experiment #14 control), `vertical_local_axis` (corner-defined perpendicular coordinate normalized by eye width), and `vertical_lid_distances` (relative iris-to-upper/lower-lid distances). Exact formulas and verified landmark sets are in [README.md](README.md). The supplied quantitative summaries below concern **`binocular_vertical_local_axis` only**. The human observations identify it as the most promising vertical feature family. Bbox-based vertical features were not consistently useful. Lid-distance features conveyed direction in some conditions but were substantially noisier and strongly affected by eyelid/blink behavior. Per-run numbers for the latter two candidates were not supplied, so their comparative magnitude cannot be independently recalculated here.

## Measurements

| Run | Elapsed | Sampling frames | Usable | No face | Invalid geometry | Failed reads | Tracking loss |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 48.63 s | 894 | 894 | 0 | 0 | 0 | 0 |
| 2 — diagnostic | 48.68 s | 894 | 894 | 0 | 0 | 0 | 0 |
| 3 — normal opening with glasses | 49.13 s | 897 | 897 | 0 | 0 | 0 | 0 |

`binocular_vertical_local_axis` aggregate values and the **five reported trial means** for each label are recorded exactly below. Per-label sample counts, numeric raw ranges, and individual frame values were not supplied; only total sampling/usable counts and overlap observations are available.

| Run | Target | Mean | Std | Trial 1 | Trial 2 | Trial 3 | Trial 4 | Trial 5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | UP | -0.0519 | 0.0141 | -0.0458 | -0.0506 | -0.0540 | -0.0547 | -0.0544 |
| 1 | CENTER | -0.0471 | 0.0059 | -0.0487 | -0.0458 | -0.0445 | -0.0511 | -0.0452 |
| 1 | DOWN | -0.0397 | 0.0076 | -0.0434 | -0.0417 | -0.0417 | -0.0404 | -0.0310 |
| 2 | UP | -0.0508 | 0.0056 | -0.0471 | -0.0530 | -0.0518 | -0.0524 | -0.0500 |
| 2 | CENTER | -0.0409 | 0.0050 | -0.0402 | -0.0422 | -0.0425 | -0.0420 | -0.0374 |
| 2 | DOWN | -0.0326 | 0.0029 | -0.0281 | -0.0345 | -0.0330 | -0.0340 | -0.0335 |
| 3 | UP | -0.0454 | 0.0129 | -0.0372 | -0.0417 | -0.0437 | -0.0523 | -0.0523 |
| 3 | CENTER | -0.0347 | 0.0080 | -0.0307 | -0.0307 | -0.0365 | -0.0390 | -0.0369 |
| 3 | DOWN | -0.0247 | 0.0087 | -0.0247 | -0.0184 | -0.0277 | -0.0274 | -0.0250 |

## Directional Separation

The aggregate local-axis means maintained the same directional order in all three runs: **UP < CENTER < DOWN**. The reported mean differences are:

| Run | UP - CENTER | CENTER - DOWN | UP - DOWN | Raw frame-level ranges overlap? |
| --- | ---: | ---: | ---: | --- |
| 1 | -0.0048 | -0.0074 | -0.0122 | Yes |
| 2 — diagnostic | -0.0100 | -0.0083 | -0.0182 | Yes |
| 3 — normal opening with glasses | -0.0107 | -0.0101 | -0.0207 | Yes |

These differences are recorded as supplied, not recomputed from the rounded means. Run 3 shows useful mean-level vertical separation with normal eye opening while wearing glasses. Run 2's improvement cannot be attributed solely to intentionally wider eye opening. The runs do **not** establish that glasses improve performance: camera/face geometry and other conditions also differed. Absolute values shifted markedly between runs; CENTER moved from `-0.0471` to `-0.0409` to `-0.0347`. Fixed global thresholds are therefore not justified. Raw frame-level ranges still overlap, so a single unfiltered frame cannot be assumed to identify the target reliably.

## Trial-to-Trial Repeatability

All supplied local-axis trial means are listed in **Measurements**. The aggregate directional ordering reproduced across runs, but trial means varied, particularly in Run 1 and Run 3. The overlapping frame-level ranges and trial variation prevent a claim of robust per-frame classification. Trial means for bbox and lid-distance candidates were not supplied, so only the human qualitative comparison is recorded for those candidates.

## Confounding Signals

Reported **within-label correlations** with `binocular_vertical_local_axis` were:

| Run | Binocular blink | Binocular eye opening | `head_center_y` |
| --- | ---: | ---: | ---: |
| 1 | +0.943 | -0.947 | -0.008 |
| 2 — diagnostic | +0.682 | -0.723 | -0.145 |
| 3 — normal opening with glasses | +0.841 | -0.873 | -0.142 |

Blink and eye-opening signals were strongly associated with local-axis variation in these runs. This is **correlation, not causation**; it does not show that blink/eyelid effects alone produced the variation. The `head_center_y` relationship was smaller in the supplied summaries, but that coarse proxy cannot isolate head pitch from translation or exclude other head/camera effects. Natural blinking occurred in every run; no intentional winks or gesture thresholds were used. Detection and geometry remained valid for every reported sampling frame.

## Observations

The local-axis family was the leading vertical candidate in the supplied human observations. Run 2's intentionally wider eye opening was diagnostic; Run 3 preserved useful mean-level separation under natural eye opening with glasses. No tracking or acquisition interruption was reported. Raw images/video were not stored. Separate left/right-eye numerical summaries, exact head motion, lighting changes, and comfort observations were not supplied.

## Limitations

This is a **single-user exploratory experiment**; no statistical significance is claimed. Run conditions differed in glasses, intentional eye opening, and camera/face geometry, so glasses or eye opening cannot be isolated as causal factors. The supplied summaries lack numeric raw ranges, per-label counts, frame-level values, and quantitative bbox/lid-distance results. The eye-center y proxy cannot isolate pitch from translation. Correlation does not establish causation. Lighting, eyelids, glasses, posture, camera placement, and individual differences may affect features. Technical tracking stability in these runs does not establish robustness across users or hardware. These are directional features, not ground-truth screen coordinates, a validated production gaze estimator, or a permanent MediaPipe decision.

## Conclusion

Across three human runs, local-eye-axis geometry was the most promising tested vertical feature family and preserved UP/CENTER/DOWN mean ordering. Run 3 reproduced useful mean-level separation under **normal eye opening with glasses**, so the Run 2 result cannot be attributed solely to intentionally wider eye opening; it also does not prove any benefit from glasses. Absolute feature values shifted between runs, frame-level ranges overlapped, and blink/eye-opening measures remained strongly associated with local-axis variation. Raw per-frame local-axis output is therefore **not** a final gaze estimate, and fixed global thresholds are not justified. This supports investigating per-session/user calibration later, but full 2D screen-coordinate calibration is **not yet validated**. A separately approved next technical experiment could test blink/outlier rejection and short-window temporal aggregation without discarding genuine gaze information; no such experiment or implementation is included here.

## Reproduction command

The following starts the documented stable-head protocol from the repository root without writing a CSV. The exact commands used for the reported runs were not supplied. For any future repetition that needs numerical output, add `--output` with a new, unused path:

```bash
.venv/bin/python experiments/004-vertical-gaze/vertical_gaze_experiment.py --camera-index 1 --condition stable
```
