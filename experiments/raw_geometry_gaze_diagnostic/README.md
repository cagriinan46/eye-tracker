# Raw-geometry fixed-window gaze diagnostic

## Purpose and boundary

Record once, evaluate bounded representation candidates later. The completed
[fixed-window diagnostic](../fixed_window_gaze_diagnostic/RESULTS.md) concluded
**Outcome C**: production h/v retain gaze ordering, but same-target transfer and
block variability are appreciable; independent-linear calibration also leaves
residuals. Representation/normalization is prioritized before richer mapping.
Those captures retained only features and screen predictions. They cannot supply
missing iris/lid/face geometry, depth, or pose, and no images exist to rerun them.

This task builds numerical instrumentation and
[preregisters exactly R0/R1/R2](PREREGISTRATION.md). It implements no alternative
representation, estimator, map, smoothing, ML, or cursor behavior. No session
has been collected automatically and no RESULTS are claimed. Physical causes
remain unknown.

## Protocol and physical instructions

Identity: `raw_geometry_gaze_diagnostic`, version **1**, geometry schema **1**.
The physical flow reuses the existing fixed-window implementation:

| Phase | Count | Display and timing |
| --- | ---: | --- |
| READY | 1 | SPACE required before camera/model initialization |
| Calibration | 9 | Target only; 0.8 s settling + 1.2 s sampling |
| Instructional fixation cue | 27 | Cue only for 0.75 s; never gaze-gated |
| Validation | 27 | Target only, complete 3.0 s window regardless of predictions |
| Neutral transition | 27 | Blank for 0.5 s |

Targets/calibration are the 3×3 grid at x/y = {0.2, 0.5, 0.8}. Calibration is
row-major. Validation uses unchanged `random.Random(20261006).sample` ordering
with subsequent blocks rotated by three positions: every target once per block,
three blocks total. Cue is (1−target_x, 1−target_y), except center's cue is
(0.2,0.2). Target immediately replaces cue. No success/failure, dwell, timeout,
retry, gaze cursor, grading, or accuracy-dependent progress exists.

Read before SPACE:

- Sit in normal comfortable computer-use posture. Keep the physical setup
  reasonably consistent after calibration; do not rigidly freeze your head.
- Use **natural relaxed eye opening**; blink naturally. Do not deliberately
  widen or narrow the eyes.
- Look at the cue while shown, then look at the **CENTER** of the target and
  continue looking there until it disappears.
- Do not intentionally steer with the head or chase a predicted point. No gaze
  cursor or predictions will be shown.
- This is measurement, not a game; acquisition is never graded. q/Esc aborts.

Nominal timed duration: `9×2.0 + 27×(0.75+3.0+0.5) = 132.75 s`, approximately
**2 min 13 s** plus initialization, READY waiting, and scheduling overhead.
Allow **2–3 minutes after SPACE**. The display uses the existing independent GUI
deadlines and one camera worker. Actual onset/end/overrun are logged; only frames
begun and completed inside the nominal sampling interval are retained. A slow
native call cannot gate target removal. No measurement-dependent early stop.

## Same-result instrumentation and R0 preservation

`GeometryExtractor` subclasses the production MediaPipe adapter and wraps its
private native `detect_for_video` member with a read-only numerical observer.
There is one native call per frame. The original result object is returned
unchanged to the inherited production XY conversion. The same options, local
model, VIDEO timestamps, topology, features, and calibration fitter apply.
Private-member coupling stays in the experiment and is tested against the
production adapter; future adapter changes require rerunning equivalence tests.
No production accessor or file is modified.

`GeometryTap` reuses the existing R0 feature tap; `GeometryWorker` reuses its
queue/lifecycle and attaches the geometry snapshot before processing the next
frame. Camera failures cannot reuse the preceding frame's geometry. Collection
reuses `collect_window`, READY, UI drawing, cue/schedule, and fresh ordinary
`fit_session_calibration` / `IndependentLinearMapping`. Only session orchestration
is isolated for the new identity/schema. Full numerical geometry is retained
for calibration as well as validation, including available partial geometry on
unavailable-feature attempts.

## Exact landmark whitelist

Indices follow production `eye_topology.py`, installed MediaPipe 0.10.35
`FaceLandmarksConnections`, and the canonical mesh. Names are MediaPipe-left/right,
not a guarantee of mirrored screen-side placement.

| Primitive | Left | Right |
| --- | --- | --- |
| Production iris ring | 474, 475, 476, 477 | 469, 470, 471, 472 |
| Detector iris center (optional, separate from R0 ring mean) | 473 | 468 |
| Outer corner / production corner_a | 263 | 33 |
| Inner corner / production corner_b | 362 | 133 |
| Upper lid reference | 386 | 159 |
| Lower lid reference | 374 | 145 |
| Full production contour | 249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466 | 7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246 |

Non-eye anchors: **6, 197, 195, 5, 4, 1, 127, 234, 454, 356, 10, 152**.
The first six are the established NOSE chain. The next four are bilateral
FACE_OVAL references reused from the face-reference study. Superior/inferior
FACE_OVAL points 10/152 add orientation extent; the canonical model confirms
their midline vertical positions and confirms outer/inner corner naming. The
12-point reference excludes eyes, iris, brows, and lips. It is not guaranteed
expression-invariant or anatomical ground truth; chin/face-oval movement is a
potential confound, not a reason to invalidate normal-use movement.

The whitelist contains **54 unique points**, of which **52 require finite XY**
for a usable R0 geometry record. Detector centers 468/473 are optional. No full
478-point mesh is saved. Sources: [Face Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python),
[official topology](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py),
and [canonical mesh](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj).

## Numerical schema

Session metadata includes participant/session and development/holdout role,
protocol/schema versions, all timing/target/cue/order settings, READY use,
selected/required landmark and eye index maps, camera index/resolution, mapping
coefficients, model SHA-256, installed MediaPipe version, unchanged-options policy,
unknown camera intrinsics (`null`), whole-run counters, and elapsed time.

Every calibration/validation sample retains:

- Monotonic attempt-start/completion and trial-relative seconds, capture timestamp
  in ns, phase, presentation order, block, target identity/coordinates, actual
  frame resolution, availability/reason, and raw R0 h/v and mapped XY when calibrated.
- `raw_geometry.landmarks`: index-keyed **copies** of normalized `{x,y,z}`;
  z is `null` when absent/nonfinite. No normalization is substituted for raw data.
- Required/optional XY missing-index lists and explicit missing-z list. Absence
  is not replaced by zero or silently treated as complete 3D data.
- Face-anchor copies and both-eye iris-ring mean, separately exposed detector
  iris center, corners/midpoint, upper/lower lids/midpoint, pixel corner span/angle,
  lid distance/opening, production-oriented vertical basis, and monocular R0 h/v.
- Interocular corner-midpoint distance, native detector timestamp in ms, optional
  4×4 facial transform with available/not_exposed/malformed status, or no face
  (`raw_geometry: null`). All derived records retain their underlying primitives.

The installed result exposes normalized XYZ, so **z is expected** from this
Face Landmarker, but availability is checked per point/frame. Z is an estimated
relative depth, not metres or independent 3D pose. The production options leave
`output_facial_transformation_matrixes` disabled; this experiment does **not**
enable it. Thus the normal capture will have no direct pose matrix. If one is
already exposed by an otherwise compatible result, it is copied without changing
options. Selected XYZ/face anchors support approximate pose/orientation estimation
**offline later**. No new pose algorithm runs during collection or in production;
intrinsics/conventions/assumptions must be specified before candidate evaluation.

## Capture validation, optional fields, and holdout protection

`analysis.py` verifies exact protocol/schema/index set, session role, complete
9+27 schedule, fresh calibration-only production coefficients, full windows,
sample phase/order/timestamps, required finite XY, explicit optional XYZ/pose
status, same-frame identity, and raw-geometry reconstruction of R0. Derived
copies must agree with raw primitives. It reports geometry/depth/pose coverage,
usable/unavailable samples, and camera/no-face counters. It does **not** report
holdout accuracy or implement R1/R2. It rejects legacy fixed-window, eye-opening,
geometry-decomposition, and marked-incomplete/pilot reports.

Optional z, detector-center, or pose absence is reported, not fabricated and not
a hidden validity threshold. A usable R0 sample missing required eye/face XY
makes the geometry capture incomplete; its output is preserved as invalid.
Unavailable attempts/partial geometry stay logged. Poor mapped accuracy, normal
movement/blinks, and condition-independent target errors never invalidate a run.
A complete capture with signal loss may still be insufficient for later diagnosis;
coverage is reported instead of inventing a success threshold.

Geometry-1 is development; **geometry-2 is the untouched final holdout**. Keep
geometry-2 outcomes unopened until R1/R2 are frozen in an immutable commit.
Schema checks/R0 reconstruction are permitted; target-label-driven formula
choice is not. Future metrics/gates and exact freeze procedure are in
[PREREGISTRATION.md](PREREGISTRATION.md). No candidate is evaluated in this task.

## Privacy, output size, and commands

No images, video, crops, screenshots, raw frame payloads, or native detector
objects are serialized. Only numerical geometry and necessary provenance stay
local under ignored `.venv/`. Landmark/depth records can still be sensitive;
they are not committed or uploaded by the harness. Detector-library network
behavior is a separate existing project question, not a new logging channel.
Expect approximately **30–50 MiB per session** at roughly 25–30 sampled FPS with
indented JSON; actual size depends on throughput and numeric precision. This is
an estimate from the synthetic schema (28–34 MiB before extra numerical
precision/summary overhead), not a measured human capture.

After human review and merge, from repository root:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.raw_geometry_gaze_diagnostic.run --participant cagri --session geometry-1 --camera-index 1 --output .venv/raw-geometry-gaze-cagri-geometry-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.raw_geometry_gaze_diagnostic.run --participant cagri --session geometry-2 --camera-index 1 --output .venv/raw-geometry-gaze-cagri-geometry-2.json
```

Camera index is machine-specific; 1 is Çağrı's established local setup. The
local model defaults to `.venv/models/face_landmarker.task`. The existing optional
vision dependencies are required only to run live capture, not CI test collection.
Each run gets fresh calibration; existing captures/invalid siblings are never
overwritten. Aborts or technical failures preserve available partial records in
`<output-stem>.invalid.json`. Preserve/document failures, never repeat for an
inconvenient outcome.

Schema-only inspection (does not evaluate a representation):

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.raw_geometry_gaze_diagnostic.analysis .venv/raw-geometry-gaze-cagri-geometry-1.json
```

## Checks

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
git diff --check
```

Synthetic tests exercise numerical extraction/depth/pose absence, production
same-result equivalence, R0 reconstruction, fixed-window timing, all 9+27
presentations, READY-before-camera orchestration, invalid data rejection, and
holdout identities. Human UI/camera timing and empirical capture size remain
unmeasured until authorized human collection.
