# Desktop target-selection demo

Local Python + pywebview presentation prototype, issue #136. This reuses MGazeNet
and Ridge alpha0.1 from the GazeFollower experiment; it does not deploy the failed
head correction, old SVR prediction, OS clicks, or hardware movement.

## Run

Use Python3.12 and the prepared GazeFollower environment described in
[the baseline README](../gazefollower_baseline/README.md). Install the optional
GUI dependency there: `python -m pip install pywebview==6.1`.

From the repository root:

```sh
PYTHONPATH=src:. python -m experiments.desktop_demo
```

The macOS native window uses WKWebView. Windows uses Edge WebView2 (runtime
required); choose a camera with `--camera-index 0`. Windows has not been tested.
This is a runnable development application, not a signed/distributable installer.
Model files remain in the existing local GazeFollower support directory. No model
is downloaded at application startup. All UI assets are local; no account needed.

## User flow

1. Application opens with camera off. Start camera explicitly and position yourself.
2. Start fresh calibration: same13 normalized locations and45 accepted258-feature
   samples each, Ridge alpha0.1. The new GUI waits1.5seconds after rendering each
   point; unlike the old controller, it advances immediately after45 samples
   without the extra0.5second completion hold. A15second point timeout fails clearly.
3. Five separate check points each use1second settling and2seconds measurement.
   At least5 valid samples per point are required. Mean error is expressed in
   logical window pixels, not physical display pixels or a success guarantee.
4. Start12 trials with four large shapes; each shape is requested three times in
   a fixed balanced order. After1second cue time, dwell1.2seconds within one region
   selects it. A15second deadline records a timeout. Wrong choices count as wrong.
   No pointer clicking/hovering can select a shape. Preparation/pause/retry are
   operated with mouse/keyboard by the operator; this is not full independent access.
5. Results include all12 trials, correct/incorrect/timeout counts and mean elapsed
   active trial time (includes cue and timeout; excludes explicit pauses).

Calibration/check sampling starts only after the UI acknowledges rendered targets.
Coordinates use the measured drawable viewport. Moving/resizing the window or
changing display scaling invalidates calibration. Focus loss interrupts calibration
or pauses demo. Resume is explicit. Missing gaze, target changes, stale observations
(over300ms), UI heartbeat loss (over800ms), pause and layout changes reset dwell.
A single in-region frame after a long gap cannot finish a previous dwell.

## Privacy and records

Preview JPEGs exist only in memory. No images or video are written or uploaded.
Each fresh calibration/repeated demo creates a UUID directory beneath
`validation/results/desktop-gaze-*` (or `--output`). `session.json` records model
hashes, code provenance, geometry, independent check errors and gaze-only trial
results. Training fit is metadata, never the reported selection success rate.
Incomplete sessions remain aborted/failed. New sessions never overwrite old ones.

The browser-only design mockup is not included as a measurement mode. Automated
synthetic checks never become human gaze results. Existing experiment records
remain unchanged. No head-movement robustness claim is made.

## Verify

```sh
python -m pytest tests/desktop_demo -q
ruff check experiments/desktop_demo src/eye_tracker/intent/region_dwell.py tests/desktop_demo
```

Native macOS window/bridge startup is smoke-tested without opening the camera.
A real participant session is still required to establish this UI's selection
accuracy. Existing calibration experiments do not validate the new UI geometry.
