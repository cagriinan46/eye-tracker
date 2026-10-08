# Results — head-assisted pointing (Issue #84)

Collected **2026-10-08, Europe/Istanbul** after preregistration commit
`06bfbc2`. Participant: Fatih only. See [README](README.md).

## Sessions

| | Session A | Session B |
| --- | --- | --- |
| Time (+03:00) | 23:39:24–23:43:28 | 23:44:46–23:48:40, after reseating |
| Target image area | 1512×982 full screen | 1512×982 full screen |
| Trials completed | 50/50 | 50/50 |
| Camera reads / failed / no-face | 6,369 / 0 / 18 | 6,087 / 0 / 114 |
| Lines (eye_x, head_y, head_x slopes) | −3.80 per unit h, 0.0189 per °, −0.0242 per ° | +4.54, 0.0130, −0.0177 |
| Local file (Git-ignored) | `.venv/head-vertical-fatih-A.json`, 3,509,097 B, SHA-256 `b155e116…513d3aba` | `.venv/head-vertical-fatih-B.json`, 3,280,546 B, SHA-256 `ed54e2e3…2529e` |

Both runs exited 0; stderr held 8 / 6 MediaPipe clearcut "Failed to send"
lines (open telemetry question; recorded only).

## Preregistered result

| Condition / layout | A success / wrong / timeout | B success / wrong / timeout | Pass |
| --- | --- | --- | --- |
| **HEAD 3×3** | **100%** / 0% / 0% | **100%** / 0% / 0% | **yes** |
| **HEAD 4×4** | **100%** / 0% / 0% | **94%** / 6% / 0% | **yes** |
| HYBRID 3×3 | 56% / 44% / 0% | 67% / 22% / 11% | no |
| HYBRID 4×4 | 56% / 12% / 31% | 50% / 19% / 31% | no |

**HEAD (head yaw for x, head pitch for y) passes both layouts in both
sessions.** The single HEAD error (B 4×4) selected the cell one row above.
Median time to a successful selection in HEAD: 3×3 2.54 / 1.97 s, 4×4 2.33 /
2.27 s, including the 1.0 s dwell. This meets the accepted "coarse 3×3
targeting ≥ 80%" criterion **with head pointing, not with eye gaze**.

HYBRID failed. Most of its wrong selections were in the wrong **column** with
the right row (A 3×3: offsets (0, −2), (0, −1), (0, 2), (0, 2)), so head pitch
carried the vertical axis while eye-based horizontal failed. The eye_x line
also reversed sign between sessions (−3.80 vs +4.54); in Issue #77 it was
consistently about −11.

## Exploratory (NOT preregistered)

- **Head movement needed.** Calibration medians of head pitch over the five rows
  spanned 0.8° → 41.3° (A) and −16.0° → 37.3° (B), and were not monotonic in A.
  Yaw over the five columns spanned about +15° → −13° (A) and +19° → −22° (B).
  During HEAD trials, pitch ranged −22.7° to 42.2° (A) and −16.9° to 48.0° (B).
  Physically, pointing the nose from top to bottom of a 19.6 cm screen at an
  assumed 55 cm is about 20°. Either MediaPipe's pitch angle overstates
  physical pitch or Fatih moved more than necessary; this was not measured
  independently.
- **"Head still" was not still.** In the eye_x block, head yaw drifted about
  4° (A −1.8° → −5.6°; B +3.5° → −4.9°) while the eyes moved. That fits the
  Issue #81 head-rotation hypothesis and the HYBRID horizontal failure.
- Within-target head-angle spread during calibration was small (median SD
  0.6–1.2°), so head pose is a far steadier signal than the eye features.

## Interpretation

- For Fatih, **closed-loop head pointing gives reliable coarse selection**
  (49 of 50 HEAD trials across both sessions correct, one wrong selection, no
  timeouts), where every eye-based approach today failed.
- Eye features are sensitive to small head movements; combining eyes for one
  axis with head movement for the other did not work.
- The required head range looks large. Before any product use, the team needs
  an **adjustable gain** (sensitivity, already a project requirement), a
  comfort and fatigue check, and evaluation with users whose head control
  differs from Fatih's.

## Decisions for humans

1. **Direction:** making head pointing the primary pointer, with eye or blink
   gestures for actions, changes the product's central input method. That is a
   scope and architecture decision for Fatih and Çağrı.
2. **Code:** merge this experiment (it worked) or keep only the results, per
   Fatih's rule.
3. **Next tests if pursued:** gain or sensitivity and smaller head ranges,
   finer grids or continuous pointing, comfort over longer sessions, a Çağrı
   session, and combining head pointing with an intentional click mechanism
   (Phase 2).

Limits: one participant, one evening, two sessions; comfort and fatigue were
not measured; head angles come from MediaPipe's transformation matrix, not a
validated head tracker. No OS pointer is moved and nothing is clicked.
