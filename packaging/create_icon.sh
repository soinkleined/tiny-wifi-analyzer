#!/bin/bash
set -e

echo "Creating Wi-Fi icon..."

cd "$(dirname "$0")/assets"

# Create iconset directory
mkdir -p wifi-icon.iconset

# Generate PNG files at various sizes using sips
for size in 16 32 64 128 256 512; do
  sips -z $size $size wifi-icon.svg --out wifi-icon.iconset/icon_${size}x${size}.png
done

# Create @2x versions
cp wifi-icon.iconset/icon_32x32.png wifi-icon.iconset/icon_16x16@2x.png
cp wifi-icon.iconset/icon_64x64.png wifi-icon.iconset/icon_32x32@2x.png
cp wifi-icon.iconset/icon_256x256.png wifi-icon.iconset/icon_128x128@2x.png
cp wifi-icon.iconset/icon_512x512.png wifi-icon.iconset/icon_256x256@2x.png

# Convert to ICNS
iconutil -c icns wifi-icon.iconset -o wifi-icon.icns

# Clean up
rm -rf wifi-icon.iconset

echo "Icon created: assets/wifi-icon.icns"
