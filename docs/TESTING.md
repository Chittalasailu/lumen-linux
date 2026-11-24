# Testing and demo

## Boot test in CI (the shipped ISO, BIOS and UEFI)

`tests/boot_test.py` boots the ISO in QEMU without a display and uses QEMU's QMP socket for
screenshots, key presses and absolute mouse events. It passes only if the desktop appears after
automatic login at 1360x768 and the calendar, session menu, launcher, notification, maximised
window and volume scroll all behave. CI runs it for both firmware types after every build and
uploads the screenshots as the `boot-test-bios` and `boot-test-uefi` artifacts (about 600 KB each).
To run it yourself on Linux:

```sh
sudo apt install qemu-system-x86 ovmf python3-pil
python3 tests/boot_test.py --iso dist/lumen-linux-1.0.0-amd64.iso --firmware uefi --out shots
```

## Automated (no display, runs on any machine and in CI)

```sh
make test
```

* `tools/gen-theme.py --check`: generated files match the palette.
* 22 unit tests for the panel's parsers and configuration (`components/lumen-panel/tests`).
* Syntax check of every shell script and the compositor XML; `shellcheck` in CI.

## Image verification checklist

Boot takes a few minutes in software emulation: the display stays on the boot-menu image,
then goes black, then the desktop appears. Wait for it before assuming a hang.

Run after `make iso`, booting with `./run-qemu.sh` (or `run-qemu.ps1`). Record the result of each
line when you demo it.

**Boot**
- [ ] ISO boots under BIOS (default) and UEFI (`UEFI=1`)
- [ ] Both boot menus show the Lumen splash, amber selection and "Lumen Linux live" entries
- [ ] Automatic login reaches the desktop with no prompts

**Theme**
- [ ] `gsettings get org.gnome.desktop.interface gtk-theme` prints `'Lumen'`
- [ ] Thunar (`Super+E`): navy surfaces, amber selected row with dark text, no Adwaita blue

**Compositor and session**
- [ ] `echo $XDG_SESSION_TYPE` prints `wayland`; `echo $XDG_CURRENT_DESKTOP` prints `labwc:wlroots`
- [ ] `loginctl show-session $XDG_SESSION_ID -p Type` shows `Type=wayland`
- [ ] Windows have Lumen titlebars (amber border on the focused window)
- [ ] `Super+1..4` switches workspaces; `Super+Left/Right` snaps; right-click desktop shows the menu

**Panel (from scratch)**
- [ ] Panel visible at the top, full width, on top of the wallpaper
- [ ] A maximised window stops *below* the panel (exclusive zone working)
- [ ] Clock updates; clicking it opens the calendar popover
- [ ] CPU and memory values change when a load is started (`yes > /dev/null`)
- [ ] Network shows `Wired` in QEMU user networking
- [ ] Volume responds to scroll/click (needs the `hda-duplex` device)
- [ ] Power popover opens; *Lock screen* locks; *Log out* ends the session and shows the Lumen
      login screen (gtkgreet); `lumen` / `live` logs back in
- [ ] Edit `~/.config/lumen/panel.toml` (for example `position = "bottom"`): the panel moves
      without a restart
- [ ] `~/.local/state/lumen/panel.log` has no tracebacks

**Launcher (customised)**
- [ ] `Super+Space` opens it under the panel; pressing it again closes it
- [ ] The **Lumen** panel button opens it; typing filters applications; Enter starts one
- [ ] Colours match the panel and window borders

**Theming**
- [ ] Terminal (`Super+Return`), Thunar and a notification
      (`notify-send Hello "Lumen works"`) all use the Lumen palette

If the panel opens as a normal window instead of a bar, layer-shell was not initialised: read
`~/.local/state/lumen/panel.log` and check that `/usr/bin/lumen-panel` sets `LD_PRELOAD`.

If the screen stays black in QEMU, try `-device virtio-vga` (default) and confirm
`~/.local/state/lumen/session.log` for wlroots renderer messages; switching between
`-device VGA` and `-device virtio-vga` is worth trying.

## Two-minute demo script

| Time | Show | Say |
|---|---|---|
| 0:00 | Terminal: `make iso` finished, `ls -lh dist/`; then QEMU command | Reproducible Debian 13 ISO built with live-build in a container |
| 0:15 | Boot, auto login, desktop appears | Live image, greetd autologin into a labwc Wayland session |
| 0:30 | Panel: hover modules, click clock calendar, scroll volume | The panel is written from scratch on wlr-layer-shell |
| 0:50 | Maximise a window; it stops under the panel | The panel reserves space with an exclusive zone; the compositor does the rest |
| 1:05 | `Super+Space`: launcher; start Terminal; press again to close | fuzzel, customised: palette theme, toggle wrapper, panel integration |
| 1:25 | Edit `~/.config/lumen/panel.toml` live (position or layout) | Config and CSS hot-reload |
| 1:40 | Open a notification, Thunar, terminal | One palette generates every surface |
| 1:50 | `sh -c 'cat /etc/os-release \| head -3'`, `dpkg -l 'lumen-*'` | Shipped as proper Debian packages |
| 2:00 | End | |

Record with OBS (window capture of the QEMU window) or QEMU's screendump; keep audio narration
short, and trim to two minutes.
