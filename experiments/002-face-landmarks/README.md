# Experiment 002 — Real-time face and eye features

## Question and hypothesis

Can the development Mac reliably extract real-time facial landmarks and useful eye/face-related signals from its camera feed using MediaPipe Face Landmarker, with sufficient stability for later gaze and gesture experiments?

The hypothesis is that the built-in camera and Face Landmarker will provide stable landmark output and useful eye/face signals. MediaPipe is an experimental candidate, **not an accepted architecture decision**.

## Setup

From the repository root, use the existing Python 3.12 virtual environment:

```bash
.venv/bin/python -m pip install -r experiments/002-face-landmarks/requirements.txt
mkdir -p .venv/models
curl -fL -o .venv/models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
shasum -a 256 .venv/models/face_landmarker.task
```

The experiment uses Google's official float16 Face Landmarker model bundle from the [MediaPipe model page](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker#models). The downloaded asset in this setup has SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. The model is approximately 3.6 MB and stays under the ignored `.venv/` directory; it is not committed. Verify the checksum if the upstream `latest` asset changes.

The tested direct package versions are `mediapipe==0.10.35` and `opencv-python==5.0.0.93`, listed only in this experiment's `requirements.txt`. MediaPipe also installed `opencv-contrib-python==5.0.0.93` transitively in the tested environment. MediaPipe 1.0.1 aborted during model initialization on this development Mac, including with an explicit CPU delegate; 0.10.35 loaded the same official model. This is a reproducibility pin for the experiment, not a production dependency decision.

## Run

```bash
.venv/bin/python experiments/002-face-landmarks/face_landmark_baseline.py
```

Defaults are camera index `1`, 15 seconds, the model path above, and no preview. Index `1` selected this Mac's built-in camera in the prior camera experiment; index `0` selected a paired iPhone through Continuity Camera. Do not assume the same ordering on other setups.

To inspect signals visually and perform the manual sequence, run:

```bash
.venv/bin/python experiments/002-face-landmarks/face_landmark_baseline.py --camera-index 1 --duration 30 --preview
```

Use `--camera-index`, `--duration`, and `--model PATH` to change inputs. `--preview` displays local landmark dots, face status, `eyeBlinkLeft`/`eyeBlinkRight` scores, and effective processing FPS. Press `q` or Esc in the preview, or Ctrl+C, to stop early. Camera or model failure is reported with a non-zero exit.

## Measurements and manual observations

The summary reports elapsed time, first successful input resolution, successful/failed camera reads, frames submitted and processed, face/no-face counts, detection percentage, effective processed FPS, observed landmark counts, blendshape availability, blink-score ranges, and tracking loss. A tracking-loss event means a processed frame without a face immediately followed a processed frame with a face; the longest no-face streak is also reported. Processing/inference time measures each synchronous `detect_for_video()` call only, excluding camera read, color conversion, and preview drawing. Average, median, and nearest-rank p95 are reported across completed calls. Effective processing FPS divides processed frames by total elapsed experiment time, including capture and optional preview overhead.

For qualitative signal inspection, perform this short sequence if physically comfortable:

1. Neutral face.
2. Natural blinking.
3. Intentional left-eye closing/wink.
4. Intentional right-eye closing/wink.
5. Small normal head movements.

Observe whether the landmark overlay remains stable and whether the two blink-related scores visibly respond during each step. Record observations in [RESULTS.md](RESULTS.md); the aggregate score range alone cannot identify which action caused a change. Do not define command thresholds or treat these scores as clicks or gestures.

## Privacy and limitations

Frames and scores stay in local memory. The script does not save images/video or upload camera data. The optional preview displays frames locally. The model download is a separate setup step and is not part of the real-time processing path.

One short run cannot establish behavior across other cameras, lighting conditions, positions, or users. Preview can change FPS. Face/no-face counts are output-presence measurements, not ground-truth detection accuracy. This experiment does not estimate gaze, classify intentional gestures, or select a production vision framework.
