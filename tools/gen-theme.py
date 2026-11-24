#!/usr/bin/env python3
"""Generate every themed file in the tree from theme/palette.toml.

Templates live in theme/templates/*.tpl and use {{ section.key }} placeholders
with an optional filter: {{ colors.bg|nohash }}.

    python3 tools/gen-theme.py          # write generated files
    python3 tools/gen-theme.py --check  # exit 1 if any file is out of date
"""
from __future__ import annotations

import argparse
import colorsys
import itertools
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 (developer machines only)
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent
PALETTE = ROOT / "theme" / "palette.toml"
TEMPLATES = ROOT / "theme" / "templates"

# template name -> destination, relative to the repository root
TARGETS = {
    "panel.css.tpl": "components/lumen-panel/data/panel.css",
    "fuzzel.ini.tpl": "components/lumen-launcher/data/fuzzel.ini",
    "labwc-themerc.tpl": "components/lumen-desktop/usr/share/themes/Lumen/openbox-3/themerc",
    "gtk3.css.tpl": "components/lumen-desktop/usr/share/themes/Lumen/gtk-3.0/gtk.css",
    "foot.ini.tpl": "components/lumen-desktop/etc/lumen/xdg/foot/foot.ini",
    "mako.conf.tpl": "components/lumen-desktop/etc/lumen/xdg/mako/config",
    "wallpaper.svg.tpl": "components/lumen-desktop/usr/share/backgrounds/lumen/lumen-dusk.svg",
    "gschema.override.tpl": "components/lumen-desktop/usr/share/glib-2.0/schemas/90_lumen.gschema.override",
}

HEADERS = {
    ".svg": "<!-- GENERATED from theme/palette.toml by tools/gen-theme.py. Do not edit. -->\n",
    ".css": "/* GENERATED from theme/palette.toml by tools/gen-theme.py. Do not edit. */\n",
    "": "# GENERATED from theme/palette.toml by tools/gen-theme.py. Do not edit.\n",
}

PLACEHOLDER = re.compile(r"\{\{\s*([\w.]+)\s*(?:\|\s*(\w+)\s*)?\}\}")


def _filter(value: str, name: str | None) -> str:
    if name is None:
        return value
    if name == "nohash":
        return value.lstrip("#")
    if name == "rgb":  # "#rrggbb" -> "r, g, b"
        h = value.lstrip("#")
        return ", ".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))
    raise SystemExit(f"unknown filter: {name}")


def render(template: str, palette: dict) -> str:
    def sub(match: re.Match) -> str:
        node = palette
        for part in match.group(1).split("."):
            try:
                node = node[part]
            except (KeyError, TypeError):
                raise SystemExit(f"palette has no key '{match.group(1)}'") from None
        return _filter(str(node), match.group(2))

    return PLACEHOLDER.sub(sub, template)


# ---------------------------------------------------------------- GTK theme
# The Lumen GTK theme is Adwaita dark with every colour mapped onto the palette.
# Overriding Adwaita's @define-color names is not enough: its compiled stylesheet
# uses literal colours, so a selected row stays blue. Recolouring the stylesheet
# itself keeps all of Adwaita's widget drawing and changes only the colours.
ADWAITA_DARK = ROOT / "theme" / "vendor" / "adwaita" / "gtk-contained-dark.css"
ADWAITA_SELECTED = "#15539e"  # Adwaita dark's selected_bg_color
# reference colour of each Adwaita hue family -> palette key it maps to
FAMILIES = (
    ((190, 250), "#15539e", "accent"),   # blue: selection, focus, links
    ((66, 170), "#26ab62", "ok"),        # green: success
    ((13, 65), "#f57900", "warn"),       # orange: warnings
    ((340, 360), "#cc0000", "danger"),   # red: errors, destructive actions
    ((0, 12), "#cc0000", "danger"),
)
COLOR = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(?:,\s*[\d.]+\s*)?\)")


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[float, float, float]:
    return tuple(x + (y - x) * t for x, y in zip(a, b, strict=True))


def _ramp(colors: dict) -> list[tuple[int, tuple[int, int, int]]]:
    """Adwaita grey level -> Lumen neutral. Monotonic, so shading relationships survive."""
    bg = _rgb(colors["bg"])
    return [
        (0, (0, 0, 0)),
        (0x1B, tuple(round(c) for c in _mix(bg, (0, 0, 0), 0.45))),  # borders: darker than any surface
        (0x2D, bg),                                # base_color: views, entries
        (0x35, _rgb(colors["surface"])),           # bg_color: windows, toolbars
        (0x48, _rgb(colors["surface_alt"])),       # hovered / raised
        (0x5B, _rgb(colors["border"])),
        (0x91, _rgb(colors["text_dim"])),          # insensitive text
        (0xEE, _rgb(colors["text"])),              # fg_color
        (0xFF, (255, 255, 255)),
    ]


def _map_rgb(rgb: tuple[int, int, int], colors: dict, ramp) -> tuple[float, float, float]:
    hi, lo = max(rgb), min(rgb)
    if hi - lo <= 12:  # neutral grey
        level = sum(rgb) / 3
        for (l0, c0), (l1, c1) in itertools.pairwise(ramp):
            if level <= l1:
                return _mix(c0, c1, (level - l0) / (l1 - l0))
    h, light, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    if s > 0.25:
        hue = h * 360
        for (h0, h1), ref, key in FAMILIES:
            if h0 <= hue <= h1:
                th, tl, ts = colorsys.rgb_to_hls(*(c / 255 for c in _rgb(colors[key])))
                rl = colorsys.rgb_to_hls(*(c / 255 for c in _rgb(ref)))[1]
                new_l = max(0.06, min(0.94, tl + (light - rl)))
                return tuple(c * 255 for c in colorsys.hls_to_rgb(th, new_l, ts))
    return rgb


def recolor_adwaita(css: str, colors: dict) -> str:
    ramp = _ramp(colors)

    def sub(match: re.Match) -> str:
        token = match.group(0)
        if token.startswith("#"):
            if token.lower() == "#ffffff":  # Adwaita dark uses white only as text on selection
                return colors["bg"]
            return _hex(_map_rgb(_rgb(token), colors, ramp))
        parts = [p.strip() for p in token[token.index("(") + 1 : -1].split(",")]
        rgb = tuple(int(p) for p in parts[:3])
        if rgb in ((0, 0, 0), (255, 255, 255)):  # shadows and highlights stay as they are
            return token
        r, g, b = (max(0, min(255, round(c))) for c in _map_rgb(rgb, colors, ramp))
        return f"rgba({r}, {g}, {b}, {parts[3]})" if len(parts) == 4 else f"rgb({r}, {g}, {b})"

    # Adwaita's image assets are only inside libgtk's resource bundle, where relative
    # url("assets/...") resolves; from a theme on disk it must be spelled out.
    css = css.replace('url("assets/', 'url("resource:///org/gtk/libgtk/theme/Adwaita/assets/')
    return COLOR.sub(sub, css)


def header_for(dest: Path) -> str:
    if dest.suffix in HEADERS:
        return HEADERS[dest.suffix]
    # themerc, foot.ini, mako config, fuzzel.ini: '#' comments
    return HEADERS[""]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="fail if output is stale")
    args = ap.parse_args()

    palette = tomllib.loads(PALETTE.read_text(encoding="utf-8"))
    stale = []
    for tpl_name, rel in TARGETS.items():
        dest = ROOT / rel
        body = render((TEMPLATES / tpl_name).read_text(encoding="utf-8"), palette)
        if tpl_name == "gtk3.css.tpl":
            body = recolor_adwaita(ADWAITA_DARK.read_text(encoding="utf-8"), palette["colors"]) + "\n" + body
        text = header_for(dest) + body
        current = dest.read_text(encoding="utf-8") if dest.exists() else None
        if current == text:
            continue
        stale.append(rel)
        if not args.check:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(text.encode("utf-8"))  # always LF, even on Windows
            print(f"wrote {rel}")

    if args.check and stale:
        print("out of date (run `make theme`):", *stale, sep="\n  ", file=sys.stderr)
        return 1
    if not stale:
        print("theme output is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
