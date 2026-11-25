"""A second Wayland connection for the protocols GTK does not expose.

GTK owns the panel's main connection and only speaks the protocols it needs
for drawing. The task list and workspace indicator need two more, so this
module opens its own connection to the same compositor and binds:

* ``zwlr_foreign_toplevel_manager_v1`` (wlr-foreign-toplevel-management): one
  handle per application window with its title, app_id and state; requests to
  activate, minimise and close it. This is how taskbars work on wlroots
  compositors.
* ``ext_workspace_manager_v1`` (ext-workspace, wayland-protocols staging): the
  virtual desktops and which one is active; requests to switch.
* ``wl_seat``: activation must name the seat the request comes from.

Events arrive in batches closed by a ``done`` event; subscribers are called
once per batch, so the UI rebuilds once per change, not once per property.

The client works on its own (``roundtrip()`` until the state is complete, as
the ``lumen-windows`` switcher does) or inside the panel's GLib main loop
(``attach()``): the connection's file descriptor is watched and events are
dispatched when it becomes readable.
"""
from __future__ import annotations

import itertools
import logging
from typing import Callable, Optional

from .wlstate import DesktopState, Toplevel, Workspace, decode_uint_array, toplevel_states

log = logging.getLogger("lumen-panel")

TOPLEVEL_MANAGER = "zwlr_foreign_toplevel_manager_v1"
WORKSPACE_MANAGER = "ext_workspace_manager_v1"


class Unavailable(RuntimeError):
    """No Wayland display, no pywayland, or the compositor lacks the protocols."""


class Client:
    def __init__(self) -> None:
        try:
            from pywayland.client import Display
            from pywayland.protocol.wayland import WlSeat

            from .protocols.ext_workspace_v1 import ExtWorkspaceManagerV1
            from .protocols.wlr_foreign_toplevel_management_unstable_v1 import (
                ZwlrForeignToplevelManagerV1,
            )
        except ImportError as exc:
            raise Unavailable(f"pywayland is not installed ({exc})") from exc

        self.state = DesktopState()
        self._subscribers: dict[int, Callable[[], None]] = {}
        self._sub_ids = itertools.count(1)
        self._keys = itertools.count(1)
        self._toplevel_handles: dict[int, object] = {}
        self._workspace_handles: dict[int, object] = {}
        self._seat = None
        self._toplevel_manager = None
        self._workspace_manager = None
        self._watch = 0

        self.display = Display()
        try:
            self.display.connect()
        except Exception as exc:  # pywayland raises ValueError; be generous
            raise Unavailable(f"cannot connect to the Wayland display ({exc})") from exc

        globals_: dict[str, tuple[int, int]] = {}

        # pywayland hands a handler's return value back to libwayland as a C int,
        # so handlers must return None (a lambda returning a value breaks it).
        def announce(_registry, name: int, iface: str, version: int) -> None:
            globals_.setdefault(iface, (name, version))

        registry = self.display.get_registry()
        registry.dispatcher["global"] = announce
        self.display.roundtrip()

        if "wl_seat" in globals_:
            name, _ver = globals_["wl_seat"]
            self._seat = registry.bind(name, WlSeat, 1)
        if TOPLEVEL_MANAGER in globals_:
            name, ver = globals_[TOPLEVEL_MANAGER]
            self._toplevel_manager = registry.bind(name, ZwlrForeignToplevelManagerV1, min(ver, 3))
            self._toplevel_manager.dispatcher["toplevel"] = self._on_toplevel
        if WORKSPACE_MANAGER in globals_:
            name, _ver = globals_[WORKSPACE_MANAGER]
            self._workspace_manager = registry.bind(name, ExtWorkspaceManagerV1, 1)
            self._workspace_manager.dispatcher["workspace"] = self._on_workspace
            self._workspace_manager.dispatcher["done"] = lambda _m: self._notify()
        if self._toplevel_manager is None and self._workspace_manager is None:
            self.display.disconnect()
            raise Unavailable(f"compositor offers neither {TOPLEVEL_MANAGER} nor {WORKSPACE_MANAGER}")
        # The first roundtrip announces the objects, the second their properties.
        self.display.roundtrip()
        self.display.roundtrip()

    @property
    def has_toplevels(self) -> bool:
        return self._toplevel_manager is not None

    @property
    def has_workspaces(self) -> bool:
        return self._workspace_manager is not None

    # -- subscribers ---------------------------------------------------------
    def subscribe(self, callback: Callable[[], None]) -> int:
        sub = next(self._sub_ids)
        self._subscribers[sub] = callback
        return sub

    def unsubscribe(self, sub: int) -> None:
        self._subscribers.pop(sub, None)

    def _notify(self) -> None:
        for callback in list(self._subscribers.values()):
            try:
                callback()
            except Exception:  # one broken view must not stop the others
                log.exception("desktop state subscriber failed")

    # -- toplevels -------------------------------------------------------------
    def _on_toplevel(self, _manager, handle) -> None:
        key = next(self._keys)
        top = Toplevel(key)
        self._toplevel_handles[key] = handle

        def title(_h, text: str) -> None:
            top.title = text

        def app_id(_h, text: str) -> None:
            top.app_id = text

        def state(_h, data) -> None:
            top.states = toplevel_states(data)

        def done(_h) -> None:
            self.state.toplevels[key] = top
            self._notify()

        def closed(_h) -> None:
            self.state.toplevels.pop(key, None)
            self._toplevel_handles.pop(key, None)
            handle.destroy()
            self._notify()

        for event, fn in (("title", title), ("app_id", app_id), ("state", state), ("done", done), ("closed", closed)):
            handle.dispatcher[event] = fn

    def activate(self, key: int) -> None:
        handle = self._toplevel_handles.get(key)
        if handle is None or self._seat is None:
            return
        top = self.state.toplevels.get(key)
        if top is not None and top.minimized:
            handle.unset_minimized()
        handle.activate(self._seat)
        self.display.flush()

    def minimize(self, key: int) -> None:
        handle = self._toplevel_handles.get(key)
        if handle is not None:
            handle.set_minimized()
            self.display.flush()

    def close(self, key: int) -> None:
        handle = self._toplevel_handles.get(key)
        if handle is not None:
            handle.close()
            self.display.flush()

    # -- workspaces ------------------------------------------------------------
    def _on_workspace(self, _manager, handle) -> None:
        key = next(self._keys)
        ws = Workspace(key)
        self._workspace_handles[key] = handle
        self.state.workspaces[key] = ws

        def name(_h, text: str) -> None:
            ws.name = text

        def coordinates(_h, data) -> None:
            ws.coordinates = tuple(decode_uint_array(data))

        def state(_h, bits: int) -> None:
            ws.state = bits

        def removed(_h) -> None:
            self.state.workspaces.pop(key, None)
            self._workspace_handles.pop(key, None)
            handle.destroy()

        for event, fn in (("name", name), ("coordinates", coordinates), ("state", state), ("removed", removed)):
            handle.dispatcher[event] = fn

    def switch_workspace(self, key: int) -> None:
        handle = self._workspace_handles.get(key)
        if handle is None or self._workspace_manager is None:
            return
        handle.activate()
        self._workspace_manager.commit()  # ext-workspace applies requests on commit
        self.display.flush()

    # -- event loop --------------------------------------------------------------
    def roundtrip(self) -> None:
        self.display.roundtrip()

    def attach(self) -> None:
        """Dispatch this connection's events from the GLib main loop."""
        from gi.repository import GLib

        def readable(_fd, condition) -> bool:
            if condition & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                log.error("lost the Wayland connection used for windows and workspaces")
                self._watch = 0
                return GLib.SOURCE_REMOVE
            # The fd is readable, so this reads and dispatches without blocking.
            self.display.dispatch(block=True)
            self.display.flush()
            return GLib.SOURCE_CONTINUE

        self._watch = GLib.unix_fd_add_full(
            GLib.PRIORITY_DEFAULT,
            self.display.get_fd(),
            GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
            readable,
        )


_shared: Optional[Client] = None
_failed = False


def shared() -> Optional[Client]:
    """The panel's single connection, created on first use; None if unavailable."""
    global _shared, _failed
    if _shared is None and not _failed:
        try:
            _shared = Client()
            _shared.attach()
        except Unavailable as exc:
            log.warning("window list and workspaces disabled: %s", exc)
            _failed = True
    return _shared
