.PHONY: help theme check test debs docker-image iso qemu clean

IMAGE   ?= lumen-builder
VERSION ?= 1.0.0
ISO     ?= dist/lumen-linux-$(VERSION)-amd64.iso
# The image is amd64 and its boot loaders (grub-pc, syslinux) only exist for x86,
# so the build container is amd64 too. On Apple Silicon Docker runs it emulated.
PLATFORM ?= linux/amd64
# live-build's chroot needs a real Linux filesystem (device nodes, ownership).
# A bind mount from a macOS or Windows host is not one, so build/ lives in a volume.
BUILD_VOLUME ?= lumen-build
SOURCE_DATE_EPOCH ?= $(shell git log -1 --format=%ct 2>/dev/null)

help:
	@echo "make theme         regenerate themed files from theme/palette.toml"
	@echo "make test          unit tests (panel logic) + theme freshness + script syntax"
	@echo "make iso           build the bootable ISO inside a privileged Debian 13 container"
	@echo "make qemu          boot dist/lumen-linux-$(VERSION)-amd64.iso in QEMU"
	@echo "make clean         remove build/ and dist/"

theme:
	python3 tools/gen-theme.py

check: test

test:
	python3 tools/gen-theme.py --check
	cd components/lumen-panel && python3 -m unittest discover -s tests -v
	for f in build.sh run-qemu.sh packaging/build-debs.sh components/*/bin/* components/lumen-desktop/usr/bin/* iso/auto/*; do sh -n $$f || exit 1; done
	python3 -c "import xml.dom.minidom as m; [m.parse(f) for f in ['components/lumen-desktop/etc/lumen/xdg/labwc/rc.xml','components/lumen-desktop/etc/lumen/xdg/labwc/menu.xml']]"

docker-image:
	docker build --platform $(PLATFORM) -f Dockerfile.build -t $(IMAGE) .

# --privileged is required: live-build uses debootstrap, chroot and loop/bind mounts.
iso: docker-image
	docker run --rm --privileged --platform $(PLATFORM) \
		-e LUMEN_VERSION=$(VERSION) -e LUMEN_SNAPSHOT -e LUMEN_MIRROR \
		-e SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
		-v "$(CURDIR)":/work -v $(BUILD_VOLUME):/work/build $(IMAGE) ./build.sh

qemu:
	./run-qemu.sh $(ISO)

clean:
	rm -rf build dist
	-docker volume rm $(BUILD_VOLUME) 2>/dev/null
