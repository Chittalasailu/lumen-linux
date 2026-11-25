#!/usr/bin/env python3
"""Boot the Lumen ISO headless in QEMU, wait for the desktop, exercise it, save screenshots.

Used by CI (see .github/workflows/build-iso.yml) and runnable by hand on Linux or macOS
(brew install qemu; pip install pillow):

    python3 tests/boot_test.py --iso dist/lumen-linux-1.0.0-amd64.iso --firmware bios --out shots

Exit status is 0 only if the desktop was reached and the interactive checks passed.
Everything is driven through QEMU's QMP socket: screenshots (screendump), key presses
and absolute mouse events, so no display or window system is needed.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

AMBER = (255, 180, 84)  # the Lumen palette accent: colour of the panel's launcher button
ADWAITA_BLUE = (21, 83, 158)  # stock Adwaita dark selection: must never appear in Lumen apps
OVMF_DIRS = ("/usr/share/OVMF", "/usr/share/edk2/ovmf", "/usr/share/qemu",
             "/opt/homebrew/share/qemu", "/usr/local/share/qemu")
OVMF_PAIRS = (
    ("OVMF_CODE_4M.fd", "OVMF_VARS_4M.fd"),
    ("OVMF_CODE.fd", "OVMF_VARS.fd"),
    ("edk2-x86_64-code.fd", "edk2-i386-vars.fd"),
)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class Qmp:
    def __init__(self, path: str, timeout: float = 60) -> None:
        deadline = time.time() + timeout
        while True:
            try:
                self.sock = socket.socket(socket.AF_UNIX)
                self.sock.connect(path)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.5)
        self.sock.settimeout(120)  # a stuck QEMU must fail the test, not hang CI
        self.f = self.sock.makefile("rw")
        self.f.readline()  # greeting
        self.call("qmp_capabilities")

    def call(self, cmd: str, **args):
        self.f.write(json.dumps({"execute": cmd, "arguments": args}) + "\n")
        self.f.flush()
        while True:
            msg = json.loads(self.f.readline())
            if "return" in msg:
                return msg["return"]
            if "error" in msg:
                raise RuntimeError(f"QMP {cmd}: {msg['error']}")

    # -- input ----------------------------------------------------------
    def keys(self, *qcodes: str) -> None:
        self.call("send-key", keys=[{"type": "qcode", "data": q} for q in qcodes], **{"hold-time": 120})

    def type(self, text: str) -> None:
        names = {" ": "spc", "-": "minus", ".": "dot", "\n": "ret"}
        for ch in text:
            if ch.isupper():
                self.keys("shift", ch.lower())
            else:
                self.keys(names.get(ch, ch))
            time.sleep(0.08)

    def _move(self, x: float, y: float, w: int, h: int) -> None:
        self.call("input-send-event", events=[
            {"type": "abs", "data": {"axis": "x", "value": int(x / w * 32767)}},
            {"type": "abs", "data": {"axis": "y", "value": int(y / h * 32767)}},
        ])

    def click(self, x: float, y: float, size: tuple[int, int], button: str = "left") -> None:
        w, h = size
        self._move(x - 3, y - 2, w, h)
        time.sleep(0.2)
        self._move(x, y, w, h)
        time.sleep(0.3)
        for down in (True, False):
            self.call("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": button}}])
            time.sleep(0.12)

    def scroll(self, x: float, y: float, size: tuple[int, int], direction: str, ticks: int = 3) -> None:
        w, h = size
        self._move(x, y, w, h)
        time.sleep(0.3)
        button = "wheel-up" if direction == "up" else "wheel-down"
        for _ in range(ticks):
            for down in (True, False):
                self.call("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": button}}])
            time.sleep(0.1)

    # -- screen ---------------------------------------------------------
    def shot(self, path: str) -> Image.Image:
        self.call("screendump", filename=os.path.abspath(path), format="png")
        for _ in range(20):  # the file is written asynchronously
            if os.path.exists(path) and os.path.getsize(path) > 0:
                try:
                    img = Image.open(path)
                    img.load()
                    return img.convert("RGB")
                except OSError:
                    pass
            time.sleep(0.25)
        raise RuntimeError(f"screendump produced no readable file: {path}")


def amber_pixels(img: Image.Image) -> int:
    """Count launcher-button-coloured pixels in the panel's top-left corner."""
    region = img.crop((0, 0, min(200, img.width), min(48, img.height)))
    return sum(
        1 for p in region.getdata()
        if all(abs(p[i] - AMBER[i]) <= 14 for i in range(3))
    )


def orange_pixels(img: Image.Image, box: tuple[int, int, int, int]) -> int:
    """Count Firefox-logo-orange pixels (the palette's own accent is a lighter amber)."""
    return sum(1 for r, g, b in img.crop(box).getdata() if r > 230 and 90 < g < 150 and b < 70)


def changed_pixels(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int], threshold: int = 24) -> int:
    """Pixels whose brightness differs by more than *threshold* (0-255)."""
    diff = ImageChops.difference(a.crop(box), b.crop(box)).convert("L")
    return sum(1 for v in diff.getdata() if v > threshold)


def count_colour(img: Image.Image, box: tuple[int, int, int, int], rgb: tuple[int, int, int], tol: int = 14) -> int:
    """Pixels within *tol* of *rgb* on every channel."""
    return sum(1 for p in img.crop(box).getdata() if all(abs(p[i] - rgb[i]) <= tol for i in range(3)))


def panel_modules(img: Image.Image, x0: int, height: int = 36, gap: int = 16) -> list[tuple[int, int]]:
    """Horizontal extents of the drawn modules on the panel, left to right, from x0.

    A column belongs to a module when any pixel in the panel's middle band differs
    clearly from the panel background; modules are separated by at least *gap*
    empty columns (their padding), while text and icons inside one are closer.
    """
    bg = img.getpixel((x0, 2))
    band = img.crop((x0, 6, img.width, height - 6))
    w, h = band.size
    px = band.load()
    busy = [any(sum(abs(px[x, y][i] - bg[i]) for i in range(3)) > 90 for y in range(h)) for x in range(w)]
    spans, start, empty = [], None, 0
    for x, on in enumerate(busy + [False] * gap):
        if on:
            start = x if start is None else start
            empty = 0
        elif start is not None:
            empty += 1
            if empty >= gap:
                spans.append((x0 + start, x0 + x - empty))
                start, empty = None, 0
    return spans


def find_ovmf() -> tuple[str, str]:
    for d in OVMF_DIRS:
        for code, vars_ in OVMF_PAIRS:
            if os.path.exists(f"{d}/{code}") and os.path.exists(f"{d}/{vars_}"):
                return f"{d}/{code}", f"{d}/{vars_}"
    raise SystemExit("OVMF/edk2 firmware not found (apt install ovmf / brew install qemu)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iso", required=True)
    ap.add_argument("--firmware", choices=("bios", "uefi"), default="bios")
    ap.add_argument("--out", default="boot-test-out")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds to wait for the desktop")
    ap.add_argument("--mem", default="3072")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    out = args.out
    # Unix socket paths are capped at ~104 bytes (macOS) / 108 (Linux): keep it short
    # rather than inside --out, which may be deep.
    sock = os.path.join(tempfile.mkdtemp(prefix="lumen-qmp-"), "qmp.sock")

    cmd = ["qemu-system-x86_64", "-m", args.mem, "-smp", "2",
           "-cdrom", args.iso, "-boot", "d",
           "-device", "virtio-vga", "-display", "none",
           "-device", "intel-hda", "-device", "hda-duplex",
           "-nic", "user,model=virtio-net-pci",
           "-device", "qemu-xhci", "-device", "usb-tablet",
           "-qmp", f"unix:{sock},server=on,wait=off"]
    if os.access("/dev/kvm", os.R_OK | os.W_OK):
        cmd += ["-enable-kvm", "-cpu", "host"]
        log("using KVM acceleration")
    elif sys.platform == "darwin" and os.uname().machine == "x86_64":
        cmd += ["-accel", "hvf", "-cpu", "host"]
        log("using HVF acceleration")
    else:
        cmd += ["-accel", "tcg", "-cpu", "max"]
        log("no /dev/kvm: using software emulation (slow)")
    if args.firmware == "uefi":
        code, vars_src = find_ovmf()
        vars_copy = os.path.join(out, "vars.fd")
        with open(vars_src, "rb") as s, open(vars_copy, "wb") as d:
            d.write(s.read())
        cmd += ["-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={code}",
                "-drive", f"if=pflash,format=raw,unit=1,file={vars_copy}"]

    log("starting QEMU: " + " ".join(cmd))
    qemu = subprocess.Popen(cmd)
    results: dict[str, object] = {"firmware": args.firmware, "checks": {}}
    qmp = None
    ok = True

    def check(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        results["checks"][name] = {"passed": passed, "detail": detail}
        log(f"{'PASS' if passed else 'FAIL'}: {name} {detail}")
        ok = ok and passed

    try:
        qmp = Qmp(sock)
        time.sleep(20)
        qmp.shot(os.path.join(out, "00-boot-menu.png"))
        qmp.keys("ret")  # choose "Live system" (syslinux or GRUB)
        log("pressed Enter at the boot menu; waiting for the desktop")

        start = time.time()
        desktop = None
        size = (0, 0)
        first_panel = None
        while time.time() - start < args.timeout:
            time.sleep(15)
            img = qmp.shot(os.path.join(out, "poll.png"))
            n = amber_pixels(img)
            log(f"{int(time.time() - start):4d}s  screen {img.width}x{img.height}  launcher-colour pixels {n}")
            if n > 150:  # the panel's launcher button is on screen
                first_panel = first_panel or time.time()
                # give the VM display-mode switch up to a minute; then judge what we have
                if img.width >= 1000 or time.time() - first_panel > 60:
                    time.sleep(10)
                    desktop = qmp.shot(os.path.join(out, "01-desktop.png"))
                    size = desktop.size
                    break
        results["boot_seconds"] = int(time.time() - start)
        check("desktop reached", desktop is not None, f"after {results['boot_seconds']}s")
        if desktop is None:
            raise RuntimeError("desktop never appeared")
        check("auto-login to Wayland session at 1360x768", size == (1360, 768), f"screen is {size[0]}x{size[1]}")

        w, h = size
        below = (0, 41, w, 400)
        menu = Image.open(os.path.join(out, "00-boot-menu.png")).convert("RGB")
        sun = count_colour(menu, (0, 0, menu.width, menu.height // 2), AMBER, 20)
        check("boot menu carries the Lumen branding", sun > 300, f"{sun} amber pixels in the splash")

        # The right-hand modules, located on the screenshot so the test does not
        # depend on fonts: ... volume, clock, power (battery is absent in a VM).
        right = panel_modules(desktop, w // 2)
        log(f"panel modules on the right: {right}")
        if len(right) < 3:
            raise RuntimeError(f"expected at least 3 modules on the right of the panel, found {right}")
        centre = lambda span: (span[0] + span[1]) / 2  # noqa: E731
        power_x, clock_x, volume_x = centre(right[-1]), centre(right[-2]), centre(right[-3])

        # calendar popover: click the clock
        qmp.click(clock_x, 17, size)
        time.sleep(2)
        cal = qmp.shot(os.path.join(out, "02-calendar.png"))
        changed = changed_pixels(desktop, cal, below, 6)
        check("clock click opens the calendar below the panel", changed > 3000, f"{changed} pixels changed under the panel")
        qmp.click(clock_x, 17, size)  # close it
        time.sleep(1)

        # session menu: power icon, right end of the panel
        qmp.click(power_x, 17, size)
        time.sleep(2)
        power = qmp.shot(os.path.join(out, "03-power-menu.png"))
        changed = changed_pixels(desktop, power, below, 6)
        check("power icon opens the session menu below the panel", changed > 3000, f"{changed} pixels changed under the panel")
        qmp.click(power_x, 17, size)  # a popover ignores Escape here: click the icon again to close it
        time.sleep(1)

        # workspace indicator: Super+2, then back
        ws_box = (85, 0, 260, 36)
        qmp.keys("meta_l", "2")
        time.sleep(2)
        ws2 = qmp.shot(os.path.join(out, "04-workspace-2.png"))
        changed = changed_pixels(desktop, ws2, ws_box, 30)
        check("workspace indicator follows Super+2", changed > 60, f"{changed} pixels changed in the indicator")
        qmp.keys("meta_l", "1")
        time.sleep(2)

        # launcher
        qmp.keys("meta_l", "spc")
        time.sleep(3)
        qmp.type("fire")
        time.sleep(2)
        launcher = qmp.shot(os.path.join(out, "05-launcher.png"))
        changed = changed_pixels(desktop, launcher, below, 6)
        check("Super+Space opens the launcher", changed > 20000, f"{changed} pixels changed")
        # a fixed bug: with one Firefox result the launcher drew its icon at screen size
        big = orange_pixels(launcher, (0, h // 2, w, h))
        check("launcher draws no oversized icon", big < 1500, f"{big} orange pixels in the lower half")
        qmp.keys("esc")
        time.sleep(1)

        # session menu in the launcher
        qmp.keys("meta_l", "esc")
        time.sleep(3)
        session = qmp.shot(os.path.join(out, "06-session-menu.png"))
        changed = changed_pixels(desktop, session, below, 6)
        check("Super+Escape opens the session menu", changed > 10000, f"{changed} pixels changed")
        qmp.keys("esc")
        time.sleep(1)

        # terminal: appears in the task list; a notification appears top right
        qmp.keys("meta_l", "ret")
        time.sleep(6)
        term = qmp.shot(os.path.join(out, "07-terminal.png"))
        tasks_box = (260, 0, w // 2, 36)
        changed = changed_pixels(desktop, term, tasks_box, 30)
        check("task list shows the new window", changed > 150, f"{changed} pixels changed in the task list")
        note_box = (w - 400, 36, w, 160)
        before = count_colour(term, note_box, AMBER, 20)
        qmp.type("notify-send Hello Lumen-works\n")
        time.sleep(6)  # typing through QMP is slow; let the notification appear
        note = qmp.shot(os.path.join(out, "08-notification.png"))
        border = count_colour(note, note_box, AMBER, 20) - before
        check("notification appears top right with the amber border", border > 400, f"{border} new amber pixels")
        qmp.keys("meta_l", "up")
        time.sleep(3)
        qmp.shot(os.path.join(out, "09-maximized.png"))

        # volume: scroll down over the volume module
        qmp.scroll(volume_x, 17, size, "down", 3)
        time.sleep(3)
        vol = qmp.shot(os.path.join(out, "10-volume.png"))
        span = right[-3]
        changed = changed_pixels(note, vol, (span[0] - 4, 0, span[1] + 4, 36))
        check("volume module reacts to scrolling", changed > 20, f"{changed} pixels changed in the volume module")

        # window switcher (lumen-launcher --windows)
        qmp.keys("meta_l", "tab")
        time.sleep(4)
        switcher = qmp.shot(os.path.join(out, "11-window-switcher.png"))
        changed = changed_pixels(vol, switcher, (0, 41, 600, 470), 6)
        check("Super+Tab opens the window switcher", changed > 20000, f"{changed} pixels changed")
        # fuzzel draws a large image of the selected icon when few entries are left
        # unless image-size-ratio=1; with one window that covered the list
        bright = sum(1 for p in switcher.crop((40, 150, 560, 410)).getdata() if max(p) > 170)
        check("window switcher draws no oversized icon", bright < 300, f"{bright} bright pixels below the entries")
        qmp.keys("esc")
        time.sleep(1)

        # GTK theme: Thunar has the Lumen selection colour, never Adwaita's blue
        qmp.keys("meta_l", "e")
        time.sleep(15)
        fm = qmp.shot(os.path.join(out, "12-file-manager.png"))
        blue = count_colour(fm, (0, 41, w, h), ADWAITA_BLUE, 12)
        amber = count_colour(fm, (0, 41, w, h), AMBER, 14)
        check("GTK apps use the Lumen theme", blue == 0 and amber > 1000, f"{amber} amber, {blue} Adwaita-blue pixels")
        qmp.keys("meta_l", "q")
        time.sleep(2)

        # log out to the login screen, then log back in
        qmp.keys("meta_l", "shift", "e")
        greeter = None
        for _ in range(12):
            time.sleep(5)
            img = qmp.shot(os.path.join(out, "13-login-screen.png"))
            cw, ch = img.size
            if amber_pixels(img) < 50 and count_colour(img, (cw // 4, ch // 4, 3 * cw // 4, 3 * ch // 4), AMBER, 14) > 800:
                greeter = img
                break
        check("logging out shows the Lumen login screen", greeter is not None)
        if greeter is not None:
            qmp.type("lumen\n")
            time.sleep(5)
            qmp.type("live\n")
            back = None
            for _ in range(24):
                time.sleep(5)
                img = qmp.shot(os.path.join(out, "14-logged-in-again.png"))
                if amber_pixels(img) > 150:
                    back = img
                    break
            check("logging in again from the login screen reaches the desktop", back is not None)
    except Exception as exc:  # keep whatever evidence there is
        ok = False
        results["error"] = repr(exc)
        log(f"ERROR: {exc!r}")
        try:
            if qmp is not None:  # QEMU serves one QMP client at a time: reuse ours
                qmp.shot(os.path.join(out, "99-final-state.png"))
        except Exception:
            pass
    finally:
        qemu.terminate()
        try:
            qemu.wait(timeout=20)
        except subprocess.TimeoutExpired:
            qemu.kill()

    results["passed"] = ok
    with open(os.path.join(out, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    log("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
