# Building for macOS

## Prerequisites

- macOS 10.15 or later
- Python 3.10+
- uv
- pnpm

## Build Instructions

1. Install dependencies:
```bash
uv sync --all-extras
pnpm install
```

2. Run the build script:
```bash
./packaging/build_mac.sh
```

3. The app bundle will be created at `packaging/dist/Tiny Wi-Fi Analyzer.app`

## Testing the App

```bash
open "packaging/dist/Tiny Wi-Fi Analyzer.app"
```

## Creating a DMG for Distribution

```bash
hdiutil create -volname "Tiny Wi-Fi Analyzer" -srcfolder "packaging/dist/Tiny Wi-Fi Analyzer.app" -ov -format UDZO "packaging/dist/TinyWiFiAnalyzer.dmg"
```

## Notes

- The app is built as a universal binary (supports both Apple Silicon and Intel Macs natively)
- Location Services permission is required for Wi-Fi scanning
- The app is not code-signed, so users will need to right-click and select "Open" the first time
