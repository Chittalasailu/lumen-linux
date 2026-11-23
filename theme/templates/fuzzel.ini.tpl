[main]
# Lumen launcher: fuzzel (a wlr-layer-shell application launcher) themed from the
# shared palette. Colours are RRGGBBAA, no '#'.
font={{ fonts.ui_family }}:size={{ fonts.ui_size }}
prompt="  "
icon-theme=Papirus-Dark
icons-enabled=yes
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
