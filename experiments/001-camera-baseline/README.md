# Experiment 001 — macOS camera capture baseline

## Question

Can Python 3.12 reliably capture real-time frames from the development Mac's standard camera with sufficient stability to serve as the baseline input for later computer-vision experiments?

## Hypothesis

A simple OpenCV-based capture loop will provide stable real-time camera input on the development Mac and be sufficient for the next Phase 0 vision experiments. OpenCV is an experimental candidate, not a permanent architecture decision.

## Setup and run

From the repository root, use the existing project virtual environment:

```bash
.venv/bin/python -m pip install -r experiments/001-camera-baseline/requirements.txt
.venv/bin/python experiments/001-camera-baseline/capture_baseline.py
```

The default run uses camera index `0` for 10 seconds, without a preview. To change these settings:

```bash
.venv/bin/python experiments/001-camera-baseline/capture_baseline.py --camera-index 0 --duration 10 --preview
```

The preview is optional. Press `q` or Esc in the preview window to stop early, or use Ctrl+C. macOS may require camera permission for the terminal application. If the camera cannot open or no frames are captured, the script exits non-zero and reports the failure.

## Measurements

- **Frame resolution:** width and height of the first successfully captured frame, in pixels.
- **Successful frames / failed reads:** counts of `read()` calls that did or did not return a frame.
- **Effective FPS:** successful frames divided by total elapsed capture time, including failed reads and preview overhead when enabled.
- **Acquisition time:** wall-clock duration of each `read()` call, including failed attempts. Average and median summarize all attempts; p95 uses the nearest-rank method.

Run without a preview for the least UI overhead, and note the configuration alongside the results. These measurements characterize this setup; they do not by themselves establish a universal performance target.

## Privacy

Frames are processed in memory only. The script does not save images or video or upload data. The optional preview displays live frames locally.

## Known limitations

- Results depend on the Mac, camera, lighting, permissions, and other camera users.
- A short run does not establish long-term reliability or behavior across other devices.
- Preview may affect effective FPS and acquisition times.
- This experiment does not test face or eye tracking, gaze, calibration, gestures, or production architecture.

Record real execution details and measurements in [RESULTS.md](RESULTS.md). Do not conclude the hypothesis until the experiment has run on the development Mac.
