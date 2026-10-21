"""Private read-only ctypes bridge. Libraries load only inside a discovery call."""

import ctypes as C
import sys
from math import isfinite
from uuid import uuid4

from eye_tracker.intent.targets import TargetRect

SUPPORTED_ROLES = frozenset({"AXButton", "AXCheckBox", "AXRadioButton", "AXPopUpButton", "AXLink"})


class AXReadError(RuntimeError):
    pass


class AXEmptyTarget(AXReadError):
    """Known zero-area control; exclude only this target, not its descendants."""

    def __init__(self, role):
        super().__init__("zero-area target")
        self.role = role


class AXUnavailable(AXReadError):
    pass


class UnsupportedCoordinates(AXReadError):
    pass


class Pair(C.Structure):
    _fields_ = [("x", C.c_double), ("y", C.c_double)]


class Rect(C.Structure):
    _fields_ = [("origin", Pair), ("size", Pair)]


class AXBackend:
    def __init__(self, message_timeout=0.05):
        self.message_timeout = message_timeout
        self.owned = []
        self.keys = {}
        self.initial_context = None
        self.context_id = uuid4().hex

    def __enter__(self):
        if sys.platform != "darwin":
            raise AXUnavailable("macOS only")
        try:
            self._bind()
            self.system = self._own(self.create_system())
            self._timeout(self.system)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        for pointer in reversed(self.owned):
            self.release(pointer)
        self.owned.clear()
        self.keys.clear()
        self.initial_context = None

    def _bind(self):
        try:
            cf = C.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            ax = C.CDLL(
                "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
            )
        except OSError as error:
            raise AXUnavailable("native frameworks unavailable") from error
        p, index, error = C.c_void_p, C.c_long, C.c_int32

        def bind(lib, name, args, result):
            fn = getattr(lib, name)
            fn.argtypes, fn.restype = args, result
            return fn

        self.release = bind(cf, "CFRelease", [p], None)
        self.retain = bind(cf, "CFRetain", [p], p)
        self.same = bind(cf, "CFEqual", [p, p], C.c_bool)
        self.identity_hash = bind(cf, "CFHash", [p], C.c_ulong)
        self.type_id = bind(cf, "CFGetTypeID", [p], C.c_ulong)
        self.array_type = bind(cf, "CFArrayGetTypeID", [], C.c_ulong)()
        self.string_type = bind(cf, "CFStringGetTypeID", [], C.c_ulong)()
        self.boolean_type = bind(cf, "CFBooleanGetTypeID", [], C.c_ulong)()
        self.value_type_id = bind(ax, "AXValueGetTypeID", [], C.c_ulong)()
        self.element_type = bind(ax, "AXUIElementGetTypeID", [], C.c_ulong)()
        self.new_string = bind(cf, "CFStringCreateWithCString", [p, C.c_char_p, C.c_uint32], p)
        self.read_string = bind(
            cf, "CFStringGetCString", [p, C.c_char_p, index, C.c_uint32], C.c_bool
        )
        self.array_count = bind(cf, "CFArrayGetCount", [p], index)
        self.array_item = bind(cf, "CFArrayGetValueAtIndex", [p, index], p)
        self.boolean = bind(cf, "CFBooleanGetValue", [p], C.c_bool)
        self.trusted = bind(ax, "AXIsProcessTrusted", [], C.c_bool)
        self.create_system = bind(ax, "AXUIElementCreateSystemWide", [], p)
        self.create_application = bind(ax, "AXUIElementCreateApplication", [C.c_int], p)
        self.copy_attr = bind(ax, "AXUIElementCopyAttributeValue", [p, p, C.POINTER(p)], error)
        self.count_attr = bind(
            ax, "AXUIElementGetAttributeValueCount", [p, p, C.POINTER(index)], error
        )
        self.copy_children = bind(
            ax, "AXUIElementCopyAttributeValues", [p, p, index, index, C.POINTER(p)], error
        )
        self.copy_actions = bind(ax, "AXUIElementCopyActionNames", [p, C.POINTER(p)], error)
        self.position_hit = bind(
            ax, "AXUIElementCopyElementAtPosition", [p, C.c_float, C.c_float, C.POINTER(p)], error
        )
        self.set_timeout = bind(ax, "AXUIElementSetMessagingTimeout", [p, C.c_float], error)
        self.value_type = bind(ax, "AXValueGetType", [p], C.c_uint32)
        self.value_get = bind(ax, "AXValueGetValue", [p, C.c_uint32, p], C.c_bool)
        self.display_list = bind(
            ax,
            "CGGetActiveDisplayList",
            [C.c_uint32, C.POINTER(C.c_uint32), C.POINTER(C.c_uint32)],
            error,
        )
        self.display_bounds = bind(ax, "CGDisplayBounds", [C.c_uint32], Rect)

    def _own(self, p):
        if not p:
            raise AXReadError("null native reference")
        self.owned.append(p)
        return p

    def _timeout(self, node):
        if self.set_timeout(node, self.message_timeout):
            raise AXReadError("cannot set IPC timeout")

    def _key(self, name):
        if name not in self.keys:
            self.keys[name] = self._own(self.new_string(None, name.encode(), 0x08000100))
        return self.keys[name]

    def _out(self, code, output, optional=False):
        # Even an error path must not leak an unexpectedly populated output.
        p = self._own(output.value) if output.value else None
        if optional and code in {-25205, -25212}:
            return None
        if code or p is None:
            raise AXReadError(f"native read failed: {code}")
        return p

    def _attr(self, node, name):
        self._timeout(node)
        output = C.c_void_p()
        return self._out(self.copy_attr(node, self._key(name), C.byref(output)), output, True)

    def _element(self, p):
        if p is not None and self.type_id(p) != self.element_type:
            raise AXReadError("expected AX element")
        return p

    def _text(self, p):
        if p is None:
            return None
        buffer = C.create_string_buffer(128)
        if self.type_id(p) != self.string_type or not self.read_string(
            p, buffer, len(buffer), 0x08000100
        ):
            raise AXReadError("invalid role/action string")
        return buffer.value.decode("utf-8")

    def _array(self, p, cap):
        if self.type_id(p) != self.array_type:
            raise AXReadError("expected array")
        size = self.array_count(p)
        if size < 0 or size > cap:
            raise AXReadError("array exceeds bounded request")
        return tuple(self.array_item(p, n) for n in range(size))

    def _frontmost_pid(self):
        # Cocoa is already supplied by the desktop dependency stack. Keep it
        # optional/lazy so pure contracts and fake tests work on every OS.
        try:
            from AppKit import NSWorkspace
        except ImportError as error:
            raise AXUnavailable("desktop Cocoa bridge unavailable") from error
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return int(app.processIdentifier()) if app is not None else None

    def context(self):
        pid = self._frontmost_pid()
        if pid is None:
            return None
        app = self._own(self.create_application(pid))
        window = self._element(self._attr(app, "AXFocusedWindow"))
        if window is None:
            return None
        if self.initial_context is None:
            self.initial_context = app, window
            self.app, self.window = app, window
        a, w = self.initial_context
        return self.context_id if self.same(app, a) and self.same(window, w) else None

    def roots(self):
        menu = self._element(self._attr(self.app, "AXMenuBar"))
        return (self.window, menu) if menu else (self.window,)

    def screen(self):
        size = C.c_uint32()
        if self.display_list(0, None, C.byref(size)):
            raise AXReadError("cannot enumerate displays")
        if size.value != 1:
            raise UnsupportedCoordinates("initial adapter requires one active display")
        displays = (C.c_uint32 * 1)()
        if self.display_list(1, displays, C.byref(size)) or size.value != 1:
            raise UnsupportedCoordinates("display configuration changed")
        r = self.display_bounds(displays[0])
        try:
            return TargetRect(r.origin.x, r.origin.y, r.size.x, r.size.y)
        except ValueError as error:
            raise UnsupportedCoordinates("invalid display geometry") from error

    def children(self, node, limit):
        self._timeout(node)
        size = C.c_long()
        code = self.count_attr(node, self._key("AXChildren"), C.byref(size))
        if code in {-25205, -25212}:
            return (), False
        if code or size.value < 0:
            raise AXReadError("cannot count children")
        if size.value > limit:
            return (), True
        if size.value == 0:
            return (), False
        output = C.c_void_p()
        p = self._out(
            self.copy_children(node, self._key("AXChildren"), 0, size.value, C.byref(output)),
            output,
        )
        nodes = self._array(p, limit)
        if len(nodes) != size.value:
            raise AXReadError("child list changed during read")
        return tuple(self._element(n) for n in nodes), False

    def _pair(self, node, name, kind):
        p = self._attr(node, name)
        if p is None:
            return None
        value = Pair()
        if (
            self.type_id(p) != self.value_type_id
            or self.value_type(p) != kind
            or not self.value_get(p, kind, C.byref(value))
        ):
            raise AXReadError("invalid geometry value")
        return value.x, value.y

    def describe(self, node):
        role = self._text(self._attr(node, "AXRole"))
        if role is None:
            raise AXReadError("missing element role")
        rect, enabled, actions = None, None, ()
        if role in SUPPORTED_ROLES or role in {"AXWindow", "AXMenuBar"}:
            position, size = self._pair(node, "AXPosition", 1), self._pair(node, "AXSize", 2)
            if position is not None and size is not None:
                if (
                    role in SUPPORTED_ROLES
                    and all(
                        isfinite(v)
                        for v in (
                            *position,
                            *size,
                            position[0] + size[0],
                            position[1] + size[1],
                        )
                    )
                    and min(size) == 0
                ):
                    raise AXEmptyTarget(role)
                try:
                    rect = TargetRect(*position, *size)
                except ValueError as error:
                    raise AXReadError("invalid element rectangle") from error
        if role in SUPPORTED_ROLES:
            p = self._attr(node, "AXEnabled")
            if p is not None:
                if self.type_id(p) != self.boolean_type:
                    raise AXReadError("invalid enabled state")
                enabled = bool(self.boolean(p))
            self._timeout(node)
            output = C.c_void_p()
            p = self._out(self.copy_actions(node, C.byref(output)), output, True)
            if p:
                actions = tuple(self._text(a) for a in self._array(p, 32))
        return role, rect, enabled, actions

    def hit_test(self, x, y):
        self._timeout(self.system)
        output = C.c_void_p()
        return self._element(
            self._out(self.position_hit(self.system, x, y, C.byref(output)), output, True)
        )

    def parent(self, node):
        return self._element(self._attr(node, "AXParent"))
