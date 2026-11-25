"""Local paired UniGaze / ETH-XGaze ResNet18 experiment. Space starts each block."""

import argparse
import hashlib
import json
import time
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

import numpy as np

from experiments.desktop_demo.protocol import UNIGAZE_POINTS
from experiments.unigaze.camera_stream import LatestCamera
from experiments.unigaze.mapping import Ridge
from experiments.unigaze.settings import ROOT

from .replay import metrics, pose_reference, small_motion

WEIGHTS = Path.home() / ".virtualenvs/eye-tracker-xgaze-20261027-support/model.safetensors"
DIGEST = "d1c91b2aa6a0c73856c16890d337afdecdb05563ed52182dfdb77742f1c856bc"
TARGETS = [
    (0.22, 0.36),
    (0.79, 0.63),
    (0.39, 0.82),
    (0.64, 0.18),
    (0.18, 0.72),
    (0.82, 0.32),
    (0.38, 0.19),
    (0.63, 0.81),
]
MODELS = ("unigaze", "eth_xgaze", "mgaze")


class ETHGaze:
    def __init__(self):
        import timm
        import torch
        from safetensors.torch import load_file

        if hashlib.sha256(WEIGHTS.read_bytes()).hexdigest() != DIGEST:
            raise ValueError("Unexpected ETH-XGaze checkpoint")
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = timm.create_model("resnet18", num_classes=2, pretrained=False)
        self.model.load_state_dict(load_file(str(WEIGHTS)), strict=True)
        self.model.eval().to(self.device)

    def __call__(self, tensor, rotation):
        from experiments.unigaze.geometry import denormalize

        angles = self.model(tensor).detach().cpu().numpy()[0]
        _, angles = denormalize(angles, rotation)
        return angles.tolist() if np.isfinite(angles).all() else None


def summarize(rows, size, stream_factory=None):
    if stream_factory is None:
        from experiments.unigaze.smoothing import StreamFilter

        stream_factory = StreamFilter

    train = [r for r in rows if r["phase"] == "calibration" and r["score"] and r["features"]]
    center, rotation = pose_reference(train)
    report = {}
    for phase in ("comfortable", "movement"):
        observations = [r for r in rows if r["phase"] == phase]
        scored = [r for r in observations if r["score"]]
        block = {
            "joint_valid": sum(r["features"] is not None for r in scored),
            "attempted": len(scored),
        }
        for name in MODELS:
            fit = Ridge(standardize=name != "mgaze")
            fit.fit([r["features"][name] for r in train], [r["target"] for r in train])
            stream = stream_factory()
            groups = {"raw": defaultdict(list), "filtered": defaultdict(list)}
            motion_errors = defaultdict(list)
            for r in observations:
                raw = fit.predict(r["features"][name]) if r["features"] else None
                filtered, _ = stream.update(raw, r["stamp"])
                if r["score"] and raw is not None:
                    for stage, value in (("raw", raw), ("filtered", filtered)):
                        groups[stage][tuple(r["target"])].append(
                            (value - np.array(r["target"])) * size
                        )
                    if small_motion(r, center, rotation):
                        motion_errors[tuple(r["target"])].append(
                            (filtered - np.asarray(r["target"])) * size
                        )
            block[name] = {stage: metrics(values) for stage, values in groups.items()}
            block[name]["small_motion_filtered"] = metrics(motion_errors) if motion_errors else None
        report[phase] = block
    return report


class Display:
    def __init__(self):
        import pygame

        self.pg = pygame
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Bakış modeli karşılaştırması")
        self.font = pygame.font.SysFont("Helvetica", 24)
        self.size = self.screen.get_size()

    def poll(self, button=None):
        start = False
        for event in self.pg.event.get():
            if event.type == self.pg.QUIT or (
                event.type == self.pg.KEYDOWN and event.key == self.pg.K_ESCAPE
            ):
                raise KeyboardInterrupt
            if event.type == self.pg.KEYDOWN and event.key == self.pg.K_SPACE:
                start = True
            if (
                button is not None
                and event.type == self.pg.MOUSEBUTTONUP
                and event.button == 1
                and button.collidepoint(event.pos)
            ):
                start = True
        return start

    def draw(self, lines, target=None, action=None):
        self.screen.fill((25, 29, 41))
        w, h = self.size
        for i, line in enumerate(lines):
            label = self.font.render(line, True, (235, 240, 248))
            y = 22 if target else h // 2 - 40
            self.screen.blit(label, label.get_rect(center=(w // 2, y + i * 40)))
        if target:
            point = (round(target[0] * w), round(target[1] * h))
            self.pg.draw.circle(self.screen, (110, 201, 254), point, 13, 3)
            self.pg.draw.circle(self.screen, (255, 255, 255), point, 4)
        button = None
        if action:
            button = self.pg.Rect(0, 0, 240, 54)
            button.midtop = (w // 2, h // 2 + len(lines) * 40 - 36)
            self.pg.draw.rect(self.screen, (110, 201, 254), button, border_radius=8)
            label = self.font.render(action, True, (25, 29, 41))
            self.screen.blit(label, label.get_rect(center=button.center))
        self.pg.display.flip()
        return button

    def wait(self, lines, action="Devam et"):
        button = self.draw([*lines, "Boşluk ile devam   ·   Esc ile çıkış"], action=action)
        while not self.poll(button):
            self.pg.time.wait(30)


def capture_block(display, pair, camera, phase, targets, rows):
    from experiments.unigaze.desktop_worker import eligible_features

    needed = 16 if phase == "calibration" else 14
    for i, target in enumerate(targets):
        while True:
            display.draw([f"{i + 1} / {len(targets)}"], target)
            onset = time.monotonic_ns()
            valid = 0
            attempt = []
            last = -1
            while valid < needed and time.monotonic_ns() - onset < 9_000_000_000:
                display.poll()
                if not display.pg.key.get_focused():
                    break
                last, stamp, frame = camera.read_after(last)
                if stamp < onset:
                    continue
                r = pair.process(frame, last, stamp)
                angles = eligible_features(r)
                features = None
                if angles is not None and r.get("comparison_angles") is not None:
                    features = dict(
                        unigaze=angles, eth_xgaze=r["comparison_angles"], mgaze=r["mgaze_features"]
                    )
                score = stamp - onset >= 1_000_000_000
                valid += int(score and features is not None)
                attempt.append(
                    dict(
                        phase=phase,
                        target=target,
                        stamp=stamp,
                        frame_id=last,
                        score=score,
                        features=features,
                        unigaze_head_rotation=r.get("unigaze_head_rotation"),
                        unigaze_face_center=r.get("unigaze_face_center"),
                    )
                )
            if valid == needed:
                rows.extend(attempt)
                break
            display.wait(["Bu noktayı tekrar deneyelim. Önce pencereye dönüp rahatça yerleş."])


def run(output, camera_index):
    import cv2

    from experiments.unigaze.paired import PairedExtractor
    from live_svr_demo import macbook_camera_index

    display = Display()
    rows = []
    try:
        display.wait(
            [
                "UniGaze ve ETH-XGaze aynı anda ölçülecek.",
                "Rahat otur. Hedefin ortasına bakabilirsin, gözünü kırpabilirsin.",
            ],
            action="Deneye başla",
        )
        display.draw(["Modeller hazırlanıyor…"])
        with ExitStack() as stack:
            pair = stack.enter_context(PairedExtractor(comparison=ETHGaze()))
            cap = cv2.VideoCapture(
                macbook_camera_index() if camera_index is None else camera_index,
                cv2.CAP_AVFOUNDATION,
            )
            if not cap.isOpened():
                cap.release()
                raise RuntimeError("Kamera açılamadı.")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera = LatestCamera(cap, lambda _: None)
            stack.callback(camera.close)
            capture_block(display, pair, camera, "calibration", UNIGAZE_POINTS, rows)
            display.wait(["Rahat oturduğun şekilde sekiz noktaya bak."])
            capture_block(display, pair, camera, "comfortable", TARGETS, rows)
            display.wait(
                [
                    "Yine noktaya bak. Bakarken başını hafifçe oynatabilirsin.",
                    "Büyük bir hareket yapman gerekmiyor.",
                ]
            )
            capture_block(display, pair, camera, "movement", TARGETS[4:] + TARGETS[:4], rows)
            provenance = pair.candidate.provenance
        from native_window_geometry import objc, rect, send

        logical_size = rect(send(objc.objc_getClass(b"NSScreen"), "mainScreen"), "frame")[2:]
        result = summarize(rows, np.asarray(logical_size))
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"comfortable-paired-{uuid4().hex[:12]}.json"
        path.write_text(
            json.dumps(
                dict(
                    screen_size=logical_size,
                    drawing_size=display.size,
                    eth_weights_sha256=DIGEST,
                    unigaze=provenance,
                    rows=rows,
                    report=result,
                ),
                allow_nan=False,
            )
        )
        print(path, flush=True)
        display.draw(
            [
                "Ölçüm tamamlandı.",
                *(
                    f"{name}: {result['movement'][name]['filtered']['mean_px']:.1f} px"
                    for name in MODELS
                ),
                "Kapatmak için boşluk veya Esc",
            ]
        )
        while not display.poll():
            display.pg.time.wait(40)
    finally:
        display.pg.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "validation/results")
    parser.add_argument("--camera-index", type=int)
    args = parser.parse_args()
    try:
        run(args.output, args.camera_index)
    except KeyboardInterrupt:
        pass
