# Coarse gaze-target acquisition (protocol v1)

This isolated Phase 1 interaction experiment asks whether one participant can acquire coarse screen targets using the **unchanged production gaze estimate**. It measures acquisition success and latency, raw spatial error, prediction availability, repeatability, and target-position dependence. It does not move the operating-system pointer or perform clicks. The completed captures and analysis are documented in [RESULTS.md](RESULTS.md).

## Production path and calibration

Each session starts with the ordinary nine calibration centers at x and y in `{0.2, 0.5, 0.8}`, in the existing row-major order. The runner uses `collect_features_once`, `collect_presentation` (0.8 s settling, 1.2 s sampling, at least five usable samples), and `fit_session_calibration`. These use production binocular horizontal and vertical features and `IndependentLinearMapping`. Targeting then calls `eye_tracker.app.gaze_pipeline.process_gaze_frame` for every prediction. The pipeline reads one camera frame, extracts landmarks and production binocular features, and calls `estimate_gaze` with that session's fitted mapping. It does not smooth or clip. A sidecar reads the already-used frame and landmark observation to record features; it does not read another frame or feed anything back to the estimator.

## Fixed targeting design

| Item | Predeclared value |
| --- | --- |
| Protocol | `coarse_gaze_targeting`, version `1` |
| Participant | `cagri` |
| Calibration | 9 standard presentations |
| Target centers | All nine x/y combinations of `0.2`, `0.5`, `0.8` |
| Diagnostic schedule | 3 blocks, every target once per block: 27 trials |
| Order | Python `random.Random(20261006).sample` of the nine centers, cyclically offset by three positions in successive blocks |
| Acceptance rectangle | Centered on target, normalized half-width `0.14`, half-height `0.14`, inclusive edges |
| Acquisition | Raw prediction continuously inside for at least `0.300` s, timed by monotonic clock |
| Timeout | `4.0` s after target onset; automatic continuation |
| Feedback | Fixed `0.5` s, excluded from acquisition time |

An unavailable prediction or an observed prediction outside the rectangle resets active dwell. A new inside sample starts a new interval. The exact 4.0 s boundary can succeed if the required dwell has been observed by then. This is **observed-sample continuity**: time between consecutive inside samples is counted as inside until another observation says otherwise. Frame gaps therefore limit precision; availability and interruptions are recorded. No unobserved FPS is assumed. A prediction outside `[0, 1]` remains unchanged in data and metrics. Its on-screen cursor marker is omitted because it is outside the visible canvas.

## Human procedure and UI

1. A **READY** screen appears before timing or calibration begins. Press **SPACE** to begin. Use normal relaxed eye opening, sit comfortably, keep the head reasonably steady, and allow natural blinking.
2. Look at each calibration dot until it advances. Calibration uses the standard 0.8 s settling and 1.2 s sampling windows.
3. A second **TARGETING TEST** ready screen appears. Press **SPACE** when ready.
4. For each of 27 trials, a highlighted rectangle and target dot appear. Look **directly at the target**. Do **not** chase the moving gaze-cursor dot with your eyes. The cursor is feedback only. Do not intentionally narrow or widen the eyes, and do not intentionally move your head to steer the cursor. Keep a normal comfortable sitting position; natural blinking is allowed.
5. When raw gaze remains in the rectangle for 300 ms, the trial ends as acquired. Otherwise it ends as a timeout after 4 s. A brief fixed feedback screen appears, then the next target starts automatically. Press `q` or **Esc** at any point to abort.

The moving gaze cursor is an experiment-owned on-screen marker. The real OS pointer is untouched. During targeting, the screen contains only the target region/dot and the gaze marker; it shows no predictions or debug text. Feedback time is not part of acquisition latency.

## Saved data and later analysis

Successful captures are numerical JSON under ignored `.venv/`; no raw frames or video are saved. The runner refuses to overwrite existing output. Aborted or technically incomplete attempts get a separate `*.invalid.json` marker and are not treated as completed sessions. A technically valid session has one successful nine-point calibration and all 27 planned trials in order. **Targeting timeouts are results, not invalidation reasons.**

Metadata includes participant/session, protocol identity, order seed, calibration/target geometry, acceptance dimensions, dwell/timeout/feedback durations, camera index and observed resolution, window size, mapping coefficients, camera read failures, and no-face counts. Every targeting sample records trial/block/target identity, monotonic observation time, camera-frame timestamp when available, frame availability, usable/unavailable status and reason, raw predicted x/y, production horizontal/vertical features when available, raw inside-target status, and active dwell duration. The record contains no condition labels, alternative features, or clipped predictions.

Each trial saves success/timeout, first entry latency, successful-dwell entry latency, confirmed acquisition latency, entries/re-entries, dwell interruptions, longest observed dwell, usable/unavailable counts and fraction, median absolute x/y error, median and p95 Euclidean error, and final usable prediction. Acquisition latency is target onset to completion of the first successful dwell. It is **not** camera-to-photon latency. Errors use all usable raw predictions, including predictions outside the visible area.

`analysis.py` verifies the protocol and exact scheduled cells. It computes success/timeout rates, median and p95 successful acquisition time, spatial error and availability over all raw samples, dwell/re-entry counts, and separate summaries by row, column, and target. Repeated-target variation compares each target's median raw prediction across its three blocks. No success threshold was declared in the protocol; [RESULTS.md](RESULTS.md) reports the measured tradeoffs and bounded engineering decision.

## Preregistered capture commands (historical)

These were the commands for separate fresh sessions from the repository root. All five captures now exist; the runner refuses to overwrite them.

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.coarse_gaze_targeting_validation.run --participant cagri --session live-1 --camera-index 1 --output .venv/coarse-gaze-cagri-live-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.coarse_gaze_targeting_validation.run --participant cagri --session live-2 --camera-index 1 --output .venv/coarse-gaze-cagri-live-2.json
PYTHONPATH=src:. .venv/bin/python -m experiments.coarse_gaze_targeting_validation.run --participant cagri --session live-3 --camera-index 1 --output .venv/coarse-gaze-cagri-live-3.json
PYTHONPATH=src:. .venv/bin/python -m experiments.coarse_gaze_targeting_validation.run --participant cagri --session live-4 --camera-index 1 --output .venv/coarse-gaze-cagri-live-4.json
PYTHONPATH=src:. .venv/bin/python -m experiments.coarse_gaze_targeting_validation.run --participant cagri --session live-5 --camera-index 1 --output .venv/coarse-gaze-cagri-live-5.json
```

For the current collection, `live-1` used a different physical setup and `live-2` was exploratory with deliberate eye-opening changes. Preserve both captures without treating them as valid natural-use sessions. `live-3` is the first valid natural-use session; use `live-4` and `live-5` as the two replacement sessions. The protocol and schedule remain unchanged.

Each session has 9 calibration presentations and 27 trials. Calibration takes about 18 s; targeting takes about 22–122 s plus capture/render overhead, feedback included. Allow roughly **1–3 minutes per session**, excluding time at the two ready screens. The session may take longer on a slow machine.
