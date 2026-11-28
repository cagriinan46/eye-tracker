# Results — head pointer tuning on RAY (Issue #158)

Collected **2026-11-28, Europe/Istanbul**, after the preregistration commit
`dffd1cc` was pushed. Participant: Fatih only. MacBook Pro built-in display,
1512×982 logical px, full screen. Built-in camera (index 0). Environment:
`~/.virtualenvs/eye-tracker-gazefollower-20261019`. See [README](README.md).

## Sessions

| | Session A | Session B (after reseating) |
| --- | --- | --- |
| Start (+03:00) | 17:15:34 | 17:23:48 |
| Duration | 351.5 s | 276.9 s |
| Completed | yes | yes |
| Failed reads / no-face frames | 0 / 0 | 0 / 0 |
| Calibration frames | 271 | 270 |
| Order ("Ayar 1/2/3") | BASE, STEADY, STEADY_GAIN | STEADY_GAIN, STEADY, BASE |
| Local file (Git-ignored) | `.venv/head-pointer-tuning-fatih-A.json`, 2,622,930 B, SHA-256 `c8dcdcca…97172bbc` | `.venv/head-pointer-tuning-fatih-B.json`, 2,126,565 B, SHA-256 `15989980…8e330c34d96a` |

RAY was calibrated in both sessions. Both runs exited 0. MediaPipe logged
5 (A) and 4 (B) clearcut "Failed to send" lines, which were only recorded.
**The recentre key was never used** (0 presses in every block).

## Preregistered result

| Condition | A selected / timeouts | B selected / timeouts | Passes | Pooled median time | Pooled median hold jitter | Comfort A / B |
| --- | --- | --- | --- | --- | --- | --- |
| BASE (1.0 Hz, β 0.01, gain 1) | 14/16, **2** | 16/16, 0 | **no** | 3.58 s | 6.69 px | 4 / 5 |
| **STEADY** (0.3 Hz, β 0.03, gain 1) | 15/16, 1 | 16/16, 0 | **yes** | 3.89 s | 6.43 px | 4 / 4 |
| STEADY_GAIN (0.3 Hz, β 0.03, gain 1.5) | 13/16, **3** | 15/16, 1 | no | 4.04 s | 6.21 px | 3 / 4 |

**Frozen rule outcome: winner STEADY, adopted.** It was the only condition
that passed.

**This is weak evidence that STEADY is better.** It won only because BASE had
two timeouts in session A. Its 0.31 s slower pooled median and 0.26 px lower
jitter are not a meaningful difference.

- **BASE was faster.** Its pooled median time was lower (3.58 s against
  3.89 s), and it was faster in session B.
- **BASE's two timeouts were at one position.** Both were at (0.78, 0.77),
  one at 30 px and one at 60 px.
- **The same settings did better in Issue #156.** As RAY in Issue #156, they
  had 0 timeouts in 32 trials. Pooled over #156 and #158, the BASE settings
  selected 62 of 64 targets; STEADY selected 31 of 32.
- **The steadier filter did not reach its goal.** Hold jitter and entries per
  target were almost unchanged.

The higher gain (STEADY_GAIN) had the most timeouts (4) and the lowest comfort
rating in session A.

## Descriptive

| Condition / session | Median time 30 px | Median time 60 px | Median hold jitter | Median entries | Median first entry |
| --- | --- | --- | --- | --- | --- |
| BASE A | 5.21 s | 3.14 s | 7.62 px | 2 | 1.66 s |
| BASE B | 4.04 s | 2.26 s | 5.82 px | 2 | 1.33 s |
| STEADY A | 5.34 s | 3.56 s | 6.73 px | 2 | 1.84 s |
| STEADY B | 4.48 s | 2.41 s | 6.28 px | 1.5 | 1.78 s |
| STEADY_GAIN A | 5.51 s | 3.50 s | 6.53 px | 2 | 1.71 s |
| STEADY_GAIN B | 4.07 s | 3.44 s | 5.89 px | 1 | 2.21 s |

Timeouts (target position, diameter, entries):

| Condition / session | Timeouts |
| --- | --- |
| BASE A | (0.78, 0.77) 30 px, 5 entries; (0.78, 0.77) 60 px, 6 entries |
| STEADY A | (0.22, 0.77) 30 px, 6 entries |
| STEADY_GAIN A | (0.10, 0.50) 30 px, 6 entries; (0.50, 0.12) 30 px, 4 entries; (0.22, 0.23) 30 px, 3 entries |
| STEADY_GAIN B | (0.90, 0.50) 30 px, 6 entries |

Every timed-out target was entered at least three times.

## Exploratory (NOT preregistered)

- **The spread during a dwell is mostly slow head motion, not frame noise.**
  For selected trials, the RMS spread of the final 0.8 s was:

  | Condition | Unfiltered, A / B | Filtered, A / B |
  | --- | --- | --- |
  | BASE | 5.8 / 5.4 px | 6.4 / 5.1 px |
  | STEADY | 6.0 / 4.8 px | 5.5 / 5.2 px |
  | STEADY_GAIN | 5.7 / 4.8 px | 6.3 / 4.8 px |

  The window was approximated from the first logged cursor frame, so the
  numbers are approximate. A low-pass filter cannot remove slow movement like
  this. That explains why STEADY changed little, and it suggests that further
  filter tuning is the wrong lever.
- The comparison between sessions is confounded by learning. Session B was
  faster for almost every condition, and the #156 and #158 sessions came from
  the same afternoon.

## Interpretation

- RAY with either filter is a usable continuous head pointer for Fatih. Over
  this issue's 96 scored trials, 89 were selected, and every timeout was a
  target that was entered but not held.
- **Neither tuning measurably removed the bottleneck:** holding the cursor
  inside a 30 px target for 0.8 s.
- A gain of 1.5 (less head movement) did not cost speed on 60 px targets, but
  it had more timeouts and was rated less comfortable once. It is not adopted.

## Recommendation for the next step (needs Fatih's approval)

Precision at the target should come from **target-aware assistance** rather
than more smoothing. The desktop demo already has a gaze magnet (`RingMagnet`)
and accessibility targets. Two options:

1. Integrate RAY into "Masaüstünü kontrol et" as a head-cursor mode, reusing
   the magnet, and measure real desktop selections.
2. First test a speed-dependent gain on its own: slow head motion moves the
   cursor less.

The frozen-rule outcome (STEADY) is recorded as is. Whether the integration
uses STEADY or BASE is a human decision, given the weak evidence above.

Limits: one participant, one afternoon, two sessions per issue; learning
effects; single comfort ratings; recentring unused, so it is untested.
