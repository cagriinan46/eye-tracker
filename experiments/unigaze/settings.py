"""Local prepared assets. No downloads, credential access or dependency installation."""

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path(
    os.environ.get(
        "EYE_TRACKER_UNIGAZE_HOME", ROOT / "validation/results/unigaze-preflight-kit-20261029"
    )
)
PYTHON = Path(os.environ.get("EYE_TRACKER_UNIGAZE_PYTHON", HOME / "venv/bin/python"))
INTRINSICS = Path(
    os.environ.get(
        "EYE_TRACKER_CAMERA_INTRINSICS",
        ROOT / "validation/results/phone-intrinsics-cdaef08c1c6a/completion.json",
    )
)
BASELINE_PYTHON = Path(
    os.environ.get(
        "EYE_TRACKER_MGAZE_PYTHON",
        Path.home() / ".virtualenvs/eye-tracker-gazefollower-20261019/bin/python",
    )
)
# Existing baseline loader owns this location; do not imply arbitrary paths work.
BASELINE_SUPPORT = Path.home() / ".virtualenvs/eye-tracker-gazefollower-20261019-support"


def validate_assets():
    paths = [
        PYTHON,
        BASELINE_PYTHON,
        INTRINSICS,
        HOME / "support/unigaze_b16_joint.safetensors",
        HOME / "support/upstream/unigaze/data/face_model.txt",
        HOME / "support/torch/hub/checkpoints/2DFAN4-11f355bf06.pth.tar",
        HOME / "support/torch/hub/checkpoints/s3fd-619a316812.pth",
    ]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise RuntimeError(
            "UniGaze yerel dosyaları eksik; kurulum yönergesini kontrol et: " + ", ".join(missing)
        )


def verify_sources():
    manifest = json.loads(Path(__file__).with_name("source-hashes.json").read_text())
    for name, expected in manifest.items():
        if hashlib.sha256((HOME / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError("UniGaze source differs from measured version: " + name)
    return manifest
