# Experiment 002 — Results

A no-preview quantitative camera run was completed in the coding-agent environment. The controlled neutral/blink/wink/head-movement sequence remains pending, so this is not a final validation of signal usefulness or tracking reliability.

## Environment

- Development Mac: Apple M3; `system_profiler` listed a built-in FaceTime HD camera and a paired iPhone camera. Camera index `1` was identified as the built-in camera in Experiment 001.
- macOS: 26.2 (build 25C56).
- Python: 3.12.13.
- Installed direct packages: `mediapipe==0.10.35`, `opencv-python==5.0.0.93`.
- Transitive OpenCV package: `opencv-contrib-python==5.0.0.93`.
- Model: official Google Face Landmarker float16 bundle, downloaded from `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`; SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`.

## Configuration

- Camera index: `1`.
- Requested duration: `15` seconds.
- Preview: off.
- Running mode: MediaPipe Face Landmarker `VIDEO`, one face, blendshape output enabled.

## Measurements

| Measurement | Result |
| --- | --- |
| Elapsed duration | 15.345 s |
| Input resolution | 1920 x 1080 |
| Successful camera reads | 445 |
| Failed camera reads | 0 |
| Frames submitted / processed | 445 / 445 |
| Frames with detected face | 177 |
| Frames without detected face | 268 |
| Face-detection success percentage | 39.78% |
| Effective processing FPS | 29.00 |
| Average processing/inference time | 7.829 ms |
| Median processing/inference time | 7.599 ms |
| p95 processing/inference time | 9.789 ms |
| Observed face landmark count | 478 when detected |
| Blendshape output available | Yes, on 177 detected-face frames |
| `eyeBlinkLeft` observed range | 0.055 to 0.354 |
| `eyeBlinkRight` observed range | 0.084 to 0.620 |
| Tracking-loss events | 63 face-present to no-face transitions |
| Longest no-face streak | 39 processed frames |

## Signal Observations

- Neutral face: controlled observation pending.
- Natural blinking: controlled observation pending.
- Comfortable left-eye closing/wink: controlled observation pending.
- Comfortable right-eye closing/wink: controlled observation pending.
- Small normal head movements: controlled observation pending.

The observed aggregate blink-score ranges show that the two named outputs were present and varied during the run. No actions were deliberately labeled or visually inspected, so these ranges do **not** establish a response to any particular blink or wink.

## Tracking Observations

The 15-second run recorded 63 face-present to no-face transitions and a longest no-face streak of 39 processed frames. There was no controlled record of when a face was continuously in view, so these counts cannot distinguish model instability from changes in scene or subject position. Visual tracking inspection remains pending.

A separate `--duration 2 --preview` smoke run exited successfully after 2.569 s, processing 10 frames with 10 detected faces and no failed camera reads. Its 3.89 effective FPS includes preview/startup overhead over a very short interval and is not comparable with the 15-second no-preview run. The preview was not visually assessed by a human during this smoke run.

## Limitations

- The controlled manual sequence and preview inspection were not performed; qualitative blink/wink response and landmark stability remain unknown.
- The 39.78% face-presence rate is not ground-truth detection accuracy because the presence and position of a face were not controlled or labeled throughout the run.
- Timing measures only completed `detect_for_video()` calls; effective FPS also includes camera capture and loop overhead but excludes model initialization.
- A single short run will not generalize to all people, cameras, lighting, or positions.
- MediaPipe 1.0.1 aborted during model startup on this Mac, including with an explicit CPU delegate. The tested 0.10.35 package loaded and ran the same official model; this version pin is experimental, not a permanent selection.
- MediaPipe and OpenCV remain experiment-only candidates.

## Conclusion

Final conclusion pending the controlled signal-observation sequence. This run demonstrates that the tested MediaPipe package and model can process a live camera feed and return face landmarks and blendshapes, but it does not establish stable face tracking or useful blink/wink discrimination.

For the remaining manual observations, run from the repository root after the README setup:

```bash
.venv/bin/python experiments/002-face-landmarks/face_landmark_baseline.py --camera-index 1 --duration 30 --preview
```

Record the manual sequence observations above before drawing a bounded final conclusion. Do not treat blendshape values as command thresholds.
