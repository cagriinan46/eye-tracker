# Experiment 001 — Results

An execution was attempted on the development Mac, but camera authorization prevented capture. No frame-performance measurements have been obtained yet.

## Environment

- Development Mac: local development environment; camera model not confirmed.
- Python version: 3.12.13.
- OpenCV version: 5.0.0 (`opencv-python`).
- macOS version: 26.2 (build 25C56).

## Configuration

- Camera index: `0`.
- Requested duration: `10` seconds.
- Preview: off.

## Measurements

| Measurement | Result |
| --- | --- |
| Actual frame resolution | Pending |
| Successful frames | Pending |
| Failed frame reads | Pending |
| Effective FPS | Pending |
| Average frame acquisition time | Pending |
| Median frame acquisition time | Pending |
| p95 frame acquisition time | Pending |

## Observations

The command `.venv/bin/python experiments/001-camera-baseline/capture_baseline.py` exited with status `1` before frame capture. OpenCV reported `not authorized to capture video`, then failed to initialize the camera; the script reported `Could not open camera index 0.` No frames were obtained, so no FPS or acquisition-time values can be calculated.

## Limitations

Camera authorization in the coding-agent environment prevents a capture measurement. This failure does not establish whether the proposed capture loop is stable once camera access is granted. A single short run will only characterize that Mac and camera under its test conditions.

## Conclusion

Pending real camera measurements. Grant camera access to the terminal application on the development Mac, then run from the repository root:

```bash
.venv/bin/python -m pip install -r experiments/001-camera-baseline/requirements.txt
.venv/bin/python experiments/001-camera-baseline/capture_baseline.py
```

Record the actual output and environment above before writing a final conclusion. OpenCV's use in this experiment does not select it for production architecture.
