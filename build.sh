#!/bin/bash
# Build the Lumen Linux ISO. Must run as root on Debian/Ubuntu with live-build
# installed. Easiest way: `make iso`, which does this inside a privileged
# Debian 13 container (see Dockerfile.build).
#
# Output: dist/lumen-linux-<version>-amd64.iso (+ .sha256)
#
# Environment:
#   LUMEN_VERSION      default 1.0.0
#   LUMEN_SNAPSHOT     pin packages to snapshot.debian.org (see iso/auto/config)
#   LUMEN_MIRROR       alternative Debian mirror
#   SOURCE_DATE_EPOCH  timestamp for packaged files (default: last commit time)
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT"

if [ "$(id -u)" -ne 0 ]; then
    echo "build.sh must run as root (live-build needs chroot/mount). Use 'make iso'." >&2
    exit 1
fi
for tool in lb dpkg-deb python3; do
    command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done

export LUMEN_VERSION=${LUMEN_VERSION:-1.0.0}
# safe.directory: the build runs as root (sudo or the container) on a checkout owned by
# another user, which git otherwise refuses with "dubious ownership".
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git -c safe.directory="$ROOT" log -1 --format=%ct 2>/dev/null || date +%s)}

WORK="$ROOT/build/live"
DIST="$ROOT/dist"

echo ">> [1/4] regenerating and checking themed files"
python3 tools/gen-theme.py
python3 tools/gen-theme.py --check

echo ">> [2/4] running unit tests"
(cd components/lumen-panel && python3 -m unittest discover -s tests)

echo ">> [3/4] building Lumen .deb packages"
rm -rf "$WORK"
mkdir -p "$WORK" "$DIST"
cp -a iso/. "$WORK/"
packaging/build-debs.sh "$WORK/config/packages.chroot"

echo ">> [4/4] building the live image (this takes a while)"
cd "$WORK"
lb config
lb build

iso=$(ls -1 ./*.iso | head -n1)
out="$DIST/lumen-linux-${LUMEN_VERSION}-amd64.iso"
mv "$iso" "$out"
(cd "$DIST" && sha256sum "$(basename "$out")" > "$(basename "$out").sha256")
echo ">> done: $out"
ls -lh "$out"
