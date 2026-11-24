#!/usr/bin/env python3
"""Boot the Lumen ISO headless in QEMU, wait for the desktop, exercise it, save screenshots.

Used by CI (see .github/workflows/build-iso.yml) and runnable by hand on Linux:

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
import time

from PIL import Image, ImageChops

AMBER = (255, 180, 84)  # the Lumen palette accent: colour of the panel's launcher button
OVMF_DIRS = ("/usr/share/OVMF", "/usr/share/edk2/ovmf", "/usr/share/qemu")
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


def changed_pixels(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    diff = ImageChops.difference(a.crop(box), b.crop(box)).convert("L")
    return sum(1 for v in diff.getdata() if v > 24)


def find_ovmf() -> tuple[str, str]:
    for d in OVMF_DIRS:
        for code, vars_ in OVMF_PAIRS:
            if os.path.exists(f"{d}/{code}") and os.path.exists(f"{d}/{vars_}"):
                return f"{d}/{code}", f"{d}/{vars_}"
    raise SystemExit("OVMF/edk2 firmware not found (apt install ovmf)")


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
    sock = os.path.join(out, "qmp.sock")
    if os.path.exists(sock):
        os.unlink(sock)

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
        panel_box = (0, 0, w, 40)
        below = (0, 41, w, 400)

        # calendar popover: click the clock (centre of the panel)
        qmp.click(w / 2, 17, size)
        time.sleep(2)
        cal = qmp.shot(os.path.join(out, "02-calendar.png"))
        check("clock click opens the calendar below the panel",
              changed_pixels(desktop, cal, below) > 3000,
              f"{changed_pixels(desktop, cal, below)} pixels changed under the panel")
        qmp.click(w / 2, 17, size)  # close it
        time.sleep(1)

        # session menu: power icon, right end of the panel
        qmp.click(w - 27, 17, size)
        time.sleep(2)
        power = qmp.shot(os.path.join(out, "03-power-menu.png"))
        check("power icon opens the session menu below the panel",
              changed_pixels(desktop, power, below) > 3000,
              f"{changed_pixels(desktop, power, below)} pixels changed under the panel")
        qmp.keys("esc")
        time.sleep(1)

        # launcher
        qmp.keys("meta_l", "spc")
        time.sleep(3)
        qmp.type("fire")
        time.sleep(2)
        launcher = qmp.shot(os.path.join(out, "04-launcher.png"))
        check("Super+Space opens the launcher", changed_pixels(desktop, launcher, below) > 5000,
              f"{changed_pixels(desktop, launcher, below)} pixels changed")
        # a fixed bug: with one Firefox result the launcher drew its icon at screen size
        big = orange_pixels(launcher, (0, h // 2, w, h))
        check("launcher draws no oversized icon", big < 1500, f"{big} orange pixels in the lower half")
        qmp.keys("esc")
        time.sleep(1)

        # terminal + notification + maximise
        qmp.keys("meta_l", "ret")
        time.sleep(6)
        qmp.type("notify-send Hello Lumen-works\n")
        time.sleep(4)
        term = qmp.shot(os.path.join(out, "05-terminal-notification.png"))
        check("terminal opens and a notification appears", changed_pixels(desktop, term, below) > 5000)
        qmp.keys("meta_l", "up")
        time.sleep(3)
        qmp.shot(os.path.join(out, "06-maximized.png"))

        # volume: scroll down over the volume module
        qmp.scroll(w - 95, 17, size, "down", 3)
        time.sleep(3)
        vol = qmp.shot(os.path.join(out, "07-volume.png"))
        check("volume module reacts to scrolling",
              changed_pixels(term, vol, (w - 200, 0, w, 40)) > 20,
              "volume label region changed")
    except Exception as exc:  # keep whatever evidence there is
        ok = False
        results["error"] = repr(exc)
        log(f"ERROR: {exc!r}")
        try:
            Qmp(sock, timeout=5).shot(os.path.join(out, "99-final-state.png"))
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
