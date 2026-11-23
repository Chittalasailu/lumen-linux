#!/bin/sh
# Boot the Lumen Linux ISO in QEMU (Linux/macOS).
#
#   ./run-qemu.sh [path/to/lumen.iso]
#
# Environment:
#   UEFI=1   boot through OVMF (UEFI) instead of BIOS
#   GL=1     enable virgl 3D acceleration (needs QEMU built with OpenGL)
#   MEM=4096 RAM in MiB     SMP=4 virtual CPUs
set -eu

ISO=${1:-dist/lumen-linux-1.0.0-amd64.iso}
MEM=${MEM:-4096}
SMP=${SMP:-4}

[ -f "$ISO" ] || { echo "ISO not found: $ISO (build it with 'make iso')" >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null || { echo "qemu-system-x86_64 not installed" >&2; exit 1; }

set -- -m "$MEM" -smp "$SMP" -cdrom "$ISO" -boot d \
    -device intel-hda -device hda-duplex \
    -nic user,model=virtio-net-pci \
    -device qemu-xhci -device usb-tablet

# Hardware virtualisation when the host offers it; TCG (slow) otherwise.
if [ -w /dev/kvm ]; then
    set -- -enable-kvm -cpu host "$@"
fi

if [ "${GL:-0}" = 1 ]; then
    set -- "$@" -device virtio-vga-gl,xres=1280,yres=720 -display gtk,gl=on
else
    # Software path: the session falls back to wlroots' pixman renderer.
    set -- "$@" -device virtio-vga,xres=1280,yres=720 -display gtk
fi

if [ "${UEFI:-0}" = 1 ]; then
    for fw in /usr/share/OVMF/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/edk2/ovmf/OVMF_CODE.fd; do
        [ -f "$fw" ] && { set -- -bios "$fw" "$@"; break; }
    done
fi

exec qemu-system-x86_64 "$@"
