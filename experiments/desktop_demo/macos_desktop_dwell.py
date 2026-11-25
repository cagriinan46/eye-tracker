"""macOS desktop dwell controller, driven only by fresh camera observations."""

import os
import time

import AppKit as UI
import ApplicationServices as AX
import Quartz
from PyObjCTools import AppHelper

from eye_tracker.actions.window_pointer import window_point
from eye_tracker.intent.region_dwell import RegionDwell
from eye_tracker.platform_adapters._macos_ax import SUPPORTED_ROLES

from .macos_keyboard import attribute, ax_geometry
from .protocol import DWELL_SECONDS


class DwellRing(UI.NSView):
    def drawRect_(self, dirty):
        UI.NSColor.clearColor().set()
        UI.NSRectFillUsingOperation(self.bounds(), UI.NSCompositingOperationCopy)
        curve = UI.NSBezierPath.bezierPathWithOvalInRect_(((3, 3), (26, 26)))
        UI.NSColor.darkGrayColor().set()
        curve.setLineWidth_(4)
        curve.stroke()
        arc = UI.NSBezierPath.bezierPath()
        arc.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
            (16, 16), 13, 90, 90 - 360 * self.progress, True
        )
        color = UI.NSColor.systemGreenColor() if self.progress >= 1 else UI.NSColor.whiteColor()
        color.set()
        arc.setLineWidth_(4)
        arc.stroke()


def make_ring():
    rect = ((0, 0), (32, 32))
    ring = UI.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        rect,
        UI.NSWindowStyleMaskBorderless | UI.NSWindowStyleMaskNonactivatingPanel,
        UI.NSBackingStoreBuffered,
        False,
    )
    ring.setOpaque_(False)
    ring.setHasShadow_(False)
    ring.setBackgroundColor_(UI.NSColor.clearColor())
    ring.setIgnoresMouseEvents_(True)
    ring.setHidesOnDeactivate_(False)
    ring.setLevel_(UI.NSStatusWindowLevel)
    ring.setCollectionBehavior_(
        UI.NSWindowCollectionBehaviorCanJoinAllSpaces
        | UI.NSWindowCollectionBehaviorFullScreenAuxiliary
    )
    view = DwellRing.alloc().initWithFrame_(rect)
    view.progress = 0
    view.setAccessibilityElement_(False)
    ring.setAccessibilityElement_(False)
    ring.setAccessibilityChildren_([])
    ring.setContentView_(view)
    return ring


class DesktopDwell:
    def __init__(self, window, api, keyboard):
        self.window, self.api, self.keyboard = window, api, keyboard
        self.dwell = RegionDwell(seconds=DWELL_SECONDS)
        self.token = self.last_capture = self.latched_rect = self.ring = None
        self.monitors = []
        self.stopped = False

    def start(self):
        AppHelper.callAfter(self._start)

    def _start(self):
        if self.stopped:
            return

        def escape(event):
            if event.keyCode() == 53 and self.api._desktop_frame() is not None:
                self.api.command("pause")
            return event

        self.monitors = [
            UI.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(UI.NSEventMaskKeyDown, escape),
            UI.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                UI.NSEventMaskKeyDown, lambda event: escape(event) and None
            ),
        ]
        self.tick()

    def close(self):
        self.stopped = True
        AppHelper.callAfter(self._close)

    def _close(self):
        for monitor in self.monitors:
            if monitor is not None:
                UI.NSEvent.removeMonitor_(monitor)
        self.monitors.clear()
        if self.ring:
            self.ring.orderOut_(None)

    def tick(self):
        if self.stopped:
            return
        try:
            frame = self.api._desktop_frame()
            if frame is None:
                if self.token is not None:
                    self.reset(None)
            else:
                self.observe(frame)
        except Exception as error:
            self.api.command("pause")
            self.reset(None)
            print(f"Desktop dwell paused: {type(error).__name__}", flush=True)
        AppHelper.callLater(0.03, self.tick)

    def reset(self, token):
        self.token = token
        self.last_capture = self.latched_rect = None
        self.dwell.reset()
        if self.ring:
            self.ring.orderOut_(None)

    def hit(self, point, cocoa):
        panel = self.keyboard.panel
        top = UI.NSWindow.windowNumberAtPoint_belowWindowWithWindowNumber_(cocoa, 0)
        if panel and panel.isVisible() and top == panel.windowNumber():
            local = panel.convertPointFromScreen_(cocoa)
            button = panel.contentView().hitTest_(local)
            target = self.keyboard.target
            if (
                not isinstance(button, UI.NSButton)
                or not button.isEnabled()
                or not target
                or self.keyboard.focused() != target
            ):
                return None
            rect = panel.convertRectToScreen_(button.frame())
            return (target, button.identifier(), button.title()), rect
        if top == self.window.native.windowNumber():
            return None
        error, node = AX.AXUIElementCopyElementAtPosition(self.keyboard.system, *point, None)
        if error or node is None:
            return None
        front = UI.NSWorkspace.sharedWorkspace().frontmostApplication()
        error, pid = AX.AXUIElementGetPid(node, None)
        if error or not front or pid != front.processIdentifier() or pid == os.getpid():
            return None
        # Walk only a hit label/image to its enclosing control. Blank container
        # backgrounds and unsupported/disabled controls cannot nominate a target.
        for _ in range(5):
            role = attribute(node, "AXRole")
            if role not in ("AXStaticText", "AXImage"):
                break
            node = attribute(node, "AXParent")
            if node is None:
                return None
        if role not in SUPPORTED_ROLES | {"AXTextArea", "AXComboBox"}:
            return None
        if not attribute(node, "AXEnabled") or attribute(node, "AXSubrole") == "AXSecureTextField":
            return None
        if role in ("AXTextArea", "AXTextField", "AXComboBox"):
            if not any(
                AX.AXUIElementIsAttributeSettable(node, name, None) == (0, True)
                for name in ("AXSelectedText", "AXValue")
            ):
                return None
        else:
            error, actions = AX.AXUIElementCopyActionNames(node, None)
            if error or "AXPress" not in (actions or ()):
                return None
        pos = ax_geometry(attribute(node, "AXPosition"), AX.kAXValueCGPointType)
        size = ax_geometry(attribute(node, "AXSize"), AX.kAXValueCGSizeType)
        if pos is None or size is None:
            return None
        height = UI.NSScreen.screens()[0].frame().size.height
        rect = UI.NSMakeRect(pos.x, height - pos.y - size.height, size.width, size.height)
        return ((pid, node), rect) if UI.NSPointInRect(cocoa, rect) else None

    def observe(self, frame):
        mode, token, captured, gaze = frame
        if token != self.token:
            self.reset(token)
        if not AX.AXIsProcessTrusted() or self.escape_down():
            self.api.command("pause")
            self.reset(None)
            return
        if gaze is None:
            self.dwell.missing(time.monotonic())
            if self.ring:
                self.ring.orderOut_(None)
            return
        if captured == self.last_capture:
            return
        self.last_capture = captured
        native = self.window.native
        rect = native.convertRectToScreen_(native.contentView().frame())
        height = UI.NSScreen.screens()[0].frame().size.height
        point = window_point(gaze, (rect.origin.x, height - UI.NSMaxY(rect), *rect.size))
        if point is None:
            self.dwell.reset()
            if self.ring:
                self.ring.orderOut_(None)
            return
        cocoa = UI.NSMakePoint(point[0], height - point[1])
        if self.latched_rect and not UI.NSPointInRect(cocoa, self.latched_rect):
            self.latched_rect = None
        target = self.hit(point, cocoa)
        fired = self.dwell.update(captured, target)
        if not target or time.monotonic() - captured > 0.3:
            if self.ring:
                self.ring.orderOut_(None)
            return
        if self.ring is None:
            self.ring = make_ring()
        self.ring.setFrameOrigin_((cocoa.x + 12, cocoa.y + 8))
        view = self.ring.contentView()
        view.progress = self.dwell.progress
        view.setNeedsDisplay_(True)
        self.ring.orderFrontRegardless()
        if not fired or self.latched_rect:
            return
        if mode == "desktop_preview":
            self.latched_rect = target[1]
            self.api._desktop_preview_complete(token)
        elif self.hit(point, cocoa) == target:
            # Revalidate after AX IPC, immediately before posting the mouse pair.
            current = self.api._desktop_frame()
            if (
                current
                and current[:3] == frame[:3]
                and current[3] is not None
                and not self.escape_down()
            ):
                events = [
                    Quartz.CGEventCreateMouseEvent(None, kind, point, Quartz.kCGMouseButtonLeft)
                    for kind in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp)
                ]
                if all(events):
                    self.latched_rect = target[1]
                    for event in events:
                        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        if self.latched_rect is None:
            # Revalidation lost a race with a new observation. Require a new dwell.
            self.dwell.reset()

    @staticmethod
    def escape_down():
        return Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateCombinedSessionState, 53)
