# Results — coarse zone targeting with COMBO vertical (Issue #81)

Collected **2026-10-08, Europe/Istanbul** after preregistration commit
`e3d5237`. Participant: Fatih only. See [README](README.md).

## Sessions

| | Session A | Session B |
| --- | --- | --- |
| Time (+03:00) | 22:43:35–22:47:00 | 22:47:54–22:51:42, after standing up and reseating |
| Target image area | 1512×982 full screen | 1512×982 full screen |
| Calibration presentations used | 25/25 | 25/25 |
| Trials completed | 34/34 | 34/34 |
| Camera reads / failed / no-face | 5,478 / 0 / 0 | 6,170 / 0 / 15 |
| Local file (Git-ignored) | `.venv/coarse-vertical-fatih-A.json`, 1,054,424 B, SHA-256 `f5a4647a…13024b62` | `.venv/coarse-vertical-fatih-B.json`, 1,271,168 B, SHA-256 `0c8b4102…cccd8bc1` |

Both runs exited 0. Each stderr held six MediaPipe `portable_clearcut_uploader`
"Failed to send" lines (open telemetry question; recorded only).

## Preregistered result: **FAIL for both layouts**

| Layout | A success / wrong / timeout | B success / wrong / timeout | Pass A / B |
| --- | --- | --- | --- |
| 3×3 (18 trials) | **22%** / 61% / 17% | **44%** / 22% / 33% | no / no |
| 4×4 (16 trials) | **6%** / 75% / 19% | **19%** / 31% / 50% | no / no |

Required: success ≥ 80% and wrong ≤ 10% in both sessions. The 3×3 exit
criterion (≥ 80%) is not met. Success by target row (A / B, 3×3): top 50% / 67%,
middle 0% / 50%, bottom 17% / 17%. Wrong selections were mostly one row **above**
the target (row offsets A 3×3: −2, −1×5, 0×4, +1; B 3×3: −1×2, 0×2). Median
time to a successful selection: 3×3 1.54 / 2.66 s, 4×4 2.04 / 4.20 s.

## Exploratory analysis (NOT preregistered)

Errors of the live estimate against the target cell center, frames at least
0.5 s after target onset:

| | A | B |
| --- | --- | --- |
| Median y error (negative = estimate above target) | −0.187 | −0.160 |
| Mean \|y error\| | 0.231 | 0.179 |
| Median x error | +0.243 | +0.101 |
| Mean \|x error\| | 0.272 | 0.177 |

Both axes were biased in the live phase, although the horizontal mapping had
x MAE about 0.05 in Issue #77's open-loop validation. The x bias grew within a
trial (A: +0.13 in the first 0.3 s to +0.23 after 2 s). The y bias was similar
in the first and second halves of each session. A constant offset estimated
from the first six trials and applied offline did not help (A 3×3 3/12 →
3/12 with fewer wrong selections; B 3×3 8/18 → 4/18). That simulation is
open-loop and limited, because frames were only logged until each original
selection.

## Interpretation

- Coarse screen-filling zones with live COMBO and dwell **do not work for
  Fatih** in this setup; even 3×3 reached only 22–44%.
- The failure is not explained by vertical noise alone: a **systematic shift
  of both axes** appeared between calibration and live targeting. Possible
  contributors are posture change after calibration, the brighter grid display
  changing eye opening (COMBO weights eye opening heavily), and **feedback
  capture**, where the user's gaze is drawn to the shaded cell. Frames did not
  record head or eye-opening values, so these cannot be separated from this data.
- Calibration that holds for open-loop dot validation (Issue #77) did not
  transfer to an interactive screen. Any future interaction design must test
  live, closed-loop behavior and not rely on offline validation.

## Rollback status

No production code changed. The rollback point remains main
`9e55af69691d3dc1463aec34bfa5aba83fff4029`. This folder only adds the
experiment and its negative result; keeping or removing it is a human choice.
