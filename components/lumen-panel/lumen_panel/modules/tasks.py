"""Task list: one button per open window (wlr-foreign-toplevel-management).

Left click activates a window, or minimises it if it is already the focused
one; middle click closes it. Buttons are updated in place as windows change,
so the list does not flicker.
"""
from __future__ import annotations

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, Gtk, Pango  # noqa: E402

from .. import apps, wayland
from ..wlstate import Toplevel, desktop_ids
from . import Module, register

FALLBACK_ICON = "application-x-executable"


def icon_for(app_id: str) -> Gio.Icon:
    info = apps.app_info(app_id)
    if info is not None and info.get_icon() is not None:
        return info.get_icon()
    theme = Gtk.IconTheme.get_default()
    for name in desktop_ids(app_id):
        if theme.has_icon(name):
            return Gio.ThemedIcon.new(name)
    return Gio.ThemedIcon.new(FALLBACK_ICON)


class TaskButton(Gtk.Button):
    def __init__(self, client: wayland.Client, top: Toplevel, max_chars: int) -> None:
        super().__init__()
        self.client = client
        self.key = top.key
        self.max_chars = max_chars
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.get_style_context().add_class("task")
        box = Gtk.Box(spacing=6)
        self.icon = Gtk.Image()
        # Without a fixed pixel size GTK draws an app icon that only ships in large
        # sizes (foot's, for one) at that size, and the panel grows to fit it.
        self.icon.set_pixel_size(16)
        # Ellipsizing lets GTK shrink the titles when many windows are open, so the
        # task list never pushes the centred clock aside.
        self.label = Gtk.Label(xalign=0)
        self.label.set_ellipsize(Pango.EllipsizeMode.END)
        self.label.set_max_width_chars(max_chars)
        box.pack_start(self.icon, False, False, 0)
        box.pack_start(self.label, False, False, 0)
        self.add(box)
        self._app_id = None
        self.connect("button-release-event", self._on_release)
        self.update(top)

    def update(self, top: Toplevel) -> None:
        self.top = top
        if top.app_id != self._app_id:
            self._app_id = top.app_id
            self.icon.set_from_gicon(icon_for(top.app_id), Gtk.IconSize.MENU)
        self.label.set_text(top.title or top.app_id or "Window")
        self.set_tooltip_text(top.title or top.app_id)
        ctx = self.get_style_context()
        for cls, on in (("active", top.active), ("minimized", top.minimized)):
            (ctx.add_class if on else ctx.remove_class)(cls)

    def _on_release(self, _button, event: Gdk.EventButton) -> bool:
        if event.button == 2:
            self.client.close(self.key)
        elif event.button == 1:
            if self.top.click_action() == "minimize":
                self.client.minimize(self.key)
            else:
                self.client.activate(self.key)
        return False


@register("tasks")
class Tasks(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.get_style_context().remove_class("module")
        self.max_chars = int(cfg.get("max_chars", 22))
        self.buttons: dict[int, TaskButton] = {}
        self.client = None
        self._sub = 0

    def start(self) -> None:
        self.client = wayland.shared()
        if self.client is None or not self.client.has_toplevels:
            self.hide()
            return
        self._sub = self.client.subscribe(self.refresh)
        self.refresh()

    def stop(self) -> None:
        super().stop()
        if self.client is not None and self._sub:
            self.client.unsubscribe(self._sub)
            self._sub = 0

    def refresh(self) -> None:
        windows = self.client.state.windows()
        alive = {top.key for top in windows}
        for key in [k for k in self.buttons if k not in alive]:
            self.buttons.pop(key).destroy()
        for top in windows:
            button = self.buttons.get(top.key)
            if button is None:
                button = TaskButton(self.client, top, self.max_chars)
                self.buttons[top.key] = button
                self.pack_start(button, False, False, 0)
                button.show_all()
            else:
                button.update(top)
