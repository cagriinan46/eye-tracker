# Intentional gaze targeting (protocol v2, revised precollection flow)

This Phase 1 interaction study asks whether one participant can deliberately acquire smaller screen targets with the **unchanged production gaze estimator**, after a separate fixed-duration fixation cue. The earlier [coarse targeting v1 study](../coarse_gaze_targeting_validation/RESULTS.md) found coarse acquisition feasible, but its 0.28 × 0.28 regions and 300 ms dwell were permissive. This is not a vertical-feature experiment; it does not move the operating-system pointer or click.

**Pilot disposition:** Earlier v2 pilot attempts used the accuracy-gated reset design. They are protocol-invalid for this revised design and must not be used as final evidence. Two incomplete local attempt markers were preserved as `.venv/intentional-gaze-cagri-live-{1,2}-reset-gated-pilot.invalid.json`; at the time of that revision, no completed capture was found at the standard output paths. The revised cue flow below was fixed before the valid sessions were collected. The protocol identity remains `intentional_gaze_targeting`, version `2`; the analyzer requires the revised cue metadata and a target attempt for every trial, so it rejects old reset-gated captures.

## Production path and fixed design

Each `cagri` session (`live-1`, `live-2`, `live-3`) starts with a fresh standard nine-point calibration at x/y `{0.2, 0.5, 0.8}`. The runner reuses `collect_features_once`, `collect_presentation` (0.8 s settling, 1.2 s sampling, at least five usable samples), and `fit_session_calibration` with production binocular horizontal/vertical features and `IndependentLinearMapping`. Targeting calls `eye_tracker.app.gaze_pipeline.process_gaze_frame`. The logging sidecar reads the frame and observation already processed by that pipeline. No smoothing, feature correction, ML, or clipping enters acquisition or error metrics.

The same nine x/y combinations `{0.2, 0.5, 0.8}` are target centers. There are three blocks and **27 target trials**, each target once per block. Target order is exactly v1's `random.Random(20261006).sample` permutation, cyclically offset three positions between blocks; the code calls v1's `schedule()` directly.

| Parameter | Predeclared value |
| --- | --- |
| Protocol | `intentional_gaze_targeting`, version `2` |
| Target rectangle | Normalized half-width `0.10`, half-height `0.10`, inclusive raw-prediction boundary |
| Target acquisition | Continuous raw in-region gaze for `1.0` s; timeout `5.0` s |
| Fixation cue | Separate dot for fixed `0.75` s; no acquisition condition |
| Feedback | Fixed `0.5` s after target success or timeout |

For every non-center target, the cue is `(1 - target_x, 1 - target_y)`. For center `(0.5, 0.5)`, the cue is `(0.2, 0.2)`. The cue point is fixed by target identity, never by observed performance. The full target region is 0.20 × 0.20; adjacent target centers are 0.30 apart, leaving a 0.10 normalized gap. There is **no cue dwell, cue timeout, success/failure classification, or gaze-dependent target skip**.

Target dwell uses monotonic observation timestamps. An outside or unavailable prediction interrupts and resets active dwell. This is **observed-sample continuity**: time between inside observations counts until an observation says otherwise. The exact timeout boundary can succeed if required dwell has been observed by then. Raw predictions outside the visible `[0, 1]` range remain in logs and metrics; only the on-screen cursor marker is omitted.

## Human procedure and screen flow

1. On **READY**, use natural relaxed eye opening and normal comfortable computer-use posture. Keep the physical setup consistent after calibration. Natural blinking is allowed. Press **SPACE** to begin calibration; timing begins after this press.
2. Look at each of the nine calibration dots until it advances.
3. On **INTENTIONAL TARGETING TEST**, press **SPACE** to begin targeting.
4. Every trial starts with a separate **fixation cue dot only**. Look at it while it is shown for 0.75 s. Gaze during this cue is **not** judged and cannot prevent the target from appearing.
5. The cue disappears and the target dot, highlighted region, and live gaze cursor appear immediately. **Move gaze directly to the target.** Do not chase the moving cursor, deliberately narrow or widen the eyes, or steer with the head. Natural blinking is allowed. A failed trial is a valid result; do not try to game the experiment.
6. The target succeeds after 1.0 s continuous raw in-region gaze, or times out at 5.0 s. Brief feedback appears, then the next cue begins automatically. Press `q` or **Esc** to abort at any time.

Target-acquisition latency starts at **target onset**, after the cue. It is user/estimator interaction latency, not camera-to-photon latency. The cursor is an experiment-owned visual marker; no OS pointer movement or clicking occurs.

## Saved data and analysis

Completed numerical JSON reports are saved under ignored `.venv/`; no images or video are saved. The runner refuses to overwrite an existing output or invalid-run marker. Aborted or technically incomplete runs get a separate `*.invalid.json` marker. A technically complete session has successful nine-point calibration and all 27 planned targets presented, regardless of target timeouts. Target timeouts are results, not invalidation reasons.

Metadata includes participant/session, protocol identity, target-order seed, target centers and geometry, fixed cue duration/assignment, calibration timing/minimum usable count, camera index/resolution, mapping coefficients, feedback duration, camera failures, and no-face counts. Each trial records target and cue coordinates, cue onset/end, target onset/end, and target summary. Target samples record trial identity, monotonic time, frame timestamp/availability, usable/unavailable status and reason, raw prediction, production features when available, inside-target status, and active dwell. Cue gaze is not sampled or classified.

`analysis.py` rejects incompatible metadata, old reset-gated pilot captures, and missing/reordered cells. It reports target success/timeout; first-entry, successful-entry, and confirmed-acquisition latency; raw x/y/Euclidean error and p95 Euclidean error; re-entries, interruptions, longest dwell, availability, repeated same-target variation; and row, column, individual-target, camera-failure, and no-face summaries. Every planned target is attempted. No reset success rate or reset acquisition latency exists.

For pooled target success across valid sessions, the predeclared *engineering interpretation bands* are: at least 80% = promising stricter intentional selection; 60% to below 80% = partially viable with significant position-specific limitations; below 60% = current production gaze inadequate for this stricter geometry. These are not production, clinical, accessibility, or cross-user acceptance criteria. Two valid cue-based sessions were collected; the bounded engineering decision and early-stop rationale are in [RESULTS.md](RESULTS.md).

## Preregistered capture commands (historical)

These were the planned commands. **Do not run live-3 for this bounded decision:** the engineering interpretation band was locked after the two valid sessions. Camera index `1` matched the local setup. The runner refuses to overwrite existing output or invalid-run markers. The two incomplete reset-gated attempt markers remain preserved under separate names and were not used in final metrics.

```bash
PYTHONPATH=src:. .venv/bin/python -m experiments.intentional_gaze_targeting.run --participant cagri --session live-1 --camera-index 1 --output .venv/intentional-gaze-cagri-live-1.json
PYTHONPATH=src:. .venv/bin/python -m experiments.intentional_gaze_targeting.run --participant cagri --session live-2 --camera-index 1 --output .venv/intentional-gaze-cagri-live-2.json
PYTHONPATH=src:. .venv/bin/python -m experiments.intentional_gaze_targeting.run --participant cagri --session live-3 --camera-index 1 --output .venv/intentional-gaze-cagri-live-3.json
```

Nine calibration presentations take about 18 s plus processing. The 27 trial cues take about 20 s; target/feedback time ranges from about 41 s at minimum dwell to about 149 s if every target times out. Allow roughly **1.5–4+ minutes** per session including capture/render overhead, excluding the two READY screens.
