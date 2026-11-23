"""Clock with a calendar popover."""
from __future__ import annotations

import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from . import Module, register


@register("clock")
class Clock(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.get_style_context().remove_class("module")
        self.format = cfg.get("format", "%a %d %b   %H:%M")
        self.tooltip_format = cfg.get("tooltip_format", "%A, %d %B %Y")
        self.has_seconds = "%S" in self.format

        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        for c in ("module", "clock"):
            self.button.get_style_context().add_class(c)
        self.label = Gtk.Label()
        self.button.add(self.label)
        self.pack_start(self.button, False, False, 0)

        self.popover = Gtk.Popover.new(self.button)
        self.popover.get_style_context().add_class("lumen-popover")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.title = Gtk.Label(xalign=0)
        self.title.get_style_context().add_class("date-title")
        self.calendar = Gtk.Calendar()
        box.pack_start(self.title, False, False, 0)
        box.pack_start(self.calendar, False, False, 0)
        box.show_all()
        self.popover.add(box)
        self.button.connect("clicked", self._toggle)

    def _toggle(self, _button: Gtk.Button) -> None:
        if self.popover.get_visible():
            self.popover.popdown()
            return
        now = time.localtime()
        self.calendar.select_month(now.tm_mon - 1, now.tm_year)
        self.calendar.select_day(now.tm_mday)
        self.title.set_text(time.strftime("%A, %d %B %Y", now))
        self.popover.popup()

    def _tick(self) -> None:
        now = time.localtime()
        self.label.set_text(time.strftime(self.format, now))
        self.button.set_tooltip_text(time.strftime(self.tooltip_format, now))

    def start(self) -> None:
        self.every(1 if self.has_seconds else 5, self._tick)
