# Desktop target-selection demo

Local Python + pywebview presentation prototype, issues #136 and #139.
UniGaze is the default model; MGazeNet remains an explicit rollback option.
See the UniGaze setup and calibration details below. No failed head correction,
old SVR prediction, OS clicks or hardware movement is deployed.

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
2. For MGaze, start fresh calibration: same13 normalized locations and45 accepted258-feature
   samples each, Ridge alpha0.1. The new GUI waits1.5seconds after rendering each
   point; unlike the old controller, it advances immediately after45 samples
   without the extra0.5second completion hold. A15second point timeout fails clearly.
   UniGaze uses its measured13x20 timed protocol, described below.
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

Native macOS checks cover cold bridge startup, persistent error dismissal,
calibration cancellation, home navigation and pause/resume using synthetic state
(no participant accuracy claim). The actual camera was also opened, stopped,
reopened and closed through the native UI; the worker released its resources
before process exit. Camera frames were not saved. Windows remains unverified.

The camera button supports cancel/stop/restart. Stopping the camera invalidates
the eye setup; returning home while it stays open preserves the setup. Errors
remain visible until dismissed or a user action succeeds.
A real participant session is still required to establish this UI's selection
accuracy. Existing calibration experiments do not validate the new UI geometry.

## UniGaze default (issue #139)

The default model is now **UniGaze**. The existing MGaze adapter is preserved and
can be selected explicitly; there is no silent automatic fallback:

```sh
PYTHONPATH=src:. python -m experiments.desktop_demo
PYTHONPATH=src:. python -m experiments.desktop_demo --model mgaze
```

On the prepared development Mac, run these with
`~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python`. That environment
owns pywebview; it does not need torch. UniGaze runs in the separate prepared
`validation/results/unigaze-preflight-kit-20261029/venv/bin/python` environment.
Each launch starts uncalibrated. Close and restart with `--model mgaze` to roll
back; a UniGaze calibration is never reused for MGaze.

The tracked `experiments/unigaze` package contains the promoted research adapter,
not imports of ignored research Python scripts. Prepared model assets remain
local and are not downloaded at startup. Configure these existing paths if moved:

| Variable | Meaning |
| --- | --- |
| `EYE_TRACKER_UNIGAZE_HOME` | Prepared kit root containing `support/upstream`, `support/unigaze_b16_joint.safetensors`, `support/torch/hub/checkpoints` |
| `EYE_TRACKER_UNIGAZE_PYTHON` | Python with the tested UniGaze dependencies; defaults to kit `venv/bin/python` |
| `EYE_TRACKER_CAMERA_INTRINSICS` | Accepted measured-intrinsics completion JSON for the selected camera at native640x480 |
| `EYE_TRACKER_MGAZE_PYTHON` | Existing baseline worker Python; its support files retain the baseline loader's documented location |

The defaults are this development machine's measured FaceTime camera and local
assets. Do not apply those intrinsics to another camera. UniGaze rejects frames
not native640x480 instead of resizing against mismatched calibration. Upstream
source hashes and checkpoint hashes are verified. Missing assets fail visibly.
The dependency set already prepared/tested is torch2.7.1, torchvision0.22.1,
timm0.3.2, safetensors0.5.3, face-alignment1.5.0, numpy2.2.6, OpenCV4.11.0.86.
This is a local integration, not an installer or portable dependency lock.

UniGaze uses the research13-target layout and13x20 training samples, selected
uniformly over each6second window after1.5seconds settling. Expected calibration
is about98seconds. Inadequate valid samples fail explicitly. Standardized two-angle
Ridge alpha0.1 and HeuristicFilter look_ahead3 match the measured implementation.
MGaze's13x45 behavior is unchanged. The five independent check points and12
selection trials remain; reports contain filtered check error and separate raw
error/sample count for UniGaze. Training fit is not validation accuracy.

A baseline worker is still used inside the UniGaze extractor for the measured
face-matching and eligibility gates. This preserves the validated pipeline, and
costs processing time; it does not choose MGaze output. Same-frame comparison
experiments remain intact. Source/model/filter/camera provenance is recorded.

Keep a comfortable posture matching calibration; recalibrate after repositioning.
UniGaze's measured lateral-translation failure is unresolved. Invalid or stale
capture data resets selection; existing300ms freshness and800ms UI-heartbeat
limits are not relaxed to hide slow inference. Filter history age is logged
separately and is not end-to-end latency. Pause/focus loss clears filter history.

The UniGaze worker currently uses macOS/POSIX inherited sockets. Other operating
systems fail explicitly before starting this worker; MGaze remains selectable.
Windows remains a project target, but UniGaze transport/runtime verification is
pending. No Windows success or new human selection accuracy is claimed.

Python network connects and image/video writes are disabled inside the isolated
UniGaze inference process. Preview JPEGs travel only through local IPC to the
native UI. Native MediaPipe has previously logged failed Clearcut upload attempts;
its payload is unknown, so the Python guard is not a claim of native network
isolation. No camera was opened during this integration's automated checks.

## Desktop appearance and navigation (issue #141)

The preparation shell has Home, Calibration, Gaze practice, Settings and Help
pages. Navigation does not start the camera. Calibration and live trials use the
full viewport; their targets do not animate. The shell currently requires pointer,
keyboard or helper input; this is not hands-free navigation of every menu.

Settings offers Lavender, Sunflower and Sage color themes and reduced motion.
Only appearance preferences persist at `~/.eye-tracker/desktop-preferences.json`;
no calibration is restored from this file. System reduced-motion preferences are
also respected. A settings write failure leaves the previous appearance and
active calibration intact. Themes do not change the calibration stimulus colors,
model, sample protocol or dwell duration.

October 31 validation: native macOS UI and bridge checks with camera off,
including all five pages, persistent themes, reduced motion, minimum 960×640
window, and synthetic loading/error/ready/practice transitions. Synthetic state
checks are not human gaze-accuracy measurements. Local evidence and screenshots:
`validation/results/desktop-interface-20261031/`. Actual camera/model behavior
continues to use the existing UniGaze default and explicit MGaze fallback.
