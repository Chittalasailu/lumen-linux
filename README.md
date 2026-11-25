# Lumen Linux

A Debian 13 ("trixie") based live distribution with a Wayland desktop built on the
[labwc](https://labwc.github.io/) compositor (wlroots). It ships two desktop components:

| Component | Role | Origin |
|---|---|---|
| **lumen-panel** | Desktop panel / status bar: workspaces, task list, system status | **Written from scratch** (Python, GTK3, wlr-layer-shell, plus its own ext-workspace and wlr-foreign-toplevel client) |
| **lumen-launcher** | Application launcher, window switcher, session menu | **Customised and integrated** [fuzzel](https://codeberg.org/dnkl/fuzzel) |

Everything visual (compositor decorations, panel, launcher, GTK theme, terminal,
notifications, wallpaper) is generated from one palette file, so the desktop has a single
consistent identity: **Lumen Dusk**, deep navy surfaces with an amber accent.

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): boot chain, Wayland stack, how the pieces fit
- [docs/COMPONENTS.md](docs/COMPONENTS.md): the panel's internals and what was customised in the launcher
- [docs/DESIGN-DECISIONS.md](docs/DESIGN-DECISIONS.md): why each choice was made
- [docs/THIRD-PARTY.md](docs/THIRD-PARTY.md): what is original and what is reused
- [docs/TESTING.md](docs/TESTING.md): verification checklist and demo script

## Status

Every push builds the ISO in CI and then **boots it headless in QEMU under both BIOS and UEFI**
([tests/boot_test.py](tests/boot_test.py)). The test waits for automatic login, then drives the
desktop through QEMU's control socket, saves a screenshot at each step and fails if any check
fails. Panel modules are found on the screenshot rather than by fixed coordinates. All 17 checks
pass on both firmware types:

| Check | What it proves |
|---|---|
| Boot menu carries the Lumen branding | palette splash, isolinux colours and GRUB theme in the image |
| Desktop reached after automatic login, at 1360x768 | live user, greetd autologin, labwc session, virtual-GPU mode |
| Clock opens the calendar; power icon opens the session menu | panel popovers on a layer-shell surface |
| Workspace indicator follows `Super+2` | panel's ext-workspace client |
| A new window appears in the task list | panel's wlr-foreign-toplevel client |
| Scrolling over the volume module changes it | panel → WirePlumber |
| `Super+Space` opens the launcher, with no oversized icon | fuzzel integration and theme |
| `Super+Escape` opens the session menu | launcher session mode |
| `Super+Tab` opens the window switcher, with no oversized icon | launcher window switcher over foreign-toplevel |
| A notification appears top right with the amber border | mako, themed from the palette |
| Thunar shows the Lumen selection colour and no Adwaita blue | recoloured GTK theme + GSettings defaults |
| Logging out shows the Lumen login screen; logging in again works | greetd + gtkgreet in cage |

The desktop appears 85 s after the boot menu in software emulation on Apple Silicon (no KVM).
Boot-testing found and fixed real bugs, all in the git history, for example: the live user was
never created, a console login competed with greetd for the first VT, the panel's popovers opened
off-screen, GTK apps ignored the theme, and Debian's pywayland lacks a dependency on the cffi
runtime.

Screenshots, all captured from the built ISO by that test:
[desktop with task list and Lumen GTK theme](docs/screenshots/desktop.png),
[calendar](docs/screenshots/panel-calendar.png), [panel session menu](docs/screenshots/panel-power-menu.png),
[launcher](docs/screenshots/launcher.png), [window switcher](docs/screenshots/window-switcher.png),
[launcher session menu](docs/screenshots/session-menu.png),
[terminal with notification](docs/screenshots/terminal-notification.png),
[login screen](docs/screenshots/login-screen.png),
boot menu [BIOS](docs/screenshots/boot-menu-bios.png) / [UEFI](docs/screenshots/boot-menu-uefi.png).

Also checked by hand on the built ISO: moving the panel to the bottom edge through
`~/.config/lumen/panel.toml` (live reload, popovers open upwards), lock and unlock, and the run
launcher (`Alt+F2`). Not yet verified: GPU-accelerated rendering (`GL=1`), real hardware, Wi-Fi
and audio output; everything above ran on virtual devices.
Work through [docs/TESTING.md](docs/TESTING.md) to repeat the checks by hand.

## Build the ISO

The build runs inside a Debian 13 (amd64) container, so the host can be any Linux, macOS or
Windows machine with Docker. It needs about 10 GB of free disk and 20-40 minutes on an x86 host;
on Apple Silicon Docker emulates amd64 and the build takes roughly 30-60 minutes. The live-build
work directory is kept in a Docker volume (`lumen-build`) because the chroot needs a Linux
filesystem, which a macOS or Windows bind mount is not; `make clean` removes it.

```sh
git clone <this repository> lumen-linux && cd lumen-linux
make iso
```

Result: `dist/lumen-linux-1.0.0-amd64.iso` and a `.sha256` file.

No local Docker? Push the repository to GitHub: the `build-iso` workflow runs the same
`make iso` and publishes the ISO as a build artifact (and as a release asset for `v*` tags).

Building directly on a Debian/Ubuntu host (as root, with `live-build` installed):

```sh
sudo apt install live-build debootstrap squashfs-tools xorriso mtools grub-efi-amd64-bin \
                 grub-pc-bin syslinux isolinux dpkg-dev python3
sudo ./build.sh
```

### Repeatable builds

| Setting | Effect |
|---|---|
| `LUMEN_SNAPSHOT=20261101T000000Z make iso` | Pins every Debian package to that [snapshot.debian.org](https://snapshot.debian.org) archive, so the package set is identical on every build |
| `SOURCE_DATE_EPOCH` | Clamps timestamps inside the Lumen `.deb` files (defaults to the last commit time, passed in by `make iso`) |
| `LUMEN_MIRROR=...` | Use a local mirror |

The build tools run in a pinned `debian:trixie` image, the theme is generated deterministically
from `theme/palette.toml`, and CI fails when generated files are out of date. The ISO as a whole
is *reproducible in inputs*, not bit-for-bit: live-build embeds some timestamps and ordering.

## Run in QEMU

Linux / macOS (`brew install qemu` on a Mac):

```sh
./run-qemu.sh dist/lumen-linux-1.0.0-amd64.iso          # BIOS boot, software rendering
UEFI=1 ./run-qemu.sh dist/lumen-linux-1.0.0-amd64.iso    # UEFI via OVMF / edk2
GL=1   ./run-qemu.sh dist/lumen-linux-1.0.0-amd64.iso    # virgl 3D acceleration (Linux only)
```

The script picks KVM on Linux, HVF on Intel Macs and software emulation elsewhere (Apple
Silicon cannot accelerate an x86 guest: expect about 90 seconds to the desktop), and the gtk
display on Linux or cocoa on macOS.

Windows (PowerShell, QEMU on `PATH`):

```powershell
.\run-qemu.ps1 -Iso .\dist\lumen-linux-1.0.0-amd64.iso            # WHPX acceleration
.\run-qemu.ps1 -Iso .\dist\lumen-linux-1.0.0-amd64.iso -Accel tcg  # if WHPX is unavailable
.\run-qemu.ps1 -Iso .\dist\lumen-linux-1.0.0-amd64.iso -Uefi        # UEFI (GRUB) instead of BIOS
```

Or the raw command:

```sh
qemu-system-x86_64 -enable-kvm -m 4096 -smp 4 -cdrom dist/lumen-linux-1.0.0-amd64.iso -boot d \
  -device virtio-vga -display gtk -device intel-hda -device hda-duplex \
  -nic user,model=virtio-net-pci -device qemu-xhci -device usb-tablet
```

The live system logs in automatically as **`lumen`** (password **`live`**, passwordless `sudo`).
The boot menu defaults to the live system; the desktop appears after the automatic login. After
*Log out* the Lumen login screen appears; sign in again as `lumen` / `live`.

## Using the desktop

| Keys | Action |
|---|---|
| `Super+Space` or the **Lumen** button | Application launcher (press again to close) |
| `Super+Tab` | Window switcher (open windows, in the launcher) |
| `Super+Escape` | Session menu: lock, log out, restart, power off |
| `Alt+F2` | Run a command |
| `Super+Return` | Terminal (foot) |
| `Super+E` / `Super+B` | Files / Web browser |
| `Super+Q`, `Alt+Tab` | Close window, switch windows |
| `Super+Left/Right/Up/Down` | Snap left/right, maximise, minimise |
| `Super+1..4`, `Super+Shift+1..4` | Go to / send window to workspace |
| `Print`, `Shift+Print` | Screenshot area / screen |
| `Super+L` | Lock screen |
| `Super+Shift+R` / `Super+Shift+E` | Reload compositor config / log out |

Panel, left to right: the **Lumen** launcher button; workspace numbers (click or scroll to
switch); a task button per window (click to focus, click the focused one to minimise, middle
click to close); system status; the clock (click for a calendar); the power icon. Scroll on the
volume to change it, click it to mute (right-click opens the mixer).

## Customising

```sh
$EDITOR theme/palette.toml     # change colours, fonts, radius
make theme                     # regenerate every themed file
make iso                       # rebuild
```

On a running system:

| File | Purpose |
|---|---|
| `~/.config/lumen/panel.toml` | Panel layout and modules (reloads live) |
| `~/.config/lumen/panel.css` | Panel style overrides (reloads live) |
| `~/.config/lumen/launcher.ini` | Replaces the launcher theme |
| `~/.config/labwc/rc.xml` | Compositor settings and keybindings |

## Repository layout

```
theme/                  palette.toml + templates (single source of truth for the look),
                        vendor/adwaita (the GTK stylesheet that gets recoloured)
tools/gen-theme.py      renders templates into the component and boot-menu trees
components/
  lumen-panel/          from-scratch panel (Python package, CSS, tests)
  lumen-launcher/       fuzzel wrapper + generated launcher theme
  lumen-desktop/        rootfs overlay: session, labwc/greetd/GTK config, login screen, theme, wallpaper
packaging/              dpkg-deb build of the three Lumen packages
iso/                    live-build tree: package list, hooks, boot menu branding, auto/config
build.sh, Dockerfile.build, Makefile   build entry points
tests/boot_test.py                     boots the built ISO in QEMU and checks the desktop
run-qemu.sh, run-qemu.ps1              test the ISO
.github/workflows/      CI: tests, shellcheck, ISO build
```

## Development

```sh
make test          # unit tests, theme freshness, script/XML syntax
```

Run the panel on any Wayland desktop that supports `wlr-layer-shell` (sway, labwc, Hyprland,
river; not GNOME/Mutter) without installing it:

```sh
cd components/lumen-panel
LUMEN_PANEL_CSS=data/panel.css LD_PRELOAD=$(ldconfig -p | awk '/libgtk-layer-shell.so.0 /{print $NF; exit}') \
    python3 -m lumen_panel -v
```

## License

MIT, see [LICENSE](LICENSE). Third-party software keeps its own licenses, see
[docs/THIRD-PARTY.md](docs/THIRD-PARTY.md).
