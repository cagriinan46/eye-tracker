"""Optional MGazeNet adapter. Imported only when the user starts the camera."""

import base64
import hashlib
import sys
from types import SimpleNamespace

import numpy as np

from experiments.gazefollower_baseline.run import (
    SUPPORT,
    UPSTREAM_COMMIT,
    eligible,
    load_components,
)


class CameraModel:
    def __init__(self, camera_index=None):
        self.cap = self.face = self.gaze = None
        try:
            import cv2

            self.cv2 = cv2
            args = SimpleNamespace(
                upstream=SUPPORT / "upstream", face_model=SUPPORT / "face_landmarker.task"
            )
            self.config, self.face, self.gaze, self.calibration, *_ = load_components(args)
            if camera_index is None:
                if sys.platform == "darwin":
                    from live_svr_demo import macbook_camera_index

                    camera_index = macbook_camera_index()
                else:
                    camera_index = 0
            self.camera_index = camera_index
            self.cap = cv2.VideoCapture(
                camera_index, cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
            )
            if not self.cap.isOpened():
                raise RuntimeError(
                    "Kamera açılamadı. Kamera iznini ve diğer uygulamaları kontrol et."
                )
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
        except Exception:
            self.close()
            raise

    def read(self, preview=False):
        import time

        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Kamera bağlantısı kesildi. Kamerayı yeniden başlat.")
        captured = time.monotonic()
        bgr = self.cv2.resize(frame, (640, 480))
        face = self.face.detect(time.time_ns(), bgr)
        gaze = self.gaze.detect(self.cv2.cvtColor(bgr, self.cv2.COLOR_BGR2RGB), face)
        features = (
            gaze.features.copy() if eligible(face, gaze, self.config.eye_blink_threshold) else None
        )
        point = None
        if features is not None and self.calibration.has_calibrated:
            success, p = self.calibration.predict(features, gaze.raw_gaze_coordinates)
            if success and np.asarray(p).shape == (2,) and np.isfinite(p).all():
                point = list(p)
        jpeg = None
        if preview:
            small = self.cv2.resize(bgr, (400, 300))[:, ::-1]
            ok, data = self.cv2.imencode(".jpg", small, [self.cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                jpeg = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        return captured, features, point, jpeg

    def fit(self, features, labels):
        ok, error, _ = self.calibration.calibrate(features, labels)
        if not ok or not np.isfinite(self.calibration.weights).all():
            raise RuntimeError("Kalibrasyon hesaplanamadı. Yeniden dene.")
        return float(error)

    def metadata(self):
        return dict(
            upstream=UPSTREAM_COMMIT,
            camera_index=self.camera_index,
            model="MGazeNet + Ridge alpha0.1",
            model_sha256=hashlib.sha256(
                (SUPPORT / "upstream/gazefollower/res/model_weights/base.mnn").read_bytes()
            ).hexdigest(),
            face_model_sha256=hashlib.sha256(
                (SUPPORT / "face_landmarker.task").read_bytes()
            ).hexdigest(),
        )

    def close(self):
        for name in ("cap", "face", "gaze"):
            obj = getattr(self, name, None)
            if obj is not None:
                try:
                    obj.release()
                except Exception:
                    # Still release the remaining independent native resources.
                    pass
                finally:
                    setattr(self, name, None)
