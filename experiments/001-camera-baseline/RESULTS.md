# Experiment 001 — Results

The development Mac's built-in camera was captured successfully for a 10-second baseline. The measurements below were supplied after real hardware validation.

## Environment

- Device: development Mac's built-in camera (model not reported).
- Platform: macOS; exact version for the successful run was not reported.
- Runtime: Python 3.12 experiment using `opencv-python`; exact versions for the successful run were not reported. An earlier, authorization-blocked run in the local environment used Python 3.12.13 and OpenCV 5.0.0 on macOS 26.2 (build 25C56).

## Configuration

- Camera index: `1` (built-in camera).
- Elapsed capture time: `10.026 s`.
- Preview setting and exact command for the successful run: not reported.

## Measurements

| Measurement | Result |
| --- | --- |
| Camera index | 1 |
| Elapsed time | 10.026 s |
| Actual frame resolution | 1920 x 1080 |
| Successful frames | 303 |
| Failed frame reads | 0 |
| Effective FPS | 30.22 |
| Average frame acquisition time | 33.084 ms |
| Median frame acquisition time | 33.495 ms |
| p95 frame acquisition time | 40.862 ms |

## Observations

- Camera index `0` selected a paired iPhone through Apple Continuity Camera; index `1` selected the Mac's built-in camera. Camera index ordering must not be assumed to identify the built-in camera.
- The successful 10-second run captured 303 frames with no failed reads. Median and p95 frame-acquisition times were 33.495 ms and 40.862 ms, respectively.
- An earlier coding-agent attempt at index `0` was blocked by camera authorization and produced no frame measurements. Its failure is separate from the successful index `1` run reported above.

## Limitations

- One 10-second run cannot establish long-term stability or performance across other Macs, cameras, lighting conditions, users, or camera settings.
- The exact software versions and preview setting of the successful run were not reported, so their effect cannot be assessed from these measurements.
- This experiment measures frame capture only; it does not measure face or eye tracking, gaze accuracy, or final-product interaction performance.
- The result does not establish that approximately 30 FPS is sufficient for the final product or select OpenCV as a permanent project dependency.

## Conclusion

Real-time camera capture on the tested Mac was stable during this 10-second baseline: no frame reads failed, approximately 30 FPS was sustained at 1920 x 1080, and frame-acquisition timing was reasonably consistent. This validates the camera-capture baseline for proceeding to the next computer-vision experiment. It does not resolve the broader performance or architecture questions listed above.
