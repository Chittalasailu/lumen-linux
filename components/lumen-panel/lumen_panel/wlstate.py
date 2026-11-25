"""Window and workspace state as the compositor reports it.

Pure data and decoding, no GTK and no Wayland connection, so it is unit-tested
like ``sysinfo``. ``wayland.py`` fills these objects from protocol events.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Iterable, Union

# zwlr_foreign_toplevel_handle_v1.state values
TOPLEVEL_STATES = {0: "maximized", 1: "minimized", 2: "activated", 3: "fullscreen"}
# ext_workspace_handle_v1.state bits
WORKSPACE_ACTIVE, WORKSPACE_URGENT, WORKSPACE_HIDDEN = 1, 2, 4


def decode_uint_array(data: Union[bytes, Iterable[int]]) -> list[int]:
    """A wl_array of uint32, as pywayland hands it over (raw bytes) or as ints."""
    if isinstance(data, (bytes, bytearray, memoryview)):
        raw = bytes(data)
        return list(struct.unpack(f"={len(raw) // 4}I", raw[: len(raw) // 4 * 4]))
    return [int(v) for v in data]


def toplevel_states(data) -> frozenset[str]:
    return frozenset(TOPLEVEL_STATES[v] for v in decode_uint_array(data) if v in TOPLEVEL_STATES)


@dataclass
class Toplevel:
    """One application window (a zwlr_foreign_toplevel_handle_v1)."""

    key: int  # stable per connection, in creation order
    title: str = ""
    app_id: str = ""
    states: frozenset[str] = frozenset()

    @property
    def active(self) -> bool:
        return "activated" in self.states

    @property
    def minimized(self) -> bool:
        return "minimized" in self.states

    def label(self, max_chars: int) -> str:
        text = self.title or self.app_id or "Window"
        return text if len(text) <= max_chars else text[: max(1, max_chars - 1)].rstrip() + "…"

    def click_action(self) -> str:
        """What a left click on its task button should do."""
        if self.active and not self.minimized:
            return "minimize"
        return "activate"


def desktop_ids(app_id: str) -> list[str]:
    """Desktop-file ids to try for an app_id, most specific first.

    Wayland app_ids are usually the desktop id (``org.xfce.mousepad``) but some
    clients send a short name (``foot``) or a different case.
    """
    if not app_id:
        return []
    out = [app_id, app_id.lower()]
    tail = app_id.rsplit(".", 1)[-1]
    out += [tail, tail.lower()]
    seen: list[str] = []
    for candidate in out:
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen


@dataclass
class Workspace:
    """One virtual desktop (an ext_workspace_handle_v1)."""

    key: int
    name: str = ""
    coordinates: tuple[int, ...] = ()
    state: int = 0

    @property
    def active(self) -> bool:
        return bool(self.state & WORKSPACE_ACTIVE)

    @property
    def urgent(self) -> bool:
        return bool(self.state & WORKSPACE_URGENT)

    @property
    def hidden(self) -> bool:
        return bool(self.state & WORKSPACE_HIDDEN)


def ordered_workspaces(workspaces: Iterable[Workspace]) -> list[Workspace]:
    """Visible workspaces in the compositor's order: coordinates if it gives them, else creation."""
    visible = [w for w in workspaces if not w.hidden]
    return sorted(visible, key=lambda w: (w.coordinates or (w.key,), w.key))


@dataclass
class DesktopState:
    """Everything the task list and workspace indicator draw from."""

    toplevels: dict[int, Toplevel] = field(default_factory=dict)
    workspaces: dict[int, Workspace] = field(default_factory=dict)

    def windows(self) -> list[Toplevel]:
        return [self.toplevels[k] for k in sorted(self.toplevels)]

    def active_workspace(self) -> Workspace | None:
        return next((w for w in ordered_workspaces(self.workspaces.values()) if w.active), None)

    def neighbour_workspace(self, step: int) -> Workspace | None:
        """The workspace *step* places from the active one, wrapping around."""
        order = ordered_workspaces(self.workspaces.values())
        current = self.active_workspace()
        if not order or current is None:
            return None
        return order[(order.index(current) + step) % len(order)]
