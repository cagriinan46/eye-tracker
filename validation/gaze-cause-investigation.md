# Controlled investigation of regional gaze error

User-authorized 2026-10-22; prerequisite issue #129. Purpose: distinguish mapping,
calibration/protocol, posture, lighting/glasses and camera contributions before
changing the deployed estimator. Available hardware: Mac camera and iPhone. Seat
is fixed; display brightness/angle can change. No requirement to remove glasses.

## Existing-session audit (completed)

Explicit input: latest completed session `cagri-gazefollower-20261022-6cfb4e1346bf`.
The analysis read this session only; input hashes were checked before/after.
Calibration features/labels and weights were finite with expected dimensions.
Labels were constant within each of 13 targets. Re-solving the baseline ridge
normal equations reproduced saved predictions within 0.000001 screen pixel.
This checks saved-model arithmetic, not physical camera/display alignment.

Calibration training error was 20.88 pixels (equal target weight). Independent
six-location quality check was 69.53 raw / 68.29 filtered pixels. Grouped
leave-one-target-out calibration errors were:

| Ridge alpha | Mean error, screen pixels |
| --- | ---: |
| 0.1 (baseline) | 111.80 |
| 1 | 114.74 |
| 10 | 132.01 |

Each fold excluded all 45 frames of one location. Random frame splitting would
leak near-duplicate samples. These folds use 12 training locations rather than 13;
they are a diagnostic for spatial generalization, not independent runtime accuracy
or a fair direct comparison to the six-location quality metric. No deployed model
was selected or changed. Stronger regularization in these two tested settings did
not help; that does not rule out other mappings or representation limitations.

The problematic middle-right evaluation location had raw bias approximately
(-45, -114) pixels, with vertical bias changing from -91 to -133 between first
and last thirds. This cannot distinguish head drift, fixation, feature noise or
model response without synchronized observations. All six evaluation locations
were about 179 pixels from their nearest calibration location. That distance is
not itself evidence the calibration layout is incorrect.

The current runner requests 640×480 capture and also resizes inference input to
640×480. Both target drawing and normalized predictions use the same drawable
screen size. This code path showed no simple width/height swap, but does not prove
physical desktop/overlay alignment. A higher-resolution camera alone will not
increase inference resolution in this protocol.

Local audit report: `validation/results/gaze-cause-audit-1792671675105235000/report.json`.
Archived script in the same directory. No existing session was rewritten. Original
held-out records lack features, so alternative models cannot be replayed on them.

## Numerical recording prerequisite

`--diagnostic-features` adds an exclusive `diagnostic-frames.jsonl` sidecar during
calibration and evaluation only. It records capture timestamp, phase, trial/current
calibration index, usability, eligible 258-dimensional features, face rectangle,
eye openness and scalar eye-crop size/intensity/gradient statistics. No image or
full landmark array is serialized. Rejected samples remain rows with null features;
`usable` does not mean the calibration controller accepted that sample after its
settling delay. Calibration indices may include the controller's preparation state.

Evaluation rows include the matching capture timestamp, allowing an exact join to
held-out feature rows, including attempts without predictions. The recorder closes
before quality review/optional repair/live preview and on cancellation/failure.
It stops the experiment at 10,000 rows rather than silently dropping diagnostic
frames; partial records remain local. Original model and feature extraction remain
unchanged. Recording overhead may affect frame rate, so report availability and
wall-clock timing and use matching diagnostic settings for comparisons.

Scalar image statistics are proxies, not validated blur, glare or tracking-quality
scores. Face rectangle changes are not calibrated head-pose angles. Numerical
features/face geometry are participant data: keep ignored/local, do not upload.

## Ordered human protocol (not yet completed)

1. **Reference and generalization:** Mac camera, habitual glasses/posture, current
   brightness and lid angle unchanged. One normal 13-point calibration, followed
   by the existing shuffled 13 trained + 6 unseen location check. Hidden prediction
   feedback. Use `--diagnostic-features --repeat-calibration-targets`, no repair,
   pointer or semantic preview. Inspect repeated versus unseen location errors,
   bias, dispersion, missing samples and crop/face geometry before choosing the
   next capture. Do not claim intended fixation has independent ground truth.
2. **Mapping on identical frames:** fit baseline ridge alpha 0.1 and predeclared
   alpha 1 and 10 on calibration only; replay held-out features from the reference
   capture. Report each location and rejected attempts. Do not tune on evaluation,
   install a winning model or reuse this comparison as untouched final validation.
   If alternatives do not help, investigate feature/calibration quality rather than
   performing an unbounded parameter search.
3. **Repeatability/posture:** with frozen calibration, repeat reference targets in
   neutral posture, then a small comfortable head-position change, then return to
   neutral (A/B/A). No physical restraint, deliberate blinking or forced posture.
   A fixed-calibration repeated-block runner is a follow-up prerequisite; today's
   standard runner must not be misrepresented as supporting it. Compare recovery,
   drift and geometry; natural variation is a system robustness issue, not blame.
4. **Brightness/reflection:** same seat, glasses, lid angle, camera and frozen model;
   reference brightness / comfortable alternative / reference. Record settings
   manually. Do not adjust lid angle simultaneously: that also moves the camera.
   This tests a brightness-related effect, not glasses coating in isolation.
   Glasses removal is optional only if the user can see targets comfortably; an
   uncorrected-vision comparison cannot isolate reflection from visual acuity.
5. **Camera setup:** iPhone near the Mac camera position with secure support, no
   handheld motion. Separate calibration per camera, identical targets, diagnostic
   settings and lighting. Counterbalance Mac/phone order and repeat only if needed.
   Record actual capture/input size and camera pose. Attribute differences to the
   camera/setup combination, not resolution alone; alignment, processing and
   exposure can differ. Connection/device availability still needs verification.

Screen-angle effects, if still necessary, require a separate setup comparison
with recalibration, because both camera and display geometry change. No settings
are changed automatically. Pause for fatigue and preserve unsuccessful records.

## Decision rules and limits

Report per-location mean/p95 radial error, signed bias, centered dispersion,
availability, and missing-attempt-inclusive hit fraction; do not collapse all
causes into one average. Baseline success at a location does not imply semantic
success in dense UI. Fix a reproducible software fault immediately with regression
tests; select a model/camera intervention only after an independent repeat supports
it without unacceptable regional regressions. If evidence is insufficient, label
it unresolved instead of assigning a cause.

Existing logs establish a generalization concern, not whether the user, glasses,
camera or pretrained representation caused it. No new human run or camera
comparison is claimed by this document. Semantic feed availability is a separate
remaining issue and must not be attributed to gaze estimation.

## Offline model replay (issue #131)

Once a diagnostic reference session is completed, run without a camera:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. \
  ~/.virtualenvs/eye-tracker-gazefollower-20261019/bin/python \
  -m validation.gaze_model_replay validation/results/SESSION_DIRECTORY
```

The analyzer accepts one explicitly named, completed, nonsymlink session directly
under `validation/results`. It never scans historical sessions. It fits the three
predeclared ridge settings using `calibration.npz` only, then joins each evaluation
attempt to its diagnostic sample by exact capture timestamp and trial. It checks
distinct bounded plan locations/IDs, repeated locations against their calibration
identities, unseen/calibration separation, and baseline reproduction against saved weights and recorded raw
predictions (0.001 pixel tolerance). Missing, duplicate or mismatched pairs reject
the report instead of silently changing the evaluated sample set.

Rejected attempts remain in availability and 30-pixel hit-rate denominators. Reports
contain per-trial raw/unclipped error, p95, bias and centered dispersion, and separate
summaries for trained-location repeats and unseen locations. Each group needs its
expected number of trials and at least five usable samples per trial to report an
overall mean. No filter is replayed and no combined trained/unseen mean is used.

Input hashes are rechecked after analysis; a new UUID report directory is created
only after validation. No weights or input data are overwritten, no camera/UI is
opened, and no winning model is automatically selected or installed. This compares
three regularization settings of the same mapping family, not three distinct gaze
estimation architectures. A model comparison used for development still needs a
fresh independent validation before adopting a change.

The earlier session audited above cannot be replayed: it predates the diagnostic
feature records. Tool verification uses synthetic data only until the user is ready
for a new capture. Human tests remain paused at the user's explicit request.
