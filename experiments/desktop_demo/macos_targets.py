"""Verified macOS Dock and foreground window targets for pointer assistance."""

import AppKit as UI
import ApplicationServices as AX

from eye_tracker.intent.targets import TargetRect

from .macos_keyboard import attribute as attr


class Dock:
    def __init__(self, screen):
        self.screen = screen
        self.checked = -1
        self.targets = []

    def latest(self, now):
        if now - self.checked < 0.16:
            return self.targets
        self.checked = now
        self.targets = []
        apps = UI.NSRunningApplication.runningApplicationsWithBundleIdentifier_("com.apple.dock")
        if not apps:
            return self.targets
        pid = apps[0].processIdentifier()
        app = AX.AXUIElementCreateApplication(pid)
        AX.AXUIElementSetMessagingTimeout(app, 0.04)
        system = AX.AXUIElementCreateSystemWide()
        AX.AXUIElementSetMessagingTimeout(system, 0.04)
        for container in attr(app, "AXChildren") or ():
            if attr(container, "AXRole") != "AXList":
                continue
            for item in attr(container, "AXChildren") or ():
                if attr(item, "AXSubrole") != "AXApplicationDockItem":
                    continue
                error, actions = AX.AXUIElementCopyActionNames(item, None)
                pos, size = attr(item, "AXPosition"), attr(item, "AXSize")
                if error or "AXPress" not in (actions or ()) or pos is None or size is None:
                    continue
                has_pos, point = AX.AXValueGetValue(pos, AX.kAXValueCGPointType, None)
                has_size, dims = AX.AXValueGetValue(size, AX.kAXValueCGSizeType, None)
                if not has_pos or not has_size or min(dims.width, dims.height) <= 0:
                    continue
                rect = TargetRect(point.x, point.y, dims.width, dims.height)
                if self.screen.distance_to(*rect.center):
                    continue
                hit_status, hit = AX.AXUIElementCopyElementAtPosition(system, *rect.center, None)
                if hit_status or hit is None or AX.AXUIElementGetPid(hit, None) != (0, pid):
                    continue
                key = ("dock", pid, str(attr(item, "AXTitle") or ""), rect)
                self.targets.append((key, rect, True))
        return self.targets


def window_targets(feed, screen, now):
    checked = feed.latest()
    if (
        checked is None
        or checked.snapshot.screen != screen
        or checked.context_id != checked.snapshot.context_id
        or not 0 <= now - checked.checked_at <= 0.15
    ):
        return []
    return [
        (
            (
                "window",
                checked.context_id,
                target.continuity_id or (checked.snapshot.snapshot_id, target.target_id),
                target.rect,
            ),
            target.rect,
            target.enabled is True and target.category == "press",
        )
        for target in checked.snapshot.targets
    ]
