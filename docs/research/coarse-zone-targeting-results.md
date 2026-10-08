# Coarse zone targeting with COMBO vertical — results (Issue #81)

Date: **2026-10-08, Europe/Istanbul**. Participant: Fatih only. Status:
**negative result.** By Fatih's decision the experiment code was **not merged**
because it did not work. Only this record enters main. The code stays reviewable
at closed [PR #82](https://github.com/cagriinan46/eye-tracker/pull/82), commit
[`62dc8f9`](https://github.com/cagriinan46/eye-tracker/tree/62dc8f9/experiments/coarse_vertical_targeting),
with the preregistered protocol in its README (preregistration commit `e3d5237`).
No production code changed; main stayed at rollback point `9e55af6`.

## Question

After [Issue #77](../../experiments/vertical_signal_comparison/RESULTS.md) found
no vertical signal good enough for fine pointing, and
[Issue #79](appearance-gaze-options.md) proposed designing around coarse
vertical accuracy: **can Fatih reliably select screen-filling zones on 3×3
and 4×4 grids with the best signal, live COMBO, while making few wrong
selections?** The accepted exit criteria include "coarse 3×3 targeting ≥ 80%".

## Protocol (frozen before data)

- Full screen 1512×982, camera index 0, `.venv-fatih`.
- Shuffled 5×5 calibration (0.1–0.9). Live y from COMBO (production vertical,
  eye opening, blendshape `lookDown − lookUp`, head pitch). Live x from the
  production horizontal feature. Issue #77 common-frame and blink rules.
- 34 trials per session: 3×3 (each cell twice) and 4×4 (each cell once). A ran
  3×3 first, B ran 4×4 first.
- Each trial: a 0.75 s cue in the mirrored cell, then the target cell outlined
  with the currently estimated cell shaded as feedback. The estimate is the
  median of the last 7 valid frames within 0.5 s. **1.0 s** on any cell selects
  it (another cell counts as a wrong selection), and the trial times out after
  **5.0 s**.
- Pass per layout and session: success ≥ 80% and wrong ≤ 10%. A layout passes
  only if both sessions pass.

## Sessions

| | Session A | Session B |
| --- | --- | --- |
| Time (+03:00) | 22:43:35–22:47:00 | 22:47:54–22:51:42, after reseating |
| Calibration used / trials | 25/25 / 34/34 | 25/25 / 34/34 |
| Camera reads / failed / no-face | 5,478 / 0 / 0 | 6,170 / 0 / 15 |
| Local raw file (Git-ignored, never uploaded) | `.venv/coarse-vertical-fatih-A.json`, SHA-256 `f5a4647a…13024b62` | `.venv/coarse-vertical-fatih-B.json`, SHA-256 `0c8b4102…cccd8bc1` |

Each run logged six MediaPipe `portable_clearcut_uploader` "Failed to send"
lines (open telemetry question; recorded only).

## Preregistered result: **FAIL for both layouts**

| Layout | A success / wrong / timeout | B success / wrong / timeout |
| --- | --- | --- |
| 3×3 (18 trials) | 22% / 61% / 17% | 44% / 22% / 33% |
| 4×4 (16 trials) | 6% / 75% / 19% | 19% / 31% / 50% |

Wrong selections were mostly one row **above** the target. 3×3 success by row
(A / B): top 50% / 67%, middle 0% / 50%, bottom 17% / 17%.

## Exploratory analysis (NOT preregistered)

| Live estimate vs target-cell center (frames ≥ 0.5 s after onset) | A | B |
| --- | --- | --- |
| Median y error (negative = above target) | −0.187 | −0.160 |
| Median x error | +0.243 | +0.101 |

- At target level, the horizontal direction was mostly correct: median
  estimated x rose with target column, e.g. B 3×3 0.43 → 0.55 → 0.82. The one
  exception was A 4×4, where the rightmost column fell to 0.47. The live x
  mapping slope (−11.1 / −8.0) had the same sign as Issue #77 (−11.3 / −10.9),
  where horizontal ordering was 96/96. **The code has no left-right mirror
  error**, and the camera image is never flipped.
- Estimates were compressed and shifted right, and the x bias grew within a
  trial (A: +0.13 in the first 0.3 s, +0.23 after 2 s).
- A constant offset estimated from the first six trials and applied offline did
  not help (open-loop simulation, limited because frames were only logged
  until each original selection).

## Participant observation

Fatih reported that during the test, **moving his eyes right made the
feedback go left and vice versa, "as if a mirror mode were on".** The code and
target-level data show no mirror inversion. One possible explanation, not
proven here: the features measure **eye-in-head** position, not gaze on the
screen. If the head turns toward a target or toward the shaded cell while the
eyes stay on the target, the eyes rotate the other way inside the head, and
the estimate moves opposite to the head turn. Head angles were not logged
during trials, so this cannot be confirmed from this data.

## Interpretation and lessons

- Coarse zone selection with live COMBO **failed for Fatih**; even 3×3 reached
  only 22–44%.
- Calibration that works for open-loop dot validation (Issue #77) did not
  transfer to interactive use. Both axes shifted systematically between
  calibration and live targeting. Candidate causes are head rotation (eye-in-
  head features without head compensation), posture change, the brighter grid
  display changing eye opening, and feedback capture.
- Any future live test should log head pose and eye opening per frame, and
  should compare blocks with and without feedback.
- The head-rotation hypothesis also points toward head-assisted pointing,
  or head-pose compensation, as the next design direction for the team to
  discuss.
