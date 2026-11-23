<#
.SYNOPSIS
  Boot the Lumen Linux ISO in QEMU on Windows.
.EXAMPLE
  .\run-qemu.ps1 -Iso .\dist\lumen-linux-1.0.0-amd64.iso
.NOTES
  Install QEMU for Windows (https://www.qemu.org/download/#windows) and make sure
  qemu-system-x86_64.exe is on PATH. -Accel whpx needs the "Windows Hypervisor
  Platform" optional feature; use -Accel tcg if it is not enabled (slower).
#>
param(
    [string]$Iso = ".\dist\lumen-linux-1.0.0-amd64.iso",
    [int]$MemMiB = 4096,
    [int]$Cpus = 4,
    [ValidateSet("whpx", "tcg")][string]$Accel = "whpx"
)

if (-not (Test-Path $Iso)) { throw "ISO not found: $Iso" }
if (-not (Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue)) {
    throw "qemu-system-x86_64 not found on PATH"
}

& qemu-system-x86_64 `
    -accel $Accel `
    -m $MemMiB -smp $Cpus `
    -cdrom $Iso -boot d `
    -device virtio-vga,xres=1280,yres=720 -display gtk `
    -device intel-hda -device hda-duplex `
    -nic user,model=virtio-net-pci `
    -device qemu-xhci -device usb-tablet
