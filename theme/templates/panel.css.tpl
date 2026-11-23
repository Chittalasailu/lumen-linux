/* lumen-panel stylesheet. Palette: {{ name }} */

* {
  font-family: "{{ fonts.ui_family }}", sans-serif;
  font-size: {{ fonts.ui_size }}pt;
  -gtk-icon-style: symbolic;
}

window.lumen-panel {
  background-color: {{ colors.surface }};
  color: {{ colors.text }};
}

window.lumen-panel.top    { border-bottom: 1px solid {{ colors.border }}; }
window.lumen-panel.bottom { border-top: 1px solid {{ colors.border }}; }

.lumen-panel .section { padding: 0 {{ metrics.gap }}px; }

/* Every module is a flat "pill" */
.lumen-panel .module,
.lumen-panel button.module {
  background: transparent;
  background-image: none;
  color: {{ colors.text }};
  border: none;
  box-shadow: none;
  border-radius: {{ metrics.radius }}px;
  padding: 2px 10px;
  margin: 4px 2px;
  min-height: 0;
}

.lumen-panel button.module:hover   { background-color: {{ colors.surface_alt }}; }
.lumen-panel button.module:active  { background-color: {{ colors.border }}; }

.lumen-panel .module label { color: {{ colors.text }}; }
.lumen-panel .module .dim  { color: {{ colors.text_dim }}; }

/* Launcher button: the primary action */
.lumen-panel button.launcher {
  background-color: {{ colors.accent }};
  color: {{ colors.bg }};
  font-weight: 700;
  padding: 2px 14px;
}
.lumen-panel button.launcher label { color: {{ colors.bg }}; }
.lumen-panel button.launcher:hover { background-color: {{ colors.accent_alt }}; }

.lumen-panel .clock { font-weight: 600; }

/* State colours driven by the modules */
.lumen-panel .module.warn     label,
.lumen-panel .module.warn     image { color: {{ colors.warn }}; }
.lumen-panel .module.critical label,
.lumen-panel .module.critical image { color: {{ colors.danger }}; }
.lumen-panel .module.charging label,
.lumen-panel .module.charging image { color: {{ colors.ok }}; }
.lumen-panel .module.muted    label,
.lumen-panel .module.muted    image { color: {{ colors.text_dim }}; }

/* Popovers (calendar, power menu) */
popover.lumen-popover,
popover.lumen-popover > * {
  background-color: {{ colors.surface }};
  color: {{ colors.text }};
}
popover.lumen-popover {
  border: 1px solid {{ colors.border }};
  border-radius: {{ metrics.radius }}px;
  padding: 6px;
}
popover.lumen-popover button {
  background: transparent;
  background-image: none;
  border: none;
  box-shadow: none;
  color: {{ colors.text }};
  border-radius: 6px;
  padding: 6px 12px;
}
popover.lumen-popover button:hover { background-color: {{ colors.surface_alt }}; }
popover.lumen-popover button.destructive:hover { background-color: {{ colors.danger }}; color: {{ colors.bg }}; }
popover.lumen-popover calendar {
  background-color: {{ colors.surface }};
  color: {{ colors.text }};
  border: none;
}
popover.lumen-popover calendar:selected {
  background-color: {{ colors.accent }};
  color: {{ colors.bg }};
  border-radius: 6px;
}
popover.lumen-popover calendar.header,
popover.lumen-popover calendar.button { color: {{ colors.accent_alt }}; }
popover.lumen-popover .date-title { font-weight: 700; color: {{ colors.accent }}; padding: 4px 8px 8px 8px; }
