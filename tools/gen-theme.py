#!/usr/bin/env python3
"""Generate every themed file in the tree from theme/palette.toml.

Templates live in theme/templates/*.tpl and use {{ section.key }} placeholders
with an optional filter: {{ colors.bg|nohash }}.

    python3 tools/gen-theme.py          # write generated files
    python3 tools/gen-theme.py --check  # exit 1 if any file is out of date
"""
from __future__ import annotations

import argparse
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
                raise SystemExit(f"palette has no key '{match.group(1)}'")
        return _filter(str(node), match.group(2))

    return PLACEHOLDER.sub(sub, template)


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
