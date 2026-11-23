/* Lumen GTK3 theme: Adwaita's dark variant with the Lumen palette on top. */
@import url("resource:///org/gtk/libgtk/theme/Adwaita/gtk-contained-dark.css");

@define-color theme_bg_color {{ colors.surface }};
@define-color theme_base_color {{ colors.bg }};
@define-color theme_fg_color {{ colors.text }};
@define-color theme_text_color {{ colors.text }};
@define-color theme_selected_bg_color {{ colors.accent }};
@define-color theme_selected_fg_color {{ colors.bg }};
@define-color theme_unfocused_bg_color {{ colors.surface }};
@define-color theme_unfocused_base_color {{ colors.bg }};
@define-color theme_unfocused_fg_color {{ colors.text_dim }};
@define-color theme_unfocused_selected_bg_color {{ colors.surface_alt }};
@define-color insensitive_fg_color {{ colors.text_dim }};
@define-color borders {{ colors.border }};
@define-color unfocused_borders {{ colors.border }};
@define-color warning_color {{ colors.warn }};
@define-color error_color {{ colors.danger }};
@define-color success_color {{ colors.ok }};

headerbar, .titlebar { background-image: none; background-color: {{ colors.surface }}; }
selection, *:selected { background-color: {{ colors.accent }}; color: {{ colors.bg }}; }
button.suggested-action { background-image: none; background-color: {{ colors.accent }}; color: {{ colors.bg }}; }
*:focus { outline-color: {{ colors.accent_alt }}; }
