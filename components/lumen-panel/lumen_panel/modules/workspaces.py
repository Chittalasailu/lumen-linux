"""Workspace indicator (ext-workspace-v1): click to switch, scroll to step."""
from __future__ import annotations

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from .. import wayland
from ..wlstate import Workspace, ordered_workspaces
from . import Module, register


@register("workspaces")
class Workspaces(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.get_style_context().remove_class("module")
        self.labels = cfg.get("labels", "index")  # "index" (1 2 3 4) or "name"
        self.client = None
        self._sub = 0
        self._shown: list[tuple[int, str, int]] = []
        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("scroll-event", self._on_scroll)

    def start(self) -> None:
        self.client = wayland.shared()
        if self.client is None or not self.client.has_workspaces:
            self.hide()
            return
        self._sub = self.client.subscribe(self.refresh)
        self.refresh()

    def stop(self) -> None:
        super().stop()
        if self.client is not None and self._sub:
            self.client.unsubscribe(self._sub)
            self._sub = 0

    def _text(self, index: int, ws: Workspace) -> str:
        return ws.name if self.labels == "name" and ws.name else str(index)

    def refresh(self) -> None:
        order = ordered_workspaces(self.client.state.workspaces.values())
        shown = [(ws.key, self._text(i, ws), ws.state) for i, ws in enumerate(order, 1)]
        if shown == self._shown:  # most updates are window changes, not workspace ones
            return
        self._shown = shown
        for child in self.get_children():
            child.destroy()
        for i, ws in enumerate(order, 1):
            button = Gtk.Button.new_with_label(self._text(i, ws))
            button.set_relief(Gtk.ReliefStyle.NONE)
            ctx = button.get_style_context()
            ctx.add_class("workspace")
            if ws.active:
                ctx.add_class("active")
            if ws.urgent:
                ctx.add_class("urgent")
            button.set_tooltip_text(ws.name or f"Workspace {i}")
            button.connect("clicked", lambda _b, key=ws.key: self.client.switch_workspace(key))
            self.pack_start(button, False, False, 0)
        self.show_all()

    def _on_scroll(self, _widget, event: Gdk.EventScroll) -> bool:
        if self.client is None:
            return False
        step = 0
        if event.direction == Gdk.ScrollDirection.UP:
            step = -1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            step = 1
        elif event.direction == Gdk.ScrollDirection.SMOOTH and event.delta_y:
            step = 1 if event.delta_y > 0 else -1
        target = self.client.state.neighbour_workspace(step) if step else None
        if target is not None:
            self.client.switch_workspace(target.key)
        return True
