"""CPU utilisation."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import sysinfo, util
from . import Module, register


@register("cpu")
class Cpu(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.sampler = sysinfo.CpuSampler()
        dim = Gtk.Label(label="CPU")
        dim.get_style_context().add_class("dim")
        self.value = Gtk.Label(label="--%")
        self.pack_start(dim, False, False, 0)
        self.pack_start(self.value, False, False, 0)

    def _tick(self) -> None:
        text = util.read_text("/proc/stat")
        pct = self.sampler.update(text) if text else None
        if pct is None:
            return
        self.value.set_text(f"{pct:3.0f}%")
        self.set_tooltip_text(f"CPU utilisation: {pct:.1f}%")
        if pct >= self.cfg.get("critical", 90):
            self.set_state("critical")
        elif pct >= self.cfg.get("warn", 70):
            self.set_state("warn")
        else:
            self.set_state()

    def start(self) -> None:
        self.every(self.cfg.get("interval", 2), self._tick)
