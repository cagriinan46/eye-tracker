"""Local diagnostic demo: fresh 25-target calibration, then frozen live predictions.

One MacBook camera supplies eye features and pitch/yaw/roll to two RBF SVRs.
Feedback is visible: this is not a blinded validation.
EMA smooths the displayed point. Raw predictions remain logged.
Optional --control-pointer enables desktop movement and dwell clicking.
No images, clipping of numerical model outputs, or refits.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from statistics import median
from uuid import uuid4

from experiments.vertical_signal_comparison.capture import SignalExtractor, measure_signals
from experiments.vertical_signal_comparison.protocol import build_schedule
from eye_tracker.actions.pointer import PointerController
from eye_tracker.gaze.calibration import SVRCalibrationSample, fit_svr
from eye_tracker.gaze.smoothing import EMASmoother
from eye_tracker.platform_adapters.pyautogui_pointer import PyAutoGUIPointer
from eye_tracker.vision.camera import OpenCVCameraSource
from validation.real_calibration import (
    SAMPLE_SECONDS,
    SETTLE_SECONDS,
    RecordingExtractor,
    RecordingSource,
    _draw_target,
    collect_presentation,
)
from validation.real_calibration import (
    open_target_window as legacy_open_target_window,
)

ROOT = Path(__file__).resolve().parent
MODEL = Path(
    os.environ.get("EYE_TRACKER_MODEL", str(Path(sys.prefix) / "models/face_landmarker.task"))
)
LIVE_TARGETS = tuple((x, y) for y in (0.2, 0.5, 0.8) for x in (0.2, 0.5, 0.8))


CAMERAS = ("macbook",)


def safe_features(row):
    # Reject before collection/aggregation and again before live inference.
    required = (
        "horizontal",
        "vertical",
        "head_pitch_deg",
        "head_yaw_deg",
        "head_roll_deg",
        "blink_left",
        "blink_right",
    )
    if row.get("status") != "usable":
        return None
    if any(not isinstance(row.get(k), (int, float)) or not isfinite(row[k]) for k in required):
        return None
    if max(row["blink_left"], row["blink_right"]) > 0.5:
        return None
    return {
        "horizontal": row["horizontal"],
        "vertical": row["vertical"],
        "pitch": row["head_pitch_deg"],
        "yaw": row["head_yaw_deg"],
        "roll": row["head_roll_deg"],
    }


def append_calibration_row(rows, row):
    """Discard blink/invalid frames before they become calibration records."""
    if safe_features(row) is None:
        return False
    rows.append(row)
    return True


def fit_calibration(rows, size):
    groups = defaultdict(list)
    for row in rows:
        if row["phase"] == "calibration" and row.get("camera") == "macbook":
            features = safe_features(row)
            if features is not None:
                groups[row["presentation"]].append((row, features))
    samples = []
    for group in groups.values():
        if len(group) < 5:
            continue
        first = group[0][0]
        samples.append(
            SVRCalibrationSample(
                median(f["horizontal"] for _, f in group),
                median(f["vertical"] for _, f in group),
                first["target_x"],
                first["target_y"],
                median(f["pitch"] for _, f in group),
                median(f["yaw"] for _, f in group),
                median(f["roll"] for _, f in group),
            )
        )
    if len(samples) < 20:
        raise ValueError(f"MacBook: only {len(samples)}/25 valid calibration targets; need >=20")
    return {
        "model": fit_svr(samples, screen_width=size[0], screen_height=size[1]),
        "calibration_targets": len(samples),
        "feature_medians": [
            dict(
                horizontal=r.horizontal_feature,
                vertical=r.vertical_feature,
                pitch=r.pitch,
                yaw=r.yaw,
                roll=r.roll,
                target_x=r.target_x,
                target_y=r.target_y,
            )
            for r in samples
        ],
    }


def predict_single(mapping, details):
    features = safe_features(details)
    if features is None:
        return {"point": None}
    model = mapping["model"]
    px, py = model.predict_pixels(
        features["horizontal"],
        features["vertical"],
        features["pitch"],
        features["yaw"],
        features["roll"],
    )
    return {"point": (px / model.screen_width, py / model.screen_height)}


EMA_ALPHA = 0.50


def smooth_prediction(prediction, smoother):
    """Smooth the single-camera display point; never overwrite raw model output."""
    point = prediction["point"]
    return {**prediction, "point": smoother.update(None if point is None else tuple(point))}


def mapping_metadata(mapping):
    """Models stay in memory; rows and exact fit configuration permit reproduction."""
    model = mapping["model"]
    params = model.svr_x.named_steps["svr"].get_params()
    return {
        "kind": "single-macbook-rbf-svr-five-features-25point-v6",
        "features": ["horizontal", "vertical", "pitch", "yaw", "roll"],
        "pose_units": "degrees",
        "blink_max": 0.5,
        "feature_medians": mapping["feature_medians"],
        "kernel": params["kernel"],
        "C": params["C"],
        "epsilon": params["epsilon"],
        "gamma": params["gamma"] if params["kernel"] != "linear" else None,
        "scaling": "StandardScaler inputs only; calibration only",
        "target_units": "pixels; epsilon=1 pixel",
        "calibration_targets": mapping["calibration_targets"],
        "screen_size": [model.screen_width, model.screen_height],
        "persisted_model": False,
    }


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        return None
    return value


def write_new(path, value):
    with path.open("x", encoding="utf-8") as destination:
        json.dump(clean(value), destination, indent=2, allow_nan=False)
        destination.write("\n")


def text(cv2, canvas, message, y, color=(225, 225, 225), scale=0.6):
    cv2.putText(canvas, message, (25, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2)


def draw_live(cv2, np, size, target, predictions, details, fps):
    width, height = size
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    text(cv2, canvas, "MacBook | Sari: hedef | Mavi: SVR + EMA", 32)
    text(cv2, canvas, "SPACE: sonraki hedef | Esc: bitir", height - 25)
    cv2.circle(canvas, (round(target[0] * width), round(target[1] * height)), 13, (0, 230, 255), -1)
    point = predictions["point"]
    if point is not None:
        pixel = (
            round(max(8 / width, min(1 - 8 / width, point[0])) * width),
            round(max(8 / height, min(1 - 8 / height, point[1])) * height),
        )
        if all(0 <= v <= 1 for v in point):
            cv2.circle(canvas, pixel, 10, (255, 150, 30), -1)
        else:
            cv2.drawMarker(canvas, pixel, (255, 150, 30), cv2.MARKER_TILTED_CROSS, 18, 2)
    else:
        text(cv2, canvas, "TAKIP YOK / GOZ KIRPMA", height - 90, (70, 170, 255))
    text(cv2, canvas, f"{fps:.1f} FPS | {details['macbook'].get('status', '?')}", height - 60)
    return canvas


def wait_ready(cv2, np, name, size, target, title):
    width, height = size
    canvas = np.full((height, width, 3), 24, dtype=np.uint8)
    cv2.circle(canvas, (round(target[0] * width), round(target[1] * height)), 13, (0, 230, 255), -1)
    text(cv2, canvas, title, height - 120, (0, 230, 255))
    text(
        cv2,
        canvas,
        "Noktaya bak. Hazirsan ENTER. Sureler henuz baslamadi. Esc: iptal.",
        height - 80,
    )
    print(f"READY: {title}; waiting for Enter", flush=True)
    while True:
        cv2.imshow(name, canvas)
        key = cv2.waitKey(25) & 255
        if key in (27, ord("q")) or cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1:
            raise InterruptedError("Ready screen cancelled")
        if key in (10, 13):
            return


def desktop_region(cv2, name, screen_height):
    """Locate the calibrated image in OS logical desktop coordinates."""
    if sys.platform == "darwin":
        from AppKit import NSApplication

        for window in NSApplication.sharedApplication().windows():
            if window.title() == name:
                view = window.contentView().imageView()
                local = view.convertRect_toView_(view.bounds(), None)
                rect = window.convertRectToScreen_(local)
                return (
                    rect.origin.x,
                    screen_height - rect.origin.y - rect.size.height,
                    rect.size.width,
                    rect.size.height,
                )
        raise RuntimeError("Cannot determine calibrated window position")
    return cv2.getWindowImageRect(name)


def native_window_geometry(name):
    if sys.platform != "darwin":
        return None
    from native_window_geometry import geometry

    windows = geometry(name)
    if len(windows) != 1:
        raise RuntimeError("Could not verify the native target window")
    return windows[0]


def open_fitted_target_window(cv2, np, name, screen_size):
    width, height = legacy_open_target_window(cv2, np, name, screen_size)
    native = native_window_geometry(name)
    if native is not None:
        _, _, width, height = native["content_bounds"]
        width, height = round(width), round(height)
        if width <= 0 or height <= 0:
            raise RuntimeError("Native drawable area is empty")
        canvas = np.full((height, width, 3), 24, dtype=np.uint8)
        cv2.imshow(name, canvas)
        cv2.resizeWindow(name, width, height)
        cv2.waitKey(1)
        actual = native_window_geometry(name)
        image = actual["image_frame"]
        bounds = actual["content_bounds"]
        if any(abs(a - b) > 1 for a, b in zip(image, bounds)):
            raise RuntimeError("Target image still does not fill the drawable window")
    print(f"DISPLAY requested={screen_size} drawable={width}x{height}", flush=True)
    return width, height


def select_macbook_camera(devices):
    matches = [
        i
        for i, (_, name) in enumerate(sorted(devices))
        if "facetime" in name.lower() or "built-in" in name.lower() or "built in" in name.lower()
    ]
    if len(matches) != 1:
        raise RuntimeError("Cannot uniquely identify MacBook camera; supply --camera-index")
    return matches[0]


def macbook_camera_index():
    # OpenCV AVFoundation enumerates video devices sorted by uniqueID.
    import ctypes as C

    from native_window_geometry import objc, send

    C.CDLL("/System/Library/Frameworks/AVFoundation.framework/AVFoundation")
    media = send(
        objc.objc_getClass(b"NSString"),
        "stringWithUTF8String:",
        argtypes=(C.c_char_p,),
        args=(b"vide",),
    )
    devices = send(
        objc.objc_getClass(b"AVCaptureDevice"),
        "devicesWithMediaType:",
        argtypes=(C.c_void_p,),
        args=(media,),
    )
    pairs = []
    for i in range(send(devices, "count", C.c_ulong)):
        device = send(devices, "objectAtIndex:", argtypes=(C.c_ulong,), args=(i,))
        name = send(send(device, "localizedName"), "UTF8String", C.c_char_p).decode()
        uid = send(send(device, "uniqueID"), "UTF8String", C.c_char_p).decode()
        pairs.append((uid, name))
    index = select_macbook_camera(pairs)
    print(f"MACBOOK CAMERA: index={index}, name={sorted(pairs)[index][1]}", flush=True)
    return index


def wait_for_single_camera(cv2, np, name, size, source, extractor):
    width, height = size
    consecutive = 0
    while True:
        canvas = np.full((height, width, 3), 24, dtype=np.uint8)
        frame = source.read()
        valid = False
        if frame is not None:
            observation = extractor.extract(frame)
            from eye_tracker.vision.eye_features import extract_binocular_features
            from eye_tracker.vision.eye_topology import eye_geometry_from_observation

            try:
                geometry = eye_geometry_from_observation(observation)
                features = (
                    None
                    if geometry is None
                    else extract_binocular_features(*geometry, frame.width, frame.height)
                )
                valid = (
                    features is not None
                    and safe_features(
                        {
                            "status": "usable",
                            "horizontal": features.horizontal,
                            "vertical": features.vertical,
                            **(extractor.last_signals or {}),
                        }
                    )
                    is not None
                )
            except ValueError:
                valid = False
            image = frame.payload
            ratio = min((width - 60) / image.shape[1], (height - 180) / image.shape[0])
            rw, rh = round(image.shape[1] * ratio), round(image.shape[0] * ratio)
            x, y = (width - rw) // 2, 80 + (height - 180 - rh) // 2
            canvas[y : y + rh, x : x + rw] = cv2.resize(image, (rw, rh))
        consecutive = consecutive + 1 if valid else 0
        text(cv2, canvas, "MACBOOK KAMERA - Konumunu ayarla", 35)
        text(
            cv2,
            canvas,
            "GOZ TAKIBI HAZIR - ENTER: hedef ekrani"
            if consecutive >= 5
            else "YUZ / GOZ TAKIBI BEKLENIYOR",
            height - 55,
        )
        cv2.imshow(name, canvas)
        key = cv2.waitKey(1) & 255
        if key in (27, ord("q")) or cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1:
            raise InterruptedError("Camera preview cancelled")
        if key in (10, 13) and consecutive >= 5:
            return


def run(args):
    import cv2
    import numpy as np

    if args.camera_index is None:
        args.camera_index = macbook_camera_index()
    if not MODEL.is_file():
        raise FileNotFoundError(MODEL)
    folder = (
        ROOT
        / "validation/results"
        / ("cagri-live-macbook-svr-" + datetime.now().strftime("%Y%m%d") + "-" + uuid4().hex[:8])
    )
    folder.mkdir(parents=True)
    metadata = {
        "kind": "diagnostic-live-macbook-svr-v2",
        "participant": "cagri-live",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "y": "Single MacBook RBF SVR on horizontal/vertical/pitch/yaw/roll",
        "x": "Single MacBook RBF SVR on horizontal/vertical/pitch/yaw/roll",
        "calibration": "25 targets from seed77 schedule; only calibration phase; 0.8s+1.2s",
        "live": "Raw model predictions logged; EMA on single-camera output; no refits or snapping",
        "smoothing": {"kind": "EMA", "alpha": EMA_ALPHA, "reset_on_loss": True},
        "desktop_control": args.control_pointer,
        "dwell": {"radius_pixels": 30, "seconds": 1.5, "rearm": "leave circle"},
        "limitations": "Visible feedback; no held-out validation, no success claim; no population evidence",
        "gate": "Camera preview Enter, actual target screen separate Enter, live stage Enter",
        "camera_indices": {"macbook": args.camera_index},
        "source_sha256": {},
    }
    paths = [
        Path(__file__),
        Path(__file__).with_name("native_window_geometry.py"),
        MODEL,
        ROOT / "src/eye_tracker/gaze/calibration.py",
        ROOT / "src/eye_tracker/gaze/smoothing.py",
        ROOT / "src/eye_tracker/actions/pointer.py",
        ROOT / "src/eye_tracker/intent/dwell.py",
        ROOT / "src/eye_tracker/platform_adapters/pyautogui_pointer.py",
        ROOT / "experiments/vertical_signal_comparison/protocol.py",
        ROOT / "experiments/vertical_signal_comparison/capture.py",
    ]
    metadata["source_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    write_new(folder / "session.json", metadata)
    print(f"NEW LIVE SESSION: {folder}", flush=True)
    name = "Cagri - Linear SVR live gaze demo"
    sources = {c: OpenCVCameraSource(i) for c, i in metadata["camera_indices"].items()}
    recorded = {c: RecordingSource(source) for c, source in sources.items()}
    rows = []
    status = "initializing"
    live_count = 0
    pointer_backend = None
    controller = None
    try:
        size = open_fitted_target_window(cv2, np, name, (1512, 982))
        for source in sources.values():
            source.open()
        with ExitStack() as stack:
            signals = {c: stack.enter_context(SignalExtractor(MODEL)) for c in CAMERAS}
            extractors = {c: RecordingExtractor(signals[c]) for c in CAMERAS}
            wait_for_single_camera(cv2, np, name, size, sources["macbook"], signals["macbook"])
            schedule = tuple(p for p in build_schedule(seed=77) if p.phase == "calibration")
            first = schedule[0].target
            wait_ready(
                cv2, np, name, size, (first.x, first.y), "25 NOKTA KALIBRASYON - yaklasik 50 saniye"
            )
            status = "calibrating"
            started = time.monotonic()
            loop = 0
            for position, presentation in enumerate(schedule, start=1):
                sampling = False

                def show(current, is_sampling, remaining):
                    nonlocal sampling
                    sampling = is_sampling
                    cv2.imshow(
                        name,
                        _draw_target(
                            cv2, np, current, position, len(schedule), is_sampling, remaining, *size
                        ),
                    )
                    key = cv2.waitKey(1) & 255
                    return (
                        key in (27, ord("q"))
                        or cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
                    )

                def measure():
                    nonlocal loop
                    loop += 1
                    results = []
                    for camera in CAMERAS:
                        result, details = measure_signals(
                            recorded[camera], extractors[camera], signals[camera]
                        )
                        results.append(result)
                        if sampling:
                            append_calibration_row(
                                rows,
                                {
                                    "camera": camera,
                                    "loop": loop,
                                    "presentation": position,
                                    "phase": "calibration",
                                    "target_id": presentation.target.name,
                                    "target_x": presentation.target.x,
                                    "target_y": presentation.target.y,
                                    "trial_number": presentation.trial,
                                    "monotonic_seconds": time.monotonic() - started,
                                    **details,
                                },
                            )
                    return results[0]

                collect_presentation(presentation, measure, show)
            mapping = fit_calibration(rows, size)
            write_new(
                folder / "calibration.json",
                {
                    "rows": rows,
                    "mapping": mapping_metadata(mapping),
                    "window_image_area": size,
                    "settle_seconds": SETTLE_SECONDS,
                    "sample_seconds": SAMPLE_SECONDS,
                },
            )
            print(
                f"CALIBRATION SAVED: {mapping['calibration_targets']}/25 MacBook targets",
                flush=True,
            )
            target = [0.5, 0.5]
            target_index = 4
            if args.control_pointer:
                pointer_backend = PyAutoGUIPointer()
                region = desktop_region(cv2, name, pointer_backend.screen_size[1])
                controller = PointerController(pointer_backend, region)
                write_new(
                    folder / "desktop.json",
                    {"region": region, "screen_size": pointer_backend.screen_size},
                )
            wait_ready(
                cv2,
                np,
                name,
                size,
                target,
                "ENTER: GERCEK FARE + 1.5sn TIKLAMA | ESC: DURDUR"
                if controller
                else "KALIBRASYON TAMAM - ENTER: canli sari / mavi nokta",
            )
            state = {"target": target, "changed": False}

            def mouse(event, x, y, flags, param):
                if controller is None and event == cv2.EVENT_LBUTTONDOWN:
                    state["target"] = [max(0, min(1, x / size[0])), max(0, min(1, y / size[1]))]
                    state["changed"] = True

            cv2.setMouseCallback(name, mouse)
            status = "live"
            live_started = time.monotonic()
            smoother = EMASmoother(alpha=EMA_ALPHA)
            print(
                "LIVE STARTED: Space=next target, Esc=save and exit",
                flush=True,
            )
            with (folder / "live.jsonl").open("x", encoding="utf-8") as destination:
                while True:
                    if controller:
                        pointer_backend.check_stop()
                    details = {}
                    for camera in CAMERAS:
                        _, details[camera] = measure_signals(
                            recorded[camera], extractors[camera], signals[camera]
                        )
                    prediction = predict_single(mapping, details["macbook"])
                    raw_point = prediction["point"]
                    if raw_point is not None:
                        horizontal = details["macbook"]["horizontal"]
                        vertical = details["macbook"]["vertical"]
                        pixel_x = raw_point[0] * mapping["model"].screen_width
                        pixel_y = raw_point[1] * mapping["model"].screen_height
                        print(
                            f"Ham Girdi -> H: {horizontal:.4f}, V: {vertical:.4f} | "
                            f"Pitch: {details['macbook']['head_pitch_deg']:.2f}, "
                            f"Yaw: {details['macbook']['head_yaw_deg']:.2f}, "
                            f"Roll: {details['macbook']['head_roll_deg']:.2f} | "
                            f"Tahmin Edilen Piksel -> X: {pixel_x:.2f}, Y: {pixel_y:.2f}",
                            flush=True,
                        )
                    else:
                        print(
                            "Ham Girdi -> "
                            f"H: {details['macbook'].get('horizontal')}, "
                            f"V: {details['macbook'].get('vertical')} | "
                            "Tahmin Edilen Piksel -> YOK (takip kaybi / gecersiz veri / goz kirpma)",
                            flush=True,
                        )
                    displayed_prediction = smooth_prediction(prediction, smoother)
                    desktop_action = None
                    if controller:
                        current_region = desktop_region(cv2, name, pointer_backend.screen_size[1])
                        if any(abs(a - b) > 1 for a, b in zip(current_region, controller.region)):
                            raise InterruptedError(
                                "Calibration window moved; recalibration required"
                            )
                        desktop_action = controller.update(
                            time.monotonic(), displayed_prediction["point"]
                        )
                    elapsed = time.monotonic() - live_started
                    live_count += 1
                    destination.write(
                        json.dumps(
                            clean(
                                {
                                    "loop": live_count,
                                    "seconds": elapsed,
                                    "target": list(state["target"]),
                                    "target_changed": state["changed"],
                                    "predictions": prediction,
                                    "displayed_predictions": displayed_prediction,
                                    "desktop_action": desktop_action,
                                    "signals": details,
                                }
                            ),
                            allow_nan=False,
                        )
                        + "\n"
                    )
                    state["changed"] = False
                    if live_count % 15 == 0:
                        destination.flush()
                    cv2.imshow(
                        name,
                        draw_live(
                            cv2,
                            np,
                            size,
                            state["target"],
                            displayed_prediction,
                            details,
                            live_count / max(elapsed, 0.001),
                        ),
                    )
                    key = cv2.waitKey(1) & 255
                    if (
                        key in (27, ord("q"))
                        or cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
                    ):
                        status = "completed"
                        break
                    if key == ord(" "):
                        target_index = (target_index + 1) % len(LIVE_TARGETS)
                        state["target"] = list(LIVE_TARGETS[target_index])
                        state["changed"] = True
    except (InterruptedError, KeyboardInterrupt):
        status = "cancelled"
    except Exception:
        status = "failed"
        raise
    finally:
        if pointer_backend is not None:
            pointer_backend.close()
        for source in sources.values():
            source.close()
        cv2.destroyAllWindows()
        if rows and not (folder / "calibration.json").exists():
            write_new(folder / "calibration-partial.json", {"rows": rows, "status": status})
        write_new(
            folder / "completion.json",
            {
                "status": status,
                "live_loops": live_count,
                "calibration_rows": len(rows),
                "cameras": {
                    c: {
                        "reads": r.reads,
                        "failed_reads": r.failed_reads,
                        "resolution": r.resolution,
                    }
                    for c, r in recorded.items()
                },
            },
        )
        print(f"LIVE SESSION {status}: {folder}", flush=True)
    return 0 if status == "completed" else 130


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--camera-index", type=int, default=None, help="Override automatic MacBook camera selection"
    )
    parser.add_argument(
        "--control-pointer",
        action="store_true",
        help="Enable real pointer movement and 1.5-second dwell left click",
    )
    args = parser.parse_args()
    if args.camera_index is not None and args.camera_index < 0:
        parser.error("Camera index must be nonnegative")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
