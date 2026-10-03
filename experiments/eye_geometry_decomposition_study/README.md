# Eye-geometry decomposition at fixed vertical targets

## Question and boundary

The corrected [eye-opening controlled study](../eye_opening_controlled_study/RESULTS.md) found clean measured narrow < natural < wide separation in 27/27 matched sets, with vertical-feature changes that were neither globally monotonic in opening nor uniform across target rows. This follow-up asks **which recorded eye-geometry components change** when a participant holds the displayed target fixed and deliberately changes comfortable lid state. It distinguishes iris position in the eye-local frame, lid positions and aperture, and the corner-defined reference frame **numerically**. It does not identify a medical or physical cause, independently verify fixation, or select a production correction.

This is a **new protocol**, not an extension of the earlier JSON format. Its three completed sessions are analyzed in [RESULTS.md](RESULTS.md). The runner and analyzer accept only this study's explicit `protocol_name=eye_geometry_decomposition`, `protocol_version=1`, order seed, and timing metadata. They do not analyze either the earlier protocol-v2 eye-opening captures or the preserved protocol-invalid pilots.

## Exact production geometry being observed

The unchanged production [topology adapter](../../src/eye_tracker/vision/eye_topology.py) names the following MediaPipe Face Landmarker indices. “Left/right” here follows the adapter's MediaPipe naming. Coordinates are image-normalized in saved JSON; the feature calculation multiplies x by frame width and y by frame height before forming distances and projections.

| Eye | Iris ring averaged to iris center | Corner A / B | Upper / lower lid | Contour used for bounds and geometry validity |
| --- | --- | --- | --- | --- |
| Left | 474, 475, 476, 477 | 263 / 362 | 386 / 374 | 249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466 |
| Right | 469, 470, 471, 472 | 33 / 133 | 159 / 145 | 7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246 |

The unchanged [feature extractor](../../src/eye_tracker/vision/eye_features.py) computes a pixel-coordinate iris center as the arithmetic mean of the four ring points. Let `axis = corner_b − corner_a`, `width = ||axis||`, and `normal = (-axis_y, axis_x) / width`; flip the normal if `(lower_lid − upper_lid) · normal < 0`. With `corner_mid = (corner_a + corner_b)/2`, the monocular **vertical local-axis feature** is `(iris_center − corner_mid) · normal / width`. The binocular vertical feature is the mean of the two monocular vertical features. The lid points **orient** the vertical normal but are not the origin of that feature. The current diagnostic **opening** is the Euclidean pixel distance between upper/lower lid points divided by corner width; it is distinct from the lid gap projected onto the normal. The horizontal feature uses `(iris_x − contour_x_min)/(contour_x_max − contour_x_min)` in pixel coordinates. Degenerate corner width, contour spans, or projected lid gap make the feature unavailable; nothing is clipped, smoothed, or corrected.

The new per-sample record retains, **for each eye**, all four iris-ring points, their computed center, both corner points, upper and lower lid points, and four contour extrema (`x_min`, `x_max`, `y_min`, `y_max`). The full 16-point contour and all 478 face landmarks are **not** stored. These primitives and the per-row frame width/height suffice to reconstruct both current features, current opening, local axis, and the lid midpoint offline. The analyzer independently checks the reconstructed values against the captured feature fields. It can then derive image-coordinate iris/lid displacements, local iris parallel/vertical position, lid-local positions, iris relative to lid midpoint, corner-axis width/angle, and opening without changing production code. Both eyes are retained separately before any binocular summary. Image-coordinate displacement is not proof of physical iris or eyelid motion.

The runner also retains the existing corner-mean `head_center_y`, plus corner-mean `head_center_x`, pixel distance between eye-corner midpoints as an inter-eye scale proxy, and the angle of the line between those midpoints as a coarse roll proxy. These are inexpensive **image-geometry diagnostics**, not full 3D head pose; they cannot rule out pitch or camera changes.

## Fixed design and order

Participant: `cagri`. Collect exactly **three fresh sessions**, `live-1`, `live-2`, and `live-3`. Each has a fresh **nine-target 3×3 calibration** under natural relaxed opening, followed by **45 diagnostic presentations**: three vertical target rows at `(0.5, 0.25)` upper, `(0.5, 0.50)` center, `(0.5, 0.75)` lower, five opening prompts, and three blocks. Total: **54 presentations per session**. The nine-point calibration supplies only secondary mapped-y context; diagnostic presentations do not tune the mapping.

The five fixed prompts are `comfortably_narrow`, `slightly_narrow`, `natural`, `slightly_wide`, `comfortably_wide`. They are **instructions, not quantitative ground truth or equal-spaced doses**. Actual measured opening is the primary quantitative variable. The [schedule](protocol.py) uses seed **20261004** with Python's local `random.Random(seed).sample` to fix a base permutation before capture: **slightly narrow → comfortably narrow → comfortably wide → natural → slightly wide**. Within each block, row order rotates cyclically; each row's five-condition sequence is a cyclic rotation of that base, using offset `((block − 1) × 3 + row_index) mod 5`. Across the nine row visits, each condition appears once or twice in each sequence position. Every target × condition occurs once per block, three times per session. No ordering is changed after data are seen.

The window first displays **READY — press SPACE to begin**; calibration timing starts only after SPACE. Each calibration presentation shows a target dot with natural opening. **Every diagnostic presentation has two disjoint phases:**

1. **Cue:** show only its large centered instruction for approximately **1.5 s**. There is **no target and no measurement**. Read it and establish the requested comfortable state.
2. **Target:** remove the instruction completely, then show **only the dot** for **0.8 s settling** and **1.2 s sampling**. There is no condition text, prediction, debug value, or other gaze object. Look only at that dot while maintaining the state prepared during the cue.

**Perform each cue deliberately, without strain:**

- **COMFORTABLY NARROW:** Gently narrow the eyelids to a comfortable clearly-narrow state. Do not hard-squint.
- **SLIGHTLY NARROW:** Make the eyes only a little narrower than normal.
- **NATURAL:** Use normal relaxed eye opening.
- **SLIGHTLY WIDE:** Open the eyes only a little wider than normal.
- **COMFORTABLY WIDE:** Open the eyes clearly wider than normal while remaining comfortable. Do not maximally widen or strain.

For **all** conditions: read the cue first; when it disappears, look only at the target. Do not look back toward where the text was. Maintain the requested opening until that target measurement ends. Natural blinking is allowed. Keep head and sitting position as constant as practical; do not intentionally move them. Press `q` or Esc to abort at any time. The participant must report any interruption or protocol deviation, including a failure to perform a prompted state.

Nine calibration targets × 2.0 s and 45 diagnostic targets × (1.5 + 2.0) s give **175.5 s (~2 min 56 s)** of timed cue/target presentation, plus camera/model startup, processing, and time on the READY screen. Allow roughly **3–4 minutes per session**. A presentation needs at least five usable sampling frames. The exact practical duration depends on capture performance and when SPACE is pressed.

## Commands and local output

Run from the repository root. Camera index 1 matches prior Çağrı sessions **on that setup**; use the actual working index if it differs. Confirm each session's participant instructions before pressing SPACE. Each command writes a distinct JSON file under ignored `.venv/` and refuses to overwrite an existing file:

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_geometry_decomposition_study.run --participant cagri --session live-1 --camera-index 1 --output .venv/eye-geometry-cagri-live-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_geometry_decomposition_study.run --participant cagri --session live-2 --camera-index 1 --output .venv/eye-geometry-cagri-live-2.json
PYTHONPATH=src:. .venv/bin/python -m experiments.eye_geometry_decomposition_study.run --participant cagri --session live-3 --camera-index 1 --output .venv/eye-geometry-cagri-live-3.json
```

No raw images or video are saved. Each numerical sampling row includes participant/session, phase, target ID/coordinates, prompt label, block, presentation order, sample sequence, timestamp/monotonic time, status, current binocular/monocular features and opening, the explicit per-eye geometry above for usable samples, and the coarse head diagnostics. A mapped prediction is stored when available after calibration, but is never displayed. The JSON also includes protocol name/version, READY/cue/timing markers, deterministic seed, camera index/resolution, sample and failure counts, elapsed time, nine-target mapping coefficients, and presentation summaries. Partial measurements are not retained after capture exceptions; an `.invalid.json` marker records an interrupted/invalid run. Preserve and document invalid attempts rather than overwriting or silently replacing them. Retain **all** technically and protocol-valid complete sessions regardless of their results; no measured-order threshold is a hidden validity gate.

## Predeclared offline Stage 2 analysis

The [analyzer](analysis.py) first rejects incompatible metadata and any raw/saved presentation that disagrees with the fixed 54-presentation schedule. For each usable row it reconstructs per-eye horizontal, vertical, and opening from saved primitive geometry and verifies agreement with the captured fields. It then takes independent medians of each scalar field across all usable samples in a presentation; medians of different fields must not be mistaken for a single synthetic landmark configuration. It keeps raw rows and output per presentation, including target, label, block, order, and time, for later inspection.

**Manipulation check first:** for every session × target × block, report the five measured presentation-median binocular openings, actual pair separations, and how often the requested opening order holds. Five-level perfect ordering is **not** an exclusion rule; valid completed runs remain in the analysis even if the prompts fail to separate.

**Fixed-target decomposition:** at each target and block, compare all ten distinct pairs of the five prompts, with four natural-reference contrasts oriented as changed state minus natural. Preserve signed changes in measured aperture, image-coordinate iris/upper/lower/lid-midpoint positions, corner-frame width/angle, iris position in the corner-local frame, iris versus lid midpoint, current vertical feature, both monocular values, and coarse head diagnostics. Retain actual order/time for drift checks. Keep upper/center/lower and left/right separate; do not collapse to one global opening coefficient. `y_slope × Δvertical` is secondary mapped-y context only, without clipping. No condition label is treated as a measured aperture value.

For the vertical-feature contrast, the analyzer takes the coordinate-wise medians of each presentation's saved iris center and corner/lid points, then evaluates the unchanged vertical formula as `f(iris, reference)`. It computes `f(I₀,R₀)`, `f(I₁,R₀)`, `f(I₀,R₁)`, and `f(I₁,R₁)` for natural (`0`) and the changed condition (`1`). The **iris contribution** is half of `[(f10−f00)+(f11−f01)]`; the **reference contribution** is half of `[(f01−f00)+(f11−f10)]`. These are the two symmetric substitution orders and split their nonlinear interaction equally. Their sum is the change between the two representative geometries. A separately labeled **median-aggregation residual** is the recorded presentation-median feature difference minus that sum, so all three terms exactly recover the observed contrast. Because separate medians of coordinates need not form a real frame, the contributions are descriptive mathematical attributions, not physical causes. The reference includes corner coordinates and the lid-defined orientation sign; if that sign stays fixed, lid position does not directly enter the current vertical formula.

Three same-participant sessions cannot prove causal anatomy, detector error, independent fixation, a correction, production/cursor readiness, or cross-user generality. Eye opening and the vertical feature share landmarks; movements in those numerical landmarks may reflect several unmeasured factors. See [RESULTS.md](RESULTS.md) for the evidence-bounded Stage 2 interpretation.
