# Lumen: labwc window-decoration theme (Openbox-3 theme format)

border.width: {{ metrics.border_width }}
padding.width: 6
padding.height: 5
window.titlebar.padding.width: 8
window.titlebar.padding.height: 4
window.handle.width: 0

window.active.border.color: {{ colors.accent }}
window.inactive.border.color: {{ colors.border }}

window.active.title.bg.color: {{ colors.surface }}
window.inactive.title.bg.color: {{ colors.bg }}

window.active.label.text.color: {{ colors.text }}
window.inactive.label.text.color: {{ colors.text_dim }}
window.label.text.justify: left

window.active.button.unpressed.image.color: {{ colors.text }}
window.inactive.button.unpressed.image.color: {{ colors.text_dim }}
window.active.button.hover.image.color: {{ colors.accent }}
window.inactive.button.hover.image.color: {{ colors.accent }}

# Client-menu / root-menu
menu.overlap.x: 0
menu.overlap.y: 0
menu.width.min: 140
menu.width.max: 320
menu.items.padding.x: 12
menu.items.padding.y: 7
menu.items.bg.color: {{ colors.surface }}
menu.items.text.color: {{ colors.text }}
menu.items.active.bg.color: {{ colors.surface_alt }}
menu.items.active.text.color: {{ colors.accent }}
menu.separator.color: {{ colors.border }}
menu.border.width: 1
menu.border.color: {{ colors.border }}

# Alt-Tab switcher and on-screen displays
osd.bg.color: {{ colors.surface }}
osd.border.color: {{ colors.accent }}
osd.border.width: {{ metrics.border_width }}
osd.label.text.color: {{ colors.text }}
