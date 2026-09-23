# Experiment 006 — Results

## Environment

**Human calibration and held-out validation completed on the development Mac.** The successful rerun's derived numerical dataset is stored locally at `.venv/2d-gaze-mapping-rerun.csv` (897 data rows plus header). It is ignored by Git and is **not committed**. The results below were recomputed from that CSV with `analyze_mapping.py --json`; the reported 50.53 s elapsed time and zero failed camera reads came from the human-run console, not from the CSV analyzer. The Python 3.12 development environment contains MediaPipe 0.10.35 and OpenCV (`opencv-python` 5.0.0.93; `cv2.__version__` reported 5.0.0). The official float16 Face Landmarker model at `.venv/models/face_landmarker.task` had SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` during setup. These are experiment-only choices, not a production framework decision.

## Successful human rerun — reproducible local CSV

| Acquisition / protocol | Successful rerun |
| --- | ---: |
| Elapsed | 50.53 s |
| Camera index | 1 |
| Camera input | 1920 × 1080 |
| Experiment image area | 1200 × 700 |
| Sampling frames / usable | 897 / 897 |
| Failed camera reads | 0 |
| Tracking/geometry invalid | 0 |
| Experimental blink rejected | 0 |
| Calibration targets / held-out trials | 9 / 16 |

The held-out targets were interstitial locations, distinct from all nine calibration coordinates. Each of eight validation targets appeared twice. Both models were fit only to session-local calibration-target medians; the validation observations were not used for fitting.

| Held-out validation metric | Independent linear | Affine 2D |
| --- | ---: | ---: |
| Horizontal absolute error — mean | 0.0276792761 | 0.0300945161 |
| Horizontal absolute error — median | 0.0298255967 | 0.0252817617 |
| Horizontal absolute error — p95 | 0.0484333415 | 0.0582179878 |
| Vertical absolute error — mean | 0.0699321023 | 0.0721141330 |
| Vertical absolute error — median | 0.0716109298 | 0.0774523064 |
| Vertical absolute error — p95 | 0.1175718433 | 0.1135760657 |
| Normalized 2D error — mean | 0.0782647355 | 0.0807397710 |
| Normalized 2D error — median | 0.0781005589 | 0.0835093631 |
| Normalized 2D error — p95 | 0.1204899931 | 0.1184307724 |
| Window-pixel-equivalent error — mean | 62.72 px | 65.36 px |
| Window-pixel-equivalent error — median | 69.38 px | 62.44 px |
| Window-pixel-equivalent error — p95 | 87.92 px | 103.51 px |
| Mean signed x bias | -0.0214227391 | -0.0218020921 |
| Mean signed y bias | -0.0018266192 | -0.0068211625 |
| Held-out x ordering | 21/21 | 21/21 |
| Held-out y ordering | 21/21 | 21/21 |

All coordinates and normalized errors use the `[0, 1]` target-window image-area coordinate system. Window-pixel-equivalent error is relative to the measured 1200 × 700 image area, not necessarily the display's hardware pixels or physical visual angle. The ordering counts compare distinct held-out target locations after averaging repeated trials; they are descriptive, not pixel-accuracy scores.

### Held-out target predictions

The following rounded values retain the human validation's actual-versus-predicted positions and window-pixel-equivalent error for every trial. Exact values, horizontal/vertical errors, and normalized 2D errors can be recomputed from the local numerical CSV.

| Target / trial | Actual (x, y) | Linear predicted | Linear px | Affine predicted | Affine px |
| --- | --- | --- | ---: | --- | ---: |
| V-8 / 1 | (0.350, 0.500) | (0.309, 0.589) | 79.4 | (0.311, 0.552) | 59.6 |
| V-2 / 2 | (0.650, 0.350) | (0.656, 0.253) | 68.2 | (0.647, 0.271) | 55.1 |
| V-6 / 1 | (0.650, 0.500) | (0.631, 0.429) | 54.7 | (0.629, 0.454) | 40.7 |
| V-7 / 1 | (0.500, 0.650) | (0.470, 0.741) | 73.2 | (0.481, 0.751) | 74.2 |
| V-7 / 2 | (0.500, 0.650) | (0.494, 0.713) | 44.6 | (0.504, 0.726) | 53.6 |
| V-3 / 2 | (0.350, 0.650) | (0.319, 0.759) | 84.8 | (0.329, 0.736) | 65.3 |
| V-5 / 2 | (0.500, 0.350) | (0.471, 0.278) | 61.7 | (0.460, 0.256) | 81.8 |
| V-1 / 2 | (0.350, 0.350) | (0.294, 0.322) | 70.6 | (0.282, 0.262) | 101.7 |
| V-2 / 1 | (0.650, 0.350) | (0.632, 0.232) | 85.4 | (0.622, 0.243) | 82.1 |
| V-3 / 1 | (0.350, 0.650) | (0.312, 0.767) | 94.0 | (0.322, 0.743) | 73.5 |
| V-6 / 2 | (0.650, 0.500) | (0.672, 0.451) | 43.3 | (0.672, 0.487) | 28.3 |
| V-8 / 2 | (0.350, 0.500) | (0.304, 0.563) | 70.6 | (0.305, 0.523) | 57.0 |
| V-5 / 1 | (0.500, 0.350) | (0.466, 0.242) | 85.9 | (0.454, 0.216) | 108.9 |
| V-4 / 2 | (0.650, 0.650) | (0.663, 0.635) | 18.3 | (0.671, 0.681) | 33.4 |
| V-1 / 1 | (0.350, 0.350) | (0.305, 0.335) | 54.7 | (0.295, 0.279) | 82.7 |
| V-4 / 1 | (0.650, 0.650) | (0.659, 0.662) | 14.1 | (0.669, 0.710) | 47.7 |

## Earlier preliminary run — CSV export failed

The earlier human-run console reached model fitting and metric reporting. Final CSV export then failed with `dict contains fields not in fieldnames: 'binocular_blink'`. The earlier `.venv/2d-gaze-mapping.csv` contains only a header and **no frame rows**. Its reported aggregates are preserved as preliminary observations, **not** as the successful rerun's reproducible dataset. No missing rows have been reconstructed.

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

The earlier held-out target locations were separate from calibration. The preliminary run suggested session-local spatial mapping, but its individual trial rows were not saved, so they cannot be checked independently. The human report noted some individual trials around 20–40 px and others around 145–170 px, with larger errors mainly vertical. Both models showed negative held-out x bias; no correction was added. The successful rerun had lower reported p95 window-pixel-equivalent error (87.92/103.51 px versus 140.80/151.14 px), but one improved rerun does **not** establish universal stability or explain the difference between runs.

## Display / Camera Configuration

The successful rerun used camera index 1, 1920 × 1080 input, and a 1200 × 700 target-window image area. Every saved row reports these same dimensions. Device identity, macOS version, glasses use, lighting, distance, and any window/display scaling or placement issue were not recorded with the provided run metadata. Camera index 1 previously selected the built-in camera on this Mac, but ordering can vary.

## Feature Inputs

The inputs were Experiment 003's binocular normalized horizontal iris position (`binocular_horizontal_control` in Experiment 004) and Experiment 004's `binocular_vertical_local_axis`. No new feature geometry was introduced. Left/right values, eye opening, blink scores, and coarse head-center-y are diagnostic only.

## Calibration Layout

Nine normalized targets form a 3×3 grid at x/y = `0.20`, `0.50`, `0.80`. Each target has a settling period and multiple sampling frames; its median feature pair is used for fitting. The successful CSV contains all nine calibration presentations. The earlier failed-export run's per-target data remain unavailable.

## Validation Layout

Eight interstitial normalized targets are listed in [README.md](README.md#target-layouts), with two shuffled trials each. They are never identical to calibration coordinates and are not used to fit the mapping. The successful CSV contains all 16 held-out trials; their predictions are shown above. The earlier failed-export run's trial rows remain unavailable.

## Mapping Candidates

Independent axis-wise linear mapping (four coefficients) and 2D affine mapping (six coefficients) were fit within the same session from calibration summaries only. Both remain experimental candidates; no production mapping is chosen. The successful CSV can reproduce fitted coefficients and errors. The earlier failed-export run's coefficients were not preserved.

## Human Protocol

The prescribed condition was normal/natural eye opening and blinking; no intentional winks; approximately stable head; comfortable viewing distance; camera reasonably centered; glasses worn normally if needed. The successful rerun lasted 50.53 s. Compliance details and any protocol deviations were not recorded with the provided run metadata.

## Calibration Measurements

The successful CSV permits per-target sample counts, median horizontal/vertical features, feature MAD, and left/right disagreement to be recomputed. Calibration-fit errors, **separate from held-out validation**, were:

| Calibration-fit metric | Independent linear | Affine 2D |
| --- | ---: | ---: |
| Mean horizontal absolute error | 0.0439 | 0.0466 |
| Mean vertical absolute error | 0.0729 | 0.0578 |
| Mean normalized 2D error | 0.0938 | 0.0817 |
| Median normalized 2D error | 0.0767 | 0.0837 |
| p95 normalized 2D error | 0.1954 | 0.1697 |
| Mean window-pixel-equivalent error | 82.71 px | 76.06 px |
| Median window-pixel-equivalent error | 69.17 px | 59.97 px |
| p95 window-pixel-equivalent error | 188.38 px | 182.17 px |

Calibration-fit and held-out target geometries differ; lower held-out errors in this run do **not** show that held-out prediction is inherently easier or better. Calibration-fit error is not the primary feasibility evidence.

## Validation Measurements

The successful CSV saved all 16 held-out trials. Their actual and predicted normalized positions and rounded window-pixel-equivalent errors appear above. The numerical dataset retains the exact feature samples; `analyze_mapping.py --json` recomputes exact per-trial horizontal, vertical, normalized 2D, and pixel-equivalent errors. The earlier failed-export run did not save its per-trial observations.

## Error Metrics

The successful rerun's held-out mean, median, and p95 errors are reported above and independently recomputed from its CSV. Calibration-fit metrics are reported separately. No hard success threshold was predetermined. The earlier preliminary aggregates cannot be independently recomputed from their header-only CSV.

## Spatial Consistency

Both models achieved 21/21 descriptive held-out x ordering and 21/21 y ordering. Repeated-target predictions and per-target errors are shown above. Both models had a small negative mean signed x bias (about -0.021 in normalized coordinates), an observed systematic tendency left uncorrected. Horizontal absolute error was substantially lower than vertical absolute error; vertical accuracy remains the dominant bottleneck.

## Observed Failure Modes

The successful rerun showed larger vertical than horizontal errors and a small negative x bias. No tracking/geometry-invalid or experimentally blink-rejected sampling frames were reported. The current data do not isolate the causes of vertical error or x bias. Edge effects, nonlinear regions, head-position sensitivity, calibration inconsistency, and glasses/lighting effects were not established by this single controlled run. No ad-hoc bias correction was applied.

## Limitations

This is a controlled single-user, session-local feasibility result, not a statistical or multi-user validation. It does not establish production-ready eye tracking, pixel-perfect accuracy, cursor control, accessibility usability, cross-session calibration persistence, or performance with other users, cameras, lighting, glasses, or display conditions. The two human runs do not isolate what caused their different tail errors. The derived CSV is ignored locally; no raw images or video were saved. Experimental blink rejection is not a production threshold, and prior temporal smoothing is not a validated preprocessing stage.

## Conclusion

The successful rerun provides reproducible local evidence that the existing binocular horizontal feature and binocular local-axis vertical feature can support **limited, approximate session-local 2D gaze mapping** under the tested controlled single-user condition. Held-out targets were distinct from calibration targets, and both simple mappings preserved all 21/21 x and 21/21 y spatial-order comparisons. Coordinate accuracy was not pixel-perfect; vertical error was substantially larger than horizontal error, and a small negative held-out x bias remained. Independent linear and affine 2D both remain reasonable experimental candidates; this dataset does not justify selecting a production winner or adding a correction constant. The feasibility question is answered positively enough to justify continued development, **not** to claim a production-ready tracker, cursor control, cross-session persistence, multi-user validity, or accessibility usability.
