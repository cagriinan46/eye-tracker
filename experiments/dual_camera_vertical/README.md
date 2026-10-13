# Simultaneous dual-camera vertical signals — Issue #90

Preregistered **2026-10-13, Europe/Istanbul**, before any Issue #90 session.
Task approved by Fatih in chat ("çift kamerayla deneyelim"); this
preregistration approved by Fatih before session A. Diagnostic experiment; no
production change.

## Question

[Issue #88](../camera_placement_vertical/RESULTS.md) found the iPhone
(Continuity Camera, rear camera, below the screen) better than the built-in
camera above the screen (best candidate COMBO, mean y MAE 0.077 vs 0.103), but
no candidate passed both iPhone sessions. Those sessions ran at different
times, so the cameras never saw the same gaze. **When both cameras record the
same gaze simultaneously, does fusing the top and bottom camera signals reduce
vertical error below the best single camera?** The top camera sees the upper
lid and eye opening, the bottom camera the iris from below; their errors may be
partly independent.

## Collector

`run.py` reuses the Issue #77 schedule, timing, signal path and frozen
thresholds unchanged. Each loop reads the **top** camera and then the
**bottom** camera, each with its own MediaPipe Face Landmarker instance
(VIDEO mode needs one timeline per camera), and writes one row per camera
tagged `camera` and `loop`. A loop counts as usable for the protocol's
five-sample minimum when either camera produced features; the analysis applies
the frozen per-camera availability rule. Only derived numbers are written to a
Git-ignored file; no images or video.

A no-save smoke test before session A records camera indices (lens-cover
brightness test), per-camera rate, face-detection rate and inter-camera frame
gap.

## Sessions

Fatih only, `.venv-fatih`, model `.venv-fatih/models/face_landmarker.task`
(SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`),
full screen 1512×982, built-in camera on top, iPhone in landscape on the
Issue #88 stand below the screen connected by USB, video effects off.
Two sessions, A then B, reseating between, results hidden until both end:

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.dual_camera_vertical.run \
  --participant fatih-dual --session A --top-index 0 --bottom-index 1 \
  --screen-size 1512x982 --model .venv-fatih/models/face_landmarker.task \
  --output validation/results/dual-camera-fatih-A.json
# then --session B ... dual-camera-fatih-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.dual_camera_vertical.analysis \
  validation/results/dual-camera-fatih-A.json validation/results/dual-camera-fatih-B.json
```

Indices are those found by the smoke test.

## Analysis (frozen before data)

Per session, only presentations with ≥ 5 common frames in **both** cameras are
kept (common-frame rule of Issue #77, blink ≤ 0.5). A session is valid when
both cameras have ≥ 20/25 calibration and ≥ 14/16 validation presentations on
that common set. Every method is fitted on the session's calibration and
scored on its validation with Issue #77 metrics (y MAE, signed bias, ordering)
and pass thresholds (y MAE ≤ 0.08, ordering ≥ 19/21, |bias| ≤ 0.05).

| Method | Definition |
| --- | --- |
| `TOP:<c>` / `BOTTOM:<c>` | Issue #77 candidates R0, OPEN, OPEN_Q, BLEND, COMBO on one camera, unchanged |
| `LATE` (primary fusion) | mean of the top camera's COMBO prediction and the bottom camera's COMBO prediction; no extra parameters |
| `SPLIT` (secondary fusion) | one OLS on top opening, bottom vertical, bottom blendshape, top head pitch (4 inputs + intercept, same size as COMBO) |

Mean y MAE is taken over sessions A and B per method.

## Preregistered decision

Requires both sessions valid; otherwise **inconclusive**. No session is
repeated or replaced after its data are seen.

- **Fusion better (primary):** `LATE` mean y MAE ≤ best single-camera
  method's mean y MAE (best of all ten `TOP:`/`BOTTOM:` methods) − **0.01**.
- **Fusion better (secondary):** the same test for `SPLIT`.
- **Vertical solved by fusion:** `LATE` or `SPLIT` passes all thresholds in
  both sessions.
- **Placement replication:** best `BOTTOM:` mean y MAE ≤ best `TOP:` mean
  y MAE − 0.02 (Issue #88 rule, now with simultaneous frames).

The single-camera reference is the best of ten methods chosen after the data,
which favours the single camera; the fusion methods are fixed. The 0.01
margin is smaller than Issue #88's 0.02 because both arms see the same gaze
in the same session.

Descriptive only: per-method metrics, calibration R², checkpoint drift, x MAE,
inter-camera frame gap, per-camera frame and detection counts, detector
latency.

## Interpretation boundaries

One person, one day, two ~100 s sessions. The iPhone differs from the built-in
camera in position and sensor; this experiment does not separate them (a
cheap low webcam would). Two cameras need a second device, a cable and a
stand, and the production Vision layer assumes one camera: a positive result
justifies a Çağrı session and a human architecture decision, not a production
change. A negative result is recorded results-only and this code is not
merged (Fatih's rule).
