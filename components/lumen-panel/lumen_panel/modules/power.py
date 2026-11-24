"""Session/power menu in a popover."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import util
from . import Module, register

ACTIONS = (
    ("lock", "Lock screen", "system-lock-screen-symbolic", False),
    ("logout", "Log out", "system-log-out-symbolic", False),
    ("reboot", "Restart", "system-reboot-symbolic", True),
    ("poweroff", "Power off", "system-shutdown-symbolic", True),
)


@register("power")
class Power(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.get_style_context().remove_class("module")

        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        for c in ("module", "power"):
            self.button.get_style_context().add_class(c)
        self.button.add(Gtk.Image.new_from_icon_name("system-shutdown-symbolic", Gtk.IconSize.MENU))
        self.button.set_tooltip_text("Session")
        self.pack_start(self.button, False, False, 0)

        self.popover = self.new_popover(self.button)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for key, text, icon, destructive in ACTIONS:
            argv = cfg.get(key)
            if not argv:
                continue
            row = Gtk.Button()
            row.set_relief(Gtk.ReliefStyle.NONE)
            if destructive:
                row.get_style_context().add_class("destructive")
            inner = Gtk.Box(spacing=10)
            inner.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
            inner.pack_start(Gtk.Label(label=text, xalign=0), True, True, 0)
            row.add(inner)
            row.connect("clicked", self._run, list(argv))
            box.pack_start(row, False, False, 0)
        box.show_all()
        self.popover.add(box)
        self.button.connect("clicked", lambda _b: self.open_popover(self.popover))

    def _run(self, _button: Gtk.Button, argv: list) -> None:
        self.popover.popdown()
        util.spawn(argv)
