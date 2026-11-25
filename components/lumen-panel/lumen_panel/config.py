"""Panel configuration: built-in defaults overlaid by TOML files.

Search order (later wins, tables are merged key by key):

1. built-in DEFAULTS
2. /etc/lumen/panel.toml          (distribution defaults)
3. ~/.config/lumen/panel.toml     (user overrides)
"""
from __future__ import annotations

import copy
import logging
import os
from typing import Any, Iterable, Optional

try:
    import tomllib
except ModuleNotFoundError:  # developer machines older than Python 3.11
    import tomli as tomllib  # type: ignore[no-redef]

log = logging.getLogger("lumen-panel")

DEFAULTS: dict[str, Any] = {
    "panel": {
        "position": "top",  # "top" or "bottom"
        "height": 36,
        "layer": "top",  # "top" keeps windows from covering it; "overlay" floats above
    },
    "layout": {
        "left": ["launcher", "workspaces", "tasks"],
        "center": [],
        "right": ["cpu", "memory", "network", "volume", "battery", "clock", "power"],
    },
    "launcher": {"label": "Lumen", "command": ["lumen-launcher"]},
    "workspaces": {"labels": "index"},  # "index" (1 2 3 4) or "name" (the compositor's names)
    "tasks": {"max_chars": 22},
    "clock": {"format": "%a %d %b   %H:%M", "tooltip_format": "%A, %d %B %Y"},
    "cpu": {"interval": 2, "warn": 70, "critical": 90},
    "memory": {"interval": 3, "warn": 75, "critical": 90},
    "network": {"interval": 5, "command": ["nm-connection-editor"]},
    "volume": {"interval": 2, "step": 5, "mixer": ["pavucontrol"]},
    "battery": {"interval": 30, "warn": 25, "critical": 10},
    "power": {
        "lock": ["swaylock", "-f"],
        "logout": ["labwc", "--exit"],
        "reboot": ["systemctl", "reboot"],
        "poweroff": ["systemctl", "poweroff"],
    },
}

SYSTEM_CONFIG = "/etc/lumen/panel.toml"


def user_config_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "lumen", "panel.toml")


def merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into a copy of *base*."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def validate(cfg: dict) -> dict:
    """Clamp obviously bad values back to defaults instead of crashing the panel."""
    panel = cfg["panel"]
    if panel.get("position") not in ("top", "bottom"):
        log.warning("panel.position must be 'top' or 'bottom'; using 'top'")
        panel["position"] = "top"
    if panel.get("layer") not in ("top", "overlay"):
        log.warning("panel.layer must be 'top' or 'overlay'; using 'top'")
        panel["layer"] = "top"
    height = panel.get("height")
    if not isinstance(height, int) or not 16 <= height <= 128:
        log.warning("panel.height out of range; using 36")
        panel["height"] = 36
    for zone in ("left", "center", "right"):
        names = cfg["layout"].get(zone)
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            log.warning("layout.%s must be a list of module names", zone)
            cfg["layout"][zone] = copy.deepcopy(DEFAULTS["layout"][zone])
    return cfg


def load(paths: Optional[Iterable[str]] = None) -> dict:
    """Load configuration. *paths* overrides the default search list (tests)."""
    if paths is None:
        paths = [SYSTEM_CONFIG, user_config_path()]
    cfg = copy.deepcopy(DEFAULTS)
    for path in paths:
        try:
            with open(path, "rb") as f:
                cfg = merge(cfg, tomllib.load(f))
        except FileNotFoundError:
            continue
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.error("ignoring %s: %s", path, exc)
    return validate(cfg)
