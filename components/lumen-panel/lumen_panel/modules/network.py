"""Network state from sysfs; click opens the connection editor."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import sysinfo, util
from . import Module, register


@register("network")
class Network(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.get_style_context().remove_class("module")
        self.command = cfg.get("command", ["nm-connection-editor"])

        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        for c in ("module", "network"):
            self.button.get_style_context().add_class(c)
        box = Gtk.Box(spacing=6)
        self.icon = Gtk.Image.new_from_icon_name("network-offline-symbolic", Gtk.IconSize.MENU)
        self.label = Gtk.Label(label="offline")
        box.pack_start(self.icon, False, False, 0)
        box.pack_start(self.label, False, False, 0)
        self.button.add(box)
        self.button.connect("clicked", lambda _b: util.spawn(self.command))
        self.pack_start(self.button, False, False, 0)

    def _tick(self) -> None:
        state = sysinfo.read_network()
        self.icon.set_from_icon_name(state.icon, Gtk.IconSize.MENU)
        if state.kind == "none":
            self.label.set_text("offline")
            self.button.set_tooltip_text("No active connection")
        else:
            self.label.set_text("Wi-Fi" if state.kind == "wifi" else "Wired")
            self.button.set_tooltip_text(f"{state.interface} ({state.kind})")

    def start(self) -> None:
        self.every(self.cfg.get("interval", 5), self._tick)
