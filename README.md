# Lumen Linux

A Debian 13 ("trixie") based live distribution with a Wayland desktop built on the
[labwc](https://labwc.github.io/) compositor (wlroots). It ships two desktop components:

| Component | Role | Origin |
|---|---|---|
| **lumen-panel** | Desktop panel / status bar | **Written from scratch** (Python, GTK3, wlr-layer-shell) |
| **lumen-launcher** | Application launcher | **Customised and integrated** [fuzzel](https://codeberg.org/dnkl/fuzzel) |

Everything visual (compositor decorations, panel, launcher, GTK theme, terminal,
notifications, wallpaper) is generated from one palette file, so the desktop has a single
consistent identity: **Lumen Dusk**, deep navy surfaces with an amber accent.

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): boot chain, Wayland stack, how the pieces fit
- [docs/COMPONENTS.md](docs/COMPONENTS.md): the panel's internals and what was customised in the launcher
- [docs/DESIGN-DECISIONS.md](docs/DESIGN-DECISIONS.md): why each choice was made
- [docs/THIRD-PARTY.md](docs/THIRD-PARTY.md): what is original and what is reused
- [docs/TESTING.md](docs/TESTING.md): verification checklist and demo script

## Status

The ISO was built by CI, downloaded, checksum-verified and booted in QEMU (BIOS boot, Windows
host with WHPX). Boot-testing found and fixed two image bugs (see the git history). What has and
has not been verified:

| Verified in QEMU | Not yet verified |
|---|---|
| Boots; greetd logs `lumen` in automatically; labwc Wayland session starts | UEFI boot (`UEFI=1`) |
| Panel appears with launcher button, clock, CPU, memory, network, volume, power | Mouse-driven panel features: calendar popover, power menu, volume scroll/click (keyboard-only testing so far) |
| Launcher opens under the panel (`Super+Space`), filters, themed | GPU-accelerated rendering (`GL=1`); only the software path was run |
| Terminal, notification (mako) and maximised window stop below the panel | Real hardware, Wi-Fi, audio output |
| Panel moves to the bottom when `~/.config/lumen/panel.toml` is written (live reload) | The last two fixes (launcher icon theme, 1360x768 mode in VMs) were tested live but not in a rebuilt ISO |

In QEMU without KVM the first boot to desktop took about 3 minutes; with `-accel kvm`/WHPX it
is faster once the host is idle. Screenshots: [desktop](docs/screenshots/desktop.png),
[launcher](docs/screenshots/launcher.png), [panel at the bottom](docs/screenshots/panel-bottom.png).
Work through [docs/TESTING.md](docs/TESTING.md) to repeat the checks.

## Build the ISO

The build runs inside a Debian 13 container, so the host can be any Linux, macOS or Windows
machine with Docker. It needs about 10 GB of free disk and 20-40 minutes.

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
| `SOURCE_DATE_EPOCH` | Clamps timestamps inside the Lumen `.deb` files (defaults to the last commit time) |
| `LUMEN_MIRROR=...` | Use a local mirror |

The build tools run in a pinned `debian:trixie` image, the theme is generated deterministically
from `theme/palette.toml`, and CI fails when generated files are out of date. The ISO as a whole
is *reproducible in inputs*, not bit-for-bit: live-build embeds some timestamps and ordering.

## Run in QEMU

Linux / macOS:

```sh
./run-qemu.sh dist/lumen-linux-1.0.0-amd64.iso          # BIOS boot, software rendering
UEFI=1 ./run-qemu.sh dist/lumen-linux-1.0.0-amd64.iso    # UEFI via OVMF
GL=1   ./run-qemu.sh dist/lumen-linux-1.0.0-amd64.iso    # virgl 3D acceleration
```

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
The boot menu defaults to the live system; the desktop appears after the automatic login.

## Using the desktop

| Keys | Action |
|---|---|
| `Super+Space` or the **Lumen** button | Application launcher (press again to close) |
| `Alt+F2` | Run a command |
| `Super+Return` | Terminal (foot) |
| `Super+E` / `Super+B` | Files / Web browser |
| `Super+Q`, `Alt+Tab` | Close window, switch windows |
| `Super+Left/Right/Up/Down` | Snap left/right, maximise, minimise |
| `Super+1..4`, `Super+Shift+1..4` | Go to / send window to workspace |
| `Print`, `Shift+Print` | Screenshot area / screen |
| `Super+L` | Lock screen |
| `Super+Shift+R` / `Super+Shift+E` | Reload compositor config / log out |

Panel: click the clock for a calendar, scroll on the volume to change it, click it to mute
(right-click opens the mixer), click the power icon for lock/logout/restart/power off.

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
theme/                  palette.toml + templates (single source of truth for the look)
tools/gen-theme.py      renders templates into the component trees
components/
  lumen-panel/          from-scratch panel (Python package, CSS, tests)
  lumen-launcher/       fuzzel wrapper + generated launcher theme
  lumen-desktop/        rootfs overlay: session, labwc/greetd/GTK config, theme, wallpaper
packaging/              dpkg-deb build of the three Lumen packages
iso/                    live-build tree: package list, hooks, auto/config
build.sh, Dockerfile.build, Makefile   build entry points
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
