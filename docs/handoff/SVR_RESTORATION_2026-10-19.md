# Single-camera SVR restoration

The live diagnostic demo is now versioned as `live_svr_demo.py` with its macOS
window helper `native_window_geometry.py`. The prior external support copy
was restored too, but future changes should use the repository copy.

- MacBook camera only; gaze plus auxiliary head pose, not head-only control.
- 25 calibration targets from the existing seed-77 calibration schedule.
  Each target has 0.8 s settling and 1.2 s sampling; at least 20 targets
  with at least 5 usable frames each are required.
- Blink/invalid frames excluded before collection; per-target medians of
  horizontal, vertical, pitch, yaw, roll (angles in degrees).
- Two RBF SVRs: C=1000, gamma=0.1, epsilon=1.0. StandardScaler on inputs
  only; outputs are drawable-area pixels. EMA alpha=0.50.
- `--control-pointer` enables actual movement and 30-pixel / 1.5-second
  dwell left click. Leaving the circle rearms. Tracking loss restarts the timer.
- Camera preview Enter, target-screen Enter, and live-stage Enter remain separate.
  Escape stops. PyAutoGUI corner failsafe is disabled per the user's request.
- Session directories are unique under ignored `validation/results/`.
  Raw predictions and smoothed output are recorded separately; no images saved.
- Human gaze accuracy is not established by synthetic tests. No new human
  experiment or historical Stage B2 evaluation was run for this restoration.
- Historical 9-point/linear session data remain untouched. This is source
  restoration, not a claim that an earlier committed binary was recovered.
- Desktop adapter has macOS/Windows code; this camera/window demo is macOS-specific.

## Run from the repository root

Use the existing dedicated Python environment, with vision, gaze and desktop
dependencies installed. Do not use or alter the archival `.venv` or `.venv-fatih`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src:$PWD" /Users/cagri/.virtualenvs/eye-tracker-cagri-20261018/bin/python live_svr_demo.py --control-pointer
```

The model defaults to `<active Python prefix>/models/face_landmarker.task`;
set `EYE_TRACKER_MODEL` to override. macOS camera/accessibility permissions
are required for the live session. Tests use synthetic inputs and fake pointer
backends, with no camera capture or real clicks.
