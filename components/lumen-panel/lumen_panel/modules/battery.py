"""Battery level. Hides itself on machines without one (desktops, VMs)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import sysinfo
from . import Module, register


@register("battery")
class BatteryModule(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.set_no_show_all(True)  # stay hidden until a battery is found
        self.icon = Gtk.Image()
        self.value = Gtk.Label()
        self.pack_start(self.icon, False, False, 0)
        self.pack_start(self.value, False, False, 0)

    def _tick(self) -> None:
        bat = sysinfo.read_battery()
        if bat is None:
            self.hide()
            return
        self.icon.set_from_icon_name(sysinfo.battery_icon(bat), Gtk.IconSize.MENU)
        self.value.set_text(f"{bat.percent}%")
        self.set_tooltip_text(f"{bat.percent}% ({bat.status})")
        if bat.charging:
            self.set_state("charging")
        elif bat.percent <= self.cfg.get("critical", 10):
            self.set_state("critical")
        elif bat.percent <= self.cfg.get("warn", 25):
            self.set_state("warn")
        else:
            self.set_state()
        self.show_all()

    def start(self) -> None:
        self.every(self.cfg.get("interval", 30), self._tick)
