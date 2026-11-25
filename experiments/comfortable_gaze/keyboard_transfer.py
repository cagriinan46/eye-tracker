"""Paired, read-only gaze scoring on the real focus keyboard and a separate editor."""

import argparse
import json
import multiprocessing
import os
import queue
import threading
import time
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import AppKit as UI
import numpy as np
from Foundation import NSDate, NSDefaultRunLoopMode
from PyObjCTools import AppHelper

from experiments.desktop_demo.macos_keyboard import AX, FocusKeyboard, panel_rect
from experiments.desktop_demo.protocol import UNIGAZE_POINTS
from experiments.desktop_demo.unigaze_model import CameraModel
from experiments.unigaze.mapping import Ridge
from experiments.unigaze.settings import ROOT
from experiments.unigaze.smoothing import StreamFilter

from .local_residual import PersonalCorrection
from .replay import metrics

KEYS = ("ç", "e", "k", "z", "ü", "a", "m", "ı", "s", "g")
SETTLE_SECONDS = 3


def panel_process(pipe, editor_pid):
    app = UI.NSApplication.sharedApplication()
    app.setActivationPolicy_(UI.NSApplicationActivationPolicyAccessory)
    kb = FocusKeyboard()
    key = None
    progress = 0
    bar = UI.NSView.alloc().initWithFrame_(UI.NSZeroRect)
    bar.setWantsLayer_(True)
    bar.layer().setBackgroundColor_(UI.NSColor.labelColor().CGColor())

    def poll():
        nonlocal key, progress
        try:
            while pipe.poll():
                message = pipe.recv()
                if message is None:
                    AppHelper.stopEventLoop()
                    return
                key, progress = message
            if key is None:
                AppHelper.callLater(0.1, poll)
                return
            focus = kb.focused()
            if not focus or focus[0] != editor_pid:
                kb.target = None
                if kb.panel:
                    kb.panel.orderOut_(None)
                pipe.send((time.monotonic(), None, None))
            else:
                if focus != kb.target:
                    kb.target = focus
                    kb.fallback = UI.NSEvent.mouseLocation()
                    kb.build()
                rect = panel_rect(focus[1], kb.fallback)
                if not UI.NSEqualRects(rect, kb.panel.frame()):
                    kb.build(rect)
                bounds = None
                for button in kb.panel.contentView().subviews():
                    selected = button.identifier() == key
                    button.setBezelColor_(UI.NSColor.systemYellowColor() if selected else None)
                    if selected:
                        if bar.superview() != button:
                            bar.removeFromSuperview()
                            button.addSubview_(bar)
                        width = button.bounds().size.width - 8
                        bar.setFrame_(((4, 4), (width * max(0, progress) / 100, 3)))
                        if progress < 0:
                            button.setBezelColor_(UI.NSColor.systemOrangeColor())
                        r = kb.panel.convertRectToScreen_(button.frame())
                        h = UI.NSScreen.screens()[0].frame().size.height
                        bounds = [r.origin.x, h - UI.NSMaxY(r), r.size.width, r.size.height]
                kb.panel.displayIfNeeded()
                pipe.send((time.monotonic(), key, bounds))
        except (EOFError, BrokenPipeError):
            AppHelper.stopEventLoop()
            return
        AppHelper.callLater(0.1, poll)

    app.finishLaunching()
    pipe.send("ready")
    AppHelper.callAfter(poll)
    AppHelper.runEventLoop()


class Controls(UI.NSObject):
    def begin_(self, sender):
        self.started = True

    def windowShouldClose_(self, window):
        self.cancelled = True
        return False


class Editor:
    def __init__(self):
        self.app = UI.NSApplication.sharedApplication()
        self.app.setActivationPolicy_(UI.NSApplicationActivationPolicyRegular)
        self.controls = Controls.alloc().init()
        self.controls.started = self.controls.cancelled = False
        self.window = UI.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            ((100, 200), (700, 200)),
            UI.NSWindowStyleMaskTitled | UI.NSWindowStyleMaskClosable,
            UI.NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Masaüstü klavyesi · Bakış ölçümü")
        self.window.setDelegate_(self.controls)
        self.label = UI.NSTextField.wrappingLabelWithString_(
            "Önce 13 beyaz noktayı takip et. Klavye açılınca sarı tuşun ortasına bak. Çizgi dolunca sıradaki tuş yanar. Turuncu, kameranın göz verisi beklediğini gösterir."
        )
        self.label.setFont_(UI.NSFont.systemFontOfSize_(19))
        self.label.setFrame_(((20, 112), (660, 65)))
        self.window.contentView().addSubview_(self.label)
        self.field = UI.NSTextField.alloc().initWithFrame_(((20, 65), (660, 34)))
        self.field.setPlaceholderString_("Klavye ölçüm alanı")
        self.window.contentView().addSubview_(self.field)
        self.button = UI.NSButton.buttonWithTitle_target_action_(
            "Deneye başla", self.controls, "begin:"
        )
        self.button.setFrame_(((255, 12), (190, 40)))
        self.button.setKeyEquivalent_(" ")
        self.window.contentView().addSubview_(self.button)
        self.window.center()
        self.app.finishLaunching()
        self.window.makeKeyAndOrderFront_(None)
        self.app.activateIgnoringOtherApps_(True)
        frame = UI.NSScreen.screens()[0].frame()
        self.size = np.array(tuple(frame.size))
        self.overlay = UI.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, UI.NSWindowStyleMaskBorderless, UI.NSBackingStoreBuffered, False
        )
        self.overlay.setLevel_(UI.NSStatusWindowLevel)
        self.overlay.setBackgroundColor_(UI.NSColor.darkGrayColor())
        self.dot = UI.NSView.alloc().initWithFrame_(((0, 0), (10, 10)))
        self.dot.setWantsLayer_(True)
        self.dot.layer().setCornerRadius_(5)
        self.dot.layer().setBackgroundColor_(UI.NSColor.whiteColor().CGColor())
        self.overlay.contentView().addSubview_(self.dot)
        self.caption = UI.NSTextField.labelWithString_("")
        self.caption.setTextColor_(UI.NSColor.whiteColor())
        self.caption.setFrame_(((18, 10), (680, 24)))
        self.overlay.contentView().addSubview_(self.caption)

    def pump(self):
        for _ in range(32):
            event = self.app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                UI.NSEventMaskAny, NSDate.date(), NSDefaultRunLoopMode, True
            )
            if event is None:
                break
            if event.type() == UI.NSEventTypeKeyDown and event.keyCode() == 53:
                self.controls.cancelled = True
            self.app.sendEvent_(event)
        if self.controls.cancelled:
            raise KeyboardInterrupt
        self.app.updateWindows()

    def fixation(self, target):
        x, y = target * self.size
        self.dot.setFrameOrigin_((x - 5, self.size[1] - y - 5))
        self.overlay.orderFrontRegardless()
        self.overlay.display()


class CameraFeed:
    """Keep the editor's Cocoa event loop responsive to native AX requests."""

    def __init__(self, camera):
        self.camera = camera
        self.stop = threading.Event()
        self.frames = queue.Queue(maxsize=2)
        self.thread = threading.Thread(target=self.collect, daemon=True)
        self.thread.start()

    def collect(self):
        while not self.stop.is_set():
            try:
                frame = self.camera.read()
            except Exception as error:
                frame = error
            while not self.stop.is_set():
                try:
                    self.frames.put(frame, timeout=0.1)
                    break
                except queue.Full:
                    continue
            if isinstance(frame, Exception):
                return

    def read(self, ui):
        while True:
            ui.pump()
            try:
                frame = self.frames.get(timeout=0.008)
            except queue.Empty:
                continue
            if isinstance(frame, Exception):
                raise frame
            return frame

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)


def calibrate(ui, camera, checkpoint):
    x, y = [], []
    for index, target in enumerate(UNIGAZE_POINTS, 1):
        ui.fixation(np.array(target))
        onset = time.monotonic()
        start = len(x)
        while len(x) - start < 16:
            ui.pump()
            stamp, angles, _, _ = camera.read(ui)
            if not ui.app.isActive():
                ui.overlay.orderOut_(None)
                ui.label.setStringValue_("Kalibrasyona devam etmek için bu pencereye tıkla.")
                del x[start:]
                del y[start:]
                while not ui.app.isActive():
                    camera.read(ui)
                ui.fixation(np.array(target))
                onset = time.monotonic()
                continue
            if angles is not None and stamp >= onset + 1 and time.monotonic() - stamp <= 0.3:
                x.append(angles)
                y.append(target)
            note = (
                "Beyaz noktaya bak"
                if len(x) > start or time.monotonic() - onset < 2
                else "Yüzünü kameraya çevir"
            )
            if angles is None or time.monotonic() - stamp > 0.3:
                note = "Güncel göz verisi bekleniyor"
            ui.caption.setStringValue_(
                f"Kalibrasyon {index}/{len(UNIGAZE_POINTS)}   ·   {len(x) - start}/16   ·   {note}"
            )
    checkpoint.write_text(json.dumps(dict(size=ui.size.tolist(), x=x, y=y)))
    return fit_calibration(ui, checkpoint)


def fit_calibration(ui, checkpoint):
    data = json.loads(checkpoint.read_text())
    if data["size"] != ui.size.tolist():
        raise ValueError("Ekran boyutu değişti. Yeni kalibrasyon gerekiyor.")
    model = Ridge(standardize=True)
    x, y = np.asarray(data["x"]), np.asarray(data["y"])
    model.fit(x, y)
    correction = PersonalCorrection(model, x, y)
    ui.overlay.orderOut_(None)
    return model, correction


def measure(ui, camera, pipe, rows, model, correction):
    until = time.monotonic() + 10
    while not pipe.poll(0.015):
        ui.pump()
        if time.monotonic() > until:
            raise RuntimeError("Klavye işlemi açılamadı.")
    if pipe.recv() != "ready":
        raise RuntimeError("Klavye bağlantısı kurulamadı.")
    ui.window.makeKeyAndOrderFront_(None)
    ui.app.activateIgnoringOtherApps_(True)
    ui.window.makeFirstResponder_(ui.field)
    ui.label.setStringValue_("Klavye görünmüyorsa ölçüm alanına tıkla.")
    ui.label.setHidden_(True)
    for key in KEYS:
        last_message = None

        def show(progress):
            nonlocal last_message
            message = (key, progress)
            if message != last_message:
                pipe.send(message)
                last_message = message

        show(0)
        onset = bounds = None
        observation = (0, None, None)
        filters = [StreamFilter(), StreamFilter()]
        trial = []
        valid = 0
        while True:
            ui.pump()
            stamp, angles, _, _ = camera.read(ui)
            # Discard evidence whenever the highlighted key or its rectangle changes.
            while pipe.poll():
                observation = pipe.recv()
                seen, selected, rect = observation
                if selected != key or rect != bounds:
                    onset = seen
                    bounds = rect if selected == key else None
                    trial.clear()
                    valid = 0
                    for stream in filters:
                        stream.reset()
            seen, selected, rect = observation
            ui.label.setHidden_(bool(bounds) or not seen)
            if not bounds or onset is None or stamp < onset or time.monotonic() - seen > 0.4:
                show(0)
                continue
            raw = (
                model.predict(angles)
                if angles is not None and time.monotonic() - stamp <= 0.3
                else None
            )
            points = [
                stream.update(value, int(stamp * 1e9))[0]
                for stream, value in zip(
                    filters,
                    (raw, correction.correct(raw) if raw is not None else None),
                    strict=True,
                )
            ]
            if raw is None:
                show(-1)
                continue
            if stamp - onset < SETTLE_SECONDS:
                show(0)
            else:
                valid += 1
                progress = min((stamp - onset - SETTLE_SECONDS) / 2, valid / 5, 1)
                show(int(progress * 100))
                trial.append(
                    dict(
                        key=key,
                        rect=bounds,
                        stamp=stamp,
                        points=[
                            (np.asarray(v) * ui.size).tolist() if v is not None else None
                            for v in points
                        ],
                    )
                )
            if stamp - onset >= SETTLE_SECONDS + 2 and valid >= 5:
                rows.extend(trial)
                break


def summarize(rows):
    result = {}
    for index, name in enumerate(("baseline", "personal")):
        errors, hits = defaultdict(list), defaultdict(list)
        for row in rows:
            point = row["points"][index]
            if point is None:
                continue
            x, y, w, h = row["rect"]
            errors[row["key"]].append(np.asarray(point) - [x + w / 2, y + h / 2])
            hits[row["key"]].append(x <= point[0] < x + w and y <= point[1] < y + h)
        if hits:
            result[name] = dict(
                metrics(errors), correct_key=float(np.mean([np.mean(v) for v in hits.values()]))
            )
    return result


def run(output):
    ui = Editor()
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"keyboard-transfer-{uuid4().hex[:12]}.json"
    checkpoint = path.with_suffix(".calibration.json")
    rows = []
    status = "interrupted"
    try:
        while not ui.controls.started:
            ui.pump()
            time.sleep(0.02)
        if not AX.AXIsProcessTrusted():
            raise RuntimeError("Masaüstü klavyesi için macOS Erişilebilirlik izni gerekiyor.")
        ui.button.setHidden_(True)
        ui.label.setStringValue_("Kamera hazırlanıyor…")
        ui.window.display()
        camera = CameraModel()
        feed = CameraFeed(camera)
        try:
            model, correction = calibrate(ui, feed, checkpoint)
            parent, child = multiprocessing.Pipe()
            helper = multiprocessing.get_context("spawn").Process(
                target=panel_process, args=(child, os.getpid())
            )
            helper.start()
            child.close()
            try:
                measure(ui, feed, parent, rows, model, correction)
                status = "completed"
            finally:
                parent.close()
                helper.join(timeout=2)
                if helper.is_alive():
                    helper.terminate()
                    helper.join()
        finally:
            feed.close()
            camera.close()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        status = str(error)
    finally:
        ui.overlay.orderOut_(None)
    report = summarize(rows)
    path.write_text(
        json.dumps(
            dict(
                status=status,
                settle_seconds=SETTLE_SECONDS,
                screen_size=ui.size.tolist(),
                keys=KEYS,
                rows=rows,
                report=report,
            ),
            allow_nan=False,
        )
    )
    print(path, status, flush=True)
    if status != "interrupted":
        ui.label.setHidden_(False)
        ui.controls.started = False
        if status == "completed":
            base, personal = report["baseline"], report["personal"]
            ui.label.setStringValue_(
                f"Doğru tuş: %{100 * base['correct_key']:.0f} → %{100 * personal['correct_key']:.0f}  ·  "
                f"Merkeze uzaklık: {base['mean_px']:.1f} → {personal['mean_px']:.1f} px"
            )
        else:
            ui.label.setStringValue_(status)
        ui.button.setTitle_("Kapat")
        ui.button.setHidden_(False)
        while not ui.controls.started and not ui.controls.cancelled:
            ui.pump()
            time.sleep(0.03)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "validation/results")
    args = parser.parse_args()
    run(args.output)
