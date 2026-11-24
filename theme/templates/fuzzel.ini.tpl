[main]
# Lumen launcher: fuzzel (a wlr-layer-shell application launcher) themed from the
# shared palette. Colours are RRGGBBAA, no '#'.
font={{ fonts.ui_family }}:size={{ fonts.ui_size }}
prompt="  "
# Adwaita, not Papirus: with Papirus-Dark fuzzel drew Firefox's icon at its native
# size, covering the whole screen. Missing icons fall back to hicolor.
icon-theme=Adwaita
icons-enabled=yes
# Fixed 96 dpi. With dpi-aware=auto the launcher scaled itself from the display's reported
# physical size: a normal window under QEMU's gtk display drew it nearly full width with
# oversized icons, while a headless display drew it small. Fixed scaling is predictable.
dpi-aware=no
terminal=foot -e
layer=overlay
anchor=top-left
x-margin={{ metrics.gap }}
y-margin={{ metrics.gap }}
width=42
lines=10
horizontal-pad=18
vertical-pad=14
inner-pad=8
line-height=26
tabs=4
fields=filename,name,generic
exit-on-keyboard-focus-loss=yes

[colors]
background={{ colors.surface|nohash }}f2
text={{ colors.text|nohash }}ff
match={{ colors.accent|nohash }}ff
selection={{ colors.surface_alt|nohash }}ff
selection-text={{ colors.text|nohash }}ff
selection-match={{ colors.accent|nohash }}ff
border={{ colors.accent|nohash }}ff
input={{ colors.text|nohash }}ff
prompt={{ colors.accent_alt|nohash }}ff
placeholder={{ colors.text_dim|nohash }}ff
counter={{ colors.text_dim|nohash }}ff

[border]
width={{ metrics.border_width }}
radius={{ metrics.radius }}

[dmenu]
exit-immediately-if-empty=yes
