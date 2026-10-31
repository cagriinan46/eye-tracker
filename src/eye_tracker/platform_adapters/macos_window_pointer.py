"""Main-thread native cursor display, constrained to a focused demo window."""

from eye_tracker.actions.window_pointer import window_point


class MacOSWindowPointer:
    def __init__(self, window, sample, pause):
        self.window, self.sample, self.pause = window, sample, pause
        self.stopped = False

    def start(self):
        from PyObjCTools import AppHelper

        AppHelper.callAfter(self._tick)

    def _tick(self):
        import AppKit
        import Quartz
        from PyObjCTools import AppHelper

        if self.stopped:
            return
        try:
            native = self.window.native
            point = self.sample()
            if native is not None and native.isKeyWindow() and point is not None:
                if Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateCombinedSessionState, 53):
                    self.pause()
                else:
                    rect = native.convertRectToScreen_(native.contentView().frame())
                    # Cocoa and Quartz both use logical points; their Y origins differ.
                    height = AppKit.NSScreen.screens()[0].frame().size.height
                    region = (
                        rect.origin.x,
                        height - rect.origin.y - rect.size.height,
                        rect.size.width,
                        rect.size.height,
                    )
                    pixel = window_point(point, region)
                    if pixel is not None:
                        Quartz.CGWarpMouseCursorPosition(pixel)
        except Exception:
            self.pause()
            self.stopped = True
            return
        AppHelper.callLater(1 / 60, self._tick)

    def close(self):
        self.stopped = True
