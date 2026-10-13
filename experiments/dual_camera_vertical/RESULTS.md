# Simultaneous dual-camera vertical signals — results (Issue #90)

Date: **2026-10-13, Europe/Istanbul**. Participant: Fatih only. Protocol and
decision rule: [README](README.md), preregistered in commit `4be1081`, pushed
before session A.

## Setup checks

- Built-in camera above the screen (**top**, OpenCV index 0) and iPhone
  Continuity Camera by USB in landscape on the Issue #88 stand below the
  screen (**bottom**, index 1). Indices were confirmed by a no-save lens-cover
  test: index 1 brightness 149.4 → 127.8 when covered, index 0 126.3 → 127.7.
- Smoke test (no data kept): 13.3 loops/s, i.e. ≈13 frames/s per camera
  instead of ≈30 for a single camera in #88; inter-camera frame gap median
  16.8 ms.
- Video effects off was requested as in #88; not separately reconfirmed.
- MediaPipe 0.10.35; clearcut "Failed to send" lines recorded only.

## Sessions

| Session | Time (+03:00) | Loops (rows per camera) | Common presentations | Cal / val per camera | Inter-camera gap median / max ms | Detector median ms top / bottom | Local file (Git-ignored) SHA-256 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 13:49:30–13:51:16 | 895 | 50/50 | 25/25, 16/16 | 22.0 / 38.6 | 7.7 / 6.9 | `e79a5bd9…9395` |
| B | 13:52:28–13:54:14 | 726 | 50/50 | 25/25, 16/16 | 35.8 / 47.2 | 7.8 / 7.7 | `00243f5f…d169` |

Files: `validation/results/dual-camera-fatih-{A,B}.json` (2,239,146 /
1,818,053 B; full SHA-256 in WORK_LOG). Both exited 0 with 50/50
presentations, no failed reads and no missing faces in either camera; both
sessions are **valid**. Session B ran ≈19% fewer loops (≈12 vs 15 per
sampling second; cause not established) with a larger inter-camera gap.

## Frozen per-session metrics (validation, 16 targets)

y MAE / signed bias / ordering of 96 pairs; pass needs y MAE ≤ 0.08,
ordering ≥ 0.905 (≥ 87/96) and |bias| ≤ 0.05.

| Method | A | B | Mean y MAE |
| --- | --- | --- | --- |
| **LATE** (primary fusion) | **0.054 / −0.039 / 96 (PASS)** | **0.057 / +0.018 / 94 (PASS)** | **0.056** |
| BOTTOM:BLEND | 0.054 / −0.008 / 94 (PASS) | 0.082 / −0.060 / 93 | 0.068 |
| SPLIT (secondary fusion) | 0.072 / −0.061 / 96 | 0.067 / +0.006 / 93 (PASS) | 0.069 |
| BOTTOM:R0 | 0.070 / +0.009 / 94 (PASS) | 0.094 / −0.056 / 93 | 0.082 |
| TOP:COMBO | 0.062 / −0.005 / 94 (PASS) | 0.104 / +0.086 / 95 | 0.083 |
| BOTTOM:COMBO | 0.077 / −0.072 / 96 | 0.091 / −0.050 / 91 | 0.084 |
| TOP:BLEND | 0.072 / +0.053 / 94 | 0.100 / +0.066 / 93 | 0.086 |
| TOP:R0 | 0.078 / +0.033 / 94 (PASS) | 0.098 / +0.073 / 94 | 0.088 |
| TOP:OPEN / OPEN_Q | 0.116 / 0.121 | 0.141 / 0.138 | 0.129 / 0.129 |
| BOTTOM:OPEN_Q / OPEN | 0.156 / 0.155 | 0.155 / 0.162 | 0.156 / 0.159 |

Calibration R²: LATE 0.97 / 0.97; SPLIT 0.98 / 0.95; COMBO top 0.91 / 0.93,
bottom 0.97 / 0.93. Horizontal x MAE 0.022 / 0.029 (top), 0.029 / 0.045
(bottom), x ordering 96/96 everywhere.

## Preregistered decision

| Test | Values | Result |
| --- | --- | --- |
| Fusion better (primary, LATE) | 0.056 ≤ best single BOTTOM:BLEND 0.068 − 0.01 = 0.058 | **YES** (margin 0.012 vs required 0.010) |
| Fusion better (secondary, SPLIT) | 0.069 > 0.058 | NO |
| Vertical solved by fusion | LATE passes all thresholds in A **and** B | **YES** |
| Placement replication (bottom vs top, 0.02) | 0.068 vs 0.083 (difference 0.015) | NO |

**LATE is the first method to pass the Issue #77 exit thresholds in two
sessions for Fatih.** No single-camera method passed both sessions; BOTTOM:BLEND,
TOP:COMBO, BOTTOM:R0 and TOP:R0 each passed A only. On the ≈19.6 cm display,
LATE's mean y MAE ≈ 1.1 cm.

## Exploratory observations (not preregistered)

- **Bias cancellation is a large part of the gain.** The two cameras' COMBO
  biases had opposite signs or differed widely (A: top −0.005, bottom −0.072;
  B: top +0.086, bottom −0.050), and LATE's bias was smaller (−0.039 / +0.018).
  Whether the opposite-sign pattern is stable across days or people is
  unknown; if it is session-specific, the gain will not hold.
- **Drift is not solved.** LATE's checkpoint prediction moved downward from
  block 1 to block 3 at every checkpoint in both sessions (A +0.09 / +0.11 /
  +0.15, B +0.16 / +0.15 / +0.03 for bottom / center / top) over ≈100 s. The
  validation block sits between the checkpoints, so longer use would likely
  show larger error without recalibration.
- Today's top camera was better than in #88 (COMBO 0.083 vs 0.103 mean) and
  the bottom camera's best single method changed from COMBO to BLEND, so
  single-camera rankings are not stable across sessions.
- Eye opening (OPEN) was again poor from below (R² 0.47 / 0.55).
- Frame rate per camera roughly halved versus a single camera.

## Limitations

One person, one day, two ~100 s sessions, twelve methods compared (two
preregistered fusions). The primary margin exceeds the rule by only 0.002.
Position and sensor remain confounded. The setup requires an iPhone, a USB
cable and a stand, and production Vision assumes one camera; any product use
is a human architecture/scope decision for Fatih and Çağrı and would first
need a Çağrı session and a longer (drift) session. No production behavior
changed.
