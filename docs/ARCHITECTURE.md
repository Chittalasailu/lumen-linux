# Architecture

Lumen Linux has four layers. Each is small, replaceable, and documented here from the
bottom up.

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │ 4  Applications     foot · Thunar · Firefox · Mousepad (Wayland-native)  │
 ├──────────────────────────────────────────────────────────────────────────┤
 │ 3  Desktop shell    lumen-panel   lumen-launcher   mako   swaybg         │
 │                     (all are *clients* of the compositor)                │
 ├──────────────────────────────────────────────────────────────────────────┤
 │ 2  Compositor       labwc  ──  wlroots  ──  DRM/KMS · libinput · Mesa    │
 ├──────────────────────────────────────────────────────────────────────────┤
 │ 1  System           systemd · logind · greetd · PipeWire · NetworkManager │
 │                     live-boot / live-config · Debian 13 kernel           │
 └──────────────────────────────────────────────────────────────────────────┘
```

## 1. Boot chain (live ISO)

```
 firmware (BIOS or UEFI)
   └─ syslinux (BIOS) / GRUB-EFI (UEFI)           iso-hybrid image: boots from CD or USB
        └─ Linux kernel + initramfs (live-boot)   finds the ISO, mounts filesystem.squashfs read-only
             └─ overlayfs (tmpfs upper layer)     a writable view; nothing is written to the ISO
                  └─ systemd
                       ├─ live-config.service     creates user "lumen" from the kernel command line
                       └─ greetd.service          After=live-config.service
                            └─ [initial_session]  autologin as "lumen" (PAM + logind session)
                                 └─ lumen-session exec → labwc → autostart
```

Details that matter:

* **Kernel command line** (`iso/auto/config`): `boot=live components username=lumen
  hostname=lumen locales=en_US.UTF-8 keyboard-layouts=us timezone=UTC`. live-config reads these
  at boot, so the same ISO needs no per-machine configuration.
* **Ordering**: the live user does not exist until live-config has run, so a drop-in
  (`greetd.service.d/live.conf`) orders greetd after it. Without it, autologin would race the
  user creation.
* **Installed systems**: `[initial_session]` is added only by the live-image hook. The
  `lumen-desktop` package itself ships a greeter-based configuration, so installing the package
  on a normal Debian machine gives a login screen, not an autologin.
* **Session leader**: `lumen-session` ends with `exec labwc`. The compositor becomes the
  process the login manager waits on, so exiting labwc ends the session cleanly.

## 2. The Wayland stack

In Wayland the *compositor is the display server*. There is no separate server process, no
window manager protocol, and no global coordinates a client can spy on. Clients connect to a
Unix socket (`$XDG_RUNTIME_DIR/wayland-0`) and speak the `wl_display` protocol; everything
else is negotiated through **globals** announced in the registry.

```
          clients                                compositor process (labwc)
 ┌─────────────────────┐                  ┌─────────────────────────────────────┐
 │ foot, Firefox, ...  │──xdg_shell──────▶│ window management, focus, snapping  │
 │ lumen-panel         │──layer_shell────▶│ layer surfaces + usable-area math   │
 │ lumen-launcher      │──layer_shell────▶│                                     │
 │ mako, swaybg        │──layer_shell────▶│          wlroots scene graph        │
 │ grim                │──screencopy─────▶│  (damage tracking, composition)     │
 └─────────────────────┘                  ├─────────────────────────────────────┤
        ▲  wl_surface buffers (shm/dmabuf)│ renderer: GLES2 (GPU) or pixman     │
        │                                 │ backend:  DRM/KMS + libinput        │
        └─────────────────────────────────┴─────────────────────────────────────┘
                                                         │
                                                  kernel DRM / evdev
```

### Why labwc

labwc is a *stacking* compositor built on wlroots with an Openbox-style configuration model. It
gives a conventional desktop (overlapping windows, titlebars, workspaces, root menu) while
leaving the shell, panel, launcher, notifications, wallpaper, to separate clients. That matches
the assignment: the compositor is a reused, configured component; the *shell components are
ours*. wlroots does the heavy protocol work (DRM, input, buffer handling, ~25 protocol
implementations), which is the part not worth rewriting for a six-day project.

### Protocols the desktop depends on

| Protocol | Used by | What it provides |
|---|---|---|
| `xdg_shell` | every normal window | toplevel/popup windows, maximise, fullscreen |
| `wlr-layer-shell-unstable-v1` | panel, launcher, mako, swaybg, slurp | surfaces that are *not* windows: placed on a layer, anchored to edges, optionally reserving space |
| `xdg-decoration` | labwc, GTK/Qt clients | server-side titlebars so all windows look uniform |
| `wlr-screencopy` | grim | screenshots |
| `wl_data_device` / `wlr-data-control` | wl-clipboard | clipboard |
| `xdg-activation`, `idle-notify` | toolkits, lockers | focus requests, idle detection |
| XWayland | legacy X11 apps | rootless X server driven by the compositor |

### Layer shell, the protocol the panel is built on

`wlr-layer-shell` gives a client four things:

1. **Layer**: `background < bottom < top < overlay`. Ordinary windows live between `bottom` and
   `top`. Lumen uses `background` (wallpaper), `top` (panel) and `overlay` (launcher,
   notifications).
2. **Anchor**: a bitmask of edges. Anchoring left+right+top and giving a height makes a
   full-width bar at the top.
3. **Exclusive zone**: pixels of the anchored edge that no other surface should cover. The
   compositor subtracts every layer surface's zone from the output to compute the **usable
   area**, and uses that area for window placement, maximise and snapping. This is why a
   maximised window stops below the panel, and why no panel-aware code exists in labwc's config.
4. **Keyboard interactivity**: `none` for the panel (it never steals focus); the launcher asks
   for keyboard focus while it is open so typing works, and closes when it loses it
   (`exit-on-keyboard-focus-loss`).

A zero exclusive zone means *"place me inside the usable area"*. That is how the launcher
(anchored top-left, zone 0) opens just below the panel without knowing its height, and how
notifications avoid the panel as well. The layering of everything the user sees:

```
 overlay   ─  lumen-launcher (fuzzel), mako notifications
 top       ─  lumen-panel  (exclusive zone = 36 px)
 ····· regular windows (xdg_shell), titlebars drawn by labwc ·····
 bottom    ─  (unused)
 background─  swaybg wallpaper
```

### Multiple outputs

Each `wl_output` becomes a `Gdk.Monitor`. The panel creates one layer surface per monitor and
listens for `monitor-added` / `monitor-removed`, so hot-plugging a display adds or removes a
panel without a restart.

## 3. Desktop shell components

```
        ~/.config/lumen/panel.toml ─┐
        /etc/lumen/panel.toml  ─────┴─▶ config.py ──▶ layout (left / center / right)
                                                         │
 /proc, /sys, wpctl ──▶ sysinfo.py (pure parsers)        ▼
                              └────────▶ modules/*.py ──▶ GTK widgets ──▶ wl_surface
 panel.css (generated) + ~/.config/lumen/panel.css ──▶ CssProvider ───────┘
```

See [COMPONENTS.md](COMPONENTS.md) for the panel internals and for exactly what was customised
in the launcher.

## 4. Theming pipeline

One file drives every surface, so nothing can drift:

```
 theme/palette.toml ──▶ tools/gen-theme.py ──┬─▶ panel.css              (lumen-panel)
        │                     ▲              ├─▶ fuzzel.ini             (lumen-launcher)
        │          theme/templates/*.tpl     ├─▶ labwc themerc          (window decorations, menus, OSD)
        │                                    ├─▶ GTK3 theme "Lumen"     (all GTK apps)
        │                                    ├─▶ foot.ini, mako config  (terminal, notifications)
        │                                    └─▶ wallpaper SVG ──▶ PNG at image build (rsvg-convert)
        └─ CI runs `gen-theme.py --check`: a stale generated file fails the build
```

The generated files are committed so a reader can see the final output, and the generator
refuses to leave them stale.

## 5. Configuration layering

Defaults live under `/etc/lumen/xdg`, which `lumen-session` puts **first** in
`XDG_CONFIG_DIRS`. Lookup order for labwc, foot and GTK is therefore:

```
 ~/.config/<app>/            user (wins)
 /etc/lumen/xdg/<app>/       Lumen distribution defaults
 /etc/xdg/<app>/             stock package defaults
```

This avoids dpkg file conflicts with packages that ship their own `/etc/xdg` files (foot, mako,
greetd), keeps all Lumen configuration in one directory, and lets users override anything per
file.

## 6. Build pipeline

```
 theme/palette.toml ─▶ gen-theme.py ─▶ components/*   (generated files committed)
                                            │
 packaging/build-debs.sh ───────────────────┘  dpkg-deb: lumen-panel, lumen-launcher, lumen-desktop
        │                                                (SOURCE_DATE_EPOCH, root:root, xz)
        ▼
 iso/config/packages.chroot/*.deb ─┐
 iso/config/package-lists/*.list  ─┼─▶ live-build (debootstrap → chroot → hooks → squashfs → ISO)
 iso/config/hooks/live/*.hook     ─┘                    inside Dockerfile.build (debian:trixie)
        ▼
 dist/lumen-linux-1.0.0-amd64.iso  (+ sha256)           CI: .github/workflows/build-iso.yml
```

The distribution's own software is shipped as real Debian packages instead of files copied
into the image. That makes the desktop installable on any Debian 13 system
(`apt install ./lumen-desktop_*.deb`), upgradable, and removable cleanly, and it is how a
distribution would deliver it in practice.
