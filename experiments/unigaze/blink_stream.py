"""Read-only blink observations from the existing local camera stream."""

import os
import sys
import threading
from collections import deque
from pathlib import Path

from .settings import BASELINE_PYTHON, ROOT


class BlinkStream:
    def __init__(self, camera, cv2):
        self.camera, self.cv2 = camera, cv2
        self.stop = threading.Event()
        self.enabled = threading.Event()
        self.lock = threading.Lock()
        self.samples = deque(maxlen=24)
        # Issue #160: (stamp, eyeBlinkLeft, eyeBlinkRight, mean mouthSmile, jawOpen,
        # mouthPucker, browInnerUp) for face gestures.
        self.eye_scores = deque(maxlen=24)
        self.available = False
        self.thread = None

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, name="desk-blink", daemon=True)
            self.thread.start()

    def enable(self, active):
        if active:
            self.start()
            self.enabled.set()
        else:
            self.enabled.clear()
            with self.lock:
                self.samples.clear()
                self.eye_scores.clear()

    def drain(self):
        if not self.available:
            return None
        with self.lock:
            values = list(self.samples)
            self.samples.clear()
        return values

    def drain_eyes(self):
        if not self.available:
            return None
        with self.lock:
            values = list(self.eye_scores)
            self.eye_scores.clear()
        return values

    def run(self):
        try:
            # Reuse the prepared environment where the repository runs its Face
            # Landmarker experiments. Imports are optional in the gaze worker.
            if sys.platform == "darwin":
                sys.path.append(
                    str(
                        BASELINE_PYTHON.parent.parent
                        / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
                    )
                )
            import mediapipe as mp

            model = Path(
                os.environ.get(
                    "EYE_TRACKER_BLINK_MODEL", ROOT / ".venv/models/face_landmarker.task"
                )
            )
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                output_face_blendshapes=True,
                num_faces=2,
            )
            seq, last_ms = -1, -1
            with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
                self.available = True
                while not self.stop.is_set():
                    if not self.enabled.wait(0.1) or self.stop.is_set():
                        continue
                    seq, stamp, frame = self.camera.read_after(seq)
                    rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
                    ms = max(last_ms + 1, stamp // 1_000_000)
                    last_ms = ms
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ms
                    )
                    closed = None
                    eyes = None
                    if len(result.face_blendshapes) == 1:
                        scores = {v.category_name: v.score for v in result.face_blendshapes[0]}
                        left, right = scores.get("eyeBlinkLeft"), scores.get("eyeBlinkRight")
                        smile = [scores.get(k) for k in ("mouthSmileLeft", "mouthSmileRight")]
                        if left is not None and right is not None:
                            smiled = None if None in smile else (smile[0] + smile[1]) / 2
                            held = [
                                scores.get(k) for k in ("jawOpen", "mouthPucker", "browInnerUp")
                            ]
                            eyes = (stamp / 1e9, float(left), float(right), smiled, *held)
                            if min(left, right) >= 0.50:
                                closed = True
                            elif max(left, right) <= 0.30:
                                closed = False
                    with self.lock:
                        if self.enabled.is_set():
                            self.samples.append((stamp / 1e9, closed))
                            if eyes is not None:
                                self.eye_scores.append(eyes)
        except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
            pass
        finally:
            self.available = False

    def close(self):
        self.stop.set()
        self.enabled.set()
        if self.thread is not None:
            self.thread.join(timeout=0.25)
