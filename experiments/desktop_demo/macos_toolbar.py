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
from .dictation import Dictation
from .macos_keyboard import attribute

COMMANDS = (
    ("left", "Sol tık", "cursorarrow.click"),
    ("right", "Sağ tık", "computermouse"),
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
    def __init__(self, size, recalibrate, open_settings, keyboard, reduced_motion=False):
        self.width, self.height = size
        self.recalibrate = recalibrate
        self.open_settings = open_settings
        self.system_reduced_motion = reduced_motion
        self.reduced_motion = False
        self.scroll_multiplier = 1
        self.panel = nonactivating_panel((WIDTH, 500))
        self.panel.setTitle_("Göz kontrolü")
        self.tab = nonactivating_panel((54, 96))
        self.tab.setTitle_("Göz kontrolü oku")
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
        self.edge_dwell = RegionDwell(seconds=0.42)
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
        self.active_mode = self.anchor = self.aim_since = self.front_pid = None
        self.activity = self.animation = self.last_keyboard_poll = 0
        self.last_stamp = self.last_action_stamp = self.last_frame = None
        self.progress_mark = -1
        self.latest_point = self.mode_origin = self.blocked_rect = None
        self.hover = self.marker_state = None
        self.center_left = False
        self.home()
        self.show_tab()
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

    def show_tab(self, caption=None):
        mode = self.active_mode
        icon = "play.fill" if self.paused else ("xmark" if mode else "chevron.left")
        tab_width = 232 if caption else 54
        size = (tab_width, 88)
        view = self.surface(size, self.background, 17)
        label = caption or ("Devam et" if self.paused else "Göz kontrolünü aç")
        button = self.button("edge", "", icon, ((tab_width - 49, 6), (43, 76)))
        button.setAccessibilityLabel_(label)
        view.addSubview_(button)
        if caption:
            self.label(view, caption, ((13, 11), (tab_width - 72, 65)), 14, self.ink)
        self.tab.setContentView_(view)
        self.tab.setFrame_display_(
            ((self.width - tab_width, (self.height - size[1]) / 2), size), False
        )
        self.tab.orderFrontRegardless()

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
            self.position(time.monotonic())

    def render_home(self):
        if self.paused:
            self.render(
                "Duraklatıldı",
                "Devam etmek için oynat simgesine bak.",
                (("pause", "Devam et", "play.fill"),),
            )
        else:
            self.render("Göz kontrolü", "Seçmek için simgeye bak.", COMMANDS)

    def position(self, now):
        t = min(1, max(0, (now - self.animation) / 0.33))
        if self.system_reduced_motion or self.reduced_motion or self.tools_ready:
            t = 1
        eased = 1 - (1 - t) ** 3
        spring = 10 * math.sin(math.pi * t) * eased
        x = self.width - (WIDTH + 14) * eased - spring
        if self.tools_ready and self.tools_on_left:
            x = 14
        x, y = round(x), round(max(9, (self.height - self.panel_height) / 2))
        frame = ((x, y), (WIDTH, self.panel_height))
        if frame != self.last_frame:
            self.last_frame = frame
            self.panel.setFrame_display_(frame, False)

    def open(self, now):
        self.visible = True
        self.activity = self.animation = now
        self.last_frame = None
        self.position(now)
        self.tab.orderOut_(None)
        self.panel.orderFrontRegardless()

    def hide(self, caption=None):
        self.visible = False
        self.dwell.reset()
        self.edge_dwell.reset()
        self.blocked_rect = None
        self.panel.orderOut_(None)
        self.show_tab(caption)

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
        if self.visible:
            self.status.setStringValue_(text)
        elif not self.active_mode and not self.paused:
            self.show_tab(text)

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

    def click(self, side, point):
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
        events = [
            Quartz.CGEventCreateMouseEvent(None, event, point, button) for event in (down, up)
        ]
        if all(event is not None for event in events):
            for event in events:
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

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
        self.active_mode = self.anchor = self.aim_since = self.front_pid = None
        self.tools_ready = self.center_left = False
        self.confirm.reset()
        self.scrolling.reset()
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
            "scroll": "Kaydır\nKaydırmak istediğin alana bak.",
        }[key]
        self.hide(caption)

    def render_tools(self):
        mode = self.active_mode
        commands = tuple((f"{mode}-{key}", title, icon) for key, title, icon in DIRECTIONS)
        if mode == "precise":
            commands += (
                ("fine-click-left", "Buraya sol tık", "cursorarrow.click"),
                ("fine-click-right", "Buraya sağ tık", "computermouse"),
            )
        commands += (("cancel", "Bitir", "xmark"),)
        if mode == "precise":
            self.render(
                "Hassas imleç", "Artıyı oklarla 12 piksel taşı. Sonra tık türünü seç.", commands
            )
        else:
            self.render(
                "Kaydır", "Oka bakılı tuttukça hızlanır. Bakışını ayırınca durur.", commands
            )

    def home(self):
        self.page = "home"
        self.render_home()

    def command(self, key):
        self.activity = time.monotonic()
        if self.visible and key in self.rects:
            (left, bottom), (width, height) = self.rects[key]
            origin, _ = self.last_frame
            self.blocked_rect = ((origin[0] + left, origin[1] + bottom), (width, height))
        if self.paused and key not in ("edge", "pause"):
            return
        if key == "edge":
            if self.active_mode:
                self.cancel_mode()
            self.home()
            self.open(self.activity)
        elif key in ("left", "right", "precise", "scroll"):
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
            if self.keyboard.reveal():
                self.hide()
            else:
                self.status.setStringValue_("Önce yazılabilir bir metin alanına tıkla.")
        elif key == "dictation":
            self.dictate()
        elif key == "dock":
            self.load_dock()
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
                self.status.setStringValue_("Bu uygulama açılamadı.")
        elif key.startswith("precise-") and self.tools_ready:
            dx, dy = VECTORS[key.removeprefix("precise-")]
            x, y = self.anchor
            self.anchor = (
                max(0, min(self.width - 1, x + dx * 12)),
                max(0, min(self.height - 1, y + dy * 12)),
            )
            Quartz.CGWarpMouseCursorPosition(self.anchor)
            self.mark(self.anchor, "armed")
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
            self.page = "settings"
            self.render_settings()
            self.open_settings()
        elif key == "speed":
            self.scroll_multiplier = 1.6 if self.scroll_multiplier == 1 else 1
            self.render_settings()
        elif key == "back":
            self.home()
        elif key == "cancel":
            self.cancel_mode()
            self.hide()

    def tick(self, stamp, now, point, closed, assisted=None):
        self.process_results()
        self.latest_point = point
        if self.blocked_rect is not None and point is not None:
            (x, y), (w, h) = self.blocked_rect
            if x <= point[0] < x + w and y <= self.height - point[1] < y + h:
                return True
            self.blocked_rect = None
            self.dwell.reset()
        fresh = stamp != self.last_stamp
        if fresh:
            self.last_stamp = stamp
        if self.visible:
            self.position(now)
            (origin_x, origin_y), (width, height) = self.last_frame
            inside = False
            key = None
            if point is not None:
                x = point[0] - origin_x
                y = self.height - point[1] - origin_y
                inside = 0 <= x < width and 0 <= y < height
                if inside:
                    self.activity = now
                    for name, ((left, bottom), (w, h)) in self.rects.items():
                        if left <= x < left + w and bottom <= y < bottom + h:
                            key = name
                            break
            else:
                self.dwell.missing(now)
                self.scrolling.reset()
                if self.dwell.target is None:
                    self.set_hover(None)
            recording = self.dictation.thread is not None and self.dictation.thread.is_alive()
            if not self.tools_ready and self.page != "settings" and not recording:
                if now - self.activity > 3:
                    self.hide()
                    return self.paused
            if fresh and point is not None:
                settled = now - self.animation >= 0.24
                if key and key.startswith("scroll-") and settled:
                    amount = self.scrolling.update(stamp, key)
                    if amount:
                        self.scroll(key.removeprefix("scroll-"), amount)
                    self.dwell.reset()
                    progress = min(1, (stamp - self.scrolling.started) / 0.32)
                    self.set_hover(key, progress)
                else:
                    self.scrolling.reset()
                    fired = self.dwell.update(stamp, key if settled else None)
                    self.set_hover(key, self.dwell.progress)
                    if fired:
                        self.command(key)
            return inside or self.tools_ready or self.paused

        edge = self.at_edge(point)
        if edge:
            if self.active_mode and not self.center_left:
                return False
            if fresh and self.edge_dwell.update(stamp, "edge"):
                self.command("edge")
                return True
            return self.active_mode is None
        if point is not None:
            self.edge_dwell.reset()
            if self.active_mode and not self.center_left:
                self.center_left = math.dist(point, self.mode_origin) >= 64
        else:
            self.edge_dwell.missing(now)
        return self.paused

    def at_edge(self, point):
        return (
            point is not None
            and point[0] >= self.width - 96
            and abs(point[1] - self.height / 2) <= 73
        )

    def desktop_gaze(self, stamp, point, closed, valid, assisted):
        if not valid:
            if self.confirm.phase == "armed":
                self.show_tab("Hedefe tekrar bak.")
            self.confirm.reset()
            self.anchor = self.aim_since = None
            self.key_dwell.missing(time.monotonic())
            self.mark(None, None)
            return False
        if stamp == self.last_action_stamp:
            return False
        self.last_action_stamp = stamp
        if self.keyboard.target and stamp - self.last_keyboard_poll >= 0.2:
            self.last_keyboard_poll = stamp
            self.keyboard.refresh()
        if self.active_mode is None:
            if point is None:
                self.key_dwell.missing(stamp)
                return False
            key = self.keyboard.key_at(*point, self.height)
            if self.key_dwell.update(stamp, key):
                self.keyboard.press(key)
            return key is not None

        if self.at_edge(point):
            if self.confirm.phase == "armed":
                self.show_tab("Hedefe tekrar bak.")
            self.confirm.reset()
            self.anchor = self.aim_since = None
            self.mark(None, None)
            return False
        if not self.center_left:
            return False
        now = time.monotonic()
        if not closed and point is None:
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
                self.show_tab("Hedefe tekrar bak.")
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
                self.tools_on_left = self.anchor[0] >= self.width / 2
                self.tools_ready = True
                Quartz.CGWarpMouseCursorPosition(self.anchor)
                self.mark(self.anchor if self.active_mode == "precise" else None, "armed")
                self.render_tools()
                self.open(now)
                return True
            return False

        old = self.confirm.phase
        phase = self.confirm.update(stamp, pid if self.anchor is not None else None, closed)
        if phase == "armed" and old != "armed":
            self.click_point = assisted or self.anchor
            self.mark(self.click_point, "armed")
            self.show_tab("Tık hazır\nŞimdi iki kez kırp.")
            UI.NSBeep()
        elif phase == "confirmed":
            self.click(self.active_mode, self.click_point)
            self.cancel_mode()
            self.hide()
        elif phase != "armed" and old == "armed":
            self.mark(None, None)
            self.show_tab("Hedefe tekrar bak.")
        return False

    def close(self):
        self.dictation.close()
        self.keyboard.dispose()
        for panel in (self.reticle, self.tab, self.panel):
            panel.close()
