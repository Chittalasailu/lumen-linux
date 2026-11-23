# Design decisions

Each entry: the decision, what else was considered, and the trade-off accepted.

## Compositor: labwc, not a custom wlroots compositor

*Alternatives:* write a compositor on wlroots (tinywl-style); sway; Hyprland; Weston.

A custom compositor is the heaviest option and, in six days, would consume the time needed for
the shell components, the distribution build and the documentation, which are what the
assignment weights. labwc is a small wlroots stacking compositor with a conventional desktop
model and an Openbox-style config, so it gets the desktop behaviour for free while the panel and
launcher stay separate clients. sway is tiling, which suits fewer users; Hyprland tracks
upstream too fast for a frozen Debian base; Weston does not implement `wlr-layer-shell`,
which a custom panel and launcher depend on.
*Trade-off:* the compositor is configured, not authored. Understanding is shown in
[ARCHITECTURE.md](ARCHITECTURE.md) and in the panel's direct use of layer-shell.

## Debian 13 (trixie) base

Stable, has labwc, fuzzel, greetd, foot and gtk-layer-shell in the archive, and Python 3.13
so `tomllib` needs no extra package. *Trade-off:* package versions are frozen; newer labwc
features are unavailable, so the config sticks to long-standing keys.

## Components: panel from scratch, launcher customised

The task requires one of each. The panel is the better candidate to write: it is the component
that exercises the most compositor machinery (layer surfaces, exclusive zones, per-output
surfaces, popups). A launcher from scratch would mostly be a list filter. Customising fuzzel
instead demonstrates integration: theming, behaviour, placement and packaging against a real
upstream.

## Panel language: Python + GTK3, not C or Rust

*Alternatives:* C + GTK3/gtk-layer-shell, Rust + gtk-rs, Qt/QML with LayerShellQt, raw
`wl_surface` with Cairo.

Python made the module system, hot reload and tests cheap, and the panel's work (a few label
updates per second) does not need native speed. The cost is a heavier runtime than a C panel and
the `LD_PRELOAD` wrapper. Raw Wayland drawing would show more protocol work but would require
reimplementing text shaping, input, icons and popups, and the result would be a smaller, less
polished panel.

## Single palette feeding generated files

Hand-edited colours in seven config formats drift. One TOML palette and a 100-line template
renderer keep every surface identical and make re-theming a one-line change. CI enforces
freshness. *Trade-off:* a generator step in the workflow, and templates must be written for each
format (GTK CSS, INI, Openbox themerc, SVG).

## Distribution software as .deb packages

Files could have been dropped into `includes.chroot`. Packages give dependency tracking,
clean upgrade/removal, conffile handling, and make the desktop installable on a stock Debian
13. *Trade-off:* a small build script (`packaging/build-debs.sh`) and care over file ownership.

## Config under /etc/lumen/xdg, first in XDG_CONFIG_DIRS

foot and mako ship files in `/etc/xdg`, and greetd owns `/etc/greetd/config.toml`; shipping
the same paths from our package would make dpkg refuse to install. Putting Lumen defaults in
their own directory removes the conflict, keeps our configuration in one place, and preserves
user override precedence. The greetd case uses a service drop-in that passes `--config` to a
file we own.

## greetd + autologin only in the live image

greetd needs no display server or toolkit, runs sessions through PAM/logind, and is enough for
a text greeter on installed systems. Autologin is appended by the image hook, not shipped in the
package, so installing `lumen-desktop` on a real machine never silently logs a user in.

## Software rendering fallback

`WLR_RENDERER_ALLOW_SOFTWARE=1` lets wlroots use pixman when there is no GPU acceleration, which
is the default situation in QEMU. Real GPUs and virgl still use GLES2. *Trade-off:* slower
compositing in a plain VM, acceptable for a demonstration.

## Reproducibility scope

What is controlled: the build container (pinned `debian:trixie`), optional snapshot.debian.org
pinning of every package, `SOURCE_DATE_EPOCH` for our packages, deterministic theme generation
and a CI freshness check. What is not: live-build embeds timestamps and some ordering, so the
ISO is repeatable in *inputs*, not bit-identical. The README states this plainly.

## Left out on purpose

Task list / system tray in the panel (need protocol bindings outside GTK), an installer
(`--debian-installer none`; the ISO is a live system), custom boot splash, Secure Boot signing.
