# What is original, customised, and reused

## Written for this project

| Item | Path |
|---|---|
| **lumen-panel**, the from-scratch component (app, config, modules, CSS loader, tests) | `components/lumen-panel/` |
| Theme generator and every template | `tools/gen-theme.py`, `theme/` |
| Palette "Lumen Dusk", wallpaper design | `theme/palette.toml`, `theme/templates/wallpaper.svg.tpl` |
| Launcher wrapper (toggle, layering, modes) | `components/lumen-launcher/bin/lumen-launcher` |
| Session script, screenshot helper | `components/lumen-desktop/usr/bin/` |
| Package build (three `.deb`s, maintainer scripts) | `packaging/` |
| live-build configuration, hooks, package list | `iso/` |
| Build entry points, container, CI, QEMU runners | `build.sh`, `Dockerfile.build`, `Makefile`, `run-qemu.*`, `.github/` |
| Documentation | `README.md`, `docs/` |

## Customised upstream components

| Upstream | What was customised |
|---|---|
| [fuzzel](https://codeberg.org/dnkl/fuzzel) (GPL-3.0), the application launcher | palette-generated theme, placement, toggle wrapper, config layering, modes, panel and keybinding integration, packaging |
| [labwc](https://github.com/labwc/labwc) (GPL-2.0), the compositor | `rc.xml` keybindings and behaviour, `Lumen` window theme, root menu, environment, autostart |
| [foot](https://codeberg.org/dnkl/foot) (MIT), terminal | generated colour scheme and font |
| [mako](https://github.com/emersion/mako) (MIT), notifications | generated theme |
| GTK 3 (LGPL-2.1+) | `Lumen` theme layered on Adwaita dark, settings |
| greetd (GPL-3.0) | login configuration, live-image autologin |

## Reused without modification

Debian 13 base system and kernel, live-build, live-boot, live-config, wlroots, systemd,
PipeWire/WirePlumber, NetworkManager, Mesa, XWayland, swaybg, swaylock, grim, slurp,
wl-clipboard, Thunar, Firefox ESR, Mousepad, GTK 3, gtk-layer-shell (MIT), PyGObject, the
Inter and JetBrains Mono fonts, Papirus and Adwaita icon themes.

All third-party software is installed from the Debian archive and retains its own license; only
the original work listed in the first table is covered by this repository's MIT license.
