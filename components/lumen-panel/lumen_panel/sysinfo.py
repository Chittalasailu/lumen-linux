"""Pure parsers/readers for the data the panel displays.

Nothing here imports GTK. Each function takes text (or a sysfs root) so tests
can feed canned data.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional


# --------------------------------------------------------------------- CPU
def parse_cpu_times(proc_stat: str) -> tuple[int, int]:
    """Return (idle, total) jiffies from the aggregate ``cpu`` line of /proc/stat."""
    for line in proc_stat.splitlines():
        if line.startswith("cpu "):
            fields = [int(x) for x in line.split()[1:]]
            idle = fields[3] + (fields[4] if len(fields) > 4 else 0)  # idle + iowait
            return idle, sum(fields[:8])
    raise ValueError("no aggregate cpu line in /proc/stat")


class CpuSampler:
    """Turns successive /proc/stat snapshots into a utilisation percentage."""

    def __init__(self) -> None:
        self._prev: Optional[tuple[int, int]] = None

    def update(self, proc_stat: str) -> Optional[float]:
        idle, total = parse_cpu_times(proc_stat)
        prev, self._prev = self._prev, (idle, total)
        if prev is None:
            return None
        d_total = total - prev[1]
        if d_total <= 0:
            return 0.0
        return max(0.0, min(100.0, 100.0 * (1.0 - (idle - prev[0]) / d_total)))


# ------------------------------------------------------------------ Memory
def parse_meminfo(text: str) -> tuple[int, int]:
    """Return (used_kib, total_kib) where used = MemTotal - MemAvailable."""
    values = {}
    for line in text.splitlines():
        m = re.match(r"(\w+):\s+(\d+)", line)
        if m:
            values[m.group(1)] = int(m.group(2))
    total = values["MemTotal"]
    available = values.get("MemAvailable", values.get("MemFree", 0))
    return total - available, total


def format_kib(kib: int) -> str:
    gib = kib / (1024 * 1024)
    if gib >= 1:
        return f"{gib:.1f} GiB"
    return f"{kib / 1024:.0f} MiB"


# ----------------------------------------------------------------- Battery
@dataclass(frozen=True)
class Battery:
    percent: int
    status: str  # Charging, Discharging, Full, Not charging, Unknown

    @property
    def charging(self) -> bool:
        return self.status == "Charging"


def read_battery(root: str = "/sys/class/power_supply") -> Optional[Battery]:
    """First battery found under *root*, or None on a desktop/VM."""
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return None
    for entry in entries:
        base = os.path.join(root, entry)
        try:
            with open(os.path.join(base, "type")) as f:
                if f.read().strip() != "Battery":
                    continue
            with open(os.path.join(base, "capacity")) as f:
                percent = int(f.read().strip())
            try:
                with open(os.path.join(base, "status")) as f:
                    status = f.read().strip()
            except OSError:
                status = "Unknown"
            return Battery(percent=max(0, min(100, percent)), status=status)
        except (OSError, ValueError):
            continue
    return None


def battery_icon(b: Battery) -> str:
    level = (b.percent // 10) * 10
    suffix = "-charging" if b.charging else ""
    return f"battery-level-{level}{suffix}-symbolic"


# ----------------------------------------------------------------- Network
@dataclass(frozen=True)
class NetState:
    kind: str  # "wired", "wifi" or "none"
    interface: str = ""

    @property
    def icon(self) -> str:
        return {
            "wired": "network-wired-symbolic",
            "wifi": "network-wireless-symbolic",
        }.get(self.kind, "network-offline-symbolic")


def read_network(root: str = "/sys/class/net") -> NetState:
    """Pick the first non-loopback interface whose operstate is 'up'."""
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return NetState("none")
    best: Optional[NetState] = None
    for name in names:
        if name == "lo":
            continue
        base = os.path.join(root, name)
        try:
            with open(os.path.join(base, "operstate")) as f:
                state = f.read().strip()
        except OSError:
            continue
        if state != "up":
            continue
        kind = "wifi" if os.path.isdir(os.path.join(base, "wireless")) else "wired"
        cand = NetState(kind, name)
        if best is None or (best.kind == "wifi" and kind == "wired"):
            best = cand
    return best or NetState("none")


# ------------------------------------------------------------------ Volume
@dataclass(frozen=True)
class Volume:
    percent: int
    muted: bool

    @property
    def icon(self) -> str:
        if self.muted or self.percent == 0:
            return "audio-volume-muted-symbolic"
        if self.percent < 34:
            return "audio-volume-low-symbolic"
        if self.percent < 67:
            return "audio-volume-medium-symbolic"
        return "audio-volume-high-symbolic"


def parse_wpctl_volume(output: str) -> Optional[Volume]:
    """Parse ``wpctl get-volume`` output, e.g. ``Volume: 0.45 [MUTED]``."""
    m = re.search(r"Volume:\s+([0-9.]+)", output)
    if not m:
        return None
    return Volume(percent=round(float(m.group(1)) * 100), muted="[MUTED]" in output)
