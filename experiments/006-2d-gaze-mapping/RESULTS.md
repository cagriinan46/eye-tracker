# Experiment 006 — Results

## Environment

**A human capture and held-out validation run completed, but its numerical CSV did not export. Reproducible dataset and final conclusion remain pending.** The Python 3.12 development environment contains MediaPipe 0.10.35 and OpenCV (`opencv-python` 5.0.0.93; `cv2.__version__` reported 5.0.0). The existing official float16 Face Landmarker model at `.venv/models/face_landmarker.task` had SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. The `--check-model` preflight initialized Face Landmarker successfully on this Mac. This preflight did not access the camera and is **not** a gaze-mapping result.

## Observed human run — CSV export failed

The human-run console reached model fitting and metric reporting. Final CSV export then failed with `dict contains fields not in fieldnames: 'binocular_blink'`. The existing `.venv/2d-gaze-mapping.csv` contains only a header and **no frame rows**. These reported aggregates are preserved as observations, not as a complete, independently reanalyzable dataset. No missing rows have been reconstructed.

| Acquisition / protocol | Observed value |
| --- | ---: |
| Elapsed | 50.40 s |
| Camera index | 1 |
| Camera input | 1920 × 1080 |
| Experiment image area | 1200 × 700 |
| Frames / usable samples | 892 / 892 |
| Failed camera reads | 0 |
| Tracking/geometry invalid | 0 |
| Experimental blink rejected | 0 |
| Calibration targets / held-out validation trials | 9 / 16 |

| Held-out metric | Independent linear | Affine 2D |
| --- | ---: | ---: |
| Horizontal absolute error — mean | 0.0437801 | 0.0463699 |
| Horizontal absolute error — median | 0.0453055 | 0.0388105 |
| Horizontal absolute error — p95 | 0.0709043 | 0.0873569 |
| Vertical absolute error — mean | 0.0725301 | 0.0638755 |
| Vertical absolute error — median | 0.0589640 | 0.0357261 |
| Vertical absolute error — p95 | 0.1711274 | 0.1981629 |
| Normalized 2D error — mean | 0.0915507 | 0.0847556 |
| Normalized 2D error — median | 0.0782271 | 0.0698932 |
| Normalized 2D error — p95 | 0.1774395 | 0.2044445 |
| Window-pixel-equivalent error — mean | 79.37 px | 76.67 px |
| Window-pixel-equivalent error — median | 77.17 px | 73.71 px |
| Window-pixel-equivalent error — p95 | 140.80 px | 151.14 px |
| Mean signed x bias | -0.0437801 | -0.0463699 |
| Mean signed y bias | -0.0083167 | -0.0221703 |
| Held-out x ordering | 21/21 | 21/21 |
| Held-out y ordering | 19/21 | 20/21 |

The held-out target locations were separate from calibration. This run offers **preliminary** evidence of session-local 2D spatial mapping: horizontal ordering was complete by the reported comparison, while vertical ordering was slightly weaker. Median window-pixel-equivalent error was approximately 74–77 px. The human report also noted some individual trials around 20–40 px and others around 145–170 px, with larger errors mainly vertical; individual trial rows were not saved, so those observations cannot be checked independently. Vertical accuracy was less stable than horizontal accuracy. Both models had negative held-out x bias; this is recorded as a possible systematic offset, not corrected here. These observations do **not** establish production-ready gaze tracking or accessibility usability.

## Display / Camera Configuration

The observed run used camera index 1, 1920 × 1080 input, and a 1200 × 700 target-window image area. Device identity, macOS version, glasses use, lighting, distance, and any window/display scaling or placement issue were not recorded with the reported aggregates. Camera index 1 previously selected the built-in camera on this Mac, but ordering can vary.

## Feature Inputs

The planned inputs are Experiment 003's binocular normalized horizontal iris position (`binocular_horizontal_control` in Experiment 004) and Experiment 004's `binocular_vertical_local_axis`. No new feature geometry is introduced. Left/right values, eye opening, blink scores, and coarse head-center-y are diagnostic only.

## Calibration Layout

Nine normalized targets form a 3×3 grid at x/y = `0.20`, `0.50`, `0.80`. Each target has a settling period and multiple sampling frames; its median feature pair is used for fitting. Per-target usable counts and calibration-fit errors: **not recoverable from the failed CSV export**.

## Validation Layout

Eight interstitial normalized targets are listed in [README.md](README.md#target-layouts), with two shuffled trials each. They are never identical to calibration coordinates and are not used to fit the mapping. The observed run reported 16 held-out trials; trial order and per-trial usable counts are **not recoverable from the failed CSV export**.

## Mapping Candidates

Independent axis-wise linear mapping (four coefficients) and 2D affine mapping (six coefficients), both fit within the same session from calibration summaries only. No production mapping is chosen. Fitted coefficients and rank/conditioning observations were **not preserved**.

## Human Protocol

The prescribed condition was normal/natural eye opening and blinking; no intentional winks; approximately stable head; comfortable viewing distance; camera reasonably centered; glasses worn normally if needed. The observed duration was 50.40 s. Compliance details and any protocol deviations were **not recorded with the reported aggregates**.

## Calibration Measurements

Per-target sample counts, median horizontal/vertical features, feature MAD, left/right disagreement, and calibration-fit error **separately** for each candidate remain unavailable without a complete numerical dataset.

## Validation Measurements

Per-trial actual and predicted coordinates and errors were not saved. They must be obtained from a complete numerical dataset; do not substitute calibration observations for validation data.

## Error Metrics

The observed held-out aggregate metrics are preserved above, but cannot be independently recomputed from the header-only CSV. Calibration-fit metrics were not preserved and must be reported separately from a complete dataset. No hard success threshold is predetermined.

## Spatial Consistency

The observed held-out ordering and signed bias are preserved above. Repeated-target consistency and per-target spatial behavior remain unavailable without saved rows.

## Observed Failure Modes

The observed aggregates indicate larger vertical errors and negative x bias. Edge effects, nonlinear regions, head-position sensitivity, calibration inconsistency, left/right disagreement, and per-frame blink behavior cannot be assessed from a header-only CSV. Do not automatically compensate for observed bias.

## Limitations

The model-initialization preflight is not physical camera validation. This is a controlled single-session/single-user feasibility design. It cannot validate production eye tracking, cursor control, accessibility usability, universal or persistent calibration, other users, or other camera/display conditions. No raw images or video are saved. Experimental blink rejection is not a production threshold, and prior temporal smoothing is not a validated preprocessing stage.

## Conclusion

**Final reproducible conclusion pending a successful CSV export from a complete human run.** The observed console metrics provide preliminary evidence that this session-local feature pair can preserve useful held-out spatial ordering, but they are not a saved dataset and do not validate a production gaze tracker. No model selection or bias correction is justified from this incomplete export.
