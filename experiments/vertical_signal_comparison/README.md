# Vertical signal comparison — Issue #77

Preregistered **2026-10-08, Europe/Istanbul**, before any Issue #77 session.
Approved by Fatih in chat. Diagnostic experiment; no production change.

## Question

[Issue #75](../vertical_signal_drift_diagnosis/RESULTS.md) classified Fatih's
vertical failure as `SIGNAL`: the production iris-vs-corner vertical feature had
calibration R² 0.24 / 0.21, while eye opening tracked target rows (R² 0.97 /
0.90) but shifted between calibration and validation. **Which vertical signal,
fitted from calibration only, meets the accepted vertical exit criteria for
Fatih in two separate sessions?**

## Signals and capture

`capture.SignalExtractor` subclasses the production MediaPipe adapter: same
image conversion, timestamps and landmark conversion, but the detector is
created with `output_face_blendshapes` and `output_facial_transformation_matrixes`
enabled. Production features and Issue #44 diagnostics come from the unchanged
`measure_once` path. Per sampling frame the collector stores only derived
numbers: binocular/left/right production features, eye opening (lid-point
distance / corner distance), head-center-y proxy, blendshapes `eyeLookUp*`,
`eyeLookDown*`, `eyeBlink*`, head pitch/yaw/roll from the transformation
matrix, and the detector call duration. No landmarks, images or video.

A pre-data hardware smoke test on Fatih's Mac (no data saved) found all
blendshape and pose fields present in 90/90 usable frames, and a median detector
call of 6.81 ms with the extra outputs versus 6.70 ms for the production adapter.

## Protocol

Full screen only (`--screen-size` is required; see the Issue #75 amendment).
Each presentation keeps 0.8 s settling, 1.2 s sampling and at least five usable
frames. Schedule (`protocol.build_schedule`, seed 77), 50 presentations ≈ 100 s:

1. Checkpoint block 1: K-top (0.5, 0.1), K-center (0.5, 0.5), K-bottom (0.5, 0.9).
2. Calibration: 5×5 grid at 0.1/0.3/0.5/0.7/0.9, **shuffled** so time is not
   confounded with screen row.
3. Checkpoint block 2.
4. Validation: 4×4 grid at 0.2/0.4/0.6/0.8, shuffled; no overlap with calibration.
5. Checkpoint block 3.

Fatih runs Session A, stands up and reseats, then Session B; results are not
shown between sessions. Camera index 0, `.venv-fatih` only:

```bash
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_signal_comparison.run \
  --participant fatih --session A --camera-index 0 --screen-size 1512x982 \
  --output .venv/vertical-signals-fatih-A.json
# reseat, then the same with --session B and .venv/vertical-signals-fatih-B.json
PYTHONPATH=src:. .venv-fatih/bin/python -m experiments.vertical_signal_comparison.analysis \
  .venv/vertical-signals-fatih-A.json .venv/vertical-signals-fatih-B.json
```

## Frozen analysis

**Common frames.** A frame enters the analysis only if its status is usable,
every input below is present, and max(`eyeBlinkLeft`, `eyeBlinkRight`) ≤ **0.5**.
All candidates therefore use identical frames. A presentation needs at least
five such frames; a session is invalid if fewer than **20/25** calibration or
**14/16** validation presentations remain.

**Presentation medians** of: production horizontal `h` and vertical `v`,
binocular eye opening `o`, `blend = mean(lookDown) − mean(lookUp)`, head pitch.

**Candidates** — ordinary least squares with intercept, fitted on calibration
presentation medians only, applied to validation presentation medians:

| Name | Model for screen y |
| --- | --- |
| R0 | `v` (equals the production independent-linear y fit; tested) |
| OPEN | `o` |
| OPEN_Q | `o`, `o²` |
| BLEND | `blend` |
| COMBO | `v`, `o`, `blend`, pitch |

A rank-deficient design makes that candidate unavailable (fails). x is reported
from a production-style `h` fit and is not a candidate.

**Per-session pass** (the accepted exit thresholds): validation y MAE ≤ **0.08**,
pair ordering ≥ **19/21** (90.5%) of the 96 distinct-row validation pairs at
least 0.05 apart, and |mean signed y error| ≤ **0.05**.

**Winner:** the candidate passing in **both** sessions; if several, the lowest
mean y MAE across sessions; if none, `None`. Constants and candidate
definitions are asserted by tests and must not change after data collection.

**Descriptive only:** calibration R² per candidate, checkpoint predictions per
block and |block 3 − block 1| (drift), x metrics, detector latency (median, p95),
frame counts.

## Interpretation boundaries

Five candidates are compared on the same validation set; requiring a pass in
two independent sessions limits selection by chance but does not remove it. A
winner here is evidence for Fatih only. It would justify a Çağrı session and a
human decision on exposing the signal through the Vision contract; it does not
change production by itself. If no candidate wins, humans choose between an
appearance-based model, a head-assisted vertical interaction, or other
directions. Blink threshold, head-pose convention and eye-opening definition
are engineering choices, not validated physiology.
