"""MPIIFaceGaze ResNet-18 checkpoint and its local camera preprocessing."""

import hashlib

import cv2
import numpy as np
import torch
from safetensors.torch import load_file
from torch import nn
from torchvision.models import resnet18

from . import geometry
from .settings import HOME, INTRINSICS, mpiiface_weights

DIGEST = "094f1cdd95e4e8d1b11ae63df8404095df9b1ee082d0d7e720baf323d972d2c7"


class ResNetGaze(nn.Module):
    def __init__(self):
        super().__init__()
        self.feature_extractor = resnet18()
        for name in ("layer4", "avgpool", "fc"):
            delattr(self.feature_extractor, name)
        self.conv = nn.Conv2d(256, 1, 1)
        self.fc = nn.Linear(256 * 14 * 14, 2)

    def forward(self, image):
        backbone = self.feature_extractor
        image = backbone.maxpool(backbone.relu(backbone.bn1(backbone.conv1(image))))
        features = backbone.layer3(backbone.layer2(backbone.layer1(image)))
        return self.fc((features * self.conv(features).relu()).flatten(1))


class Extractor:
    def __init__(self):
        import face_alignment

        weights = mpiiface_weights()
        if hashlib.sha256(weights.read_bytes()).hexdigest() != DIGEST:
            raise ValueError("MPIIFaceGaze checkpoint hash mismatch")
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = ResNetGaze()
        self.model.load_state_dict(load_file(str(weights)), strict=True)
        self.model.eval().to(self.device)
        torch.set_num_threads(4)
        checkpoints = HOME / "support/torch/hub/checkpoints"
        torch.hub.set_dir(str(checkpoints.parent))
        self.detector = face_alignment.FaceAlignment(
            face_alignment.LandmarksType.TWO_D,
            device=self.device,
            flip_input=False,
            compile=False,
            face_detector_kwargs={"path_to_detector": str(checkpoints / "s3fd-619a316812.pth")},
        )
        self.camera, self.distortion = geometry.camera_parameters()
        self.provenance = dict(
            checkpoint="hysts/ptgaze-mpiifacegaze-resnet-simple",
            weights_sha256=DIGEST,
            camera_measurement_sha256=hashlib.sha256(INTRINSICS.read_bytes()).hexdigest(),
            face_alignment_version=face_alignment.__version__,
            device=self.device,
            preprocessing="Single FAN face, shared six-point PnP face center, 1600/1000, 224x224 BGR",
        )

    @torch.inference_mode()
    def observe(self, frame):
        corrected = geometry.prepare_frame(frame)
        rgb = cv2.cvtColor(cv2.resize(corrected, (320, 240)), cv2.COLOR_BGR2RGB)
        faces = self.detector.get_landmarks_from_image(rgb)
        if faces is None or len(faces) != 1:
            return (
                None,
                None,
                "multiple_faces" if faces is not None and len(faces) > 1 else "no_face",
            )
        landmarks = faces[0] * 2
        normalized = geometry.normalize_frame(corrected, landmarks)
        if normalized is None:
            return None, None, "invalid_face_geometry"
        _, _, pose = normalized
        eyes = landmarks[36:48].reshape(2, 6, 2)
        rays = (eyes.reshape(-1, 2) - self.camera[:2, 2]) / self.camera.diagonal()[:2]
        eye_preview, _ = cv2.projectPoints(
            np.c_[rays, np.ones(len(rays))], np.zeros(3), np.zeros(3), self.camera, self.distortion
        )
        eye_preview = eye_preview.reshape(2, 6, 2).tolist()
        patch, rotation, _, _, _, _ = geometry.native.normalize(
            corrected,
            landmarks,
            1600,
            1000,
            (224, 224),
            pose["center"],
            pose["hr"],
            pose["ht"],
            self.camera,
        )
        model_input = geometry.tensor_from_patch(patch)[:, [2, 1, 0]].to(self.device)
        angles = self.model(model_input)[0].cpu().numpy()
        _, angles = geometry.denormalize(angles, rotation)
        if not np.isfinite(angles).all():
            return None, eye_preview, "invalid_angles"
        return angles.tolist(), eye_preview, "valid"

    def close(self):
        self.detector = self.model = None
