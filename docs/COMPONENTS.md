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
  wayland.py      second Wayland connection: foreign-toplevel + ext-workspace client (pywayland)
  wlstate.py      pure window/workspace state and protocol decoding
  apps.py         app_id -> desktop entry and icon (Gio)
  protocols/      Python bindings generated from protocols/*.xml (tools/gen-protocols.sh)
  modules/        launcher, workspaces, tasks, clock, cpu, memory, network, volume, battery, power
protocols/        vendored protocol XML: wlr-foreign-toplevel-management-v1, ext-workspace-v1
bin/lumen-panel   wrapper that preloads libgtk-layer-shell
tests/            35 unit tests (sysinfo, config, window/workspace state); no display required
```

### Windows and workspaces: a second Wayland connection

GTK owns the panel's main Wayland connection and only speaks the protocols it needs to draw.
A task list and a workspace indicator need two more, so `wayland.py` opens **its own connection**
to the same compositor (through pywayland) and binds:

| Protocol | Global | Gives the panel | Requests used |
|---|---|---|---|
| wlr-foreign-toplevel-management v3 | `zwlr_foreign_toplevel_manager_v1` | one handle per window: title, app_id, state (activated, minimised, maximised, fullscreen) | `activate(seat)`, `set_minimized`, `unset_minimized`, `close` |
| ext-workspace v1 (wayland-protocols staging) | `ext_workspace_manager_v1` | workspaces: name, coordinates, state (active, urgent, hidden) | `activate` + `commit` |
| core | `wl_seat` | the seat named in `activate` | |

Both protocols batch property events and close each batch with `done`; the client calls its
subscribers once per batch, so a window that changes title and state redraws once. The
connection's file descriptor is watched by the GLib main loop (`GLib.unix_fd_add_full`) and
events are dispatched when it becomes readable, so nothing blocks and no thread is needed. One
connection is shared by every module on every monitor. If pywayland is missing or the
compositor lacks the protocols, the two modules hide themselves and the rest of the panel runs.

pywayland ships only the core protocol, so the XML of both protocols is vendored in
`protocols/` and `tools/gen-protocols.sh` generates the bindings (committed, like the theme).
The script also breaks an import cycle the generator produces for ext-workspace (handle ↔ group).

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
| `workspaces` | ext-workspace | click: switch; scroll: next/previous; the current one is amber |
| `tasks` | wlr-foreign-toplevel | click: focus, or minimise the focused window; middle click: close. Icons from the app's desktop entry; titles ellipsize so many windows share the space |
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
* **Separate logic from GTK.** `sysinfo.py`, `config.py` and `wlstate.py` import nothing
  graphical, which is what lets the 35 unit tests run in CI without a compositor.
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

* No system tray (StatusNotifierItem).
* The task list shows the windows of every output and workspace: neither protocol, as labwc
  0.8 implements them, says which workspace a window is on. Activating a window on another
  workspace switches to it.
* Popover placement relies on GTK's xdg_popup handling for layer surfaces.

---

## lumen-launcher: customised fuzzel

`components/lumen-launcher/`. The launcher itself is **upstream fuzzel**; Lumen's work is the
integration:

| Customisation | Where | Why it matters |
|---|---|---|
| Theme generated from the shared palette | `theme/templates/fuzzel.ini.tpl` | identical colours, radius, border and font as the panel and windows; the desktop's Papirus-Dark icons; fixed 96 dpi; fuzzel's large single-match image turned off (`image-size-ratio=1`), which had drawn one icon over the whole list |
| Toggle behaviour | `bin/lumen-launcher` | one key or button opens *and* closes the launcher (fuzzel alone only opens) |
| Config layering | `bin/lumen-launcher` | `~/.config/lumen/launcher.ini` replaces the distribution theme without editing system files |
| Five modes | `bin/lumen-launcher` | apps (default), `--run` (executables in `PATH`), `--dmenu` (scripting), `--windows`, `--session` |
| Window switcher | `bin/lumen-windows` | `Super+Tab`: open windows with their app icons in the launcher; pick one to focus it. The list comes from the compositor through lumen-panel's foreign-toplevel client, and is shown through fuzzel's dmenu mode in the launcher's own theme |
| Session menu | `bin/lumen-launcher --session` | `Super+Escape`: lock, log out, restart, power off from the keyboard |
| Panel-aware placement | `fuzzel.ini` (`anchor=top-left`, zone 0) | the compositor places it inside the usable area, so it opens under the panel with no hard-coded offsets |
| Panel integration | `lumen-panel` launcher module | the **Lumen** button runs the wrapper |
| Compositor integration | `rc.xml` | `Super+Space`, `Alt+F2`, `Super+Tab`, `Super+Escape`, root-menu entry |
| Packaging | `lumen-launcher` `.deb` | depends on fuzzel and lumen-panel (window list), recommends icon theme and notifications |
| Graceful failure | `bin/lumen-launcher` | if fuzzel is missing, a notification and a non-zero exit instead of nothing |

Fuzzel was chosen because it is itself a layer-shell client, so it behaves correctly with the
panel's exclusive zone, renders natively on Wayland (no XWayland), and is configured by a plain
INI file that a template can generate.
