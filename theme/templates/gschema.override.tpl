# Under Wayland GTK takes its theme, icons and fonts from GSettings
# (org.gnome.desktop.interface), not from gtk-3.0/settings.ini. These are the
# distribution defaults; libglib's dpkg trigger compiles them on install.
[org.gnome.desktop.interface]
gtk-theme='Lumen'
icon-theme='Papirus-Dark'
cursor-theme='Adwaita'
cursor-size=24
font-name='{{ fonts.ui_family }} {{ fonts.ui_size }}'
document-font-name='{{ fonts.ui_family }} {{ fonts.ui_size }}'
monospace-font-name='{{ fonts.mono_family }} {{ fonts.mono_size }}'
color-scheme='prefer-dark'
