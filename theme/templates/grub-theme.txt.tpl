# UEFI boot menu (GRUB) theme. Replaces live-build's grub-pc/live-theme/theme.txt;
# the splash already carries the title, so title-text is empty.
desktop-image: "../splash.png"
title-text: ""
message-font: "Unifont Regular 16"
message-color: "{{ colors.text_dim }}"
terminal-font: "Unifont Regular 16"

+ label {
        top = 100%-50
        left = 0
        width = 100%
        height = 20
        text = "@KEYMAP_SHORT@"
        align = "center"
        color = "{{ colors.text_dim }}"
        font = "Unifont Regular 16"
}

+ boot_menu {
        left = 10%
        width = 80%
        top = 52%
        height = 48%-80
        item_color = "{{ colors.text }}"
        item_font = "Unifont Regular 16"
        selected_item_color = "{{ colors.accent }}"
        selected_item_font = "Unifont Regular 16"
        item_height = 16
        item_padding = 0
        item_spacing = 4
        icon_width = 0
        icon_height = 0
        item_icon_space = 0
}

+ progress_bar {
        id = "__timeout__"
        left = 15%
        top = 100%-80
        height = 16
        width = 70%
        font = "Unifont Regular 16"
        text_color = "{{ colors.bg }}"
        fg_color = "{{ colors.accent }}"
        bg_color = "{{ colors.surface_alt }}"
        border_color = "{{ colors.border }}"
        text = "@TIMEOUT_NOTIFICATION_LONG@"
}
