# Results — head pointer signal comparison (Issue #156)

Collected **2026-11-28, Europe/Istanbul**, after the preregistration commit
`071d9f0` was pushed. Participant: Fatih only. MacBook Pro built-in display,
1512×982 logical px, full screen. Built-in MacBook Pro camera (OpenCV index 0,
1920×1080, 30.3 fps). Environment: `~/.virtualenvs/eye-tracker-gazefollower-20261019`
(MediaPipe 0.10.35). See [README](README.md).

Camera index 0 was identified before the sessions with a 3-second signal printout
and nothing saved. The first check had the face off-centre (nose x 0.81, yaw −22°)
and camera index 1 found no face. After Fatih sat centred in front of the
MacBook, index 0 gave nose x 0.52 and yaw −2.8°.

## Sessions

| | Session A | Session B (after reseating) |
| --- | --- | --- |
| Start (+03:00) | 13:40:13 | 13:46:47 |
| Duration | 325.0 s | 299.5 s |
| Completed | yes | yes |
| Failed reads / no-face frames | 0 / 0 | 0 / 0 |
| Calibration frames (9 dots) | 272 | 270 |
| Candidate order (shown as "Aday 1/2/3") | NOSE, ANGLES, RAY | RAY, ANGLES, NOSE |
| Local file (Git-ignored) | `.venv/head-pointer-fatih-A.json`, 2,344,342 B, SHA-256 `4b09e49d…b8bb2cba` | `.venv/head-pointer-fatih-B.json`, 2,209,336 B, SHA-256 `7c4be808…1160add8ab` |

All three candidates were calibrated in both sessions. Both runs exited 0.
MediaPipe's native code logged 5 (A) and 4 (B) clearcut "Failed to send" lines
on stderr. This is the known telemetry question; it was only recorded.

## Preregistered result

Selection time is measured from target onset and includes the 0.8 s dwell.

| Candidate | A selected / timeouts | B selected / timeouts | Passes | Pooled median time | Pooled median hold jitter |
| --- | --- | --- | --- | --- | --- |
| NOSE | 16/16, 0 | 15/16, 1 | yes | 4.11 s | 7.26 px |
| ANGLES | 15/16, 1 | 15/16, 1 | yes | 3.91 s | 7.11 px |
| **RAY** | **16/16, 0** | **16/16, 0** | **yes** | **3.79 s** | **7.05 px** |

**Winner: RAY.** All three candidates passed. RAY had the lowest pooled median
time. ANGLES (3.91 s) was within the 5 % tie band (limit 3.98 s), so the tie
was broken on hold jitter: RAY 7.05 px against ANGLES 7.11 px. NOSE (4.11 s)
was outside the band.

**The margin is small.** RAY beat ANGLES by 0.12 s in time and by 0.06 px in
jitter. With one participant and 32 scored trials per candidate, this does not
show a robust difference between RAY and ANGLES. RAY was the only candidate
with no timeout in either session.

## Descriptive (preregistered as descriptive only)

| Candidate / session | Median time 30 px | Median time 60 px | Median hold jitter | Median entries |
| --- | --- | --- | --- | --- |
| NOSE A | 5.96 s | 3.39 s | 6.42 px | 3 |
| NOSE B | 5.44 s | 3.08 s | 9.26 px | 2 |
| ANGLES A | 5.31 s | 3.78 s | 7.23 px | 3 |
| ANGLES B | 4.91 s | 3.06 s | 5.45 px | 2 |
| RAY A | 4.53 s | 3.06 s | 7.16 px | 2 |
| RAY B | 4.81 s | 3.01 s | 6.47 px | 2 |

All three timeouts were on 30 px targets:

| Session | Candidate | Target position (normalized) | Entries |
| --- | --- | --- | --- |
| A | ANGLES | (0.10, 0.50) | 5 |
| B | ANGLES | (0.22, 0.77) | 6 |
| B | NOSE | (0.78, 0.23) | 7 |

The cursor reached and entered these targets but did not stay inside long
enough.

## Exploratory (NOT preregistered)

- **Reaching is not the bottleneck; holding still is.** The median time to
  first entry was about 1.8–2.2 s for every candidate in both sessions. Most of
  the rest of the time went to leaving and re-entering the target. A hold
  jitter of about 7 px RMS is large next to a 30 px target's 15 px radius.
- **Large head movement.** RAY's lines map about 23 cm (A) or 26 cm (B) of
  ray-point movement to the screen width. ANGLES' lines map about 36–38° of yaw
  to the width and about 28° of pitch to the height. Comfort and fatigue were
  not measured.
- Practice trials (4 per block) were not scored. Order effects cannot be
  separated with two sessions.

## Interpretation

- For Fatih, on this setup, **all three head signals give a usable continuous
  pointer for 30–60 px targets**: 93 of 96 scored trials were selected. RAY
  was the most consistent, with 32/32 selected.
- The pointer is **not yet "flawless"**. A median of 3.8 s per target, about
  two entries, and small-target times around 4.5–4.8 s are slow, and the cause
  is the cursor's steadiness at the target.
- Fatih's question "should the point be the nose?" has this answer here: the
  nose's *forward line* (RAY) did slightly better than the nose-tip image
  position (NOSE), which was the slowest. The difference from head angles
  (ANGLES) is within noise.

## Next step (needs Fatih's approval as a new task)

Improve steadiness and comfort on RAY alone, as a new preregistered comparison:
the filter (lower min cutoff, or a stronger hold at the target), gain (smaller
head movement for the full screen) and recentring. Integrating the pointer into
"Masaüstünü kontrol et" and eye-based clicking are later, separately approved
steps. The constants above are not changed retroactively.

Limits: one participant, one sitting, two sessions, one camera and display;
MediaPipe's matrix is not a validated head tracker; the filter was fixed before
any data. No OS pointer was moved and nothing was clicked.
