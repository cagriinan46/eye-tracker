"""Lazy desktop adapter: importing this module never moves the pointer."""

import sys


def _escape_reader():
    if sys.platform == "darwin":
        import Quartz

        return lambda: Quartz.CGEventSourceKeyState(
            Quartz.kCGEventSourceStateCombinedSessionState, 53
        )
    if sys.platform == "win32":
        import ctypes

        return lambda: bool(ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000)
    raise RuntimeError("Pointer control supports macOS and Windows only")


class PyAutoGUIPointer:
    def __init__(self, api=None, escape_pressed=None):
        native = api is None
        if api is None:
            import pyautogui

            api = pyautogui
            if sys.platform == "darwin":
                import ctypes

                service = ctypes.CDLL(
                    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
                )
                service.AXIsProcessTrusted.restype = ctypes.c_bool
                if not service.AXIsProcessTrusted():
                    raise RuntimeError(
                        "Enable macOS Accessibility permission for the launching app"
                    )
        self.escape_pressed = escape_pressed or _escape_reader()
        self.api = api
        self.screen_size = tuple(api.size())
        if native and sys.platform == "darwin":
            import Quartz

            # CGEvent mouse locations use logical points, not Retina backing pixels.
            bounds = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
            self.screen_size = (int(bounds.size.width), int(bounds.size.height))
        self._old_failsafe, self._old_pause = api.FAILSAFE, api.PAUSE
        api.FAILSAFE = False
        api.PAUSE = 0  # No default 100 ms sleep after every frame's moveTo.

    def check_stop(self):
        if self.escape_pressed():
            raise InterruptedError("Global Escape: pointer control stopped")

    def move(self, x, y):
        self.check_stop()
        self.api.moveTo(x, y, duration=0)

    def click(self):
        self.check_stop()
        self.api.click(button="left")

    def close(self):
        self.api.FAILSAFE, self.api.PAUSE = self._old_failsafe, self._old_pause
