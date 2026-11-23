"""Entry point: ``python3 -m lumen_panel`` (normally run through bin/lumen-panel)."""
from __future__ import annotations

import argparse
import logging
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lumen-panel", description="Lumen Linux desktop panel")
    ap.add_argument("--version", action="version", version=f"lumen-panel {__version__}")
    ap.add_argument("--list-modules", action="store_true", help="print available modules and exit")
    ap.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="lumen-panel: %(levelname)s: %(message)s",
    )

    # GTK is imported lazily so --version / --help work without a display.
    from . import modules

    if args.list_modules:
        modules.load_builtin_modules()
        print("\n".join(modules.available()))
        return 0

    from .app import PanelApp

    return PanelApp().run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
