"""The panel application: one layer-shell window per monitor.

How it maps onto the Wayland protocol stack
-------------------------------------------
* ``zwlr_layer_shell_v1`` (via gtk-layer-shell) lets a client declare *what a
  surface is* instead of letting the compositor treat it as a normal window:
  a ``namespace``, a ``layer`` (background < bottom < top < overlay), edge
  ``anchors`` and an ``exclusive zone``.
* The exclusive zone is how the panel reserves screen space. The compositor
  shrinks the "usable area" it hands to ordinary windows (maximise, snap,
  placement), which is why a maximised window stops below the panel.
* One surface per ``wl_output``: ``Gdk.Monitor`` objects are the GTK view of
  ``wl_output`` globals, and ``monitor-added/removed`` mirror registry
  global events (hot-plug).
"""
from __future__ import annotations

import logging
import signal
from typing import Dict

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell  # noqa: E402

from . import __version__, config, modules, theme

log = logging.getLogger("lumen-panel")

LAYERS = {
    "top": GtkLayerShell.Layer.TOP,
    "overlay": GtkLayerShell.Layer.OVERLAY,
}


class PanelWindow(Gtk.Window):
    def __init__(self, cfg: dict, monitor: Gdk.Monitor) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.cfg = cfg
        self.modules: list[modules.Module] = []
        self.set_title("lumen-panel")
        self.set_decorated(False)
        self.set_resizable(False)
        ctx = self.get_style_context()
        ctx.add_class("lumen-panel")
        ctx.add_class(cfg["panel"]["position"])

        self._init_layer_shell(monitor)
        self._build()

    def _init_layer_shell(self, monitor: Gdk.Monitor) -> None:
        panel = self.cfg["panel"]
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, "lumen-panel")  # compositors can match on this
        GtkLayerShell.set_layer(self, LAYERS[panel["layer"]])
        GtkLayerShell.set_monitor(self, monitor)
        edge = GtkLayerShell.Edge.TOP if panel["position"] == "top" else GtkLayerShell.Edge.BOTTOM
        for e in (edge, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, e, True)
        # Reserve exactly our own height on the anchored edge.
        GtkLayerShell.auto_exclusive_zone_enable(self)
        self.set_size_request(-1, panel["height"])

    def _build(self) -> None:
        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        zones = {}
        for zone in ("left", "center", "right"):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            box.get_style_context().add_class("section")
            zones[zone] = box
            for name in self.cfg["layout"][zone]:
                mod = modules.create(name, self.cfg.get(name, {}))
                if mod is not None:
                    self.modules.append(mod)
                    box.pack_start(mod, False, False, 0)
        root.pack_start(zones["left"], False, False, 0)
        root.set_center_widget(zones["center"])
        root.pack_end(zones["right"], False, False, 0)
        self.add(root)

    def start(self) -> None:
        self.show_all()
        for mod in self.modules:
            mod.start()

    def teardown(self) -> None:
        for mod in self.modules:
            mod.stop()
        self.destroy()


class PanelApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id="org.lumen.Panel", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.theme = theme.ThemeLoader()
        self.windows: Dict[Gdk.Monitor, PanelWindow] = {}
        self.cfg: dict = {}
        self._reload_id = 0
        self._monitors: list[Gio.FileMonitor] = []

    # -- Gtk.Application ---------------------------------------------------
    def do_activate(self) -> None:
        if self.windows:  # second launch: behave like a reload
            self.reload()
            return
        modules.load_builtin_modules()
        self.cfg = config.load()
        self.theme.load()

        display = Gdk.Display.get_default()
        display.connect("monitor-added", lambda _d, m: self._add_monitor(m))
        display.connect("monitor-removed", lambda _d, m: self._remove_monitor(m))
        for i in range(display.get_n_monitors()):
            self._add_monitor(display.get_monitor(i))

        # SIGUSR1 = reload config and CSS. Handy from `pkill -USR1 -f lumen_panel`.
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self._on_sigusr1)
        self._watch_user_files()
        self.hold()  # a panel has no "last window closed" exit condition
        log.info("lumen-panel %s running on %d monitor(s)", __version__, len(self.windows))

    # -- monitors ------------------------------------------------------------
    def _add_monitor(self, monitor: Gdk.Monitor) -> None:
        if monitor in self.windows:
            return
        win = PanelWindow(self.cfg, monitor)
        self.windows[monitor] = win
        self.add_window(win)
        win.start()

    def _remove_monitor(self, monitor: Gdk.Monitor) -> None:
        win = self.windows.pop(monitor, None)
        if win is not None:
            win.teardown()

    # -- reload --------------------------------------------------------------
    def reload(self) -> None:
        log.info("reloading configuration and stylesheet")
        self.cfg = config.load()
        self.theme.load()
        monitors = list(self.windows)
        for m in monitors:
            self._remove_monitor(m)
        for m in monitors:
            self._add_monitor(m)

    def _on_sigusr1(self) -> bool:
        self.reload()
        return GLib.SOURCE_CONTINUE

    def _watch_user_files(self) -> None:
        """Reload shortly after the user's panel.toml / panel.css change."""
        for path in (config.user_config_path(), theme.user_css_path()):
            gfile = Gio.File.new_for_path(path)
            try:
                mon = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            except GLib.Error:
                continue
            mon.connect("changed", self._on_file_changed)
            self._monitors.append(mon)  # keep a reference or it is collected

    def _on_file_changed(self, *_args) -> None:
        if self._reload_id:  # debounce editors that write several events
            GLib.source_remove(self._reload_id)

        def fire() -> bool:
            self._reload_id = 0
            self.reload()
            return GLib.SOURCE_REMOVE

        self._reload_id = GLib.timeout_add(300, fire)
