"""GazeFollower components, unchanged model/calibration, user-paced local UI.

This is a feasibility probe, not a replacement for the production gaze subsystem.
No desktop actions, automatic recalibration, historical-data reads or image saving.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

UPSTREAM_COMMIT = "c61ffe20cd8c16b35291e5ac198d1b76c7702290"
ROOT = Path(__file__).resolve().parents[2]
SUPPORT = Path.home() / ".virtualenvs/eye-tracker-gazefollower-20261019-support"


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def new_session(root):
    folder = root / f"cagri-gazefollower-{datetime.now():%Y%m%d}-{uuid4().hex[:12]}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def eligible(face, gaze, threshold):
    return bool(
        face.status
        and face.can_gaze_estimation
        # Upstream may silently return BlazeFace's 12 approximate landmarks after
        # a Tasks failure. Its constant eye openness must not pass as valid data.
        and np.asarray(getattr(face, "face_landmarks", None)).shape == (478, 3)
        and gaze.status
        and gaze.features is not None
        and np.asarray(gaze.features).shape == (258,)
        and np.isfinite(gaze.features).all()
        and np.isfinite([face.left_eye_openness, face.right_eye_openness]).all()
        and min(face.left_eye_openness, face.right_eye_openness) > threshold
    )


def finite_point(point):
    if point is None or np.asarray(point).shape != (2,) or not np.isfinite(point).all():
        return None
    return [float(v) for v in point]


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["trial"]].append(row)
    trials = []
    for trial, group in groups.items():
        result = dict(trial=trial, target_px=group[0]["target_px"])
        for key, field in (("raw", "raw_px"), ("filtered", "filtered_px")):
            points = [finite_point(r[field]) for r in group]
            valid = [p for p in points if p is not None]
            stats = dict(
                attempts=len(group),
                valid=len(valid),
                availability=len(valid) / len(group),
                mean_error_px=None,
                p95_error_px=None,
                bias_px=None,
                centered_rms_px=None,
                within_30px_fraction=0.0,
            )
            if valid:
                errors = np.asarray(valid) - result["target_px"]
                distances = np.linalg.norm(errors, axis=1)
                bias = errors.mean(axis=0)
                stats.update(
                    mean_error_px=float(distances.mean()),
                    p95_error_px=float(np.percentile(distances, 95)),
                    bias_px=bias.tolist(),
                    centered_rms_px=float(np.sqrt(np.mean(np.sum((errors - bias) ** 2, axis=1)))),
                    within_30px_fraction=float(np.sum(distances <= 30) / len(group)),
                )
            result[key] = stats
        trials.append(result)
    enough = len(trials) == 6 and all(t["raw"]["valid"] >= 5 for t in trials)
    return dict(
        trials=trials,
        sufficient_data=enough,
        mean_error_px_equal_target_weight={
            k: float(np.mean([t[k]["mean_error_px"] for t in trials]))
            if enough and all(t[k]["mean_error_px"] is not None for t in trials)
            else None
            for k in ("raw", "filtered")
        },
        limitations="One instructed stable-seat session; fixation not independently verified. "
        "Unclipped pixel errors. Availability includes rejected frames. "
        "Training error is not evaluation accuracy. Not a controlled comparison to old sessions.",
    )


def read_frame(source):
    ok, frame = source.read()
    if not ok or frame is None:
        raise RuntimeError("Camera frame unavailable; stopped without fabricated frames")
    return frame


def enter_pressed(pg):
    entered = False
    for event in pg.event.get():
        if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
            raise InterruptedError("User cancelled")
        if event.type == pg.KEYDOWN and event.key in (pg.K_RETURN, pg.K_KP_ENTER):
            entered = True
    return entered


def wait_enter(pg, draw):
    draw()
    pg.event.clear()
    while not enter_pressed(pg):
        pg.time.wait(20)


def load_components(args):
    upstream = args.upstream.resolve()
    head = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != UPSTREAM_COMMIT:
        raise RuntimeError(f"Expected upstream {UPSTREAM_COMMIT}, found {head}")
    if subprocess.check_output(["git", "-C", str(upstream), "diff", "HEAD", "--"], text=True):
        raise RuntimeError("Upstream tracked files changed; inspect before running")
    if not args.face_model.is_file():
        raise FileNotFoundError("Prepare the local FaceLandmarker model before running")
    sys.path.insert(0, str(upstream))
    from gazefollower.calibration import CalibrationController, MultivariateRidgeCalibration
    from gazefollower.face_alignment import MediaPipeFaceAlignment
    from gazefollower.filter import HeuristicFilter
    from gazefollower.gaze_estimator import MGazeNetGazeEstimator
    from gazefollower.misc import DefaultConfig

    config = DefaultConfig()
    face = MediaPipeFaceAlignment(
        model_path=str(args.face_model), enable_filter=config.enable_face_filter
    )
    if not face.use_tasks_api:
        face.release()
        raise RuntimeError(
            "FaceLandmarker Tasks initialization failed; no silent detector fallback"
        )
    gaze = MGazeNetGazeEstimator()
    return (
        config,
        face,
        gaze,
        MultivariateRidgeCalibration(),
        HeuristicFilter,
        CalibrationController,
    )


def run(args):
    import cv2
    import pygame as pg

    config, face_model, gaze_model, calibration, filter_type, controller_type = load_components(
        args
    )
    cap = None
    folder = None
    status = "failed"
    try:
        if args.check:
            from gazefollower.misc import FaceInfo

            face = FaceInfo(
                status=True,
                can_gaze_estimation=True,
                img_w=640,
                img_h=480,
                face_rect=[100, 80, 300, 300],
                left_rect=[150, 150, 80, 40],
                right_rect=[280, 150, 80, 40],
            )
            start = time.perf_counter()
            result = gaze_model.detect(np.zeros((480, 640, 3), np.uint8), face)
            if not result.status or not np.isfinite(result.features).all():
                raise RuntimeError("MGazeNet synthetic inference failed")
            print(
                json.dumps(
                    dict(
                        check="passed_no_camera",
                        features=len(result.features),
                        inference_ms=(time.perf_counter() - start) * 1000,
                        upstream=UPSTREAM_COMMIT,
                    )
                ),
                flush=True,
            )
            return 0

        # Reuse only device enumeration; no legacy gaze estimator/model is executed.
        from live_svr_demo import macbook_camera_index

        index = args.camera_index if args.camera_index is not None else macbook_camera_index()
        pg.display.init()
        pg.font.init()
        screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        pg.display.set_caption("GazeFollower | MacBook")
        size = screen.get_size()
        config.screen_size = np.array(size)
        font = pg.font.SysFont("Arial", 24)
        cap = cv2.VideoCapture(
            index, cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
        )
        if not cap.isOpened():
            raise RuntimeError("Camera could not be opened")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        controller = controller_type(
            config.cali_mode,
            config.camera_position,
            config.screen_size,
            physical_screen_size=None,
            eye_blink_threshold=config.eye_blink_threshold,
        )

        def label(message, y):
            screen.blit(font.render(message, True, (245, 245, 245)), (30, y))

        def draw(target, message, blue=None):
            screen.fill((24, 24, 24))
            pg.draw.rect(screen, (190, 60, 60), screen.get_rect(), 2)
            pg.draw.circle(
                screen, (255, 225, 0), (round(target[0] * size[0]), round(target[1] * size[1])), 12
            )
            if blue is not None and 0 <= blue[0] < size[0] and 0 <= blue[1] < size[1]:
                pg.draw.circle(screen, (40, 150, 255), (round(blue[0]), round(blue[1])), 8)
            label(message, size[1] - 75)
            label(
                "Normal otur; sari noktaya bak. ESC: bitir. Fare ve tiklama kapali.", size[1] - 40
            )
            pg.display.flip()

        def observe():
            frame = read_frame(cap)
            captured_at = time.monotonic()
            bgr = cv2.resize(frame, (640, 480))
            t0 = time.monotonic()
            # Detector documents BGR; MGazeNet receives RGB, as in upstream camera.capture.
            face = face_model.detect(time.time_ns(), bgr)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            gaze = gaze_model.detect(rgb, face)
            return rgb, face, gaze, (time.monotonic() - t0) * 1000, captured_at

        # Preview is live but unrecorded. Enter only advances to a second ready gate.
        print("PREVIEW: adjust placement, then ENTER", flush=True)
        pg.event.clear()
        while True:
            rgb, face, gaze, _, _ = observe()
            screen.fill((24, 24, 24))
            preview = pg.surfarray.make_surface(np.swapaxes(rgb, 0, 1))
            width = min(size[0] - 100, 960)
            height = min(size[1] - 180, int(width * 480 / 640))
            preview = pg.transform.smoothscale(preview, (int(height * 640 / 480), height))
            screen.blit(preview, ((size[0] - preview.get_width()) // 2, 70))
            label("KAMERA ONIZLEME | Yerles, sonra ENTER", 25)
            label(
                f"Yuz/goz verisi: {'HAZIR' if eligible(face, gaze, config.eye_blink_threshold) else 'BEKLENIYOR'}",
                size[1] - 85,
            )
            label("Kayit yok. ENTER: kalibrasyon hazirlik ekrani | ESC: iptal", size[1] - 45)
            pg.display.flip()
            if enter_pressed(pg):
                break
        wait_enter(pg, lambda: draw((0.5, 0.5), "13 NOKTA KALIBRASYON | Hazirsan tekrar ENTER"))
        folder = new_session(ROOT / "validation/results")
        print(f"SESSION: {folder}", flush=True)
        model_path = args.upstream / "gazefollower/res/model_weights/base.mnn"
        write_new(
            folder / "session.json",
            dict(
                upstream=UPSTREAM_COMMIT,
                model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
                face_model_sha256=hashlib.sha256(args.face_model.read_bytes()).hexdigest(),
                runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                model="public MGazeNet, trained on 7M images; not paper's 32M model",
                calibration="upstream 13 targets, 45 accepted frames/target, Ridge alpha=0.1",
                screen_size=list(size),
                input_size=[640, 480],
                camera_index=index,
                capture_size=[
                    cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                    cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                ],
                filter="upstream HeuristicFilter look_ahead=3",
                os_control=False,
                calibration_feedback_hidden=True,
                evaluation_feedback_hidden=True,
                fallback_frames_rejected=True,
            ),
        )
        controller.new_session()
        previous_index = -1
        target_started = time.monotonic()
        while controller.calibrating:
            if controller._current_index > config.cali_mode.value:
                controller.calibrating = False
                break
            controller.update_position()
            if controller._current_index != previous_index:
                previous_index = controller._current_index
                target_started = time.monotonic()
                draw(
                    (controller.x, controller.y),
                    f"KALIBRASYON {previous_index}/13 | Sari noktayi takip et",
                )
                controller._each_point_onset_time = time.time()
            if time.monotonic() - target_started > 15:
                raise RuntimeError("Calibration target timed out: insufficient usable eye frames")
            enter_pressed(pg)
            _, face, gaze, _, _ = observe()
            if not eligible(face, gaze, config.eye_blink_threshold):
                gaze.status = False
            controller.add_cali_feature(gaze, face)
        features = np.asarray(controller.feature_vectors, dtype=np.float32)
        labels = np.asarray(controller.label_vectors, dtype=np.float32)
        if features.shape != (13, 45, 258) or labels.shape != (13, 45, 2):
            raise RuntimeError(f"Incomplete calibration: {features.shape}, {labels.shape}")
        with (folder / "calibration.npz").open("xb") as stream:
            np.savez_compressed(stream, features=features, labels=labels)
        fitted, train_error, _ = calibration.calibrate(
            features.reshape(-1, 258), labels.reshape(-1, 2)
        )
        if not fitted or not np.isfinite(calibration.weights).all():
            raise RuntimeError("Upstream calibration did not produce finite weights")
        with (folder / "ridge_weights.npy").open("xb") as stream:
            np.save(stream, calibration.weights, allow_pickle=False)
        write_new(
            folder / "calibration-fit.json",
            dict(training_error_normalized=float(train_error), independent_accuracy=False),
        )

        targets = [controller.normalized_point[i - 1] for i in controller._six_vali_idx]
        wait_enter(pg, lambda: draw(targets[0], "6 HEDEF KONTROLU (~23 saniye) | Hazirsan ENTER"))
        rows = []
        smooth = filter_type()
        with (folder / "evaluation.jsonl").open("x") as stream:
            for trial, target in enumerate(targets, 1):
                draw(target, f"KONTROL {trial}/6 | Sadece sari noktaya bak")
                start = time.monotonic()
                while True:
                    enter_pressed(pg)
                    _, face, gaze, inference_ms, captured_at = observe()
                    elapsed = captured_at - start
                    if elapsed >= 3.8:
                        break
                    raw = filtered = None
                    if eligible(face, gaze, config.eye_blink_threshold):
                        ok, normalized = calibration.predict(
                            gaze.features, gaze.raw_gaze_coordinates
                        )
                        if ok:
                            raw = finite_point(controller.convert_to_pixel(normalized))
                        if raw is not None:
                            filtered = finite_point(smooth.filter_values(raw))
                    else:
                        smooth = filter_type()
                    if elapsed >= 0.8:
                        row = dict(
                            trial=trial,
                            seconds=elapsed,
                            target_px=(target * size).tolist(),
                            raw_px=raw,
                            filtered_px=filtered,
                            inference_ms=inference_ms,
                        )
                        rows.append(row)
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stream.flush()
        report = summarize(rows)
        write_new(folder / "report.json", report)
        print("RESULT: " + json.dumps(report["mean_error_px_equal_target_weight"]), flush=True)
        status = "completed"
        # A separate optional qualitative view, excluded from accuracy measurements.
        wait_enter(
            pg,
            lambda: draw((0.5, 0.5), "OLCUM BITTI | ENTER: sari/mavi canli goruntu | ESC: kapat"),
        )
        target_index = 0
        live_targets = [(0.5, 0.5)] + [tuple(p) for p in targets]
        smooth = filter_type()
        while True:
            if enter_pressed(pg):
                target_index = (target_index + 1) % len(live_targets)
            _, face, gaze, _, _ = observe()
            blue = None
            if eligible(face, gaze, config.eye_blink_threshold):
                ok, normalized = calibration.predict(gaze.features, gaze.raw_gaze_coordinates)
                point = finite_point(controller.convert_to_pixel(normalized)) if ok else None
                if point is not None:
                    blue = finite_point(smooth.filter_values(point))
            else:
                smooth = filter_type()
            draw(
                live_targets[target_index],
                "CANLI | ENTER: sonraki hedef | Sonuclar kaydedildi",
                blue,
            )
    except InterruptedError:
        if status != "completed":
            status = "cancelled"
        return 0
    finally:
        if cap is not None:
            cap.release()
        face_model.release()
        gaze_model.release()
        pg.quit()
        if folder is not None:
            write_new(folder / "completion.json", dict(status=status))
            print(f"SESSION {status}: {folder}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=SUPPORT / "upstream")
    parser.add_argument("--face-model", type=Path, default=SUPPORT / "face_landmarker.task")
    parser.add_argument("--camera-index", type=int)
    parser.add_argument(
        "--check", action="store_true", help="Synthetic model inference; no camera/window"
    )
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
