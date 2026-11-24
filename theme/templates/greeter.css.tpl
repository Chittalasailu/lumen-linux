/* gtkgreet, the Lumen login screen. Widgets come from the Lumen GTK theme;
 * this only lays the card over the wallpaper. Palette: {{ name }} */

window {
  background-color: {{ colors.bg }};
  background-image: url("file:///usr/share/backgrounds/lumen/lumen-dusk.png");
  background-size: cover;
  background-position: center;
  font-family: "{{ fonts.ui_family }}", sans-serif;
}

box#body {
  background-color: alpha({{ colors.surface }}, 0.92);
  border: {{ metrics.border_width }}px solid {{ colors.accent }};
  border-radius: {{ metrics.radius }}px;
  padding: 36px 44px;
}

box#body label {
  color: {{ colors.text }};
  font-size: 12pt;
}

box#body button.suggested-action label {
  color: {{ colors.bg }};
}

box#body entry {
  min-width: 260px;
  min-height: 34px;
  border-radius: {{ metrics.radius }}px;
}

box#body button {
  min-height: 34px;
  border-radius: {{ metrics.radius }}px;
  padding: 0 18px;
}
