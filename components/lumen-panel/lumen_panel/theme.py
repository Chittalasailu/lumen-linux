"""CSS loading: the shipped stylesheet first, then the user's override on top."""
from __future__ import annotations

import logging
import os
from typing import Optional

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402
from gi.repository import GLib  # noqa: E402

log = logging.getLogger("lumen-panel")

SYSTEM_CSS = "/usr/share/lumen-panel/panel.css"


def user_css_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "lumen", "panel.css")


class ThemeLoader:
    """Owns the two CssProviders so a reload swaps them without stacking."""

    def __init__(self, system_css: Optional[str] = None) -> None:
        self.system_css = system_css or os.environ.get("LUMEN_PANEL_CSS", SYSTEM_CSS)
        self._providers: list[Gtk.CssProvider] = []

    def load(self) -> None:
        screen = Gdk.Screen.get_default()
        for provider in self._providers:
            Gtk.StyleContext.remove_provider_for_screen(screen, provider)
        self._providers.clear()

        # APPLICATION < USER so the user's file always wins.
        for path, priority in (
            (self.system_css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION),
            (user_css_path(), Gtk.STYLE_PROVIDER_PRIORITY_USER),
        ):
            if not os.path.exists(path):
                continue
            provider = Gtk.CssProvider()
            try:
                provider.load_from_path(path)
            except GLib.Error as exc:
                log.error("CSS error in %s: %s", path, exc.message)
                continue
            Gtk.StyleContext.add_provider_for_screen(screen, provider, priority)
            self._providers.append(provider)
