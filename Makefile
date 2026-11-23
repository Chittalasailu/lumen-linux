.PHONY: help theme check test debs docker-image iso qemu clean

IMAGE   ?= lumen-builder
VERSION ?= 1.0.0
ISO     ?= dist/lumen-linux-$(VERSION)-amd64.iso

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
	docker build -f Dockerfile.build -t $(IMAGE) .

# --privileged is required: live-build uses debootstrap, chroot and loop/bind mounts.
iso: docker-image
	docker run --rm --privileged \
		-e LUMEN_VERSION=$(VERSION) -e LUMEN_SNAPSHOT -e LUMEN_MIRROR \
		-v "$(CURDIR)":/work $(IMAGE) ./build.sh

qemu:
	./run-qemu.sh $(ISO)

clean:
	rm -rf build dist
