"""Opt-in macOS outline process. Imports never create a window or read a camera."""

import multiprocessing
import os
import sys
from math import isfinite
from time import monotonic


def visible_rect(values, now, size):
    """Validate an expiring AX rectangle and convert to single-screen Cocoa points."""
    x, y, width, height, expires = values
    if (
        not all(isfinite(v) for v in (*values, now, *size))
        or not 0 < expires - now <= 0.25
        or min(width, height, *size) <= 0
        or min(x, y) < 0
        or x + width > size[0]
        or y + height > size[1]
    ):
        return None
    return ((x, size[1] - y - height), (width, height))


def _screen_matches(api, size):
    screens = api.NSScreen.screens()
    if len(screens) != 1:
        return False
    frame = screens[0].frame()
    return (frame.origin.x, frame.origin.y, frame.size.width, frame.size.height) == (
        0,
        0,
        *size,
    )


def _make_panel(api):
    class SemanticOutlinePanel(api.NSPanel):
        def canBecomeKeyWindow(self):
            return False

        def canBecomeMainWindow(self):
            return False

    class SemanticOutlineView(api.NSView):
        def drawRect_(self, dirty):
            api.NSColor.clearColor().set()
            api.NSRectFillUsingOperation(self.bounds(), api.NSCompositingOperationCopy)
            api.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.9, 0.55, 0.95).set()
            bounds = self.bounds()
            inset = min(2.0, bounds.size.width / 4, bounds.size.height / 4)
            path = api.NSBezierPath.bezierPathWithRect_(api.NSInsetRect(bounds, inset, inset))
            path.setLineWidth_(2.0)
            path.stroke()

    panel = SemanticOutlinePanel.alloc().initWithContentRect_styleMask_backing_defer_(
        ((0, 0), (1, 1)),
        api.NSWindowStyleMaskBorderless | api.NSWindowStyleMaskNonactivatingPanel,
        api.NSBackingStoreBuffered,
        False,
    )
    panel.setReleasedWhenClosed_(False)
    panel.setOpaque_(False)
    panel.setBackgroundColor_(api.NSColor.clearColor())
    panel.setHasShadow_(False)
    panel.setIgnoresMouseEvents_(True)
    panel.setHidesOnDeactivate_(False)
    panel.setLevel_(api.NSFloatingWindowLevel)
    panel.setAccessibilityElement_(False)
    panel.setAccessibilityChildren_([])
    view = SemanticOutlineView.alloc().initWithFrame_(((0, 0), (1, 1)))
    view.setAccessibilityElement_(False)
    view.setAccessibilityChildren_([])
    panel.setContentView_(view)
    return panel, view


def _serve(size, mailbox, stop, status, parent_pid):
    panel = None
    try:
        import AppKit as api
        import objc
        import Quartz
        from Foundation import NSDate, NSDefaultRunLoopMode

        app = api.NSApplication.sharedApplication()
        if not app.setActivationPolicy_(api.NSApplicationActivationPolicyAccessory):
            raise RuntimeError("outline application policy unavailable")
        if not _screen_matches(api, size):
            raise RuntimeError("outline requires matching single display")
        panel, view = _make_panel(api)
        status.value = 1
        while not stop.is_set() and os.getppid() == parent_pid:
            with objc.autorelease_pool():
                if Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateCombinedSessionState, 53):
                    status.value = 2
                    break
                values = (0, 0, 0, 0, 0)
                lock = mailbox.get_lock()
                if lock.acquire(False):
                    try:
                        values = tuple(mailbox.get_obj())
                    finally:
                        lock.release()
                rect = (
                    visible_rect(values, monotonic(), size) if _screen_matches(api, size) else None
                )
                if rect is None:
                    panel.orderOut_(None)
                else:
                    panel.setFrame_display_(rect, False)
                    view.setNeedsDisplay_(True)
                    panel.orderFrontRegardless()
                    panel.displayIfNeeded()
                # Service only this helper's events; never activate the app.
                for _ in range(16):
                    event = app.nextEventMatchingMask_untilDate_inMode_dequeue_(
                        api.NSEventMaskAny, NSDate.date(), NSDefaultRunLoopMode, True
                    )
                    if event is None:
                        break
                    app.sendEvent_(event)
            stop.wait(0.016)
    except Exception:
        status.value = -1
    finally:
        if panel is not None:
            panel.orderOut_(None)
            panel.close()


class MacOSOutline:
    """Latest-only geometry mailbox; the helper expires frames independently."""

    def __init__(self, size, *, context=None, clock=monotonic):
        if sys.platform != "darwin" and context is None:
            raise RuntimeError("native semantic preview currently supports macOS only")
        if len(size) != 2 or any(not isfinite(v) or v <= 0 for v in size):
            raise ValueError("invalid logical screen size")
        self.size = tuple(size)
        self.clock = clock
        self.context = context or multiprocessing.get_context("spawn")
        self.mailbox = self.context.Array("d", 5)
        self.stop = self.context.Event()
        self.status = self.context.Value("i", 0)
        self.process = None
        self._process_started = False
        self.started_at = None
        self.closed = False

    def start(self):
        if self.closed or self.process is not None:
            raise RuntimeError("outline is single-use")
        self.started_at = self.clock()
        self.process = self.context.Process(
            target=_serve,
            args=(self.size, self.mailbox, self.stop, self.status, os.getpid()),
            daemon=True,
        )
        self.process.start()
        self._process_started = True

    def check_stop(self):
        if not self._process_started:
            return
        status = self.status.value
        if status == 2:
            raise InterruptedError("Global Escape: semantic preview stopped")
        if status == -1 or not self.process.is_alive():
            raise RuntimeError("semantic outline helper failed")
        if status == 0 and self.clock() - self.started_at > 5:
            raise RuntimeError("semantic outline helper startup timed out")

    def _write(self, values):
        lock = self.mailbox.get_lock()
        if lock.acquire(False):
            try:
                self.mailbox.get_obj()[:] = values
            finally:
                lock.release()

    def show(self, rect, expires_at):
        if self.closed:
            return
        values = (rect.x, rect.y, rect.width, rect.height, expires_at)
        if visible_rect(values, self.clock(), self.size) is None:
            self.hide()
        else:
            self._write(values)

    def hide(self):
        self._write((0, 0, 0, 0, 0))

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stop.set()
        self.hide()
        if self._process_started:
            self.process.join(0.3)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(0.3)
