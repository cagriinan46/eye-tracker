# Phase 1 real session calibration validation

This is Issue #42's controlled validation harness, not the production calibration GUI or a cursor controller. It composes the current production camera, landmark, eye-feature, median-aggregation, independent-linear calibration, and gaze-pipeline components. No algorithm or production contract is changed here.

## Protocol

The target positions and timing come from [Experiment 006](../experiments/006-2d-gaze-mapping/gaze_mapping_experiment.py), and its sample/metric rules come from [its analyzer](../experiments/006-2d-gaze-mapping/analyze_mapping.py). Nine calibration positions form a 3×3 grid with x and y each at 0.20, 0.50, 0.80. The eight separate held-out positions are (0.35, 0.35), (0.65, 0.35), (0.35, 0.65), (0.65, 0.65), (0.50, 0.35), (0.65, 0.50), (0.50, 0.65), and (0.35, 0.50). Each held-out position appears twice in a reproducibly shuffled order (default seed 42), giving 16 validation trials.

Each presentation has 0.8 seconds to settle and 1.2 seconds to sample. At least five usable samples are needed for each presentation; this is an **experiment protocol** rule, not a production calibration requirement. Calibration uses the existing per-axis median aggregator and session-local independent-linear fitter. During held-out trials, each usable frame goes through the existing `process_gaze_frame` pipeline, then the trial's predicted x/y are summarized by per-axis medians. Because the current mapping is independent linear, this gives the same per-axis median prediction as mapping median features; no mapping formula is duplicated. Calibration-fit and held-out metrics are reported separately.

Look at the displayed dot with a comfortable normal viewing distance, natural eye opening and blinking, approximately stable head, no intentional winks, and glasses worn normally if needed. The user sees only targets, not predictions. Press `q` or Esc to cancel; an incomplete run writes no result. The camera index is always selected at runtime because camera ordering varies by machine.

## Setup and run

Use the repository's Python 3.12 `.venv` with its already-configured production Vision dependencies and a local Face Landmarker model. From the repository root, after installing the existing Vision dependency group if needed, run:

```bash
PYTHONPATH=src .venv/bin/python -m validation.real_calibration --camera-index 1 --model .venv/models/face_landmarker.task --output .venv/real-calibration-cagri.json
```

On macOS, OpenCV shows a full-screen window's image centered at its own size, so the default 1200×700 canvas does not cover a larger display. Add `--screen-size WIDTHxHEIGHT` with the display's logical size in points (for example `1512x982`; `osascript -e 'tell application "Finder" to get bounds of window of desktop'` prints it) to draw targets over the whole screen; the run stops if the measured image area differs. Omitting it keeps the historical 1200×700 behavior.

Index `1` selected the built-in camera on Çağrı's development Mac during Phase 0, but is not universal. Fatih must substitute his own available camera index and use a distinct ignored output name such as `.venv/real-calibration-fatih.json`. The output path must be a new path under `.venv/` to keep human-derived numerical results Git-ignored. Omit `--output` to print the completed report without saving it. The script does not download a model or use a network service during the run.

The JSON report includes camera index/resolution, target-window image dimensions, total/successful/failed camera reads and no-face counts (including settling), sampling **attempts** and usable counts per presentation, separate calibration-fit and held-out trial metrics, and the protocol difference below. A sampling attempt may be a failed camera read and must not be equated with Experiment 006's captured-frame count. For each trial it reports actual/predicted normalized coordinates, horizontal and vertical absolute error, normalized 2D Euclidean error, and window-pixel-equivalent error. Each error type has mean, median, and linearly interpolated p95 summaries; signed x/y bias and descriptive ordering of distinct held-out targets are also reported. Pixel-equivalent error uses the measured target-window image area, **not necessarily monitor hardware pixels** or physical viewing angle. There is no predetermined accuracy pass threshold.

## Protocol difference and limitations

Experiment 006 used an **experimental** blink/near-closure gate. The production Vision/Gaze path has no validated blink filter or blendshape signal in its public contracts, so this harness **does not apply that gate**. Missing frames, missing face, and invalid features are not filled in; unavailable estimates are counted. Comparisons with Experiment 006 must mention this difference. The harness also reports total reads and no-face observations including settling, unlike Experiment 006's sampling-frame count.

No raw camera images or video are saved or uploaded. An optional local JSON contains derived target/prediction metrics, which may still be sensitive and must not be committed. One person/session cannot establish general accuracy, accessibility usability, production readiness, cross-session calibration persistence, or multi-user validity. Record Çağrı's result in the PR, then Fatih's independent run separately before merge; do not average the users together.

## Read-only semantic target discovery

From the repository root, using the existing desktop-enabled Python environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
  ~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
  -m validation.semantic_targets
```

This performs one bounded scan of the **currently foreground application's focused
window** and its menu bar. It does not switch applications, open the camera, request
permissions, move the pointer, change focus, or activate any control. macOS access
uses ApplicationServices/CoreFoundation and the Cocoa bridge already installed by
this project's desktop stack; missing Cocoa or accessibility access yields an
unavailable result, without downloading/installing anything.

The JSON contains status, target/role counts, elapsed time and limits. It omits UI
text, URLs, values, coordinates, application/window identifiers and native handles.
Exit 0 means the scan completed (possibly zero targets); exit 2 means unavailable,
incomplete, changed context or unsupported coordinates. No output file is created.

Initial scope: one active display; pressable buttons, checkboxes, radio buttons,
popup buttons and links exposed in the foreground window's AX tree. Closed menu
subtrees are skipped. Menu items, custom-drawn controls, text editing, dragging and
multiple displays are not supported. `ok` means this scoped traversal completed;
it does not assert that all visible UI is represented. A snapshot's identities are
local to that snapshot, not persistent labels for later gaze tracking.

Targets require enabled state, valid window/screen-clipped geometry and native
hit-testing at their proposed center. A hit on a descendant needs bounded ancestry
verification. This proves the center at the instant of the read, not visibility of
the full rectangle or future validity. Snapshots do not authorize actions.

A supported control with finite, nonnegative geometry but zero width or height is
excluded as a target; its descendants are still inspected. This does not make a
zero-area window/menu-bar root valid, and negative, nonfinite or overflowing
geometry still invalidates the scan. The shared target rectangle contract continues
to require positive area.

Default limits: 1024 nodes, depth 64, 128 children per node, a cooperative 0.5-second
scan budget and 50 ms IPC timeouts. Truncation/errors discard **all** candidate
results; increasing coverage requires measured follow-up work, not treating a
partial tree as complete. A native call sequence can exceed the cooperative budget;
this command is not a realtime camera-loop service. Complex applications may
consistently return `incomplete` at these limits.

The node/depth defaults were increased after a native development probe required
561 nodes and more than 20 wrapper levels. Time and child-list budgets remain
unchanged. This is a measured starting configuration, not a guarantee of coverage
or latency in other applications. Initial Cocoa loading also consumes the scan
budget, so a cold run can be incomplete even when a subsequent scan completes.

Portable contracts and fake-backend failure tests run without macOS. Native smoke
checks are opt-in. Pure target resolution is described below; background refresh,
live highlights, snapping and user accuracy evaluation remain
separate work. Existing live traces have no intended-target labels and cannot prove
semantic selection improvement.

## Pure semantic resolution (synthetic development only)

Run without a camera or native UI access:

```sh
PYTHONPATH=src:. python -m validation.semantic_resolution
```

`intent/targeting.py` consumes immutable UI snapshots and logical gaze points.
Callers must supply the current application/window context independently and use
one monotonic clock for snapshot capture, gaze capture and `now`. It returns a
candidate or an explicit abstention, never an action or a modified gaze sample.
A candidate requires bounded rectangle distance, separation from the runner-up,
and consecutive evidence. Nested/overlapping competitors abstain. Invalid or stale
inputs clear evidence immediately. Disabled/non-press targets and targets whose
centers are outside the snapshot screen cannot be selected. Discovery is still
responsible for visibility verification; the pure resolver cannot prove visibility.

All six configuration values are mandatory. The harness uses radius 50 logical
units, separation 10 units, stability 0.1 seconds, maximum sample/update gap 0.08
seconds, snapshot age 0.5 seconds and gaze age 0.05 seconds. These are development
settings, not user-tuned defaults or calibrated probabilities. Age/radius bounds
are inclusive; duplicate or reversed sample/update timestamps reset evidence.

Evidence never crosses snapshot replacement, even if IDs and rectangles look
identical. IDs are snapshot-local. Frequent snapshot refresh may therefore prevent
acquisition; live refresh cadence and stable cross-snapshot identity require later
validation/design. This module is not yet connected to the gaze runtime or overlay.

The JSON report compares unique coordinate containment, nearest eligible target,
and the conservative temporal resolver on independently labeled synthetic traces:
isolated offset, dense boundary, nested overlap and tracking loss. It reports
correct/wrong/abstention counts, switches between emitted target identities
(including across intervening abstentions), and time to first correct candidate
(null if none). Each sample counts once. No activations occur. These hand-authored
scenarios exercise expected tradeoffs; they do not establish improved human
accuracy, application coverage or live performance.
