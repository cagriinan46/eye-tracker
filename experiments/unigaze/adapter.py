"""Pinned UniGaze branch, measured geometry; no camera, downloads or image writes."""

import hashlib
import os
import socket
from pathlib import Path

import cv2
import numpy as np
import torch

from . import geometry
from .settings import HOME as PREFLIGHT
from .settings import INTRINSICS, verify_sources


def deny(*args, **kwargs):
    raise RuntimeError("Network and image/video writes are disabled")


def overlap(a, b):
    def area(r):
        return max(0, r[2] - r[0]) * max(0, r[3] - r[1])

    intersection = area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])
    union = area(a) + area(b) - intersection
    return float(intersection / union) if union > 0 else 0.0


def bounds(points):
    return np.r_[points.min(0), points.max(0)]


def matched_landmarks(faces, landmarks, mgaze_rect):
    if faces is None or len(faces) != 1:
        return None, None, "no_face" if faces is None or len(faces) == 0 else "multiple_faces"
    points = np.asarray(landmarks, float)
    rect = np.asarray(mgaze_rect, float)
    if (
        points.shape != (468, 2)
        or rect.shape != (4,)
        or not np.isfinite(points).all()
        or not np.isfinite(rect).all()
    ):
        return None, None, "missing_baseline_face"
    fan = np.asarray(faces[0], float) / 0.5
    if fan.shape != (68, 2) or not np.isfinite(fan).all():
        return None, None, "invalid_candidate_landmarks"
    x, y, w, h = rect
    corners = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], float)
    k, dist = geometry.camera_parameters()
    corrected_corners = cv2.undistortPoints(corners[:, None, :], k, dist, P=k).reshape(-1, 2)
    overlaps = [
        overlap(bounds(fan), bounds(points)),
        overlap(bounds(fan), bounds(corrected_corners)),
    ]
    if min(overlaps) < 0.3:
        return None, overlaps, "face_mismatch"
    return fan, overlaps, None


class Candidate:
    def __init__(self):
        os.environ["TORCH_HOME"] = str(PREFLIGHT / "support/torch")
        os.environ["NUMBA_CACHE_DIR"] = str(PREFLIGHT / "support/numba-cache")
        os.environ["HF_HUB_OFFLINE"] = "1"
        import face_alignment

        cv2.imwrite = cv2.VideoWriter = deny
        socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
        torch.set_num_threads(4)
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        weights = PREFLIGHT / "support/torch/hub/checkpoints"
        hashes = {}
        for name, prefix in [
            ("2DFAN4-11f355bf06.pth.tar", "11f355bf06"),
            ("s3fd-619a316812.pth", "619a316812"),
        ]:
            digest = hashlib.sha256((weights / name).read_bytes()).hexdigest()
            if not digest.startswith(prefix):
                raise ValueError("Detector weights mismatch")
            hashes[name] = digest
        self.detector = face_alignment.FaceAlignment(
            face_alignment.LandmarksType.TWO_D,
            device=self.device,
            flip_input=False,
            compile=False,
            face_detector_kwargs={"path_to_detector": str(weights / "s3fd-619a316812.pth")},
        )
        self.model = geometry.load_model(self.device)
        self.provenance = dict(
            upstream_commit=geometry.REVISION,
            upstream_source_sha256=verify_sources(),
            weights_sha256=geometry.WEIGHT_SHA,
            detector_hashes=hashes,
            device=self.device,
            threads=4,
            face_alignment_version="1.5.0",
            geometry_source_sha256=hashlib.sha256(Path(geometry.__file__).read_bytes()).hexdigest(),
            camera_measurement_sha256=hashlib.sha256(INTRINSICS.read_bytes()).hexdigest(),
            features="2 camera-frame pitch/yaw radians, inverse-R denormalized; separate standardized Ridge .1",
            preprocessing="Measured K/D undistort once, native68 six-point PnP, full corrected frame warp224, RGB ImageNet",
            matching="Exactly one FAN face; IoU>=.3 against corrected MP468 bounds AND undistorted MGaze rectangle",
        )
        with torch.inference_mode():
            self.model(
                geometry.tensor_from_patch(np.zeros((224, 224, 3), np.uint8)).to(self.device)
            )
            self.detector.get_landmarks_from_image(np.zeros((240, 320, 3), np.uint8))

    def prepare(self, raw):
        return geometry.prepare_frame(raw)

    def infer(self, corrected, landmarks, mgaze_rect):
        result = dict(unigaze_valid=False, unigaze_angles=None, unigaze_reason="no_face")
        rgb = cv2.cvtColor(
            cv2.resize(corrected, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
            cv2.COLOR_BGR2RGB,
        )
        with torch.inference_mode():
            faces = self.detector.get_landmarks_from_image(rgb)
            result["unigaze_face_count"] = 0 if faces is None else len(faces)
            fan, overlaps, reason = matched_landmarks(faces, landmarks, mgaze_rect)
            result.update(face_box_ious=overlaps, unigaze_reason=reason)
            if fan is None:
                return result
            points = np.asarray(landmarks, float)
            result["eye_gap_ratios"] = [
                float(
                    np.linalg.norm(points[u] - points[d])
                    / max(np.linalg.norm(points[a] - points[b]), 1e-6)
                )
                for a, b, u, d in [(263, 362, 386, 374), (33, 133, 159, 145)]
            ]
            prepared = geometry.normalize_frame(corrected, fan)
            if prepared is None:
                result["unigaze_reason"] = "invalid_geometry"
                return result
            patch, rotation, detail = prepared
            angles = (
                self.model(geometry.tensor_from_patch(patch).to(self.device))["pred_gaze"]
                .cpu()
                .numpy()[0]
            )
            vector, camera_angles = geometry.denormalize(angles, rotation)
            if not np.isfinite(camera_angles).all():
                result["unigaze_reason"] = "nonfinite_output"
                return result
            result.update(
                unigaze_valid=True,
                unigaze_angles=camera_angles.tolist(),
                unigaze_normalized_angles=angles.tolist(),
                unigaze_vector=vector.tolist(),
                unigaze_head_rotation=detail["hr"].ravel().tolist(),
                unigaze_face_center=detail["center"].ravel().tolist(),
                unigaze_reason=None,
            )
        return result
