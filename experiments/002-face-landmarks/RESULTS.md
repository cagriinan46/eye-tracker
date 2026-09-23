# Experiment 002 — Results

Real hardware validation was completed on the development Mac. The controlled face-present run below is the primary result; earlier exploratory runs are noted separately.

## Environment

- Development Mac: macOS ARM64 with built-in FaceTime HD camera at index `1`, as identified in Experiment 001. An earlier local environment check identified an Apple M3 running macOS 26.2 (build 25C56); the exact OS/device details were not separately reconfirmed for this run.
- Python: 3.12 for the completed run. An earlier local environment check reported 3.12.13; the patch version was not separately reconfirmed for this run.
- MediaPipe: `0.10.35`, which initialized successfully and was used for the completed run. The experiment requirements pin `opencv-python==5.0.0.93`; that package version was verified in the earlier local environment but not separately reported for this run.
- Transitive OpenCV package in the earlier local environment: `opencv-contrib-python==5.0.0.93`.
- Model: official Google Face Landmarker float16 bundle, downloaded from `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`; SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`.

## Configuration

- Camera index: `1`.
- Elapsed duration: `34.458` seconds. Requested duration and preview setting were not provided with the completed-run measurements.
- Running mode: MediaPipe Face Landmarker `VIDEO`, one face, blendshape output enabled.

## Measurements

| Measurement | Result |
| --- | --- |
| Camera index | 1 |
| Elapsed duration | 34.458 s |
| Input resolution | 1920 x 1080 |
| Successful camera reads | 864 |
| Failed camera reads | 0 |
| Frames submitted / processed | 864 / 864 |
| Frames with detected face | 864 |
| Frames without detected face | 0 |
| Face-detection success percentage | 100.00% |
| Effective processing FPS | 25.07 |
| Average processing/inference time | 6.773 ms |
| Median processing/inference time | 6.450 ms |
| p95 processing/inference time | 6.737 ms |
| Observed face landmark count | 478 |
| Frames with blendshape output | 864 |
| `eyeBlinkLeft` observed range | 0.002 to 0.727 |
| `eyeBlinkRight` observed range | 0.002 to 0.694 |
| Tracking-loss events | 0 |
| Longest no-face streak | 0 processed frames |

## Signal Observations

Both blink-related blendshape outputs were present for all 864 detected-face frames. Their observed ranges were `eyeBlinkLeft` 0.002–0.727 and `eyeBlinkRight` 0.002–0.694. These aggregate ranges show variation but were not supplied with phase-by-phase labels for neutral face, natural blinking, left/right eye closing, or head movement. They therefore do not establish reliable classification of any intentional gesture.

No blink/wink command thresholds were defined.

## Tracking Observations

The controlled face-present run detected a face in all 864 processed frames: 100.00% face-detection success, zero face-present to no-face transitions, and zero no-face streak. This supports stable face-landmark and blendshape output over this tested 34.458-second interval.

An earlier, uncontrolled 15.345-second no-preview run processed 445 frames, with 177 face-present results and 63 face-present to no-face transitions. Face presence and position were not controlled or labeled, so those counts cannot be interpreted as model failure and are not directly comparable with the controlled run. A separate 2.569-second preview smoke run processed 10 frames with 10 detected faces; its short-duration FPS is likewise not comparable with the primary run.

## Limitations

- The supplied blink scores are aggregate ranges without step-specific observations; they cannot establish blink/wink classification or a command threshold.
- Face presence in a controlled run is not a ground-truth accuracy study, and this experiment does not test gaze estimation.
- Timing measures only completed `detect_for_video()` calls; effective FPS also includes camera capture and loop overhead but excludes model initialization.
- A single 34.458-second run does not establish performance across all hardware, users, lighting, positioning, or longer sessions.
- MediaPipe 1.0.1 produced a native SIGABRT during Face Landmarker model initialization on the tested macOS ARM64 / Python 3.12 environment, including with an explicit CPU delegate. MediaPipe 0.10.35 initialized successfully and was used for the completed experiment. This compatibility finding does not permanently select a MediaPipe version or framework.
- MediaPipe and OpenCV remain experiment-only candidates.

## Conclusion

On the tested development Mac, MediaPipe 0.10.35 provided sufficiently stable face-landmark and blendshape output during the controlled face-present run to proceed to the next Phase 0 eye/gaze-feature experiment. All 864 processed frames contained a detected face, with 478 landmarks and blendshape output, and no tracking-loss events occurred. This does not establish reliable intentional-gesture classification or working gaze estimation, does not set final-product performance requirements, and does not permanently select MediaPipe for production.
