font={{ fonts.ui_family }} {{ fonts.ui_size }}
background-color={{ colors.surface }}
text-color={{ colors.text }}
border-color={{ colors.accent }}
border-size={{ metrics.border_width }}
border-radius={{ metrics.radius }}
padding=12
margin={{ metrics.gap }}
width=360
default-timeout=6000
layer=overlay
anchor=top-right
icons=1
max-icon-size=40

[urgency=low]
border-color={{ colors.border }}

[urgency=critical]
border-color={{ colors.danger }}
default-timeout=0
