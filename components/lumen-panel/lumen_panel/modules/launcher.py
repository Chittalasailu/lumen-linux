"""Launcher button: opens (or toggles) the application launcher."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import util
from . import Module, register


@register("launcher")
class Launcher(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        # The launcher button is the panel's primary action, so it carries its own
        # CSS class and replaces the generic module look.
        self.get_style_context().remove_class("module")
        self.command = cfg.get("command", ["lumen-launcher"])
        button = Gtk.Button.new_with_label(cfg.get("label", "Lumen"))
        button.get_style_context().add_class("module")
        button.get_style_context().add_class("launcher")
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_tooltip_text("Applications (Super+Space)")
        button.connect("clicked", lambda _b: util.spawn(self.command))
        self.pack_start(button, False, False, 0)
