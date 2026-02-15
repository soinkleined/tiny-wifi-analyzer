<p align="center">
  <img src="packaging/assets/wifi-icon.svg" alt="Tiny Wi-Fi Analyzer Logo" width="128">
</p>

# Tiny Wi-Fi Analyzer

<p align="center">
  Simple, open-source Wi-Fi channel and strength analyzer for macOS.<br>
  Made with PyObjC, pywebview, ApexCharts, and PyInstaller.
</p>

<p align="center">
  Forked from <a href="https://github.com/nolze/tiny-wifi-analyzer">nolze/tiny-wifi-analyzer</a>
</p>

### Light Mode
<p align="center">
  <img src="img/twa_light.png" alt="Tiny Wi-Fi Analyzer - Light Mode" width="800">
</p>

### Dark Mode
<p align="center">
  <img src="img/twa_dark.png" alt="Tiny Wi-Fi Analyzer - Dark Mode" width="800">
</p>

## Features

* Real-time updates of Wi-Fi networks
* Support for 2.4 GHz, 5 GHz, and 6 GHz Wi‑Fi bands
* Highlight the chart for the selected SSID
* Settings menu with persistent configuration:
  - Debug mode toggle
  - Dark mode (auto, light, or dark)
  - Side-by-side or stacked layout
  - CSV streaming for continuous data logging
  - Adjustable refresh interval (0.1-10 seconds)
* Export charts as images (PNG or SVG)
* Export chart data as a CSV file
* Full-screen mode for individual band charts

## Requirements

* macOS 10.15 (Catalina) or later
* **macOS 14 Sonoma and later**: Location Services permission is required to display Wi-Fi SSIDs

## Download

[Visit the latest release](https://github.com/soinkleined/tiny-wifi-analyzer/releases/latest/)

### Installation Notes

Because the application is not code-signed, you will need to follow these steps to run it:

1. **Double-click the app** - You'll see a warning that the app cannot be opened:

   <p align="center">
     <img src="img/not_opened_warning.png" alt="Cannot Open Warning" width="300">
     <img src="img/no_opened_warning2.png" alt="Cannot Open Warning Alternative" width="300">
   </p>

2. **Open System Settings** - Go to **System Settings > Privacy & Security** and scroll down to find the security warning:

   <p align="center">
     <img src="img/open_anyway_preferences.png" alt="Open Anyway in System Settings" width="600">
   </p>

3. **Click "Open Anyway"** and enter your password if prompted:

   <p align="center">
     <img src="img/privacy_security_password.png" alt="Enter Password" width="400">
   </p>

4. **Confirm** - Click "Open" in the final confirmation dialog:

   <p align="center">
     <img src="img/open_anyway.png" alt="Final Confirmation" width="300">
   </p>

### Location Services Permission (macOS 14+)

On macOS 14 Sonoma and later, you must grant Location Services permission for the app to display Wi-Fi SSIDs:

1. **Grant permission on first launch** - The app will display this prompt:

   <p align="center">
     <img src="img/use_location_services_prompt.png" alt="Location Services Permission Prompt" width="400">
   </p>

2. **Enable manually if needed** - Go to **System Settings > Privacy & Security > Location Services**, find "Tiny Wi-Fi Analyzer" and enable it:

   <p align="center">
     <img src="img/use_location_services_toggle.png" alt="Location Services Settings Toggle" width="600">
   </p>

3. **Restart the app** after granting permission

## Todos

* [x] Bundle scripts with Parcel
* [x] Prepare GitHub Pages
* [x] Settings menu with persistent configuration
* [x] CSV streaming for data logging
* [x] Full-screen mode for charts
* [x] PyInstaller build script for macOS
* [ ] Code signing for easier installation
* [ ] Support for additional export formats

## Develop

```sh
git clone https://github.com/soinkleined/tiny-wifi-analyzer
cd tiny-wifi-analyzer
uv sync --all-extras
pnpm install

# Run in development mode
uv run python -m tiny_wifi_analyzer

# Frontend development
pnpm run watch # or pnpm run build
```

## Building for Distribution

### macOS App Bundle (Universal Binary)

```sh
# Build the app (supports both Apple Silicon and Intel Macs)
./packaging/build_mac.sh

# The app will be created at: packaging/dist/Tiny Wi-Fi Analyzer.app

# Create a DMG for distribution
hdiutil create -volname "Tiny Wi-Fi Analyzer" -srcfolder "packaging/dist/Tiny Wi-Fi Analyzer.app" -ov -format UDZO "packaging/dist/TinyWiFiAnalyzer.dmg"
```

See [packaging/BUILD.md](packaging/BUILD.md) for detailed build instructions.

### Regenerating the Icon

If you need to regenerate the app icon from the SVG source:

```sh
./create_icon.sh
```

## Configuration

The app looks for a configuration file at `~/.config/tiny-wifi-analyzer/config.json`. All settings are automatically saved when changed through the UI.

Example configuration:
```json
{
  "scan_interval_ms": 3000,
  "update_interval_s": 0.3,
  "debug": false,
  "log_level": "WARNING",
  "dark_mode": "auto",
  "show_24ghz": true,
  "show_5ghz": true,
  "show_6ghz": true,
  "layout": "stacked",
  "window_width": 1200,
  "window_height": 800
}
```

Configuration options:
- `scan_interval_ms`: How often to scan for Wi-Fi networks (milliseconds)
- `update_interval_s`: How often to update the charts (seconds, adjustable via Settings menu)
- `debug`: Enable debug logging (toggle via Settings menu)
- `dark_mode`: "auto" (follows system), "light", or "dark" (toggle via Settings menu)
- `show_24ghz`, `show_5ghz`, `show_6ghz`: Enable/disable specific Wi-Fi bands
- `layout`: "stacked" or "side-by-side" (toggle via Settings menu)
- `window_width`, `window_height`: Window size (automatically saved)

See `config.example.json` for a template.

### CSV Streaming

Enable "Stream CSV" in the Settings menu to continuously log Wi-Fi data to a timestamped CSV file in your home directory (`~/wifi_stream_YYYYMMDD_HHMMSS.csv`). The CSV includes:
- Timestamp
- SSID
- BSSID (MAC address)
- Channel
- Signal strength (RSSI)
- Band (2.4GHz, 5GHz, or 6GHz)

## License

```
Copyright 2020 nolze
Copyright 2026 David Klein (soinkleined)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
