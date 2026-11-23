# Components

## lumen-panel: built from scratch

`components/lumen-panel/`: about 1,100 lines of Python, no panel framework underneath. It is a
GTK3 application whose only unusual part is that its window is a **layer-shell surface** instead
of an `xdg_toplevel`.

### Why this stack

| Choice | Reason |
|---|---|
| GTK3 + `gtk-layer-shell` | Layer-shell surfaces need protocol-level setup; the library does it while GTK still does text, icons, popovers and theming. GTK3 is what the rest of the desktop (Thunar, theme) already uses. |
| Python 3.13 | Fast to iterate on, easy for a user to read and extend, `tomllib` is in the standard library. A panel updates a few labels per second; interpreter speed is irrelevant. |
| TOML + CSS | Layout and behaviour in a declarative file, appearance in the CSS dialect GTK already provides. Both hot-reload. |

### Structure

```
lumen_panel/
  __main__.py     CLI entry (--version, --list-modules, -v)
  app.py          Gtk.Application; one PanelWindow per monitor; reload logic
  config.py       defaults ◀ /etc/lumen/panel.toml ◀ ~/.config/lumen/panel.toml, validation
  theme.py        ThemeLoader: shipped CSS (APPLICATION priority) + user CSS (USER priority)
  sysinfo.py      pure parsers: /proc/stat, /proc/meminfo, sysfs battery & network, wpctl output
  util.py         non-blocking subprocess helpers on Gio.Subprocess
  modules/        launcher, clock, cpu, memory, network, volume, battery, power
bin/lumen-panel   wrapper that preloads libgtk-layer-shell
tests/            22 unit tests (sysinfo, config); no display required
```

### How it talks to the compositor

`PanelWindow._init_layer_shell` is the whole protocol conversation:

```python
GtkLayerShell.init_for_window(self)                 # wl_surface → zwlr_layer_surface_v1
GtkLayerShell.set_namespace(self, "lumen-panel")    # compositors/rules can identify it
GtkLayerShell.set_layer(self, Layer.TOP)            # above windows, below overlays
GtkLayerShell.set_monitor(self, monitor)            # bind to one wl_output
GtkLayerShell.set_anchor(self, TOP|LEFT|RIGHT, True)# full-width bar
GtkLayerShell.auto_exclusive_zone_enable(self)      # reserve our height: windows stop below us
```

* One layer surface per `wl_output`, created and destroyed on `monitor-added` /
  `monitor-removed`.
* The panel never takes keyboard focus; popovers (calendar, power menu) become `xdg_popup`
  surfaces parented to the layer surface.
* **Preload wrapper**: gtk-layer-shell must be loaded *before* libwayland-client. GObject
  introspection loads libraries lazily, which breaks that order and would silently turn the
  panel into an ordinary window. `bin/lumen-panel` sets `LD_PRELOAD` to the library, the
  workaround upstream documents for language bindings.

### Module system

A module is a `Gtk.Box` registered with `@register("name")`. `panel.toml` lists names per zone
(`left`, `center`, `right`); unknown names are logged and skipped, so a typo cannot stop the
panel. Modules own their timers (`start()` / `stop()`), which is what makes monitor hot-plug and
config reload leak-free: a reload tears windows down and rebuilds them.

| Module | Source of data | Interaction |
|---|---|---|
| `launcher` | n/a | click: run `lumen-launcher` |
| `clock` | `time.localtime()` | click: calendar popover; `format` is strftime |
| `cpu` | `/proc/stat` deltas | warn/critical colour thresholds |
| `memory` | `/proc/meminfo` (total − available) | warn/critical thresholds |
| `network` | `/sys/class/net/*/operstate`, `wireless/` | click: open connection editor |
| `volume` | `wpctl get-volume` (PipeWire/WirePlumber) | scroll: ±5 % (capped at 100 %), click: mute, right-click: mixer |
| `battery` | `/sys/class/power_supply` | hides itself when there is no battery |
| `power` | n/a | popover: lock, log out, restart, power off |

Design rules followed throughout:

* **Never block the main loop.** All commands go through `Gio.Subprocess` with async completion.
* **Isolate failures.** A timer callback that raises is logged and the next tick still runs.
* **Separate logic from GTK.** `sysinfo.py` and `config.py` import nothing graphical, which is
  what lets the 22 unit tests run in CI without a compositor.
* **Degrade quietly.** Missing `wpctl`, no battery, no wireless: the module shows `n/a` or hides.

### Reload

* `SIGUSR1` (`pkill -USR1 -f lumen_panel`) reloads config and CSS.
* `Gio.FileMonitor` watches `~/.config/lumen/panel.{toml,css}` and reloads 300 ms after the
  last change (debounced, since editors write several events).
* Launching a second instance acts as a reload (`Gtk.Application` is single-instance).

### Extending

```python
# lumen_panel/modules/uptime.py
from . import Module, register
@register("uptime")
class Uptime(Module):
    ...  # build widgets in __init__, call self.every(seconds, fn) in start()
```

Add the file to `load_builtin_modules()` and name it in `layout.right`.

### Known limitations

* No task list / window switcher. That needs the `wlr-foreign-toplevel-management` protocol,
  which GTK does not expose; it would require a Wayland client binding (for example
  `pywayland`). labwc's own Alt+Tab switcher covers window switching meanwhile.
* No system tray (StatusNotifierItem) and no workspace indicator.
* Popover placement relies on GTK's xdg_popup handling for layer surfaces.

---

## lumen-launcher: customised fuzzel

`components/lumen-launcher/`. The launcher itself is **upstream fuzzel**; Lumen's work is the
integration:

| Customisation | Where | Why it matters |
|---|---|---|
| Theme generated from the shared palette | `theme/templates/fuzzel.ini.tpl` | identical colours, radius, border and font as the panel and windows |
| Toggle behaviour | `bin/lumen-launcher` | one key or button opens *and* closes the launcher (fuzzel alone only opens) |
| Config layering | `bin/lumen-launcher` | `~/.config/lumen/launcher.ini` replaces the distribution theme without editing system files |
| Three modes | `bin/lumen-launcher` | apps (default), `--run` (executables in `PATH`), `--dmenu` (scripting) |
| Panel-aware placement | `fuzzel.ini` (`anchor=top-left`, zone 0) | the compositor places it inside the usable area, so it opens under the panel with no hard-coded offsets |
| Panel integration | `lumen-panel` launcher module | the **Lumen** button runs the wrapper |
| Compositor integration | `rc.xml` | `Super+Space`, `Alt+F2`, root-menu entry |
| Packaging | `lumen-launcher` `.deb` | depends on fuzzel, recommends icon theme and notifications |
| Graceful failure | `bin/lumen-launcher` | if fuzzel is missing, a notification and a non-zero exit instead of nothing |

Fuzzel was chosen because it is itself a layer-shell client, so it behaves correctly with the
panel's exclusive zone, renders natively on Wayland (no XWayland), and is configured by a plain
INI file that a template can generate.
