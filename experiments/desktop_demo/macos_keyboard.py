"""Click keyboard for the focused macOS accessibility text control."""

import os

import AppKit as UI
import ApplicationServices as AX
import Quartz
from PyObjCTools import AppHelper

from .keyboard import LETTER_ROWS, SYMBOL_ROWS, turkish_upper


def attribute(element, name):
    error, value = AX.AXUIElementCopyAttributeValue(element, name, None)
    return value if error == 0 else None


def ax_geometry(value, kind):
    if value is not None and AX.AXValueGetType(value) == kind:
        ok, geometry = AX.AXValueGetValue(value, kind, None)
        if ok:
            return geometry
    return None


def panel_rect(element, fallback):
    # AX uses a top-left origin on the primary display; Cocoa uses bottom-left.
    screens = UI.NSScreen.screens()
    top = UI.NSMaxY(screens[0].frame())
    position = ax_geometry(attribute(element, "AXPosition"), AX.kAXValueCGPointType)
    size = ax_geometry(attribute(element, "AXSize"), AX.kAXValueCGSizeType)
    field = caret = None
    if position is not None and size is not None:
        field = UI.NSMakeRect(position.x, top - position.y - size.height, size.width, size.height)
    selected = attribute(element, "AXSelectedTextRange")
    if selected is not None:
        err, value = AX.AXUIElementCopyParameterizedAttributeValue(
            element, "AXBoundsForRange", selected, None
        )
        bounds = ax_geometry(value, AX.kAXValueCGRectType) if not err else None
        if bounds and bounds.size.height > 0:
            caret = UI.NSMakeRect(
                bounds.origin.x,
                top - bounds.origin.y - bounds.size.height,
                max(1, bounds.size.width),
                bounds.size.height,
            )
    anchor = caret or field or UI.NSMakeRect(fallback.x, fallback.y, 1, 1)

    def area(a, b):
        overlap = UI.NSIntersectionRect(a, b)
        return overlap.size.width * overlap.size.height

    screen = max(screens, key=lambda screen: area(screen.frame(), anchor))
    v = screen.visibleFrame()
    width = min(760, v.size.width - 24)
    height = min(235, v.size.height * 0.36)
    xs = (UI.NSMidX(v) - width / 2, UI.NSMinX(v) + 8, UI.NSMaxX(v) - width - 8)
    ys = (UI.NSMinY(v) + 8, UI.NSMaxY(v) - height - 8)
    candidates = [UI.NSMakeRect(x, y, width, height) for y in ys for x in xs]
    return min(
        candidates,
        key=lambda rect: (
            area(rect, UI.NSInsetRect(anchor, -8, -8)),
            area(rect, field) if field else 0,
        ),
    )


class KeyboardPanel(UI.NSPanel):
    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False

    def keyClicked_(self, sender):
        self.controller.press(sender.identifier())


class FocusKeyboard:
    def __init__(self):
        self.system = AX.AXUIElementCreateSystemWide()
        AX.AXUIElementSetMessagingTimeout(self.system, 0.1)
        self.panel = self.target = None
        self.stopped = self.shift = self.symbols = False

    def focused(self):
        if not AX.AXIsProcessTrusted():
            return None
        element = attribute(self.system, "AXFocusedUIElement")
        if element is None or attribute(element, "AXRole") not in (
            "AXTextField",
            "AXTextArea",
            "AXComboBox",
        ):
            return None
        if attribute(element, "AXSubrole") == "AXSecureTextField":
            return None
        error, pid = AX.AXUIElementGetPid(element, None)
        writable = any(
            AX.AXUIElementIsAttributeSettable(element, name, None) == (0, True)
            for name in ("AXSelectedText", "AXValue")
        )
        if error or pid == os.getpid() or not writable:
            return None
        return pid, element

    def tick(self):
        if self.stopped:
            return
        target = self.focused()
        if target != self.target:
            self.target = target
            self.shift = self.symbols = False
            if self.panel:
                self.panel.orderOut_(None)
            if target:
                self.fallback = UI.NSEvent.mouseLocation()
                self.build()
        elif target and self.panel and self.panel.isVisible():
            rect = panel_rect(target[1], self.fallback)
            if not UI.NSEqualRects(rect, self.panel.frame()):
                self.build(rect)
        AppHelper.callLater(0.25, self.tick)

    def build(self, rect=None):
        rect = rect or panel_rect(self.target[1], self.fallback)
        width, height = rect.size
        if self.panel is None:
            self.panel = KeyboardPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                rect, UI.NSWindowStyleMaskNonactivatingPanel, UI.NSBackingStoreBuffered, False
            )
            self.panel.controller = self
            self.panel.setFloatingPanel_(True)
            self.panel.setLevel_(UI.NSFloatingWindowLevel)
            self.panel.setHidesOnDeactivate_(False)
            self.panel.setCollectionBehavior_(
                UI.NSWindowCollectionBehaviorCanJoinAllSpaces
                | UI.NSWindowCollectionBehaviorFullScreenAuxiliary
            )
        self.panel.setFrame_display_(rect, True)
        view = UI.NSView.alloc().initWithFrame_(UI.NSMakeRect(0, 0, width, height))
        view.setWantsLayer_(True)
        view.layer().setCornerRadius_(12)
        self.panel.setContentView_(view)
        rows = SYMBOL_ROWS if self.symbols else LETTER_ROWS
        lines = [[(c, turkish_upper(c) if self.shift else c, 1) for c in row] for row in rows]
        lines.append(
            [
                ("shift", "⇧", 1),
                ("page", "ABC" if self.symbols else "123", 1),
                ("space", "Boşluk", 4),
                ("period", ".", 1),
                ("backspace", "⌫", 1),
                ("hide", "Kapat", 1),
            ]
        )
        step = (height - 12) / 4
        for index, row in enumerate(lines):
            unit = (width - 16) / sum(weight for _, _, weight in row)
            x = 8
            for key, label, weight in row:
                button = UI.NSButton.buttonWithTitle_target_action_(
                    label, self.panel, "keyClicked:"
                )
                button.setIdentifier_(key)
                button.setBezelStyle_(UI.NSBezelStyleRegularSquare)
                button.setFont_(UI.NSFont.systemFontOfSize_(19))
                button.setFrame_(
                    UI.NSMakeRect(
                        x + 2, height - 6 - (index + 1) * step, unit * weight - 4, step - 4
                    )
                )
                view.addSubview_(button)
                x += unit * weight
        self.panel.orderFrontRegardless()

    def press(self, key):
        if self.stopped or not self.target or self.focused() != self.target:
            return
        if key == "hide":
            self.panel.orderOut_(None)
            return
        if key in ("shift", "page"):
            if key == "shift":
                self.shift = not self.shift
            else:
                self.symbols = not self.symbols
            self.build()
            return
        # Send a normal editing event to the still-focused application. Its editor
        # owns caret position, selection replacement, undo, and deletion.
        pid, _ = self.target
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, 51 if key == "backspace" else 0, down)
            Quartz.CGEventSetFlags(event, 0)
            if key != "backspace":
                char = {"space": " ", "period": "."}.get(key, key)
                char = turkish_upper(char) if self.shift else char
                Quartz.CGEventKeyboardSetUnicodeString(event, len(char), char)
            Quartz.CGEventPostToPid(pid, event)
        if self.shift:
            self.shift = False
            self.build()

    def start(self):
        AppHelper.callAfter(self.tick)

    def close(self):
        self.stopped = True
        if self.panel:
            AppHelper.callAfter(self.panel.orderOut_, None)
