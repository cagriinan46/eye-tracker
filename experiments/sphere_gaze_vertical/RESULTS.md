# 3D eye-sphere gaze feature on the built-in camera — results (Issue #92)

Date: **2026-10-13, Europe/Istanbul**. Participant: Fatih only. Result:
**negative**; the experiment code is not merged (Fatih's rule for failed
experiments) and stays on branch `experiment/92-sphere-gaze-vertical`
(preregistration commit `ae48969`, pushed before session A).

## What was tested

A port of the gaze method in Jason Orlosky's MIT-licensed webcam prototype
([JEOresearch/EyeTracker](https://github.com/JEOresearch/EyeTracker),
`Webcam3DTracker/MonitorTracking.py`; video "3D Eye Tracking on a Webcam"),
which reports no measured accuracy:

- head frame = PCA axes of 24 nose landmarks (x·w, y·h, z·w), right-handed,
  signs aligned to the first frame; scale = mean pairwise nose distance;
- a virtual eyeball centre per eye locked in that frame one radius behind the
  iris while looking at screen centre (first `K-center` checkpoint, before
  calibration); radius 20 px × frame width / 640 (our adaptation of the
  prototype's 20 px to 1920×1080);
- gaze = averaged unit vector eyeball centre → 3D iris (468/473) in camera
  space; `sphere_pitch` = atan2(−d_y, −d_z) in degrees.

Frozen Issue #77 protocol and thresholds (y MAE ≤ 0.08, ordering ≥ 19/21,
|bias| ≤ 0.05), Fatih, built-in camera (index 0), 1512×982 full screen, two
sessions. Candidates: unchanged #77 R0/OPEN/OPEN_Q/BLEND/COMBO plus `SPHERE`
(sphere pitch alone) and `SPHERE_COMBO` (COMBO with the production vertical
replaced by sphere pitch), all on identical common frames. Preregistered rule:
primary SPHERE ≤ R0 − 0.02; secondary SPHERE_COMBO ≤ COMBO − 0.01; "solved" if
either passes both sessions.

## Smoke test (no data kept)

29.7 fps at 1920×1080. Sphere pitch median, two cycles: centre −0.04° / −0.24°,
top +1.31° / +2.52°, bottom −3.43° / −3.69°. The feature responds in the
expected direction with a ≈5–6° top–bottom range.

## Sessions

| Session | Time (+03:00) | Rows / common frames | Cal / val | Lock (presentation, frames) | Detector median ms | Local file (Git-ignored) SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| A | 14:37:44–14:39:28 | 1,775 / 1,768 | 25/25, 16/16 | 2, 33 | 7.15 | `ef924221…8b1d` |
| B | 14:40:01–14:41:45 | 1,779 / 1,757 | 25/25, 16/16 | 2, 35 | 7.04 | `ec2d7f46…c6d5` |

Files `validation/results/sphere-gaze-fatih-{A,B}.json` (3,346,654 /
3,355,877 B; full SHA-256 in WORK_LOG). Both exited 0, 50/50 presentations,
no missing faces, eye-sphere numbers present in every usable frame; both
**valid**.

## Results (validation, 16 targets)

y MAE / signed bias / ordering of 96 pairs:

| Candidate | A | B | Mean y MAE |
| --- | --- | --- | --- |
| COMBO | 0.081 / −0.061 / 93 | 0.164 / −0.163 / 94 | 0.123 |
| R0 (production feature) | **0.059 / +0.008 / 94 (PASS)** | 0.198 / −0.198 / 92 | 0.129 |
| SPHERE_COMBO | 0.142 / −0.132 / 93 | 0.137 / −0.131 / 94 | 0.139 |
| **SPHERE** | 0.182 / +0.182 / 92 | 0.098 / +0.018 / 94 | **0.140** |
| BLEND | 0.227 / +0.227 / 93 | 0.137 / +0.137 / 96 | 0.182 |
| OPEN / OPEN_Q | 0.232 / 0.240 | 0.202 / 0.218 | 0.217 / 0.229 |

Calibration R²: SPHERE **0.66 / 0.29**, R0 0.91 / 0.85, COMBO 0.96 / 0.91,
SPHERE_COMBO 0.96 / 0.93.

| Preregistered test | Values | Result |
| --- | --- | --- |
| Primary: SPHERE better than R0 | 0.140 vs 0.129 − 0.02 | **NO** (SPHERE is worse) |
| Secondary: SPHERE_COMBO better than COMBO | 0.139 vs 0.123 − 0.01 | **NO** |
| Vertical solved by sphere | no sphere candidate passed any session | **NO** |

No candidate passed both sessions; only R0 passed session A.

## Descriptive and exploratory

- The prototype's own mapping (±5° to the screen edges, one-point centre lock):
  y MAE 0.261 (A) / 0.076 (B). Its B value is below 0.08 but bias −0.049 and
  the A value fails badly; with one session each way it is not evidence.
- Validation-row medians of sphere pitch (rows 0.2 / 0.4 / 0.6 / 0.8):
  A +0.65 / −1.38 / −3.61 / −5.18°; B +2.66 / +1.01 / −0.17 / −2.15°. Rows stay
  ordered within each session, but the whole curve shifted by ≈2–3° between
  sessions and between calibration and validation (low calibration R²), so
  the 3D vector is not more stable than the 2D production feature.
- x from sphere yaw: x MAE 0.047 / 0.072, ordering 96/96 (production x
  0.035 / 0.026).
- Session B had a large within-session shift for every method: checkpoint
  predictions at screen centre (R0) were 0.46 / 0.11 / 0.33 in blocks 1 / 2 / 3,
  and COMBO 0.51 / 0.15 / 0.39, i.e. calibration and validation saw different
  states. Today's built-in COMBO (0.123 mean) was worse than in #88 (0.103) and
  #90 (0.083), so the sessions were harder than usual. All candidates were
  scored on the same frames, so the comparison stands, but absolute values are
  pessimistic.

## Interpretation

On Fatih's built-in camera, the prototype's 3D eye-sphere signal **did not
improve vertical gaze** and was less stable than the production iris-to-corner
feature. MediaPipe's per-landmark z and a nose-PCA frame add noise that the
geometric head compensation does not repay here. This tests our port under
our protocol, not the prototype's unmeasured demo; it does not rule out other
3D eye models. Combined with Issues #88/#90, the more promising direction
remains a second (low) camera with prediction fusion. One person, one day,
two ~100 s sessions.
