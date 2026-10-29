"""Camera-free UniGaze research adapter. Images stay in caller memory.

Input landmarks: native 68-point face_alignment convention, detected on the
undistorted full frame. No MediaPipe-to-68 substitution. No detector/download.
"""

import hashlib
import importlib.util
import json
import sys

import cv2
import numpy as np
import torch
from safetensors.torch import load_file
from torchvision import transforms

from .settings import HOME as HERE
from .settings import INTRINSICS, verify_sources

UPSTREAM = HERE / "support/upstream"
REVISION = "9c240fbe33f3d6146970a77b7c8fa06a7e60019e"
WEIGHT_SHA = "2580d707b1395840ecabe7906e2cb35705f38c4ddb0be9c3c38ebb2d5546ffb8"

verify_sources()
sys.path.insert(0, str(UPSTREAM / "unigaze_easy/src"))
from unigaze.models.mae_gaze import MAE_Gaze  # noqa: E402 -- pinned local source


def source_module(name, path):
    spec = importlib.util.spec_from_file_location(name, UPSTREAM / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = source_module("native_normalize", "unigaze/gazelib/gaze/normalize.py")
labels = source_module("native_labels", "unigaze/gazelib/label_transform.py")
FACE_MODEL = np.loadtxt(UPSTREAM / "unigaze/data/face_model.txt")
FACE_SIX = FACE_MODEL[[20, 23, 26, 29, 15, 19]].reshape(6, 1, 3)
LANDMARK_SIX = [36, 39, 42, 45, 31, 35]
TRANSFORM = transforms.Compose(
    [
        transforms.ToPILImage(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


def camera_parameters():
    path = INTRINSICS
    data = json.loads(path.read_text())
    report = data["report"]
    if data["status"] != "screening_passed" or not report["accepted"]:
        raise ValueError("Camera calibration not accepted")
    if report["image_size"] != [640, 480]:
        raise ValueError("Camera size mismatch")
    return np.array(report["camera_matrix"]), np.array(report["distortion_coefficients"])


def prepare_frame(raw):
    if raw.shape != (480, 640, 3) or raw.dtype != np.uint8:
        raise ValueError("Expected unmirrored native 640x480 uint8 BGR")
    k, dist = camera_parameters()
    return cv2.undistort(raw, k, dist, None, k)


def normalize_frame(corrected, landmarks):
    """Exactly one face's landmarks on prepare_frame output; K unchanged, D=0."""
    if corrected.shape != (480, 640, 3) or corrected.dtype != np.uint8:
        raise ValueError("Expected corrected 640x480 uint8 BGR")
    if landmarks is None:
        return None
    lm = np.asarray(landmarks, dtype=float)
    if lm.shape != (68, 2) or not np.isfinite(lm).all():
        return None
    if (lm < 0).any() or (lm[:, 0] >= 640).any() or (lm[:, 1] >= 480).any():
        return None
    if np.linalg.matrix_rank(lm - lm.mean(0)) < 2:
        return None
    k, _ = camera_parameters()
    pts = lm[LANDMARK_SIX].reshape(6, 1, 2)
    ok, hr, ht = cv2.solvePnP(FACE_SIX, pts, k, np.zeros(5), flags=cv2.SOLVEPNP_EPNP)
    if not ok:
        return None
    ok, hr, ht = cv2.solvePnP(FACE_SIX, pts, k, np.zeros(5), hr, ht, True)
    if not ok or not np.isfinite(hr).all() or not np.isfinite(ht).all():
        return None
    rot = cv2.Rodrigues(hr)[0]
    center, _ = labels.get_face_center_by_nose(rot, ht, FACE_MODEL)
    if center[2, 0] <= 0 or np.linalg.norm(np.cross(center.ravel(), rot[:, 0])) < 1e-8:
        return None
    patch, rotation, norm_head, _, _, warp = native.normalize(
        corrected, lm, 960, 600, (224, 224), center, hr, ht, k
    )
    head_angles = np.array(
        [np.arcsin(np.clip(norm_head[1, 2], -1, 1)), np.arctan2(norm_head[0, 2], norm_head[2, 2])]
    )
    if np.linalg.norm(head_angles) > np.deg2rad(80):
        return None
    if not np.isfinite(rotation).all() or not np.isfinite(warp).all():
        return None
    return patch, rotation, dict(hr=hr, ht=ht, center=center, warp=warp)


def tensor_from_patch(patch):
    if patch.shape != (224, 224, 3) or patch.dtype != np.uint8:
        raise ValueError("Expected normalized 224x224 uint8 BGR patch")
    return TRANSFORM(patch[:, :, [2, 1, 0]]).unsqueeze(0)


def denormalize(angles, rotation):
    pitch, yaw = np.asarray(angles, float)
    vector = np.array([np.cos(pitch) * np.sin(yaw), np.sin(pitch), np.cos(pitch) * np.cos(yaw)])
    vector = np.linalg.inv(rotation) @ vector
    vector /= np.linalg.norm(vector)
    return vector, np.array(
        [np.arcsin(np.clip(vector[1], -1, 1)), np.arctan2(vector[0], vector[2])]
    )


def load_model(device="cpu"):
    path = HERE / "support/unigaze_b16_joint.safetensors"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != 346291616 or digest != WEIGHT_SHA:
        raise ValueError("Official pinned checkpoint size/hash mismatch")
    model = MAE_Gaze(model_type="vit_b_16", custom_pretrained_path=None)
    weights = load_file(str(path), device="cpu")
    expected = model.state_dict()
    if weights.keys() != expected.keys():
        raise ValueError("Checkpoint keys mismatch")
    for name, tensor in weights.items():
        if tensor.shape != expected[name].shape or not torch.isfinite(tensor).all():
            raise ValueError("Invalid checkpoint tensor: " + name)
    model.load_state_dict(weights, strict=True)
    return model.to(device).eval()
