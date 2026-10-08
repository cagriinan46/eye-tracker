# Results — vertical signal comparison (Issue #77)

Collected **2026-10-08, Europe/Istanbul** after preregistration commit
`e4cd8dc`. Participant: Fatih only; not pooled. See [README](README.md).

## Sessions

| | Session A | Session B |
| --- | --- | --- |
| Time (+03:00) | 21:53:15–21:55:00 | 21:56:01–21:57:46, after standing up and reseating |
| Target image area | 1512×982 full screen | 1512×982 full screen |
| Camera reads / failed / no-face | 3,008 / 0 / 0 | 3,011 / 0 / 0 |
| Usable / common (blink-excluded) frames | 1,790 / 1,786 | 1,781 / 1,781 |
| Presentations available | 25/25 calibration, 16/16 validation | 25/25, 16/16 |
| Detector call median / p95 | 5.63 / 6.49 ms | 5.73 / 6.55 ms |
| Local file (Git-ignored) | `.venv/vertical-signals-fatih-A.json`, 2,162,026 B, SHA-256 `e3b0127d…ace25a` | `.venv/vertical-signals-fatih-B.json`, 2,150,241 B, SHA-256 `06b550bc…a03bfd` |

Both runs exited 0 with 50 presentations. Each stderr contained a MediaPipe
`portable_clearcut_uploader` line "Failed to send to clearcut:
FAILED_PRECONDITION". This is the project's open third-party telemetry
question (see PROJECT_CONTEXT); no project code uploads data, and the payload
and the conditions of any later send are unknown.

## Preregistered result: **no winner**

Validation over 16 targets and 96 distinct-row pairs. Pass needs y MAE ≤ 0.08,
ordering ≥ 0.905 and |bias| ≤ 0.05 in **both** sessions.

| Candidate | A: R² / y MAE / bias / ordering | B: R² / y MAE / bias / ordering | Pass A / B |
| --- | --- | --- | --- |
| R0 (production `v`) | 0.707 / 0.158 / +0.026 / 77/96 | 0.771 / 0.118 / −0.016 / 82/96 | no / no |
| OPEN | 0.690 / 0.156 / −0.103 / 71/96 | 0.647 / 0.145 / −0.039 / 73/96 | no / no |
| OPEN_Q | 0.690 / 0.156 / −0.104 / 71/96 | 0.647 / 0.145 / −0.035 / 73/96 | no / no |
| BLEND | 0.780 / 0.383 / −0.383 / 89/96 | 0.701 / 0.127 / −0.064 / 80/96 | no / no |
| **COMBO** | 0.878 / **0.092** / +0.031 / **95/96** | 0.891 / 0.109 / −0.007 / 83/96 | no / no |

Ranking by mean y MAE: COMBO 0.100, R0 0.138, OPEN_Q 0.150, OPEN 0.150,
BLEND 0.255. COMBO came closest: in A it failed only y MAE (0.092); in B it
failed y MAE (0.109) and ordering (0.865). Horizontal: x MAE 0.046 / 0.062,
96/96 ordering in both sessions.

## Checkpoint repeats (descriptive)

Mean |block 3 − block 1| prediction change: R0 0.105 / 0.163, COMBO 0.127 /
0.147, OPEN 0.490 / 0.516, OPEN_Q 0.490 / 0.477, BLEND 0.583 / 0.342 (A / B).
Single checkpoints varied widely between blocks, e.g. R0 K-top in B predicted
0.036, 0.488 and 0.368 for the same target. Repeated fixations of one target
are not reproducible to the precision the exit criteria require.

## Exploratory (NOT preregistered)

Recentering each candidate with the block-2 K-center checkpoint (just before
validation) did not help: R0 y MAE became 0.161 / 0.127, COMBO 0.110 / 0.114.
One checkpoint is itself too variable to serve as an anchor.

## Interpretation

- **Correction to the Issue #75 interpretation.** There, eye opening looked
  strong (R² 0.97 / 0.90), but calibration ran row by row, so a time trend
  could appear as a row effect. With shuffled calibration and repeated
  checkpoints, eye opening drifted strongly over time (≈0.5 screen-y between
  blocks 1 and 3) and was **not** better than R0. It should not be pursued
  alone.
- **The production feature carries more vertical signal for Fatih than #75
  suggested.** With full screen, 25 shuffled calibration points spanning
  0.1–0.9, R0 reached R² 0.71 / 0.77 and 80–85% ordering, versus R² 0.24 / 0.21
  in #75. Wider span, more points, and shuffling were all changed, so the
  cause cannot be separated.
- **Combining signals helps but is not enough.** COMBO had the best fit and
  error, yet missed the 0.08 MAE threshold in both sessions.
- **The limiting factor is repeatability**, not a single offset: repeated
  fixations on the same point vary by up to ~0.4 in predicted y.

Limits: one participant, one evening, two sessions; five candidates on one
validation set; the eye-opening definition, blink threshold and head-pose
convention are engineering choices. No physical cause is established.

## Possible next steps (proposal, not authorization)

1. **Accept coarse vertical and design around it**: about 0.10 normalized y
   error suggests roughly 4–5 reliable vertical zones rather than pixel
   pointing; test a zone/row-based or two-step (zoom) selection against the
   targeting criterion.
2. **Temporal smoothing and multi-point re-anchoring** of COMBO, preregistered
   on new sessions (single-point recentering already failed here).
3. **Appearance-based gaze model** evaluated against COMBO under this protocol;
   largest cost and needs a human decision on ML and architecture.
4. **Run this protocol with Çağrı** to learn whether COMBO or R0 passes for him.
