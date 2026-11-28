"""Native controls for the local desktop gaze trial."""

import math
import plistlib
import queue
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import AppKit as UI
import ApplicationServices as AX
import objc
import Quartz

from eye_tracker.intent.region_dwell import RegionDwell

from .confirmation import Confirmation
from .desktop_gaze_filter import HeldDirection
from .dictation import Dictation
from .eye_gestures import scroll_step
from .macos_keyboard import attribute

COMMANDS = (
    ("left", "Sol tık", "cursorarrow.click"),
    ("right", "Sağ tık", "contextualmenu.and.cursorarrow"),
    ("precise", "Hassas imleç", "scope"),
    ("scroll", "Kaydır", "arrow.up.and.down"),
    ("keyboard", "Klavye", "keyboard"),
    ("dictation", "Türkçe dikte", "mic"),
    ("dock", "Dock", "dock.rectangle"),
    ("calibrate", "Kalibrasyon", "viewfinder"),
    ("settings", "Ayarlar", "gearshape"),
    ("pause", "Duraklat", "pause.fill"),
)
DIRECTIONS = (
    ("up", "Yukarı", "arrow.up"),
    ("down", "Aşağı", "arrow.down"),
    ("left", "Sola", "arrow.left"),
    ("right", "Sağa", "arrow.right"),
)
VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
BACK = ("back", "Geri", "chevron.left")
RAIL_COLLAPSE_SECONDS = 3.0  # the open menu closes after the cursor stays away this long
RECENTRE = ("recentre", "Kafa ortala", "dot.viewfinder")
RECENTRE_DELAY_SECONDS = 1.5  # time to turn the head back from the rail before recentring
REVEAL_KEYBOARD_AFTER_SECONDS = 0.35  # let the clicked app move focus first
SCROLL_STOP_HINTS = {
    "long_blink": "gözlerini kapalı tut",
    "smile": "gülümse",
    "wink_right": "sağ gözünü kırp",
    "wink_left": "sol gözünü kırp",
    "mouth_open": "ağzını aç",
    "pucker": "dudaklarını büz",
    "brows": "kaşlarını kaldır",
}
WIDTH = 340


def color(red, green, blue, alpha=1.0):
    return UI.NSColor.colorWithSRGBRed_green_blue_alpha_(red, green, blue, alpha)


class BarItem(UI.NSObject):
    callback = None

    def press_(self, button):
        self.callback(str(button.identifier()))


def nonactivating_panel(size):
    panel = UI.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        ((0, 0), size),
        UI.NSWindowStyleMaskBorderless | UI.NSWindowStyleMaskNonactivatingPanel,
        UI.NSBackingStoreBuffered,
        False,
    )
    panel.setFloatingPanel_(True)
    panel.setAppearance_(UI.NSAppearance.appearanceNamed_(UI.NSAppearanceNameDarkAqua))
    panel.setHidesOnDeactivate_(False)
    panel.setCollectionBehavior_(
        UI.NSWindowCollectionBehaviorCanJoinAllSpaces
        | UI.NSWindowCollectionBehaviorFullScreenAuxiliary
    )
    panel.setLevel_(UI.NSStatusWindowLevel)
    panel.setReleasedWhenClosed_(False)
    panel.setOpaque_(False)
    panel.setBackgroundColor_(UI.NSColor.clearColor())
    return panel


def dock_preferences():
    """Read saved Dock tiles, including applications without an AX item."""
    try:
        result = subprocess.run(
            ["/usr/bin/defaults", "export", "com.apple.dock", "-"],
            capture_output=True,
            check=True,
            timeout=1,
        )
        state = plistlib.loads(result.stdout)
    except (OSError, ValueError, plistlib.InvalidFileException, subprocess.SubprocessError):
        return []
    entries = []
    for tile in state.get("persistent-apps", []):
        data = tile.get("tile-data", {})
        file_url = urlsplit(data.get("file-data", {}).get("_CFURLString", ""))
        title = data.get("file-label")
        path = Path(unquote(file_url.path))
        if file_url.scheme == "file" and path.suffix.lower() == ".app" and title:
            entries.append((title, path))
    return entries


def dock_applications():
    entries = [(title, path, None) for title, path in dock_preferences()]
    pinned_titles = {title for title, _, _ in entries}
    applications = UI.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        "com.apple.dock"
    )
    if applications:
        root = AX.AXUIElementCreateApplication(applications[0].processIdentifier())
        AX.AXUIElementSetMessagingTimeout(root, 0.08)
        for container in attribute(root, "AXChildren") or []:
            if attribute(container, "AXRole") != "AXList":
                continue
            for item in attribute(container, "AXChildren") or []:
                if attribute(item, "AXSubrole") not in (
                    "AXApplicationDockItem",
                    "AXRecentApplicationDockItem",
                ):
                    continue
                title = attribute(item, "AXTitle")
                if title and title not in pinned_titles:
                    entries.append((str(title), None, item))
                    pinned_titles.add(title)
    return entries


class ScrollRepeat:
    """Emit only while fresh gaze samples stay on one scroll button."""

    def reset(self):
        self.key = self.started = self.last = self.emitted = None

    def __init__(self):
        self.reset()

    def update(self, stamp, key):
        if key is None:
            self.reset()
            return 0
        if key != self.key or not 0 <= stamp - self.last <= 0.22:
            self.key, self.started, self.emitted = key, stamp, None
        self.last = stamp
        duration = stamp - self.started
        if duration < 0.32 or (self.emitted is not None and stamp - self.emitted < 0.09):
            return 0
        self.emitted = stamp
        return round(24 + 78 * min(1, (duration - 0.32) / 1.5))


class Toolbar:
    def __init__(
        self,
        size,
        recalibrate,
        open_settings,
        keyboard,
        recentre=None,
        head_mode=False,
        scroll_stop_hint=lambda: SCROLL_STOP_HINTS["long_blink"],
    ):
        self.scroll_stop_hint = scroll_stop_hint
        self.width, self.height = size
        # Issue #160: head-cursor extras. ``recentre`` asks the model to recentre.
        self.recentre = recentre
        self.head_mode = head_mode
        self.commands = COMMANDS + ((RECENTRE,) if recentre is not None else ())
        self.recentre_at = self.reveal_after = self.head_scroll = None
        self.head_scroll_pending = self.face_holding = False
        self.on_rail = self.rail_expanded = False
        self.rail_left_at = None
        self.recalibrate = recalibrate
        self.open_settings = open_settings
        self.scroll_multiplier = 1
        self.panel = nonactivating_panel((WIDTH, 500))
        self.panel.setTitle_("Göz kontrolü")
        self.rail = nonactivating_panel((200, 500))
        self.rail.setTitle_("Masaüstü komutları")
        self.hint = nonactivating_panel((260, 62))
        self.hint.setIgnoresMouseEvents_(True)
        self.hint_until = 0
        self.reticle = nonactivating_panel((44, 44))
        self.reticle.setIgnoresMouseEvents_(True)
        self.background = color(0.07, 0.09, 0.13)
        self.card = color(0.13, 0.16, 0.22)
        self.hover_card = color(0.18, 0.30, 0.33)
        self.ink = color(0.95, 0.98, 0.99)
        self.muted = color(0.72, 0.79, 0.84)
        self.accent = color(0.40, 1.0, 0.81)
        self.delegate = BarItem.alloc().init()
        self.delegate.callback = self.command
        self.dwell = RegionDwell(seconds=0.88)
        self.rail_dwell = RegionDwell(seconds=0.72)
        self.direction = HeldDirection()
        self.key_dwell = RegionDwell(seconds=1.0)
        self.confirm = Confirmation()
        self.scrolling = ScrollRepeat()
        self.results = queue.Queue()
        self.dock_results = queue.Queue()
        self.dock_loading = False
        self.dock_entries = []
        self.dictation = Dictation(self.results)
        self.keyboard = keyboard
        self.keyboard.dictate = self.dictate
        self.visible = self.paused = self.tools_ready = False
        self.status = None
        self.active_mode = self.anchor = self.aim_since = self.front_pid = None
        self.last_keyboard_poll = 0
        self.last_stamp = self.last_action_stamp = self.last_frame = None
        self.progress_mark = -1
        self.latest_point = self.mode_origin = self.blocked_rect = None
        self.keyboard_owned = False
        self.hover = self.marker_state = None
        self.center_left = False
        self.home()
        marker = UI.NSView.alloc().initWithFrame_(((0, 0), (44, 44)))
        for x, y, w, h in ((20, 0, 4, 14), (20, 30, 4, 14), (0, 20, 14, 4), (30, 20, 14, 4)):
            line = self.surface((w, h), self.accent, 2)
            line.setFrameOrigin_((x, y))
            marker.addSubview_(line)
        self.reticle.setContentView_(marker)

    def surface(self, size, fill, radius):
        view = UI.NSView.alloc().initWithFrame_(((0, 0), size))
        view.setWantsLayer_(True)
        view.layer().setCornerRadius_(radius)
        view.layer().setBackgroundColor_(fill.CGColor())
        return view

    def button(self, key, title, icon, rect, app_icon=None):
        button = UI.NSButton.buttonWithTitle_target_action_(title, self.delegate, "press:")
        button.setIdentifier_(key)
        button.setBordered_(False)
        button.setAccessibilityLabel_(title)
        button.setFrame_(rect)
        button.setWantsLayer_(True)
        button.layer().setBackgroundColor_(self.card.CGColor())
        button.layer().setCornerRadius_(13)
        button.setFont_(UI.NSFont.systemFontOfSize_weight_(15, UI.NSFontWeightSemibold))
        button.setContentTintColor_(self.ink)
        button.setAttributedTitle_(
            UI.NSAttributedString.alloc().initWithString_attributes_(
                title,
                {
                    UI.NSForegroundColorAttributeName: self.ink,
                    UI.NSFontAttributeName: button.font(),
                },
            )
        )
        image = app_icon
        if image is None:
            image = UI.NSImage.imageWithSystemSymbolName_accessibilityDescription_(icon, title)
            if image:
                config = UI.NSImageSymbolConfiguration.configurationWithPointSize_weight_(
                    23, UI.NSFontWeightMedium
                )
                image = image.imageWithSymbolConfiguration_(config)
        if image:
            button.setImage_(image)
            button.setImagePosition_(UI.NSImageAbove if title else UI.NSImageOnly)
        return button

    def label(self, parent, title, rect, size, ink, weight=UI.NSFontWeightRegular):
        label = UI.NSTextField.wrappingLabelWithString_(title)
        label.setFont_(UI.NSFont.systemFontOfSize_weight_(size, weight))
        label.setTextColor_(ink)
        label.setFrame_(rect)
        parent.addSubview_(label)
        return label

    def render_rail(self):
        """Issue #160: one "Menü" button that opens the two-column icon tiles."""
        if self.paused:
            items = [("pause", "Devam et", "play.fill")]
        elif self.rail_expanded:
            items = [("menu", "Kapat", "xmark"), *self.commands]
        else:
            items = [("menu", "Menü", "square.grid.2x2.fill")]
        expanded = len(items) > 1
        gap = 7
        if expanded:
            rows = math.ceil(len(items) / 2)
            tile = math.floor(min(90, (self.height - 105) / rows))
            width = 2 * tile + gap + 18
            height = rows * (tile + gap) + 11
        else:
            tile = 96
            width = height = tile + 18
        view = self.surface((width, height), color(0.07, 0.09, 0.13, 0.96), 23)
        view.layer().setBorderWidth_(1)
        view.layer().setBorderColor_(self.hover_card.CGColor())
        self.rail_origin = (self.width - width - 10, round((self.height - height) / 2))
        self.rail_size = (width, height)
        self.rail_items = {}
        self.rail_rects = {}
        self.rail_hover = None
        self.rail_progress = self.surface((0, 4), self.accent, 2)
        for i, (key, label, icon) in enumerate(items):
            if expanded:
                y, x = divmod(i, 2)
                rect = ((9 + x * (tile + gap), height - 9 - tile - y * (tile + gap)), (tile, tile))
                button = self.button(key, "", icon, rect)
            else:
                rect = ((9, 9), (tile, tile))
                button = self.button(key, label, icon, rect)
                button.layer().setCornerRadius_(18)
                button.layer().setBackgroundColor_(self.hover_card.CGColor())
            button.setAccessibilityLabel_(label)
            button.setToolTip_(label)
            view.addSubview_(button)
            self.rail_items[key] = (rect, button)
            self.rail_rects[key] = rect
        view.addSubview_(self.rail_progress)
        self.rail.setContentView_(view)
        self.rail.setFrame_display_((self.rail_origin, self.rail_size), False)
        self.rail.orderFrontRegardless()

    def set_rail_expanded(self, expanded):
        if expanded != self.rail_expanded:
            self.rail_expanded = expanded
            self.rail_left_at = None
            self.rail_dwell.reset()
            self.render_rail()

    def show_hint(self, text):
        size = (260, 56)
        view = self.surface(size, self.background, 14)
        self.label(view, text, ((12, 5), (236, 46)), 14, self.ink)
        self.hint.setContentView_(view)
        self.hint.setFrame_display_(
            ((self.rail_origin[0] - size[0] - 12, self.rail_origin[1]), size), False
        )
        self.hint.orderFrontRegardless()
        self.hint_until = time.monotonic() + 3

    def rail_feedback(self, key):
        if key != self.rail_hover:
            if self.rail_hover in self.rail_items:
                base = self.card if self.rail_expanded else self.hover_card
                self.rail_items[self.rail_hover][1].layer().setBackgroundColor_(base.CGColor())
            if key in self.rail_items:
                hover = self.hover_card if self.rail_expanded else self.accent
                self.rail_items[key][1].layer().setBackgroundColor_(hover.CGColor())
            self.rail_hover = key
        if key:
            (x, y), (width, _) = self.rail_items[key][0]
            self.rail_progress.setFrame_(
                ((x + 8, y + 6), ((width - 16) * self.rail_dwell.progress, 4))
            )
        self.rail_progress.setHidden_(not key)

    def render(self, title, subtitle, commands, icons=None):
        self.hover = None
        self.progress_mark = -1
        columns = 2
        rows = math.ceil(len(commands) / columns)
        top = 101
        tile_height = max(48, min(81, (self.height - top - 30) // max(1, rows) - 8))
        gap = 8
        self.panel_height = top + rows * (tile_height + gap) + 15
        view = self.surface((WIDTH, self.panel_height), self.background, 23)
        view.layer().setBorderWidth_(1)
        view.layer().setBorderColor_(self.card.CGColor())
        self.label(
            view,
            title,
            ((17, self.panel_height - 48), (WIDTH - 34, 34)),
            25,
            self.ink,
            UI.NSFontWeightBold,
        )
        self.status = self.label(
            view, subtitle, ((18, self.panel_height - 95), (WIDTH - 36, 42)), 14, self.muted
        )
        self.rows = {}
        self.rects = {}
        tile_width = (WIDTH - 32 - gap) / columns
        for index, (key, label, icon) in enumerate(commands):
            row, column = divmod(index, columns)
            x = 16 + column * (tile_width + gap)
            y = self.panel_height - top - row * (tile_height + gap) - tile_height
            width = WIDTH - 32 if index == len(commands) - 1 and column == 0 else tile_width
            rect = ((x, y), (width, tile_height))
            button = self.button(key, label, icon, rect, (icons or {}).get(key))
            view.addSubview_(button)
            self.rows[key] = button
            self.rects[key] = rect
        self.progress = self.surface((0, 3), self.accent, 1.5)
        view.addSubview_(self.progress)
        self.panel.setContentView_(view)
        if self.visible:
            self.position()

    def position(self):
        if self.tools_ready and self.active_mode == "precise":
            frame = self.precision_frame
        else:
            x = self.rail_origin[0] - WIDTH - 10
            origin = (max(8, x), round(max(9, (self.height - self.panel_height) / 2)))
            frame = (origin, (WIDTH, self.panel_height))
        if frame != self.last_frame:
            self.last_frame = frame
            self.panel.setFrame_display_(frame, False)

    def open(self):
        self.visible = True
        self.last_frame = None
        self.position()
        self.panel.orderFrontRegardless()
        self.rail.orderFrontRegardless()

    def hide(self, caption=None):
        self.visible = False
        self.dwell.reset()
        self.direction.reset()
        self.blocked_rect = None
        self.panel.orderOut_(None)
        self.status = None
        if caption:
            self.show_hint(caption)

    def mark(self, point, state):
        if point is None:
            if self.marker_state is not None:
                self.reticle.orderOut_(None)
                self.marker_state = None
            return
        marker = (*map(round, point), state)
        if self.marker_state == marker:
            return
        x, y, _ = marker
        ink = self.accent if state == "armed" else self.ink
        for line in self.reticle.contentView().subviews():
            line.layer().setBackgroundColor_(ink.CGColor())
        self.reticle.setFrame_display_(((x - 22, self.height - y - 22), (44, 44)), False)
        if self.marker_state is None:
            self.reticle.orderFrontRegardless()
        self.marker_state = marker

    def set_hover(self, key, progress=0):
        if key != self.hover:
            for name in (self.hover, key):
                if name in self.rows:
                    fill = self.hover_card if name == key else self.card
                    self.rows[name].layer().setBackgroundColor_(fill.CGColor())
            self.hover = key
            self.progress_mark = -1
        mark = min(20, int(progress * 20))
        if mark != self.progress_mark:
            self.progress_mark = mark
            if key in self.rects:
                (x, y), (width, _) = self.rects[key]
                self.progress.setFrame_(((x + 9, y + 4), ((width - 18) * mark / 20, 3)))
            self.progress.setHidden_(key is None or mark == 0)

    def render_dock(self):
        per_page = 8
        pages = max(1, math.ceil(len(self.dock_entries) / per_page))
        self.dock_page = max(0, min(self.dock_page, pages - 1))
        start = self.dock_page * per_page
        rows, icons = [], {}
        workspace = UI.NSWorkspace.sharedWorkspace()
        for i, (title, path, _) in enumerate(self.dock_entries[start : start + per_page], start):
            key = f"dock-item-{i}"
            rows.append((key, title, "app"))
            if path and path.exists():
                image = workspace.iconForFile_(str(path)).copy()
                image.setSize_((28, 28))
                icons[key] = image
        if pages > 1:
            rows.extend(
                (
                    ("dock-previous", "Önceki", "chevron.left"),
                    ("dock-next", "Sonraki", "chevron.right"),
                )
            )
        rows.append(BACK)
        subtitle = (
            f"{len(self.dock_entries)} uygulama  ·  Sayfa {self.dock_page + 1}/{pages}"
            if self.dock_entries
            else "Dock uygulamaları bulunamadı."
        )
        self.render("Dock", subtitle, rows, icons)

    def load_dock(self):
        self.dock_page = 0
        self.page = "dock"
        self.render("Dock", "Uygulamalar yükleniyor…", (BACK,))
        if self.dock_loading:
            return
        self.dock_loading = True

        def read():
            try:
                with objc.autorelease_pool():
                    entries = dock_applications()
            except Exception as error:
                print(f"Dock listesi okunamadı: {error}", flush=True)
                entries = []
            self.dock_results.put(entries)

        threading.Thread(target=read, daemon=True).start()

    def render_settings(self):
        self.render(
            "Göz kontrolü ayarları",
            "Bu oturumda gözle kontrol açık.",
            (
                (
                    "speed",
                    "Kaydırma: " + ("Hızlı" if self.scroll_multiplier > 1 else "Normal"),
                    "speedometer",
                ),
                BACK,
            ),
        )

    def message(self, text):
        if self.visible and self.status is not None:
            self.status.setStringValue_(text)
        elif not self.paused:
            self.show_hint(text)

    def dictate(self):
        target = self.keyboard.focused()
        if target is None:
            self.message("Önce yazılabilir bir metin alanına tıkla.")
            return
        recording = self.dictation.start(target)
        self.message(
            "Dinleniyor. Bitirmek için Dikte’yi tekrar seç."
            if recording
            else "Konuşma yazıya çevriliyor…"
        )

    def process_results(self):
        if self.dock_loading:
            try:
                self.dock_entries = self.dock_results.get_nowait()
            except queue.Empty:
                pass
            else:
                self.dock_loading = False
                if self.page == "dock":
                    self.render_dock()
        try:
            target, text, error = self.results.get_nowait()
        except queue.Empty:
            return
        if error or not text or self.paused or self.keyboard.focused() != target:
            self.message(error or "Dikte durdu veya metin alanı değişti.")
            return
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, 0, down)
            Quartz.CGEventSetFlags(event, 0)
            Quartz.CGEventKeyboardSetUnicodeString(event, len(text.encode("utf-16-le")) // 2, text)
            Quartz.CGEventPostToPid(target[0], event)
        self.message("Dikte metne eklendi.")

    def click(self, side, point, count=1):
        if point is None or self.paused:
            return
        button, down, up = (
            (Quartz.kCGMouseButtonLeft, Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp)
            if side == "left"
            else (
                Quartz.kCGMouseButtonRight,
                Quartz.kCGEventRightMouseDown,
                Quartz.kCGEventRightMouseUp,
            )
        )
        for clicks in range(1, count + 1):
            events = [
                Quartz.CGEventCreateMouseEvent(None, event, point, button) for event in (down, up)
            ]
            if not all(event is not None for event in events):
                return
            for event in events:
                # A double click must carry click state 2 on its second press.
                Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventClickState, clicks)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        # A click into a text field opens the keyboard (Issue #160).
        self.reveal_after = time.monotonic() + REVEAL_KEYBOARD_AFTER_SECONDS

    def scroll(self, direction, amount):
        if self.anchor is None or self.paused:
            return
        dx, dy = VECTORS[direction]
        amount = round(amount * self.scroll_multiplier)
        event = Quartz.CGEventCreateScrollWheelEvent(
            None,
            Quartz.kCGScrollEventUnitPixel,
            2,
            -dy * amount,
            -dx * amount,
        )
        if event is not None:
            Quartz.CGEventSetLocation(event, self.anchor)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def cancel_mode(self):
        self.head_scroll = None
        self.head_scroll_pending = False
        self.active_mode = self.anchor = self.aim_since = self.front_pid = None
        self.tools_ready = self.center_left = False
        self.confirm.reset()
        self.scrolling.reset()
        self.direction.reset()
        self.mark(None, None)

    def start_mode(self, key):
        self.cancel_mode()
        self.active_mode = key
        self.mode_origin = self.latest_point
        if self.mode_origin is None:
            position = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
            self.mode_origin = (position.x, position.y)
        caption = {
            "left": "Sol tık\nHedefe bak. Ses gelince iki kez kırp.",
            "right": "Sağ tık\nHedefe bak. Ses gelince iki kez kırp.",
            "precise": "Hassas imleç\nİmleci koymak istediğin yere bak.",
            "scroll": "Kaydır\nKaydırmak istediğin alana imleci getir."
            if self.head_mode
            else "Kaydır\nKaydırmak istediğin alana bak.",
        }[key]
        self.hide(caption)

    def render_precision(self):
        self.status = None
        tile, gap, pad = 78, 9, 10
        pitch = tile + gap
        width, height = pitch * 3 + 11, pitch * 4 + 11
        x, y = self.anchor
        self.precision_frame = (
            (
                round(max(8, min(self.rail_origin[0] - width - 8, x - width / 2))),
                round(max(8, min(self.height - height - 8, self.height - y - (2 * pitch + 39)))),
            ),
            (width, height),
        )
        view = UI.NSView.alloc().initWithFrame_(((0, 0), (width, height)))
        self.hover = None
        self.progress_mark = -1
        self.rows, self.rects = {}, {}
        controls = [
            ("precise-up", "Yukarı", "arrow.up", 1, 3),
            ("precise-left", "Sola", "arrow.left", 0, 2),
            ("precise-right", "Sağa", "arrow.right", 2, 2),
            ("precise-down", "Aşağı", "arrow.down", 1, 1),
            ("fine-click-left", "Sol tık", "cursorarrow.click", 0, 0),
            ("fine-click-right", "Sağ tık", "contextualmenu.and.cursorarrow", 1, 0),
            ("cancel", "Kapat", "xmark", 2, 0),
        ]
        for key, label, icon, col, row in controls:
            rect = ((pad + pitch * col, pad + pitch * row), (tile, tile))
            button = self.button(key, "", icon, rect)
            button.setAccessibilityLabel_(label)
            button.setToolTip_(label)
            view.addSubview_(button)
            self.rects[key], self.rows[key] = rect, button
        self.progress = self.surface((0, 3), self.accent, 1.5)
        view.addSubview_(self.progress)
        self.panel.setContentView_(view)

    def move_precisely(self, now, direction):
        delta = self.direction.step(now, direction)
        if not delta:
            return
        dx, dy = VECTORS[direction]
        x, y = self.anchor
        self.anchor = (
            max(0, min(self.width - 1, x + dx * delta)),
            max(0, min(self.height - 1, y + dy * delta)),
        )
        Quartz.CGWarpMouseCursorPosition(self.anchor)
        self.mark(self.anchor, "armed")

    def render_tools(self):
        mode = self.active_mode
        if mode == "precise":
            self.render_precision()
            return
        commands = tuple((f"{mode}-{key}", title, icon) for key, title, icon in DIRECTIONS)
        self.render(
            "Kaydır", "Bir yön okuna bakılı tut.", commands + (("cancel", "Bitir", "xmark"),)
        )

    def home(self):
        self.page = "home"
        self.hide()
        self.render_rail()

    def command(self, key):
        if key == "menu":
            self.set_rail_expanded(not self.rail_expanded)
            return
        if self.rail_expanded and key in self.rail_rects:
            self.set_rail_expanded(False)
        if self.visible and key in self.rects and not key.startswith("precise-"):
            (left, bottom), (width, height) = self.rects[key]
            origin, _ = self.last_frame
            self.blocked_rect = ((origin[0] + left, origin[1] + bottom), (width, height))
        if self.paused and key != "pause":
            return
        if key in ("left", "right", "precise", "scroll"):
            self.start_mode(key)
        elif key == "pause":
            self.paused = not self.paused
            self.cancel_mode()
            self.keyboard.stow()
            if self.paused:
                self.dictation.close()
            self.home()
            self.hide()
        elif key == "keyboard":
            self.cancel_mode()
            if self.keyboard.reveal():
                self.hide()
            else:
                self.show_hint("Önce yazılabilir bir metin alanına tıkla.")
        elif key == "dictation":
            self.cancel_mode()
            self.dictate()
        elif key == "dock":
            self.cancel_mode()
            self.load_dock()
            self.open()
        elif key in ("dock-next", "dock-previous"):
            self.dock_page += 1 if key == "dock-next" else -1
            self.render_dock()
        elif key.startswith("dock-item-"):
            i = int(key.removeprefix("dock-item-"))
            _, path, item = self.dock_entries[i]
            if path:
                opened = UI.NSWorkspace.sharedWorkspace().openURL_(
                    UI.NSURL.fileURLWithPath_(str(path))
                )
            else:
                opened = AX.AXUIElementPerformAction(item, "AXPress") == 0
            if opened:
                self.home()
                self.hide()
            else:
                self.message("Bu uygulama açılamadı.")
        elif key.startswith("fine-click-") and self.tools_ready:
            point = self.anchor
            self.cancel_mode()
            self.hide()
            self.click(key.removeprefix("fine-click-"), point)
        elif key.startswith("scroll-") and self.tools_ready:
            self.scroll(key.removeprefix("scroll-"), 108)
        elif key == "calibrate":
            self.recalibrate()
        elif key == "settings":
            self.cancel_mode()
            self.page = "settings"
            self.render_settings()
            self.open()
            self.open_settings()
        elif key == "speed":
            self.scroll_multiplier = 1.6 if self.scroll_multiplier == 1 else 1
            self.render_settings()
        elif key == "back":
            self.home()
        elif key == "recentre" and self.recentre is not None:
            self.cancel_mode()
            self.recentre_at = time.monotonic() + RECENTRE_DELAY_SECONDS
            self.show_hint("Kafanı rahat, orta bir duruşa getir.\n1,5 sn sonra ortalanacak.")
        elif key == "cancel":
            self.cancel_mode()
            self.hide()

    def hit_test(self, point, frame, controls):
        if point is None:
            return False, None
        (origin_x, origin_y), (width, height) = frame
        x, y = point[0] - origin_x, self.height - point[1] - origin_y
        inside = 0 <= x < width and 0 <= y < height
        if inside:
            for key, ((left, bottom), (w, h)) in controls.items():
                if left <= x < left + w and bottom <= y < bottom + h:
                    return True, key
        return inside, None

    def start_head_scroll(self, point):
        """A face gesture starts head scrolling at ``point`` (Issue #160).

        The neutral height is taken once the gesture has ended, because the
        gesture itself shifts the head-pose reading.
        """
        self.cancel_mode()
        self.active_mode, self.anchor, self.tools_ready = "scroll", point, True
        self.head_scroll_pending = True
        Quartz.CGWarpMouseCursorPosition(point)
        self.mark(point, "armed")
        self.show_hint(
            "Kaydırma: kafanı aşağı eğ: aşağı, yukarı kaldır: yukarı.\n"
            f"Durdurmak için {self.scroll_stop_hint()}."
        )

    def toggle_keyboard(self):
        if self.keyboard.target is not None:
            self.keyboard.stow()
        elif not self.keyboard.reveal():
            self.show_hint("Önce yazılabilir bir metin alanına tıkla.")

    def stop_head_scroll(self):
        """The stop gesture ends head scrolling (Issue #160)."""
        if self.head_scroll is None and not self.head_scroll_pending:
            return False
        self.cancel_mode()
        self.show_hint("Kaydırma durdu.")
        return True

    @property
    def pointer_free(self):
        """The cursor may follow the head/gaze smoothly over our own panels."""
        return (
            self.confirm.phase != "armed"
            and self.head_scroll is None
            and not self.head_scroll_pending
            and (self.keyboard_owned or self.on_rail or (self.visible and not self.tools_ready))
        )

    def pending_actions(self, now):
        if self.recentre_at is not None and now >= self.recentre_at:
            self.recentre_at = None
            self.show_hint("Kafa ortalandı." if self.recentre() else "Ortalanamadı.")
        if self.reveal_after is not None and now >= self.reveal_after:
            self.reveal_after = None
            if not self.paused and self.keyboard.target is None and self.keyboard.reveal():
                self.hide()

    def tick(self, stamp, now, point, closed, assisted=None):
        self.process_results()
        self.pending_actions(now)
        self.latest_point = point
        if self.hint_until and now >= self.hint_until:
            self.hint.orderOut_(None)
            self.hint_until = 0
        fresh = stamp != self.last_stamp
        if fresh:
            self.last_stamp = stamp

        on_rail, rail_key = self.hit_test(
            point, (self.rail_origin, self.rail_size), self.rail_rects
        )
        self.on_rail = on_rail
        if self.rail_expanded:
            if on_rail:
                self.rail_left_at = None
            elif self.rail_left_at is None:
                self.rail_left_at = now
            elif now - self.rail_left_at >= RAIL_COLLAPSE_SECONDS:
                self.set_rail_expanded(False)
        if self.paused and rail_key != "pause":
            rail_key = None
        if point is None:
            self.rail_dwell.missing(now)
        elif fresh:
            fired = self.rail_dwell.update(stamp, rail_key)
            self.rail_feedback(rail_key)
            if fired:
                self.command(rail_key)
                return True
        if on_rail or self.paused:
            self.direction.reset()
            self.scrolling.reset()
            if on_rail and fresh:
                self.confirm.reset()
                if self.active_mode in ("left", "right"):
                    self.anchor = self.aim_since = None
                    self.mark(None, None)
            return True

        if point is not None and self.active_mode and not self.center_left:
            self.center_left = math.dist(point, self.mode_origin) >= 64
        if not self.visible:
            return False

        inside, key = self.hit_test(point, self.last_frame, self.rects)
        if self.blocked_rect is not None and point is not None:
            blocked, _ = self.hit_test(point, self.blocked_rect, {})
            if blocked:
                return True
            self.blocked_rect = None
            self.dwell.reset()
        if self.active_mode == "precise":
            direction = (
                key.removeprefix("precise-")
                if key and key.startswith("precise-") and now - stamp <= 0.30
                else None
            )
            self.move_precisely(now, direction)
        if point is None:
            self.dwell.missing(now)
            self.scrolling.reset()
            if self.dwell.target is None:
                self.set_hover(None)
        elif fresh:
            if key and key.startswith("scroll-"):
                amount = self.scrolling.update(stamp, key)
                if amount:
                    self.scroll(key.removeprefix("scroll-"), amount)
                self.dwell.reset()
                self.set_hover(key, min(1, (stamp - self.scrolling.started) / 0.32))
            elif key and key.startswith("precise-"):
                self.dwell.reset()
                elapsed = now - self.direction.since if self.direction.since is not None else 0
                self.set_hover(key, min(1, elapsed / 0.30))
            else:
                self.scrolling.reset()
                fired = self.dwell.update(stamp, key)
                self.set_hover(key, self.dwell.progress)
                if fired:
                    self.command(key)
        return inside or self.tools_ready

    def desktop_gaze(
        self, stamp, point, closed, valid, assisted, blink_samples=None, keyboard_point=None
    ):
        if self.head_scroll_pending:
            if point is not None and not closed and not self.face_holding:
                self.head_scroll = point[1]
                self.head_scroll_pending = False
            return True
        if self.head_scroll is not None:
            # Blinks and missing frames pause scrolling but keep the anchor.
            if point is not None and not closed and stamp != self.last_action_stamp:
                self.last_action_stamp = stamp
                amount = scroll_step(point[1] - self.head_scroll)
                if amount:
                    self.scroll("down" if amount > 0 else "up", abs(amount))
            return True
        fast_armed = self.confirm.phase == "armed" and blink_samples is not None
        if fast_armed and time.monotonic() - self.confirm.last > 0.40:
            fast_armed = False
            valid = False
        if not valid and not fast_armed:
            self.keyboard_owned = False
            if self.confirm.phase == "armed":
                self.show_hint("Hedefe tekrar bak.")
            self.confirm.reset()
            self.anchor = self.aim_since = None
            self.key_dwell.missing(time.monotonic())
            self.mark(None, None)
            return False
        if stamp == self.last_action_stamp:
            return self.confirm.phase == "armed" or self.keyboard_owned
        self.last_action_stamp = stamp
        self.keyboard_owned = False
        if self.keyboard.target and stamp - self.last_keyboard_poll >= 0.2:
            self.last_keyboard_poll = stamp
            self.keyboard.refresh()
        if self.active_mode is None:
            if point is None:
                self.key_dwell.missing(stamp)
                return False
            key = self.keyboard.key_at(*(keyboard_point or point), self.height)
            if self.key_dwell.update(stamp, key):
                self.keyboard.press(key)
            self.keyboard_owned = key is not None
            return self.keyboard_owned

        if not self.center_left:
            return False
        if not closed and point is None and not fast_armed:
            self.confirm.reset()
            self.anchor = self.aim_since = None
            self.mark(None, None)
            return False
        app = UI.NSWorkspace.sharedWorkspace().frontmostApplication()
        pid = app.processIdentifier() if app else None
        distance = 58 if self.confirm.phase == "armed" else 38
        if pid != self.front_pid or (
            point is not None
            and self.anchor is not None
            and math.dist(point, self.anchor) > distance
        ):
            if self.confirm.phase == "armed":
                self.show_hint("Hedefe tekrar bak.")
            self.anchor = self.aim_since = None
            self.confirm.reset()
            self.mark(None, None)
        self.front_pid = pid
        if pid is None:
            return False
        if point is not None and self.anchor is None:
            self.anchor, self.aim_since = point, stamp
        if self.active_mode in ("precise", "scroll"):
            if closed or point is None:
                self.anchor = self.aim_since = None
            elif stamp - self.aim_since >= 0.55:
                self.anchor = (
                    0.65 * self.anchor[0] + 0.35 * point[0],
                    0.65 * self.anchor[1] + 0.35 * point[1],
                )
                self.tools_ready = True
                Quartz.CGWarpMouseCursorPosition(self.anchor)
                if self.active_mode == "scroll" and self.head_mode:
                    # Issue #160: head tilt scrolls; a long blink stops.
                    self.head_scroll = point[1]
                    self.mark(self.anchor, "armed")
                    self.show_hint(
                        "Kafanı aşağı eğ: aşağı, yukarı kaldır: yukarı.\n"
                        f"Durdurmak için {self.scroll_stop_hint()}."
                    )
                    return True
                self.mark(self.anchor if self.active_mode == "precise" else None, "armed")
                self.render_tools()
                self.open()
                return True
            return False

        old = self.confirm.phase
        previous_blink = self.confirm.first
        target = pid if self.anchor is not None else None
        if fast_armed and old == "armed":
            phase = old
            for seen_at, observed in blink_samples:
                if self.confirm.last is not None and seen_at <= self.confirm.last:
                    continue
                phase = self.confirm.update(seen_at, target, observed)
                if phase in ("confirmed", "idle"):
                    break
        else:
            phase = self.confirm.update(stamp, target, closed)
        if phase == "armed" and old != "armed":
            self.click_point = (
                assisted
                if assisted is not None and math.dist(assisted, self.anchor) <= 45
                else self.anchor
            )
            Quartz.CGWarpMouseCursorPosition(self.click_point)
            self.mark(self.click_point, "armed")
            self.show_hint("Tık hazır\nŞimdi iki kez kırp.")
            UI.NSBeep()
        elif phase == "armed" and previous_blink != self.confirm.first:
            self.show_hint(
                "1/2 kırpma algılandı."
                if self.confirm.first is not None
                else "Tık hazır. İki kez kırp."
            )
        elif phase == "confirmed":
            self.click(self.active_mode, self.click_point)
            self.cancel_mode()
            self.hide()
        elif phase != "armed" and old == "armed":
            self.mark(None, None)
            self.show_hint("Hedefe tekrar bak.")
        return phase == "armed"

    def close(self):
        self.dictation.close()
        self.keyboard.dispose()
        for panel in (self.reticle, self.hint, self.rail, self.panel):
            panel.close()
