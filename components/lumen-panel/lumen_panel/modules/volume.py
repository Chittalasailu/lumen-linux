"""Volume via WirePlumber's wpctl. Scroll to adjust, click to mute."""
from __future__ import annotations

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from .. import sysinfo, util
from . import Module, register

SINK = "@DEFAULT_AUDIO_SINK@"


@register("volume")
class VolumeModule(Module):
    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.get_style_context().remove_class("module")
        self.step = int(cfg.get("step", 5))
        self.mixer = cfg.get("mixer", ["pavucontrol"])

        self.button = Gtk.Button()
        self.button.set_relief(Gtk.ReliefStyle.NONE)
        for c in ("module", "volume"):
            self.button.get_style_context().add_class(c)
        box = Gtk.Box(spacing=6)
        self.icon = Gtk.Image.new_from_icon_name("audio-volume-medium-symbolic", Gtk.IconSize.MENU)
        self.label = Gtk.Label(label="--")
        box.pack_start(self.icon, False, False, 0)
        box.pack_start(self.label, False, False, 0)
        self.button.add(box)
        self.button.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.button.connect("clicked", self._toggle_mute)
        self.button.connect("button-press-event", self._maybe_open_mixer)
        self.button.connect("scroll-event", self._scroll)
        self.pack_start(self.button, False, False, 0)
        self._accum = 0.0

    # -- reading ---------------------------------------------------------
    def _apply(self, out: str | None) -> None:
        vol = sysinfo.parse_wpctl_volume(out) if out else None
        if vol is None:
            self.label.set_text("n/a")
            self.set_state("muted")
            return
        self.icon.set_from_icon_name(vol.icon, Gtk.IconSize.MENU)
        self.label.set_text("mute" if vol.muted else f"{vol.percent}%")
        self.button.set_tooltip_text(
            f"Volume {vol.percent}%{' (muted)' if vol.muted else ''}\n"
            "Scroll to adjust, click to mute, right-click for mixer"
        )
        if vol.muted:
            self.set_state("muted")
        else:
            self.set_state()

    def refresh(self) -> None:
        util.capture(["wpctl", "get-volume", SINK], self._apply)

    # -- actions ---------------------------------------------------------
    def _after(self, _out: str | None) -> None:
        self.refresh()

    def _toggle_mute(self, _b: Gtk.Button) -> None:
        util.capture(["wpctl", "set-mute", SINK, "toggle"], self._after)

    def _maybe_open_mixer(self, _b: Gtk.Button, event: Gdk.EventButton) -> bool:
        if event.button == 3:
            util.spawn(self.mixer)
            return True
        return False

    def _scroll(self, _b: Gtk.Button, event: Gdk.EventScroll) -> bool:
        if event.direction == Gdk.ScrollDirection.UP:
            self._adjust(+1)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self._adjust(-1)
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            self._accum += event.delta_y
            if abs(self._accum) >= 1:
                self._adjust(-1 if self._accum > 0 else +1)
                self._accum = 0.0
        return True

    def _adjust(self, direction: int) -> None:
        sign = "+" if direction > 0 else "-"
        # -l 1.0 caps the volume at 100% so scrolling can't clip the speakers
        util.capture(["wpctl", "set-volume", "-l", "1.0", SINK, f"{self.step}%{sign}"], self._after)

    def start(self) -> None:
        self.every(self.cfg.get("interval", 2), self.refresh)
