#!/bin/sh
# Build the three Lumen packages with dpkg-deb:
#
#   lumen-panel     the from-scratch panel (Python package + CSS)
#   lumen-launcher  fuzzel integration wrapper + generated launcher theme
#   lumen-desktop   session, compositor config, theme, defaults (+ dependencies)
#
# usage: packaging/build-debs.sh [output-dir]
#
# Reproducibility: all file mtimes are clamped to SOURCE_DATE_EPOCH (default:
# the last commit time) and ownership is forced to root, so identical sources
# give byte-identical .debs.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-"$ROOT/iso/config/packages.chroot"}
VERSION=${LUMEN_VERSION:-1.0.0}
MAINTAINER="Lumen Linux Maintainers <maintainers@lumen-linux.invalid>"
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" -c safe.directory="$ROOT" log -1 --format=%ct 2>/dev/null || date +%s)}
export SOURCE_DATE_EPOCH

command -v dpkg-deb >/dev/null || { echo "dpkg-deb not found (run inside Debian/Ubuntu or the build container)" >&2; exit 1; }

# Generated theme output must be current before it is packaged.
python3 "$ROOT/tools/gen-theme.py" --check ||
    { echo "theme output is stale: run 'make theme' and commit" >&2; exit 1; }

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT"

control() { # name arch depends recommends description
    mkdir -p "$STAGE/$1/DEBIAN"
    {
        echo "Package: $1"
        echo "Version: $VERSION"
        echo "Architecture: $2"
        echo "Maintainer: $MAINTAINER"
        echo "Section: x11"
        echo "Priority: optional"
        [ -n "$3" ] && echo "Depends: $3"
        [ -n "$4" ] && echo "Recommends: $4"
        echo "Description: $5"
    } >"$STAGE/$1/DEBIAN/control"
}

finish() { # name
    pkg=$STAGE/$1
    # normalise permissions: dirs 755, files 644, then re-mark executables
    find "$pkg" -type d -exec chmod 755 {} +
    find "$pkg" -type f -exec chmod 644 {} +
    for f in "$pkg"/usr/bin/* "$pkg"/DEBIAN/postinst "$pkg"/DEBIAN/prerm "$pkg"/DEBIAN/postrm; do
        [ -f "$f" ] && chmod 755 "$f"
    done
    # every file under /etc is a conffile, as debhelper would do
    if [ -d "$pkg/etc" ]; then
        (cd "$pkg" && find etc -type f | sed 's#^#/#' | sort) >"$pkg/DEBIAN/conffiles"
    fi
    find "$pkg" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
    dpkg-deb --root-owner-group -Zxz --build "$pkg" "$OUT/$1_${VERSION}_all.deb" >/dev/null
    echo "built $OUT/$1_${VERSION}_all.deb"
}

# ---------------------------------------------------------------- lumen-panel
P=$STAGE/lumen-panel
control lumen-panel all \
    "python3 (>= 3.11), python3-gi, gir1.2-gtk-3.0, gir1.2-gtklayershell-0.1, libgtk-layer-shell0, adwaita-icon-theme" \
    "wireplumber, network-manager-gnome, pavucontrol, swaylock" \
    "Lumen Linux desktop panel
 A Wayland panel written from scratch for Lumen Linux. It uses the
 wlr-layer-shell protocol (through gtk-layer-shell) to reserve screen space
 and offers launcher, clock, CPU, memory, network, volume, battery and
 session modules, configured with TOML and styled with CSS."
mkdir -p "$P/usr/bin" "$P/usr/lib/python3/dist-packages" "$P/usr/share/lumen-panel"
install -m 755 "$ROOT/components/lumen-panel/bin/lumen-panel" "$P/usr/bin/lumen-panel"
cp -r "$ROOT/components/lumen-panel/lumen_panel" "$P/usr/lib/python3/dist-packages/"
find "$P" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$ROOT/components/lumen-panel/data/panel.css" "$P/usr/share/lumen-panel/panel.css"
cp "$ROOT/packaging/scripts/lumen-panel.postinst" "$P/DEBIAN/postinst"
cp "$ROOT/packaging/scripts/lumen-panel.prerm" "$P/DEBIAN/prerm"
finish lumen-panel

# ------------------------------------------------------------- lumen-launcher
P=$STAGE/lumen-launcher
control lumen-launcher all \
    "fuzzel, procps" \
    "libnotify-bin, papirus-icon-theme, foot" \
    "Lumen Linux application launcher
 Integration layer around the fuzzel application launcher: a toggle wrapper,
 user/system configuration layering, and a launcher theme generated from the
 shared Lumen palette."
mkdir -p "$P/usr/bin" "$P/usr/share/lumen-launcher"
install -m 755 "$ROOT/components/lumen-launcher/bin/lumen-launcher" "$P/usr/bin/lumen-launcher"
cp "$ROOT/components/lumen-launcher/data/fuzzel.ini" "$P/usr/share/lumen-launcher/fuzzel.ini"
finish lumen-launcher

# --------------------------------------------------------------- lumen-desktop
P=$STAGE/lumen-desktop
control lumen-desktop all \
    "lumen-panel (= $VERSION), lumen-launcher (= $VERSION), labwc, greetd, cage, gtkgreet, foot, mako-notifier, swaybg, lxpolkit, dbus-user-session, libpam-systemd, xwayland, grim, slurp, wl-clipboard, libnotify-bin, papirus-icon-theme, adwaita-icon-theme, fonts-inter, fonts-jetbrains-mono" \
    "swaylock, brightnessctl, thunar, firefox-esr" \
    "Lumen Linux desktop session and defaults
 The labwc-based Wayland session for Lumen Linux: session script, compositor
 configuration, greetd login screen (gtkgreet in cage), GTK/labwc themes,
 wallpaper and default settings."
cp -a "$ROOT/components/lumen-desktop/." "$P/"
cp "$ROOT/packaging/scripts/lumen-desktop.postinst" "$P/DEBIAN/postinst"
cp "$ROOT/packaging/scripts/lumen-desktop.postrm" "$P/DEBIAN/postrm"
finish lumen-desktop
