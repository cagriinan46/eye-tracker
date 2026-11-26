"""Click keyboard for the focused macOS accessibility text control."""

import os

import AppKit as UI
import ApplicationServices as AX
import Quartz

from .keyboard import LETTER_ROWS, SUGGESTION_SLOTS, SYMBOL_ROWS, is_word_character, turkish_upper


def attribute(element, name):
    error, value = AX.AXUIElementCopyAttributeValue(element, name, None)
    return value if error == 0 else None


def ax_geometry(value, kind):
    if value is not None and AX.AXValueGetType(value) == kind:
        ok, geometry = AX.AXValueGetValue(value, kind, None)
        if ok:
            return geometry
    return None


def panel_rect(element, fallback, size="medium"):
    # AX uses a top-left origin on the primary display; Cocoa uses bottom-left.
    screens = UI.NSScreen.screens()
    top = UI.NSMaxY(screens[0].frame())
    position = ax_geometry(attribute(element, "AXPosition"), AX.kAXValueCGPointType)
    field_size = ax_geometry(attribute(element, "AXSize"), AX.kAXValueCGSizeType)
    field = caret = None
    if position is not None and field_size is not None:
        field = UI.NSMakeRect(
            position.x, top - position.y - field_size.height, field_size.width, field_size.height
        )
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
    scale = {"small": 0.88, "medium": 0.96, "large": 1.0}[size]
    width = (v.size.width - 238) * scale
    height = v.size.height * (0.38 + 0.10 * scale)
    xs = (UI.NSMinX(v) + 12,)
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
    def __init__(self, suggester, suggestions_enabled, size=lambda: "medium"):
        self.suggester = suggester
        self.suggestions_enabled = suggestions_enabled
        self.size = size
        self.dictate = None
        self.prefix = ""
        self.options = []
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

    def prefix_at_caret(self):
        """Check only the panel's typed prefix and the character before it."""
        selected = attribute(self.target[1], "AXSelectedTextRange")
        caret = ax_geometry(selected, AX.kAXValueCFRangeType)
        if caret is None:
            return False
        location, length = caret
        if length or location < len(self.prefix):
            return False
        start = max(0, location - len(self.prefix) - 1)
        if location == 0:
            return not self.prefix
        span = AX.AXValueCreate(AX.kAXValueCFRangeType, (start, location - start))
        error, value = AX.AXUIElementCopyParameterizedAttributeValue(
            self.target[1], "AXStringForRange", span, None
        )
        if error or value is None or not value.endswith(self.prefix):
            return False
        return len(value) == len(self.prefix) or not is_word_character(value[0])

    def suggestions(self):
        if not self.suggestions_enabled() or not self.prefix_at_caret():
            return []
        options = self.suggester.suggest(self.prefix)
        if self.prefix[:1].isupper() or (not self.prefix and self.shift):
            return [turkish_upper(word[0]) + word[1:] for word in options]
        return options

    def reveal(self):
        target = self.focused()
        if target is None:
            return False
        self.target = target
        self.prefix = ""
        self.shift = self.symbols = False
        self.fallback = UI.NSEvent.mouseLocation()
        self.build()
        return True

    def stow(self):
        self.target = None
        self.prefix = ""
        if self.panel is not None:
            self.panel.orderOut_(None)

    def refresh(self):
        if not self.target:
            return
        if self.focused() != self.target:
            self.stow()
            return
        size, show = self.size(), self.suggestions_enabled()
        options = self.suggestions()
        if size != self.panel_size or show != self.show_suggestions or self.options != options:
            self.build(options=options)

    def key_at(self, x, y, height):
        if self.target is None or not self.panel or not self.panel.isVisible():
            return None
        frame = self.panel.frame()
        x -= frame.origin.x
        y = height - y - frame.origin.y
        for button in self.panel.contentView().subviews():
            r = button.frame()
            if (
                button.isEnabled()
                and r.origin.x <= x < UI.NSMaxX(r)
                and r.origin.y <= y < UI.NSMaxY(r)
            ):
                return str(button.identifier())
        return None

    def build(self, options=None):
        self.panel_size = self.size()
        self.show_suggestions = self.suggestions_enabled()
        rect = panel_rect(self.target[1], self.fallback, self.panel_size)
        width, height = rect.size
        if self.panel is None:
            self.panel = KeyboardPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                rect,
                UI.NSWindowStyleMaskBorderless | UI.NSWindowStyleMaskNonactivatingPanel,
                UI.NSBackingStoreBuffered,
                False,
            )
            self.panel.controller = self
            self.panel.setTitle_("Türkçe klavye")
            self.panel.setOpaque_(False)
            self.panel.setBackgroundColor_(UI.NSColor.clearColor())
            self.panel.setReleasedWhenClosed_(False)
            self.panel.setAppearance_(UI.NSAppearance.appearanceNamed_(UI.NSAppearanceNameDarkAqua))
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
        view.layer().setCornerRadius_(18)
        view.layer().setBackgroundColor_(
            UI.NSColor.colorWithSRGBRed_green_blue_alpha_(0.04, 0.07, 0.10, 0.72).CGColor()
        )
        view.layer().setBorderColor_(
            UI.NSColor.colorWithSRGBRed_green_blue_alpha_(0.67, 0.81, 0.88, 0.42).CGColor()
        )
        view.layer().setBorderWidth_(1)
        self.panel.setContentView_(view)
        rows = SYMBOL_ROWS if self.symbols else LETTER_ROWS
        lines = [[(c, turkish_upper(c) if self.shift else c, 1) for c in row] for row in rows]
        lines.append(
            [
                ("shift", "⇧", 1),
                ("page", "ABC" if self.symbols else "123", 1),
                ("space", "Boşluk", 4),
                ("dictation", "Dikte", 1.4),
                ("period", ".", 1),
                ("backspace", "⌫", 1),
                ("hide", "Kapat", 1),
            ]
        )
        self.options = self.suggestions() if options is None else options
        if self.show_suggestions:
            padded = self.options + [""] * (SUGGESTION_SLOTS - len(self.options))
            lines.insert(0, [(f"sug{i}", word, 1) for i, word in enumerate(padded)])
        step = (height - 12) / len(lines)
        for index, row in enumerate(lines):
            if not row:
                continue
            unit = (width - 16) / sum(weight for _, _, weight in row)
            x = 8
            for key, label, weight in row:
                button = UI.NSButton.buttonWithTitle_target_action_(
                    label, self.panel, "keyClicked:"
                )
                button.setIdentifier_(key)
                button.setEnabled_(bool(label))
                button.setBordered_(False)
                button.setWantsLayer_(True)
                button.layer().setCornerRadius_(8)
                fill = (0.12, 0.25, 0.26) if key.startswith("sug") else (0.11, 0.15, 0.21)
                button.layer().setBackgroundColor_(
                    UI.NSColor.colorWithSRGBRed_green_blue_alpha_(
                        *fill, 0.94 if label else 0.42
                    ).CGColor()
                )
                button.setAttributedTitle_(
                    UI.NSAttributedString.alloc().initWithString_attributes_(
                        label,
                        {
                            UI.NSForegroundColorAttributeName: UI.NSColor.whiteColor(),
                            UI.NSFontAttributeName: UI.NSFont.systemFontOfSize_weight_(
                                20 if len(label) > 2 else 28, UI.NSFontWeightSemibold
                            ),
                        },
                    )
                )
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
            self.stow()
            return
        if key == "dictation":
            if self.dictate:
                self.dictate()
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
        if key.startswith("sug"):
            slot = int(key[3:])
            if self.options != self.suggestions() or slot >= len(self.options):
                self.build()
                return
            word = self.options[slot]
            char = word[len(self.prefix) :] + " "
            self.suggester.remember(word)
            self.prefix = ""
        elif key == "backspace":
            char = ""
            self.prefix = self.prefix[:-1] if self.prefix_at_caret() else ""
        else:
            char = {"space": " ", "period": "."}.get(key, key)
            char = turkish_upper(char) if self.shift else char
            if not self.suggestions_enabled() or not self.prefix_at_caret():
                self.prefix = ""
            elif is_word_character(char):
                self.prefix += char
            else:
                self.suggester.remember(self.prefix)
                self.prefix = ""
        pid, _ = self.target
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, 51 if key == "backspace" else 0, down)
            Quartz.CGEventSetFlags(event, 0)
            if key != "backspace":
                Quartz.CGEventKeyboardSetUnicodeString(event, len(char), char)
            Quartz.CGEventPostToPid(pid, event)
        if self.shift:
            self.shift = False
            self.build()

    def dispose(self):
        self.stopped = True
        self.stow()
        if self.panel:
            self.panel.close()
            self.panel = None
