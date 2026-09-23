# Experiment 006 — Results

## Environment

**Human validation pending.** The Python 3.12 development environment contains MediaPipe 0.10.35 and OpenCV (`opencv-python` 5.0.0.93; `cv2.__version__` reported 5.0.0). The existing official float16 Face Landmarker model at `.venv/models/face_landmarker.task` had SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. The `--check-model` preflight initialized Face Landmarker successfully on this Mac. This preflight did not access the camera and is **not** a gaze-mapping result.

## Display / Camera Configuration

Pending human run. Record camera index/device, captured frame dimensions, measured target-window image-area dimensions, macOS version, normal glasses use, lighting, distance, and any window/display scaling or placement issue. Camera index 1 previously selected the built-in camera on this Mac, but ordering can vary.

## Feature Inputs

The planned inputs are Experiment 003's binocular normalized horizontal iris position (`binocular_horizontal_control` in Experiment 004) and Experiment 004's `binocular_vertical_local_axis`. No new feature geometry is introduced. Left/right values, eye opening, blink scores, and coarse head-center-y are diagnostic only.

## Calibration Layout

Nine normalized targets form a 3×3 grid at x/y = `0.20`, `0.50`, `0.80`. Each target has a settling period and multiple sampling frames; its median feature pair is used for fitting. Actual usable counts and calibration-fit errors: **pending**.

## Validation Layout

Eight interstitial normalized targets are listed in [README.md](README.md#target-layouts), with two shuffled trials each. They are never identical to calibration coordinates and are not used to fit the mapping. Trial order and usable counts: **pending**.

## Mapping Candidates

Independent axis-wise linear mapping (four coefficients) and 2D affine mapping (six coefficients), both fit within the same session from calibration summaries only. No production mapping is chosen. Fitted coefficients and rank/conditioning observations: **pending**.

## Human Protocol

Normal/natural eye opening and blinking; no intentional winks; approximately stable head; comfortable viewing distance; camera reasonably centered; glasses worn normally if needed. The approximate default duration is 50 seconds plus overhead. Actual protocol deviations or cancellation: **pending**.

## Calibration Measurements

Pending real human run. Record per-target sample counts, median horizontal/vertical features, feature MAD, left/right disagreement, and calibration-fit error **separately** for each candidate.

## Validation Measurements

Pending real human run. Record every held-out target/trial's actual and predicted normalized coordinates and horizontal, vertical, 2D, and window-pixel-equivalent errors. Do not substitute calibration observations for validation data.

## Error Metrics

Pending real human run. Report mean, median, and p95 of held-out horizontal absolute error, vertical absolute error, normalized Euclidean error, and window-pixel-equivalent error for each mapping. Report calibration-fit metrics separately. No hard success threshold is predetermined.

## Spatial Consistency

Pending real human run. Assess left-to-right and top-to-bottom ordering of held-out positions, repeated-target consistency, vertical/horizontal asymmetry, and signed bias, in addition to coordinate error.

## Observed Failure Modes

Pending real human run. Record vertical bias, edge effects, nonlinear regions, head-position sensitivity, blink contamination, calibration inconsistency, left/right disagreement, and systematic offset where observed; do not automatically compensate for them.

## Limitations

The model-initialization preflight is not physical camera validation. This is a controlled single-session/single-user feasibility design. It cannot validate production eye tracking, cursor control, accessibility usability, universal or persistent calibration, other users, or other camera/display conditions. No raw images or video are saved. Experimental blink rejection is not a production threshold, and prior temporal smoothing is not a validated preprocessing stage.

## Conclusion

**Pending the normal-use human calibration and held-out validation run.** No gaze-mapping accuracy, usefulness, or 2D calibration feasibility conclusion can be drawn from model initialization or deterministic tests alone.
