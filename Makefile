spec:
	uv run pyi-makespec tiny_wifi_analyzer/__main__.py \
		--name 'Tiny Wi-Fi Analyzer' \
		--osx-bundle-identifier 'com.github.soinkleined.tiny-wifi-analyzer' \
		--target-architecture universal2 \
		--onefile \
		--noconsole \
		--add-data 'tiny_wifi_analyzer/view:view'

build:
	pnpm run build
	uv run pyinstaller packaging/build_mac.spec \
		--distpath build/dist \
		--noconfirm \
		--clean

.PHONY: build
