<#
.SYNOPSIS
  Boot the Lumen Linux ISO in QEMU on Windows.
.EXAMPLE
  .\run-qemu.ps1 -Iso .\dist\lumen-linux-1.0.0-amd64.iso
.EXAMPLE
  .\run-qemu.ps1 -Iso .\dist\lumen-linux-1.0.0-amd64.iso -Uefi
.NOTES
  Install QEMU for Windows (https://www.qemu.org/download/#windows) and make sure
  qemu-system-x86_64.exe is on PATH. -Accel whpx needs the "Windows Hypervisor
  Platform" optional feature; use -Accel tcg if it is not enabled (slower).
  The desktop needs a few minutes to appear in software emulation.
#>
param(
    [string]$Iso = ".\dist\lumen-linux-1.0.0-amd64.iso",
    [int]$MemMiB = 4096,
    [int]$Cpus = 4,
    [ValidateSet("whpx", "tcg")][string]$Accel = "whpx",
    [switch]$Uefi
)

if (-not (Test-Path $Iso)) { throw "ISO not found: $Iso" }
if (-not (Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue)) {
    throw "qemu-system-x86_64 not found on PATH"
}

$firmware = @()
if ($Uefi) {
    # edk2 firmware ships with QEMU for Windows. Copy it to a temp dir and use a writable
    # copy of the variable store. (QEMU splits arguments at spaces, so the path must not
    # contain any, which is why the files are not used from "Program Files".)
    $share = Join-Path (Split-Path (Get-Command qemu-system-x86_64).Source) "share"
    $tmp = Join-Path $env:TEMP "lumen-uefi"
    New-Item -ItemType Directory -Force $tmp | Out-Null
    Copy-Item (Join-Path $share "edk2-x86_64-code.fd") (Join-Path $tmp "code.fd") -Force
    Copy-Item (Join-Path $share "edk2-i386-vars.fd") (Join-Path $tmp "vars.fd") -Force
    $t = $tmp -replace '\\', '/'
    $firmware = @("-drive", "if=pflash,format=raw,unit=0,readonly=on,file=$t/code.fd",
                  "-drive", "if=pflash,format=raw,unit=1,file=$t/vars.fd")
}

& qemu-system-x86_64 `
    @firmware `
    -accel $Accel `
    -m $MemMiB -smp $Cpus `
    -cdrom $Iso -boot d `
    -device virtio-vga -display gtk `
    -device intel-hda -device hda-duplex `
    -nic user,model=virtio-net-pci `
    -device qemu-xhci -device usb-tablet
