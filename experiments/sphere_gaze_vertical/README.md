# 3D eye-sphere gaze feature on the built-in camera — Issue #92

Preregistered **2026-10-13, Europe/Istanbul**, before any Issue #92 session.
Task approved by Fatih in chat ("webcami almadan şimdiki laptop kameram ile
bunu bir deneyelim"); this preregistration approved by Fatih before session A.
Diagnostic experiment; no production change.

## Question

Jason Orlosky's open-source webcam prototype
([JEOresearch/EyeTracker](https://github.com/JEOresearch/EyeTracker),
`Webcam3DTracker/MonitorTracking.py`, MIT; video "3D Eye Tracking on a
Webcam") estimates gaze from MediaPipe landmarks differently from production:
not the iris relative to the eye corners, but the 3D vector from a virtual
eyeball centre, locked in a nose-landmark head frame while the user looks at
screen centre, to the 3D iris landmark. Head rotation is compensated
geometrically. The prototype reports no measured accuracy. Our earlier studies
found that the eye-corner reference itself moves with eye opening, and a 2D
face-normalized iris y was rejected (alternative_vertical_feature_benchmark).
**Does the prototype's 3D eye-sphere vertical signal beat production features
under the frozen Issue #77 protocol on Fatih's built-in camera?**

## Port of the prototype (fixed before data)

- **Head frame** (`capture.py`, per frame): the prototype's 24 nose landmarks
  in pixels (x·w, y·h, z·w); centre = mean; axes = PCA eigenvectors sorted by
  decreasing variance, made right-handed, signs aligned to the session's first
  frame (the prototype's anti-flip reference); scale = mean pairwise distance.
- Stored per frame (derived numbers only): the 3×3 rotation, the nose scale,
  and each iris centre (landmarks 468/473) in head-local coordinates divided
  by the scale. No landmark arrays or images.
- **Lock** (analysis): the prototype's "look at centre and press c" is the
  first `K-center` checkpoint with ≥ 5 common frames (normally presentation 2,
  before calibration). Per eye, eyeball centre = median local iris + (r / median
  scale) · median camera direction in the head frame, with r = 20 px × frame
  width / 640. The prototype uses 20 px; scaling to its assumed 640-pixel
  capture width is our adaptation for 1920×1080 frames.
- **Gaze:** per eye, unit(R · (local iris − eyeball centre)); the two are
  averaged and normalized. `sphere_pitch` = atan2(−d_y, −d_z) in degrees (up
  positive, prototype convention); `sphere_yaw` = atan2(d_x, −d_z).
  Per-presentation medians replace the prototype's 10-frame moving average.

The collector is the Issue #77 collector, unchanged except that it accepts this
experiment's extractor and name. MediaPipe still makes one detector call per
frame. Model: `.venv-fatih/models/face_landmarker.task` (SHA-256
`64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`).

## Sessions

Fatih only, built-in camera above the screen (index 0 in #88/#90, rechecked at
smoke test), full screen 1512×982, `.venv-fatih`, two sessions, A then B,
reseating between, results hidden until both end:

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.sphere_gaze_vertical.run \
  --participant fatih-sphere --session A --camera-index 0 --screen-size 1512x982 \
  --model .venv-fatih/models/face_landmarker.task \
  --output validation/results/sphere-gaze-fatih-A.json
# then --session B ... sphere-gaze-fatih-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.sphere_gaze_vertical.analysis \
  validation/results/sphere-gaze-fatih-A.json validation/results/sphere-gaze-fatih-B.json
```

## Analysis (frozen before data)

Common frames: the Issue #77 rule (usable, all inputs present, blink ≤ 0.5)
**and** complete eye-sphere numbers; every candidate uses the same frames.
Validity: Issue #77 (≥ 20/25 calibration, ≥ 14/16 validation presentations)
and a lock is available. Fit on calibration, score on validation, Issue #77
metrics and pass thresholds (y MAE ≤ 0.08, ordering ≥ 19/21, |bias| ≤ 0.05).

| Candidate | Inputs (OLS with intercept) |
| --- | --- |
| R0, OPEN, OPEN_Q, BLEND, COMBO | Issue #77, unchanged |
| `SPHERE` | sphere pitch |
| `SPHERE_COMBO` | sphere pitch, eye opening, blendshape, head pitch (COMBO with the production vertical replaced) |

Descriptive only: the prototype's own mapping (y = 0.5 − (pitch − lock pitch)
/ 10°, i.e. ±5° to the screen edges, one-point centre calibration); x from
sphere yaw; per-row validation medians of sphere pitch (degrees); calibration
R²; frame counts; detector latency.

## Preregistered decision

Requires both sessions valid; otherwise **inconclusive**. No session is
repeated or replaced after its data are seen.

- **Sphere reference better (primary):** `SPHERE` mean y MAE ≤ `R0` mean
  y MAE − **0.02** (both one-feature: 3D eyeball reference vs eye-corner
  reference).
- **Secondary:** `SPHERE_COMBO` mean y MAE ≤ `COMBO` mean y MAE − 0.01.
- **Vertical solved by sphere (single built-in camera):** `SPHERE` or
  `SPHERE_COMBO` passes all thresholds in both sessions.

## Interpretation boundaries

One person, one day, one camera, two ~100 s sessions. A port, not the
prototype itself: its fixed one-point mapping is only descriptive, and the
eyeball radius is adapted to our resolution. MediaPipe's z coordinate is
weakly constrained, so a negative result says this port does not help here,
not that 3D eye models cannot. A positive result would be checked on the
webcam (dual-camera) setup and with Çağrı before any production decision. A
negative result is recorded results-only and this code is not merged.
