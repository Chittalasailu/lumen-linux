"""Small non-blocking process helpers built on Gio.Subprocess.

The panel's main loop is the GTK loop, so nothing here may block: commands
are spawned and their output delivered through callbacks.
"""
from __future__ import annotations

import logging
import shutil
from typing import Callable, Optional, Sequence

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

log = logging.getLogger("lumen-panel")


def have(program: str) -> bool:
    return shutil.which(program) is not None


def spawn(argv: Sequence[str]) -> bool:
    """Fire and forget. Gio reaps the child, so no zombies are left behind."""
    if not argv or not have(argv[0]):
        log.warning("cannot run %s: not installed", argv[0] if argv else "<empty>")
        return False
    try:
        Gio.Subprocess.new(
            list(argv), Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE
        )
        return True
    except GLib.Error as exc:
        log.error("failed to spawn %s: %s", argv[0], exc.message)
        return False


def capture(argv: Sequence[str], callback: Callable[[Optional[str]], None]) -> None:
    """Run *argv* and call ``callback(stdout_or_None)`` on the main loop."""
    if not argv or not have(argv[0]):
        callback(None)
        return
    try:
        proc = Gio.Subprocess.new(
            list(argv), Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE
        )
    except GLib.Error:
        callback(None)
        return

    def done(p: Gio.Subprocess, result: Gio.AsyncResult) -> None:
        try:
            ok, out, _ = p.communicate_utf8_finish(result)
            callback(out if ok and p.get_successful() else None)
        except GLib.Error:
            callback(None)

    proc.communicate_utf8_async(None, None, done)


def read_text(path: str) -> Optional[str]:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return None
