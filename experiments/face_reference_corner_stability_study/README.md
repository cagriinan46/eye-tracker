# Face-reference eye-corner stability study — preregistered protocol

## Question and boundary

The [eye-geometry decomposition study](../eye_geometry_decomposition_study/RESULTS.md) found that the production feature's corner-defined reference frame contributed more than the substituted iris position in 47/54 comfortable-wide eye-level contrasts. That is mathematical attribution, not anatomical movement. This experiment asks whether the **detected eye corners move relative to a separate set of detected, non-eye face landmarks** when comfortable eye-opening state changes at a fixed displayed target. It also records whether changes are consistent with broader 2D face translation, uniform scale, or in-plane rotation. The anchors and eyes are still outputs of the same detector; neither set independently measures anatomy, fixation, or full head pose. This is diagnosis only. No production feature, calibration, mapping, or correction changes.

## Exact existing eye geometry

The unchanged [topology adapter](../../src/eye_tracker/vision/eye_topology.py) takes MediaPipe-left eye corners **263 / 362**, iris ring **474–477**, upper/lower lid **386 / 374**, and MediaPipe-right eye corners **33 / 133**, iris ring **469–472**, upper/lower lid **159 / 145**. The [feature extractor](../../src/eye_tracker/vision/eye_features.py) averages each eye's four ring points into an iris center, multiplies normalized x/y by image width/height, forms the corner midpoint and corner-axis length, and projects iris-minus-corner-midpoint onto the corner-axis normal. The upper/lower lid direction orients that normal. Monocular vertical is that projection divided by corner width; binocular vertical is the two-eye mean. Opening is Euclidean upper-to-lower lid distance divided by corner width. The retained contour bounds allow the existing horizontal feature to be reconstructed. All values remain unclipped.

## Fixed, independent-from-eye anchor set

The **same 10 indices** are used for all samples and sessions: MediaPipe `FACE_LANDMARKS_NOSE` path points **6, 197, 195, 5, 4, 1** and bilateral `FACE_LANDMARKS_FACE_OVAL` path points **127, 234, 454, 356**. Their grouping comes from the named connections in the installed MediaPipe **0.10.35** `mediapipe/tasks/python/vision/face_landmarker.py`, cross-checked against [Google's Face Landmarker Python source](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/face_landmarker.py). The nose path gives central-face coverage; the face-oval pairs give broad left/right leverage for estimating 2D scale and rotation. None is in the named eye, iris, eyebrow, or lip connection sets, and none is a production eye corner or lid point. The set is fixed before capture. “Independent” means **landmark-index separation from the eye-local frame**; it does not mean independent measurement hardware or immunity to expression, detector coupling, depth, or perspective changes.

## Session-local face reference and units

Use **only usable samples in the nine natural-opening calibration presentations** to form one template: for each of the 10 anchors, take the median x pixel coordinate and median y pixel coordinate independently. Diagnostic samples never tune it. For every usable frame, convert its anchors from image-normalized coordinates to pixels and fit the orientation-preserving least-squares similarity from current points `pᵢ` to template points `qᵢ`:

`q̂ᵢ = s R(θ) pᵢ + t`, where `s > 0`, `R(θ)` is a 2D rotation, and `t` is a pixel translation.

Center both point sets. With centered points `(xᵢ,yᵢ)` and `(uᵢ,vᵢ)`, set `A=Σ(xᵢuᵢ+yᵢvᵢ)`, `B=Σ(xᵢvᵢ−yᵢuᵢ)`, `D=Σ(xᵢ²+yᵢ²)`, `θ=atan2(B,A)`, `s=hypot(A,B)/D`, and `t=q̄−sR(θ)p̄`. Save `s`, `θ` (radians), translation x/y (pixels), and RMS Euclidean anchor residual (pixels). A degenerate fit invalidates capture rather than returning invented aligned points. Apply this same pixel-space transformation to each eye point, then serialize the result as image-normalized x/y so it can be read alongside original coordinates. Derived spans remain in pixel units, angles in radians, opening and vertical features dimensionless. The 2D similarity has **translation, one uniform scale, and in-plane rotation**; it cannot remove pitch, yaw, depth/perspective changes, facial deformation, or true fixation error.

Per usable sample the JSON retains all 10 raw face anchors, both eyes' prior primitive geometry (four iris ring points, center, corners, lids, contour extrema), each eye's **original image-coordinate** and **face-normalized** corner A/B, corner midpoint, corner span, corner angle, iris center, iris position along/across the corner-local frame, upper/lower lid, lid midpoint, opening, and monocular vertical. It also retains current binocular features, sample status, target/order/time, transform and residual. Face-normalized monocular feature/opening should equal the original under a valid similarity; the runner and analyzer check this, while their **point coordinates** can differ. Unusable rows retain status and counts without fabricated geometry. No frames, images, or video are saved.

## Fixed human design and instructions

Participant `cagri`: **three fresh sessions**, `live-1`, `live-2`, `live-3`. Each starts with a standard **nine-point natural-opening calibration**, then **27 diagnostic presentations** = three vertical targets × three prompts × three blocks. Targets are upper `(0.5, 0.25)`, center `(0.5, 0.50)`, lower `(0.5, 0.75)`. Total **36 presentations per session**. No diagnostic result changes the calibration.

The three prompts are `comfortably_narrow`, `natural`, `comfortably_wide`. The deterministic seed is **20261005**; its base permutation is **natural → comfortably wide → comfortably narrow**. Row visit order rotates by block. At each row visit, condition order rotates by `((block − 1) + row_index) mod 3`, so each condition occupies each of the three positions exactly once per target across the blocks. Prompts are **labels**, not assumed quantitative opening values. No run is repeated merely because the measured result is inconvenient.

Before calibration, the full-screen **READY** screen appears and timing waits for **SPACE**. It asks the participant to keep head, body, sitting position, and facial expression as constant as practical. For each diagnostic presentation:

1. **Cue, 1.5 s:** show one large centered condition instruction, with **no target and no measurement**. Read it and prepare the instructed comfortable state.
2. **Target, 0.8 s settling + 1.2 s sampling:** remove all cue text, show **only the target dot**, and keep gaze there while maintaining the prepared eye state. No prediction, condition label, or debug value appears during fixation.

**COMFORTABLY NARROW:** Clearly but comfortably narrow the eyelids. Do not hard-squint. Do not scrunch the nose or intentionally change the rest of the face.

**NATURAL:** Use normal relaxed eye opening.

**COMFORTABLY WIDE:** Clearly but comfortably open the eyes wider. Do not maximally widen, intentionally raise the eyebrows, or move the rest of the face.

For every condition: read the cue **before** the target appears. When it disappears, look **only** at the target and maintain the state until measurement ends. Blink naturally. Avoid intentionally moving the eyebrows, nose expression, mouth, jaw, or head; do not strain. Natural involuntary changes are observations, not automatic invalidation. Press `q` or Esc to abort at any time and report interruptions or protocol deviations. The runner preserves an `.invalid.json` marker for aborted/technical invalid attempts and refuses to overwrite existing output.

Nine calibration targets × 2.0 s plus 27 diagnostic cues/targets × (1.5+2.0) s gives **112.5 s (~1 min 53 s)** of timed presentation, plus model/camera startup, READY waiting, and processing. Allow roughly **2–3 minutes per session**.

## Exact local commands

Run from repository root after reviewing the UI. Camera index 1 matched prior sessions on this particular Mac; camera ordering is not universal. These paths are distinct, ignored local numerical captures and must not already exist:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.face_reference_corner_stability_study.run --participant cagri --session live-1 --camera-index 1 --output .venv/face-reference-cagri-live-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.face_reference_corner_stability_study.run --participant cagri --session live-2 --camera-index 1 --output .venv/face-reference-cagri-live-2.json
PYTHONPATH=src:. .venv/bin/python -m experiments.face_reference_corner_stability_study.run --participant cagri --session live-3 --camera-index 1 --output .venv/face-reference-cagri-live-3.json
```

The output identifies `protocol_name=face_reference_corner_stability`, `protocol_version=1`, seed/timings, camera and resolution, face indices/method/template, mapping coefficients, sample and presentation counts, and all derived numerical geometry. Older eye-opening or eye-geometry JSON is **incompatible** and rejected by the analyzer.

## Predeclared Stage 2 analysis, interpretation limits

First check technical validity and, for every session × target × block, whether measured binocular opening follows **comfortably narrow < natural < comfortably wide**. This is a manipulation check, **not** a hidden run-exclusion rule. Retain every technically and protocol-valid session regardless of its result.

At each exact target/block, compare comfortable narrow and comfortable wide **separately against natural**. Keep signed face-normalized corner A/B/midpoint displacement, span, wrapped angle, iris-center displacement, corner-relative iris coordinate, upper/lower/lid-midpoint displacement, opening, and production monocular/binocular vertical change for each eye. Inspect transform translation/scale/rotation and RMS residual alongside these contrasts. Preserve upper/center/lower, blocks, order/time, and left/right eyes separately; report overlap and outliers rather than selecting a favorable subset. The analyzer also retains original image-coordinate values for comparison. A transform can align 2D face anchors while pitch, yaw, depth, projection, expression, detector error, or imperfect fixation remain. Do not interpret face-normalized landmark movement as anatomical movement or infer a production correction. Calibration slope times feature difference may be shown only as secondary, unclipped mapped-y context. The three completed sessions and evidence-bounded Stage 2 findings are in [RESULTS.md](RESULTS.md). The matched-natural fixed-corner counterfactual in that report is explicitly labeled a secondary, post-capture diagnostic.
