/* Lumen additions on top of the recoloured Adwaita dark above. */

/* Links and focus rings use the secondary accent so they never read as a selection. */
*:link, *:link:visited, button:link > label, button:visited > label,
button:link > label:visited, button:visited > label:visited { color: {{ colors.accent_alt }}; }
*:link:hover, button:link > label:hover, button:visited > label:hover { color: {{ colors.text }}; }

/* Suggested and destructive buttons: flat palette colours, dark text on the bright fills. */
button.suggested-action, button.suggested-action:hover {
  background-image: none;
  background-color: {{ colors.accent }};
  border-color: {{ colors.accent }};
  color: {{ colors.bg }};
  text-shadow: none;
  -gtk-icon-shadow: none;
}
button.destructive-action, button.destructive-action:hover {
  background-image: none;
  background-color: {{ colors.danger }};
  border-color: {{ colors.danger }};
  color: {{ colors.bg }};
  text-shadow: none;
  -gtk-icon-shadow: none;
}
