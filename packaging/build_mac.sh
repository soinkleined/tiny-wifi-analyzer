#!/bin/bash
set -e

echo "Building Tiny Wi-Fi Analyzer for macOS (Apple Silicon)..."

# Ensure we're in the project directory
cd "$(dirname "$0")/.."

# Build the frontend
echo "Building frontend..."
pnpm run build

# Install dependencies if not already installed
if [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    uv sync --all-extras
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf packaging/build packaging/dist

# Build the app
echo "Building macOS app bundle..."
uv run pyinstaller packaging/build_mac.spec --distpath packaging/dist --workpath packaging/build

echo ""
echo "Build complete!"
echo "App bundle created at: packaging/dist/Tiny Wi-Fi Analyzer.app"
echo ""
echo "To test the app:"
echo "  open 'packaging/dist/Tiny Wi-Fi Analyzer.app'"
echo ""
echo "To create a DMG for distribution:"
echo "  hdiutil create -volname 'Tiny Wi-Fi Analyzer' -srcfolder 'packaging/dist/Tiny Wi-Fi Analyzer.app' -ov -format UDZO 'packaging/dist/TinyWiFiAnalyzer.dmg'"
