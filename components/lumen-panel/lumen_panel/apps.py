"""Map a Wayland app_id to its installed application (desktop file).

Shared by the task list and the lumen-windows switcher. Uses Gio only, so it
works without GTK.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from .wlstate import desktop_ids


def _load(desktop_id: str) -> Optional[Gio.DesktopAppInfo]:
    try:
        return Gio.DesktopAppInfo.new(desktop_id)
    except TypeError:  # PyGObject raises when the constructor returns NULL
        return None


@lru_cache(maxsize=128)
def app_info(app_id: str) -> Optional[Gio.DesktopAppInfo]:
    """The desktop entry for *app_id*: exact ids first, then GLib's desktop search.

    The search covers clients whose app_id is not their desktop id, such as
    Mousepad (app_id ``mousepad``, desktop file ``org.xfce.mousepad.desktop``).
    """
    for candidate in desktop_ids(app_id):
        info = _load(candidate + ".desktop")
        if info is not None:
            return info
    if app_id:
        for group in Gio.DesktopAppInfo.search(app_id):
            for desktop_id in group:
                info = _load(desktop_id)
                if info is not None:
                    return info
    return None


def icon_name(app_id: str, fallback: str = "application-x-executable") -> str:
    info = app_info(app_id)
    icon = info.get_string("Icon") if info is not None else None
    return icon or app_id or fallback
