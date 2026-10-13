# Camera placement and vertical signals — results (Issue #88)

Date: **2026-10-13, Europe/Istanbul**. Participant: Fatih only. Protocol and
decision rule: [README](README.md), preregistered in commit `b518be7`, pushed
before session 1.

## Setup checks

- iPhone connected by **USB cable** as Continuity Camera ("Fatih Kamerası");
  wireless failed while the iPhone shared its connection (Personal Hotspot,
  Mac at 172.20.10.11), matching Apple's stated requirement.
- **OpenCV index 0 = built-in, 1 = iPhone**, established by a no-save
  brightness test: covering the iPhone lens changed index 1's mean brightness
  156.2 → 132.4 and index 0's 126.4 → 126.6. Swift's
  `AVCaptureDevice.devices(for: .video)` listed the opposite order, so device
  lists must not be trusted for OpenCV indices. Both cameras delivered
  1920×1080; the iPhone preview ran at 29.9 fps.
- Video effects: Fatih was asked to keep Center Stage, Portrait and Studio
  Light off; Fatih did not explicitly confirm the setting (limitation).
- Each run printed one MediaPipe clearcut "Failed to send" line (recorded only).

## Sessions

| # | Camera / session | Time (+03:00) | Rows / common frames | Calibration / validation | Detector median / p95 ms | Local file (Git-ignored) SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | built-in A | 12:24:04–12:25:48 | 1,788 / 1,780 | 25/25, 16/16 | 6.99 / 7.59 | `b44173fc…3a46ab2` |
| 2 | iPhone A | 12:26:12–12:27:57 | 1,807 / 1,802 | 25/25, 16/16 | 6.43 / 6.62 | `92182600…1761b` |
| 3 | iPhone B | 12:30:05–12:31:50 | 1,800 / 1,796 | 25/25, 16/16 | 6.42 / 6.62 | `1908bf67…b4cf` |
| 4 | built-in B | 12:32:19–12:34:03 | 1,794 / 1,791 | 25/25, 16/16 | 6.57 / 6.97 | `8ac448de…e228` |

Files: `validation/results/camera-placement-fatih-{builtin,iphone}-{A,B}.json`
(2,160,959 / 2,182,613 / 2,172,047 / 2,166,134 B). Full SHA-256 values are in
the WORK_LOG entry. All sessions exited 0 with 50/50 presentations; all four
are **valid**.

## Frozen per-session metrics (validation, 16 targets)

y MAE / signed bias / ordering of 96 distinct-row pairs; pass needs y MAE ≤ 0.08,
ordering ≥ 0.905 and |bias| ≤ 0.05.

| Candidate | built-in A | built-in B | iPhone A | iPhone B |
| --- | --- | --- | --- | --- |
| R0 | 0.111 / −0.020 / 0.86 | 0.140 / −0.056 / 0.83 | 0.103 / −0.077 / 0.96 | 0.126 / −0.059 / 0.85 |
| OPEN | 0.138 / +0.040 / 0.82 | 0.091 / +0.071 / 0.98 | 0.174 / −0.064 / 0.68 | 0.190 / −0.031 / 0.56 |
| OPEN_Q | 0.139 / +0.038 / 0.82 | 0.095 / +0.075 / 0.98 | 0.173 / −0.060 / 0.68 | 0.206 / −0.022 / 0.56 |
| BLEND | 0.127 / +0.008 / 0.83 | 0.185 / +0.182 / 0.94 | 0.140 / −0.140 / 1.00 | 0.089 / −0.018 / 0.92 |
| COMBO | 0.103 / +0.019 / 0.91 | 0.102 / +0.075 / 0.93 | **0.071 / −0.045 / 1.00 (PASS)** | 0.084 / +0.012 / 0.94 |

Calibration R² of COMBO: 0.92 / 0.84 (built-in), 0.92 / 0.90 (iPhone).
Horizontal x MAE: 0.047 / 0.030 (built-in), 0.051 / 0.038 (iPhone); x ordering
96/96 in all sessions.

## Preregistered decision

| Camera | Best candidate (mean y MAE) | #77 winner |
| --- | --- | --- |
| built-in | COMBO 0.103 | none |
| iPhone below screen | COMBO **0.077** | none (COMBO passes A, fails B on y MAE 0.084) |

- **iPhone placement better: YES.** All four sessions valid; 0.077 ≤ 0.103 −
  0.02 (margin 0.025 against the required 0.020).
- **Vertical solved: NO.** No candidate passed both iPhone sessions. COMBO in
  iPhone A is the first single-session pass of the exit thresholds recorded for
  Fatih; iPhone B missed y MAE by 0.004.

On Fatih's ≈19.6 cm-high display, mean COMBO y MAE is about 1.5 cm (iPhone)
versus 2.0 cm (built-in).

## Exploratory observations (not preregistered)

- Signals responded differently to placement: eye opening (OPEN) degraded
  sharply from below (R² 0.47 / 0.32), while blendshape BLEND and production R0
  ordering improved in session A. COMBO benefits from combining them.
- Checkpoint drift (COMBO, block 3 − block 1, in screen-height units): built-in
  bottom −0.17 / +0.19, center +0.13 / +0.02, top +0.09 / −0.12; iPhone bottom
  −0.11 / +0.29, center −0.01 / −0.10, top −0.21 / −0.38. Within-session drift
  was **not smaller** with the iPhone and was largest in iPhone B; the
  validation gain may not persist over longer use.
- Built-in COMBO today (0.103 / 0.102) is close to Issue #77 (0.092 / 0.109),
  so the library session did not obviously degrade the baseline.

## Limitations

One person, one day, one location, four ~100 s sessions. The iPhone differs in
position **and** sensor, lens and image processing, so the gain cannot be
assigned to placement alone. Five candidates were compared; the margin over
the 0.02 rule is small (0.005). Video-effect state was not confirmed. No
production behavior changed; using an iPhone (or a low external camera) as the
system camera is a human decision for Fatih and Çağrı.
