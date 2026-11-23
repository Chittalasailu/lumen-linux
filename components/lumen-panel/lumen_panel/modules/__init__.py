"""Panel modules.

A module is a ``Gtk.Box`` subclass registered under a name with
``@register("name")``. The layout in panel.toml refers to modules by that
name. Modules own their timers: ``start()`` arms them, ``stop()`` disarms
them, so rebuilding the panel on a monitor hot-plug or config reload leaks
nothing.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Type

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

log = logging.getLogger("lumen-panel")

_REGISTRY: Dict[str, Type["Module"]] = {}


def register(name: str) -> Callable[[Type["Module"]], Type["Module"]]:
    def deco(cls: Type["Module"]) -> Type["Module"]:
        cls.module_name = name
        _REGISTRY[name] = cls
        return cls

    return deco


class Module(Gtk.Box):
    """Base class: a horizontal box with the shared ``module`` CSS class."""

    module_name = ""

    def __init__(self, cfg: dict) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.cfg = cfg
        self._timer: Optional[int] = None
        self.get_style_context().add_class("module")
        self.get_style_context().add_class(self.module_name)

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:  # pragma: no cover - overridden
        """Begin updating. Called once the module is in a realised window."""

    def stop(self) -> None:
        if self._timer is not None:
            GLib.source_remove(self._timer)
            self._timer = None

    # -- helpers ---------------------------------------------------------
    def every(self, seconds: int, fn: Callable[[], None]) -> None:
        """Run *fn* now and then every *seconds* until ``stop()``."""

        def tick() -> bool:
            try:
                fn()
            except Exception:  # a broken module must not take the panel down
                log.exception("module %s failed", self.module_name)
            return True

        tick()
        self._timer = GLib.timeout_add_seconds(max(1, int(seconds)), tick)

    def set_state(self, *states: str) -> None:
        """Replace the state classes (warn/critical/charging/muted)."""
        ctx = self.get_style_context()
        for s in ("warn", "critical", "charging", "muted"):
            ctx.remove_class(s)
        for s in states:
            ctx.add_class(s)


def create(name: str, cfg: dict) -> Optional[Module]:
    cls = _REGISTRY.get(name)
    if cls is None:
        log.warning("unknown module '%s' in layout; skipping", name)
        return None
    return cls(cfg)


def available() -> list[str]:
    return sorted(_REGISTRY)


def load_builtin_modules() -> None:
    """Import every built-in module so that it registers itself."""
    from . import (  # noqa: F401
        battery,
        clock,
        cpu,
        launcher,
        memory,
        network,
        power,
        volume,
    )
