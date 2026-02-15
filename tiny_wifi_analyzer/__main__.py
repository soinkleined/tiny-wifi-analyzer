import csv
import json
import logging
import os
import os.path
import queue
import sys
import threading
from datetime import datetime
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import AppKit
import CoreLocation
import CoreWLAN
import Foundation
import webview

# NOTE: https://github.com/r0x0r/pywebview/issues/496
from objc import nil, registerMetaDataForSelector  # noqa: F401

from tiny_wifi_analyzer.config import Config
from tiny_wifi_analyzer.series import (
    CHANNEL_BAND_24,
    CHANNEL_BAND_5,
    CHANNEL_BAND_6,
    CHANNEL_NUMBER_MAX_24,
    CHANNEL_NUMBER_MAX_5,
    CHANNEL_NUMBER_MAX_6,
    to_series as series_from_networks,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

webview.settings["ALLOW_DOWNLOADS"] = True

LOCATION_CHECK_ITERATIONS = 100
LOCATION_CHECK_SLEEP_S = 0.01


class PyChannel:
    """Wrapper for CoreWLAN channel information."""

    def __init__(self, channel: Any) -> None:
        self.channel_band: int = channel.channelBand()
        self.channel_number: int = channel.channelNumber()
        self.channel_width: int = channel.channelWidth()

    def __repr__(self) -> str:
        return (
            f"<CWChannel> [channel_band={self.channel_band}, "
            f"channel_number={self.channel_number}, "
            f"channel_width={self.channel_width}]"
        )


class PyNetwork:
    """Wrapper for CoreWLAN network information."""

    def __init__(self, network: Any) -> None:
        self.ssid: Optional[str] = network.ssid()
        self.bssid: str = network.bssid()
        self.rssi: int = network.rssiValue()
        self.channel: PyChannel = PyChannel(network.wlanChannel())
        self.ibss: bool = network.ibss()

    def __repr__(self) -> str:
        return (
            f"<CWNetwork> [ssid={self.ssid}, bssid={self.bssid}, "
            f"rssi={self.rssi}, channel={self.channel}, ibss={self.ibss}]"
        )


def scan() -> Tuple[str, List[PyNetwork]]:
    client = CoreWLAN.CWWiFiClient.alloc().init()
    iface_default = client.interface()
    name = iface_default.interfaceName()

    nws, err = iface_default.scanForNetworksWithName_error_(None, None)
    nws = [PyNetwork(nw) for nw in nws]

    return name, nws


def get_supported_bands() -> Dict[str, bool]:
    client = CoreWLAN.CWWiFiClient.alloc().init()
    iface_default = client.interface()
    channels = iface_default.supportedWLANChannels()

    supported_bands = {"24": False, "5": False, "6": False}

    for channel in channels:
        band = channel.channelBand()
        if band == CHANNEL_BAND_24:
            supported_bands["24"] = True
        elif band == CHANNEL_BAND_5:
            supported_bands["5"] = True
        elif band == CHANNEL_BAND_6:
            supported_bands["6"] = True

    return supported_bands


class WifiAnalyzer:
    """Main analyzer class that manages scanning and UI updates."""

    def __init__(self, config: Config) -> None:
        self.config: Config = config
        self.update_queue: queue.Queue[Tuple[str, List[PyNetwork]]] = queue.Queue()
        self.is_closing: threading.Event = threading.Event()
        self.scanner_thread: Optional[threading.Thread] = None
        self.csv_streaming: bool = False
        self.csv_file: Optional[Any] = None
        self.csv_writer: Optional[Any] = None

    def start_scanner(self) -> threading.Thread:
        """Start the background scanner thread."""
        def loop() -> None:
            while not self.is_closing.is_set():
                try:
                    name, nws = scan()
                    self.update_queue.put((name, nws))
                except Exception as e:
                    logger.warning("scan failed: %s", e)
                sleep(max(0.05, self.config.scan_interval_ms / 1000.0))

        t = threading.Thread(target=loop, name="scanner", daemon=True)
        t.start()
        return t

    def to_series(self, nws: List[PyNetwork]) -> List[Dict[str, Any]]:
        """Convert networks to chart series data."""
        return series_from_networks(nws)

    def update(self, window: Any, supported_bands: Dict[str, bool]) -> None:
        """Update the UI with latest scan results."""
        if self.is_closing.is_set():
            return

        try:
            name, nws = self.update_queue.get_nowait()
            while True:
                try:
                    name, nws = self.update_queue.get_nowait()
                except queue.Empty:
                    break

            window.set_title(name)

            # Write to CSV if streaming is enabled
            if self.csv_streaming and self.csv_writer:
                timestamp = datetime.now().isoformat()
                for nw in nws:
                    if nw.channel.channel_band == CHANNEL_BAND_24:
                        band = "2.4GHz"
                    elif nw.channel.channel_band == CHANNEL_BAND_5:
                        band = "5GHz"
                    else:
                        band = "6GHz"
                    
                    self.csv_writer.writerow([
                        timestamp,
                        nw.ssid or "N/A",
                        nw.bssid,
                        nw.channel.channel_number,
                        nw.rssi,
                        band
                    ])
                self.csv_file.flush()

            if supported_bands["24"]:
                nws24 = [
                    x for x in nws
                    if x.channel.channel_band == CHANNEL_BAND_24
                ]
                nws24 = sorted(nws24, key=lambda x: x.channel.channel_number)
                series24 = self.to_series(nws24)
                series_json24 = json.dumps(series24)
                window.evaluate_js(
                    f"window.updateChart('24',{series_json24})"
                )

            if supported_bands["5"]:
                nws5 = [
                    x for x in nws
                    if x.channel.channel_band == CHANNEL_BAND_5
                ]
                nws5 = sorted(nws5, key=lambda x: x.channel.channel_number)
                series5 = self.to_series(nws5)
                series_json5 = json.dumps(series5)
                window.evaluate_js(f"window.updateChart('5',{series_json5})")

            if supported_bands["6"]:
                nws6 = [
                    x for x in nws
                    if x.channel.channel_band == CHANNEL_BAND_6
                ]
                nws6 = sorted(nws6, key=lambda x: x.channel.channel_number)
                series6 = self.to_series(nws6)
                series_json6 = json.dumps(series6)
                window.evaluate_js(f"window.updateChart('6',{series_json6})")

        except queue.Empty:
            pass

    def setup_client(self, window: Any) -> None:
        """Initialize the client UI with configuration."""
        supported_bands = get_supported_bands()
        # Filter bands based on config
        enabled_bands = {
            "24": supported_bands["24"] and self.config.show_24ghz,
            "5": supported_bands["5"] and self.config.show_5ghz,
            "6": supported_bands["6"] and self.config.show_6ghz,
        }
        # Pass supported bands separately so menu can show all options
        window.evaluate_js(
            f"window.supportedBands = {json.dumps(supported_bands)}"
        )
        window.evaluate_js(f"window.setDarkMode('{self.config.dark_mode}')")
        debug_mode = "true" if self.config.debug else "false"
        window.evaluate_js(f"window.setDebugMode({debug_mode})")
        window.evaluate_js(
            f"window.setRefreshInterval({self.config.update_interval_s})"
        )
        window.evaluate_js(f"window.init({json.dumps(enabled_bands)})")
        window.evaluate_js(f"window.setLayout('{self.config.layout}')")

        # Set up window resize handler
        window.evaluate_js("""
            window.addEventListener('resize', () => {
                if (window.pywebview) {
                    window.pywebview.api.save_config(
                        'window_width',
                        window.outerWidth
                    );
                    window.pywebview.api.save_config(
                        'window_height',
                        window.outerHeight
                    );
                }
            });
        """)

    def save_config_setting(self, key: str, value: Any) -> None:
        """Save a single config setting."""
        setattr(self.config, key, value)
        config_path = os.path.expanduser(
            "~/.config/tiny-wifi-analyzer/config.json"
        )
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        self.config.save(config_path)

    def toggle_csv_streaming(self, enabled: bool) -> None:
        """Toggle CSV streaming on/off."""
        self.csv_streaming = enabled

        if enabled:
            # Create CSV file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.expanduser(f"~/wifi_stream_{timestamp}.csv")
            self.csv_file = open(filename, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            # Write header
            self.csv_writer.writerow([
                'timestamp', 'ssid', 'bssid', 'channel', 'rssi', 'band'
            ])
            self.csv_file.flush()
            logger.info(f"Started CSV streaming to {filename}")
        else:
            # Close CSV file
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            logger.info("Stopped CSV streaming")

    def startup(self, window: Any) -> None:
        """Start the analyzer and begin scanning."""
        if self.scanner_thread is None:
            self.scanner_thread = self.start_scanner()

        supported_bands = get_supported_bands()
        while not self.is_closing.is_set():
            self.update(window, supported_bands)
            sleep(self.config.update_interval_s)

    def on_closing(self) -> None:
        """Handle window closing event."""
        # Save window size before closing
        try:
            windows = webview.windows
            if windows:
                window = windows[0]
                self.save_config_setting('window_width', window.width)
                self.save_config_setting('window_height', window.height)
        except Exception as e:
            logger.warning(f"Failed to save window size: {e}")

        # Close CSV file if streaming
        if self.csv_file:
            self.csv_file.close()

        self.is_closing.set()



class LocationManagerDelegate(AppKit.NSObject):
    """Delegate for handling location authorization changes."""

    def locationManagerDidChangeAuthorization_(
        self, manager: Any
    ) -> None:
        """Handle location authorization status changes."""
        status = manager.authorizationStatus()
        if status in [
            CoreLocation.kCLAuthorizationStatusDenied,
            CoreLocation.kCLAuthorizationStatusNotDetermined,
        ]:
            self.show_dialog()

    def show_dialog(self) -> None:
        """Show dialog for location services configuration."""
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Location Services are disabled")
        alert.setInformativeText_(
            "On macOS 14 Sonoma and Later, Location Services permission "
            "is required to get Wi-Fi SSIDs.\n"
            "Please enable Location Services in System Preferences > "
            "Security & Privacy > Privacy > Location Services."
        )
        alert.addButtonWithTitle_("Open Preferences")
        alert.addButtonWithTitle_("Ignore")
        alert.addButtonWithTitle_("Quit")
        response = alert.runModal()
        if response == AppKit.NSAlertFirstButtonReturn:
            url_string = (
                "x-apple.systempreferences:com.apple.preference.security?"
                "Privacy_LocationServices"
            )
            AppKit.NSWorkspace.sharedWorkspace().openURL_(
                Foundation.NSURL.URLWithString_(url_string)
            )
        elif response == AppKit.NSAlertSecondButtonReturn:
            pass
        else:
            AppKit.NSApplication.sharedApplication().terminate_(None)


def request_location_permission() -> None:
    """Request location permission from the user."""
    location_manager = CoreLocation.CLLocationManager.alloc().init()
    delegate = LocationManagerDelegate.alloc().init()
    location_manager.setDelegate_(delegate)
    location_manager.requestWhenInUseAuthorization()
    for i in range(LOCATION_CHECK_ITERATIONS):
        status = location_manager.authorizationStatus()
        if status != 0:
            break
        sleep(LOCATION_CHECK_SLEEP_S)


def main() -> None:
    """Main entry point for the application."""
    config_path = os.path.expanduser(
        "~/.config/tiny-wifi-analyzer/config.json"
    )
    config = Config.load(config_path if os.path.exists(config_path) else None)

    logging.basicConfig(level=getattr(logging, config.log_level.upper()))

    os_version = AppKit.NSAppKitVersionNumber
    if os_version > AppKit.NSAppKitVersionNumber13_1:
        request_location_permission()

    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    analyzer = WifiAnalyzer(config)

    # Create API class for JavaScript to call
    class Api:
        """JavaScript API for configuration and control."""

        def save_config(self, key: str, value: Any) -> None:
            """Save a configuration setting."""
            analyzer.save_config_setting(key, value)

        def toggle_csv_stream(self, enabled: bool) -> None:
            """Toggle CSV streaming."""
            analyzer.toggle_csv_streaming(enabled)

    # Get the correct path for bundled app or development
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
        index_html = os.path.join(base_path, "view/index.html")
    else:
        # Running in development
        base_path = os.path.dirname(__file__)
        index_html = os.path.join(base_path, "view/index.html")

    # Ensure valid window size
    width = max(800, config.window_width)
    height = max(600, config.window_height)

    window = webview.create_window(
        "Tiny Wi-Fi Analyzer",
        index_html,
        js_api=Api(),
        width=width,
        height=height
    )
    window.events.closing += analyzer.on_closing
    window.events.loaded += analyzer.setup_client
    webview.start(analyzer.startup, window, debug=config.debug)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
