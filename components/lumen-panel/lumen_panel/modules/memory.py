"""Memory usage (MemTotal - MemAvailable)."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import sysinfo, util
from . import Module, register


@register("memory")
class Memory(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        dim = Gtk.Label(label="MEM")
        dim.get_style_context().add_class("dim")
        self.value = Gtk.Label(label="--")
        self.pack_start(dim, False, False, 0)
        self.pack_start(self.value, False, False, 0)

    def _tick(self) -> None:
        text = util.read_text("/proc/meminfo")
        if not text:
            return
        used, total = sysinfo.parse_meminfo(text)
        pct = 100.0 * used / total if total else 0.0
        self.value.set_text(sysinfo.format_kib(used))
        self.set_tooltip_text(
            f"{sysinfo.format_kib(used)} of {sysinfo.format_kib(total)} used ({pct:.0f}%)"
        )
        if pct >= self.cfg.get("critical", 90):
            self.set_state("critical")
        elif pct >= self.cfg.get("warn", 75):
            self.set_state("warn")
        else:
            self.set_state()

    def start(self) -> None:
        self.every(self.cfg.get("interval", 3), self._tick)
