# iPhone ARKit (Live Link Face) vertical signal — sanity checks (Issue #86)

Date: **2026-10-09, Europe/Istanbul**. Participant: Fatih only. Status:
**exploratory, negative for vertical.** These were Stage 1 connection and
sanity checks, not a preregistered experiment. No code was merged and no
production behavior changed; the throwaway scripts lived in a temporary Claude
session directory and are not kept in the repository. No image or video was
recorded; only derived numbers were printed.

## Question

The webcam vertical axis does not meet Fatih's exit criterion (y MAE ≤ 0.08;
see [Issue #77](../../experiments/vertical_signal_comparison/RESULTS.md)).
Fatih asked whether an iPhone's TrueDepth/ARKit face tracking, streamed as
derived numbers (no images), carries a clearly better vertical eye signal. The
request's baseline figure "calibration y MAE 0.175" does not match any recorded
value (session 1 held-out y MAE 0.249; Issue #77 best COMBO 0.092 / 0.109); its
source was not identified.

## Stream format (verified against real packets)

Live Link Face (Epic
Games, free) in **Live Link (ARKit)** mode sends UDP to port **11111** of the
target IP, about 60 packets/s, no handshake. A face packet (312 bytes here) is:

| Field | Encoding |
| --- | --- |
| Packet version | `uint8` = 6 |
| Device id, subject name | each big-endian `int32` length + bytes (subject `iPhone`) |
| FrameTime | big-endian `int32` frame, `float32` subframe, `int32` rate numerator, `int32` denominator (60/1) |
| Value count | `uint8` = 61 |
| Values | 61 big-endian `float32`: the 52 ARKit blendshapes in [PyLiveLinkFace](https://github.com/JimWest/PyLiveLinkFace) order, then head yaw/pitch/roll, left eye yaw/pitch/roll, right eye yaw/pitch/roll (radians) |

Parsing from the packet end avoids the variable header. Head rotation is zero
unless the app's **Stream Head Rotation** setting is on. In the first run, about
900 packets of another 584-byte format (version byte 1, presumably a different
app mode) arrived before the ARKit stream and were not decoded.

Fields **not available** from Live Link Face: `lookAtPoint`, 4×4 eye transforms,
head position. iFacialMocap (paid; UDP 49983, text format) adds head position
but also lacks `lookAtPoint`. Those require an own iOS app (separate decision).

## Runs

Setup: MacBook display 1512×982 points, `.venv-fatih`, iPhone personal hotspot
(Mac 172.20.10.11). Silent on-screen cue: a red dot at center (0.5, 0.5), top
(0.5, 0.06), bottom (0.5, 0.94), left (0.06, 0.5), right (0.94, 0.5), 4 s each
in the order center, top, center, bottom, center, left, center, right, center.
Per phase: median of frames from 1.0 s after onset, excluding frames with
`eyeBlink` > 0.3. "Head still, eyes only."

| Run (+03:00) | Setup | Validity |
| --- | --- | --- |
| 1, 14:57–15:02 | Free looking, 5 min listener | Connection/format only. Fatih did not perform the requested up/down/left/right looks, so no direction can be inferred. |
| 2, between 15:03 and 15:08 | Cue, 1 cycle, phone **portrait** in front of the screen | **Invalid vertically:** the phone covered the bottom (and possibly center) dots. |
| 3, ≈15:08–15:10 | Cue, 2 cycles, phone portrait; added an all-dots placement check | **Invalid vertically:** Fatih reported the phone still covered the lower screen (head roll ≈ 0 confirms portrait). Horizontally, left registered and right did not. |
| 4, 15:25 | Cue, 2 cycles, phone landscape | **No data:** the Mac had moved to another network (172.20.34.163), so packets went to the old address. |
| 5, 15:30 | Cue, 2 cycles, phone **landscape** below the screen edge, all dots visible | **Valid.** Head roll ≈ 1.54 rad confirms landscape. |

Run 1 timing: median inter-packet gap 16.8 ms, p95 20.9 ms, max 33.2 ms;
frame-number gaps suggest well under 1% loss (not measured exactly). Run 5:
4,993 face packets, all 312-byte, median gap 16.8 ms, max 44.6 ms, 0–2%
blink-excluded frames per phase, head pitch/yaw drift ≤ about 2°.

### Run 5 (valid) results

Mean eye pitch (left/right average; positive = looking down), radians:

| Cycle | top | center (mean of the two neighbors) | bottom |
| --- | --- | --- | --- |
| 1 | +0.084 | +0.085 | +0.112 |
| 2 | +0.020 | +0.071 | +0.095 |

- **Down** separated from center in both cycles (+0.024 / +0.033 rad, about
  1.5–2°). **Up** separated only in cycle 2; in cycle 1 it equals center.
- `eyeLookUp` stayed **0.000 in every phase**; looking up appeared only as less
  `eyeLookDown` (center baseline about 0.12).
- Total top–bottom range 1.6°–4.3°, versus roughly 20° of physical eye rotation
  for this screen at an assumed (unmeasured) 55 cm.
- A single-threshold top/center/bottom classification would have put 2 of the 4
  top/bottom looks into "center".
- Horizontal eye yaw: left −0.003 / −0.010, right +0.131 / +0.099, centers
  +0.029–+0.060; ordering correct in both cycles, total range about 7° versus
  roughly 30° physical.

Eye pitch was an almost exact linear function of the blendshapes in run 1
(≈ 0.6 × lookDown − 0.45 × lookUp), so it is not an independent signal. In run 1
the largest `eyeLookDown` values coincided with blinks (e.g. 0.40 at blink
0.82), the same lid confound seen with the webcam eye-opening feature.

### Retracted interpretations (recorded for honesty)

During the session, Claude first reported from run 1 that `eyeLookUp` "barely
responds" and horizontal range "is narrow", then from run 2 that there was "no
vertical separation". Both were drawn before the direction protocol and the
phone occlusion were known; they were retracted. Only run 5 supports
directional statements.

## Conclusion

**In these checks, ARKit via Live Link Face did not carry a meaningfully better
vertical eye signal than the webcam.** The downward signal was weak but
consistent; the upward signal was inconsistent and `eyeLookUp` never activated;
the effect was about 8–20% of the physical angle. A direct metric comparison is
not possible (webcam R0 vertical R² 0.71 / 0.77 came from a 5×5 protocol; here
5 positions × 2 cycles), but half-failed top/center/bottom separation does not
support superiority. Stage 2 (preregistered recording) and Stage 3 (a
`GazeSource` abstraction) were therefore not started.

Limitations: one person, one setup, no preregistered rule; phone angle and
viewing distance unmeasured; whether Live Link Face smooths ARKit values is
unknown; `lookAtPoint` and raw eye transforms were not tested.

## Alternatives presented to Fatih (no decision taken)

1. Head pointing as primary pointer ([Issue #84](../../experiments/head_vertical_targeting/RESULTS.md)
   passed 3×3 and 4×4) — scope/architecture decision for Fatih and Çağrı;
   comfort and fatigue unmeasured.
2. Camera-placement hypothesis: the iPhone as an ordinary Continuity Camera
   below the screen with the existing webcam pipeline and Issue #77 protocol
   (frames processed on the Mac).
3. Dedicated infrared eye tracker — scope, budget and licensing questions.
4. Own iOS app reading `lookAtPoint` — low expected value because it comes from
   the same ARKit eye model; separate decision.
5. Appearance-model spike ([Issue #79](appearance-gaze-options.md) option 1).

Privacy: data travelled only over Fatih's personal hotspot; no data was sent
over the library network (run 4 delivered nothing). Temporary printed numbers
remained only in the Claude session scratch directory; nothing was written
under `.venv/`, and no Çağrı data, B2 file or PR #71 was touched.
