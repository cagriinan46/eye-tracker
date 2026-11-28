"""Main-thread desktop pointer and command panels for the calibrated session."""

import logging
import threading
import time
from math import isfinite

import AppKit as UI
import ApplicationServices as AX
import objc
import Quartz
from PyObjCTools import AppHelper

from eye_tracker.actions.window_pointer import PointerSmoother
from eye_tracker.app.semantic_preview import PreviewFeed
from eye_tracker.intent.targets import TargetRect
from eye_tracker.platform_adapters.macos_accessibility import MacOSAccessibility
from eye_tracker.platform_adapters.macos_outline import _screen_matches

from .desktop_gaze_filter import DesktopGazeFilter
from .eye_gestures import FACE_GESTURES, EyeGestures
from .hold_key import R_KEY_CODE, HoldKey
from .macos_keyboard import FocusKeyboard, WebAccessibility
from .macos_targets import Dock, window_targets
from .macos_toolbar import SCROLL_STOP_HINTS, Toolbar, nonactivating_panel
from .ring_magnet import RingMagnet

logger = logging.getLogger(__name__)
HID = Quartz.kCGEventSourceStateCombinedSessionState
GESTURE_LABELS = {
    "wink_right": "Sağ göz kırpma",
    "wink_left": "Sol göz kırpma",
    "smile": "Gülümseme",
    "mouth_open": "Ağız açma",
    "pucker": "Dudak büzme",
    "brows": "Kaş kaldırma",
}
ACTION_LABELS = {
    "left": "sol tık",
    "right": "sağ tık",
    "double": "çift tık",
    "scroll": "kaydırma",
    "keyboard": "klavye",
    "menu": "menü",
    "off": "kapalı",
}


def desktop_point(point, viewport, size):
    if point is None or len(point) != 2 or not all(isfinite(v) for v in point):
        return None
    x, y, width, height = viewport
    return (
        max(0, min(size[0] - 1, x + point[0] * width)),
        max(0, min(size[1] - 1, y + point[1] * height)),
    )


class MacOSDesktop:
    def __init__(self, window, api):
        self.window, self.api = window, api
        self.toolbar = self.ring = self.feed = None
        self.closed = False
        self.main_window_hidden = False
        self.escape_down = False
        self.recentre_key = HoldKey()
        self.gestures = EyeGestures()
        self.wink_point = self.smile_point = None
        self.web_accessibility = WebAccessibility()
        self.magnet = RingMagnet()
        self.fixation = DesktopGazeFilter()
        self.aim = PointerSmoother(fast=0.065, slow=0.16)
        self.cursor = PointerSmoother(fast=0.055, slow=0.12)

    def start(self):
        AppHelper.callAfter(self.tick)

    def show_main_window(self):
        native = self.window.native
        if native is not None and not self.closed:
            if native.isMiniaturized():
                native.deminiaturize_(None)
            native.makeKeyAndOrderFront_(None)
            UI.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.main_window_hidden = False

    def native_page(self, page):
        self.api.request_native_page(page)
        self.show_main_window()

    def prepare(self):
        if not AX.AXIsProcessTrusted():
            raise RuntimeError("Masaüstü kontrolü için macOS Erişilebilirlik iznini aç.")
        screens = UI.NSScreen.screens()
        self.size = tuple(screens[0].frame().size)
        if not _screen_matches(UI, self.size):
            raise RuntimeError("Masaüstü kontrolü tek ekranla çalışır.")
        native = self.window.native
        if native is None:
            raise RuntimeError("Eye Tracker penceresi hazır değil.")
        content = native.convertRectToScreen_(native.contentView().frame())
        width, height = content.size
        self.viewport = (content.origin.x, self.size[1] - UI.NSMaxY(content), width, height)
        self.desktop_rect = TargetRect(0, 0, *self.size)

        radius = self.magnet.radius
        diameter = radius * 2
        self.ring = nonactivating_panel((diameter, diameter))
        self.ring.setHasShadow_(False)
        self.ring.setIgnoresMouseEvents_(True)
        self.ring.setAccessibilityElement_(False)
        self.ring.setAccessibilityChildren_([])
        view = UI.NSView.alloc().initWithFrame_(((0, 0), (diameter, diameter)))
        view.setWantsLayer_(True)
        self.ring_layer = view.layer()
        self.ring_layer.setCornerRadius_(radius)
        self.ring_layer.setBorderColor_(UI.NSColor.whiteColor().CGColor())
        self.ring_layer.setBorderWidth_(2)
        self.ring.setContentView_(view)

        keyboard = FocusKeyboard(
            self.api._keyboard_suggester(),
            self.api._word_suggestions_enabled,
            self.api.keyboard_size,
        )
        head = getattr(self.api, "supports_recentre", lambda: False)()
        self.toolbar = Toolbar(
            self.size,
            lambda: self.native_page("calibration"),
            lambda: self.native_page("settings"),
            keyboard,
            recentre=(lambda: self.api.command("recentre").get("ok", False)) if head else None,
            head_mode=head,
            scroll_stop_hint=lambda: SCROLL_STOP_HINTS[self.api.scroll_stop()],
        )
        self.gestures.reset()
        self.wink_point = None
        self.feed = PreviewFeed(MacOSAccessibility())
        self.dock_stop = threading.Event()
        self.dock_values = []
        self.dock_thread = threading.Thread(
            target=self.poll_dock,
            args=(self.dock_stop, self.dock_values, self.desktop_rect),
            daemon=True,
        )
        self.feed.start()
        self.dock_thread.start()
        self.last_cursor = self.last_ring = None
        self.last_sample = None
        self.assisted = None
        self.next_screen_check = 0
        self.ring_locked = False
        # Preserve the calibrated viewport while exposing the desktop underneath.
        native.orderOut_(None)
        self.main_window_hidden = True

    @staticmethod
    def poll_dock(stop, values, screen):
        dock = Dock(screen)
        while not stop.is_set():
            with objc.autorelease_pool():
                try:
                    now = time.monotonic()
                    values[:] = [(now, tuple(dock.latest(now)))]
                except Exception:
                    values.clear()
            stop.wait(0.22)

    def stop(self):
        if self.feed:
            self.dock_stop.set()
            if self.dock_thread.ident is not None:
                self.dock_thread.join(0.1)
            self.feed.close()
        if self.toolbar:
            self.toolbar.close()
        if self.ring:
            self.ring.close()
        self.toolbar = self.ring = self.feed = None
        self.fixation.reset()
        self.aim.reset()
        self.cursor.reset()
        self.magnet.reset()
        if self.main_window_hidden:
            self.show_main_window()

    def display(self, now, aim, assisted):
        cursor = self.cursor.update(now, assisted)
        if cursor != self.last_cursor:
            if Quartz.CGWarpMouseCursorPosition(cursor) != 0:
                raise RuntimeError("macOS imleci hareket ettiremedi.")
            self.last_cursor = cursor
        center = tuple(map(round, aim))
        if self.last_ring != center:
            x, y = center
            radius = self.magnet.radius
            self.ring.setFrame_display_(
                ((x - radius, self.size[1] - y - radius), (radius * 2, radius * 2)), False
            )
            self.last_ring = center
        locked = self.magnet.locked is not None
        if locked != self.ring_locked:
            self.ring_layer.setBorderWidth_(4 if locked else 2)
            self.ring_locked = locked
        if not self.ring.isVisible():
            self.ring.orderFrontRegardless()

    def mouse_location(self):
        position = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        return (position.x, position.y)

    def eye_gestures(self, eye_samples):
        """Issue #160: face gestures act where the cursor was when they began."""
        drain = getattr(self.api, "drain_eye_samples", None)
        if drain is not None:
            eye_samples = drain()
        settings = getattr(self.api, "gesture_settings", None)
        if settings is not None:
            self.gestures.configure(settings())
        events = self.gestures.feed(eye_samples)
        if self.gestures.pending and self.wink_point is None:
            self.wink_point = self.mouse_location()
        actions = self.api.wink_actions()
        # Smiles, an open mouth, a pucker or raised brows reshape the face mesh and
        # read as head tilts (up to 11 degrees for an open mouth in Fatih's
        # recordings), so the cursor is held while an enabled one is in progress.
        active = getattr(self.gestures, "active", None)
        if active is None:
            active = {"smile"} if self.gestures.smiling else set()
        holding = any(actions.get(name, "off") != "off" for name in active)
        if holding and self.smile_point is None:
            self.smile_point = self.mouse_location()
        elif not holding and not any(e in FACE_GESTURES for e in events):
            self.smile_point = None
        self.toolbar.face_holding = holding
        stop = self.api.scroll_stop()
        for event in events:
            if self.toolbar.head_scroll is not None or self.toolbar.head_scroll_pending:
                # While head scrolling only the stop gesture (or a scroll toggle) acts.
                if event == stop or actions.get(event) == "scroll":
                    self.toolbar.stop_head_scroll()
                continue
            if event == "long_blink" or self.toolbar.paused:
                continue
            point = self.smile_point if event in FACE_GESTURES else self.wink_point
            self.perform(event, actions.get(event, "off"), point or self.mouse_location())
        if not self.gestures.pending:
            self.wink_point = None
        if events and not holding:
            self.smile_point = None

    def perform(self, gesture, action, point):
        label = GESTURE_LABELS[gesture]
        if action in ("left", "right"):
            self.toolbar.click(action, point)
        elif action == "double":
            self.toolbar.click("left", point, count=2)
        elif action == "scroll":
            if self.toolbar.head_mode:
                self.toolbar.start_head_scroll(point)
            else:
                self.toolbar.start_mode("scroll")
        elif action == "keyboard":
            self.toolbar.toggle_keyboard()
        elif action == "menu":
            self.toolbar.command("menu")
        elif action == "recentre":
            if self.toolbar.recentre is None:
                self.toolbar.show_hint("Kafa ortalama yalnız kafa modunda.")
                return
            self.toolbar.command("recentre")
            return  # the recentre hint explains the next step
        self.toolbar.show_hint(f"{label} → {ACTION_LABELS[action]}")

    def update(self, now, frame):
        stamp, normalized, closed, blink_samples, *rest = frame
        self.eye_gestures(rest[0] if rest else None)
        valid = 0 <= now - stamp <= 0.3 and closed is not None
        raw = desktop_point(normalized, self.viewport, self.size) if valid and not closed else None
        point = self.fixation.update(stamp, raw)
        aim = self.aim.update(now, point) if point is not None else None
        owned = self.toolbar.tick(stamp, now, point, closed is True, self.last_cursor)
        pressed = any(Quartz.CGEventSourceButtonState(HID, button) for button in (0, 1, 2))
        if not owned and not pressed:
            owned = self.toolbar.desktop_gaze(
                stamp,
                point,
                closed,
                valid,
                self.last_cursor,
                blink_samples=blink_samples,
                keyboard_point=aim,
            )
        if owned and not pressed and self.toolbar.pointer_free:
            # Issue #160: over the keyboard and our panels the cursor keeps gliding
            # (no magnet) instead of vanishing and jumping back afterwards.
            self.magnet.reset()
            self.assisted = None
            self.last_sample = None
            if aim is not None and self.smile_point is None:
                self.display(now, aim, aim)
        elif owned or pressed:
            self.cursor.reset()
            self.magnet.reset()
            self.last_sample = None
            self.last_cursor = None
            if self.ring.isVisible():
                self.ring.orderOut_(None)
        elif point is not None:
            if stamp != self.last_sample or self.assisted is None:
                targets = window_targets(self.feed, self.desktop_rect, now)
                dock = self.dock_values[:]
                if dock and now - dock[0][0] <= 0.38:
                    targets.extend(dock[0][1])
                self.assisted = self.magnet.update(stamp, point, targets)
                self.last_sample = stamp
            if self.smile_point is None:
                self.display(now, aim, self.assisted if self.magnet.locked else aim)
        elif not valid:
            self.magnet.reset()
            self.last_sample = None
            if self.ring_locked:
                self.ring_layer.setBorderWidth_(2)
                self.ring_locked = False

    def tick(self):
        if self.closed:
            self.stop()
            return
        try:
            if getattr(self.api, "supports_recentre", lambda: False)():
                held = bool(Quartz.CGEventSourceKeyState(HID, R_KEY_CODE))
                if self.recentre_key.update(time.monotonic(), held):
                    result = self.api.command("recentre")
                    if not result.get("ok"):
                        logger.info("Recentre ignored: %s", result.get("message"))
            reading = self.api.desktop_sample()
            if reading is not None:
                active, frame, _ = reading
                if active:
                    escape = Quartz.CGEventSourceKeyState(HID, 53)
                    if escape and not self.escape_down:
                        self.api.command("desktop_stop")
                        self.stop()
                    else:
                        if self.toolbar is None:
                            self.prepare()
                        now = time.monotonic()
                        if now >= self.next_screen_check:
                            self.next_screen_check = now + 0.4
                            self.web_accessibility.update(
                                UI.NSWorkspace.sharedWorkspace().frontmostApplication()
                            )
                            if not _screen_matches(UI, self.size):
                                raise RuntimeError("Ekran değişti. Kalibrasyonu yenile.")
                        self.update(now, frame)
                    self.escape_down = escape
                elif self.toolbar is not None:
                    self.stop()
        except Exception as error:
            logger.exception("Desktop controls stopped")
            self.api.desktop_failed(str(error))
            self.stop()
        AppHelper.callLater(1 / 60 if self.toolbar else 0.1, self.tick)

    def close(self, *args):
        self.closed = True
        AppHelper.callAfter(self.stop)
