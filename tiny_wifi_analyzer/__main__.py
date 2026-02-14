import json
import logging
import os.path
import queue
import sys
import threading
from time import sleep
from typing import Dict, List, Optional, Tuple

import AppKit
import CoreLocation
import CoreWLAN
import Foundation
import webview

# NOTE: https://github.com/r0x0r/pywebview/issues/496
from objc import nil, registerMetaDataForSelector  # pylint: disable=unused-import # noqa F401

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
    def __init__(self, channel):
        self.channel_band = channel.channelBand()
        self.channel_number = channel.channelNumber()
        self.channel_width = channel.channelWidth()

    def __repr__(self):
        return (
            "<CWChannel> [channel_band={}, channel_number={}, channel_width={}]".format(
                self.channel_band, self.channel_number, self.channel_width
            )
        )


class PyNetwork:
    def __init__(self, network):
        self.ssid = network.ssid()
        self.bssid = network.bssid()
        # self.security = network.security()
        self.rssi = network.rssiValue()
        self.channel = PyChannel(network.wlanChannel())
        self.ibss = network.ibss()

    def __repr__(self):
        return "<CWNetwork> [ssid={}, bssid={}, rssi={}, channel={}, ibss={}]".format(
            self.ssid, self.bssid, self.rssi, self.channel, self.ibss
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
    def __init__(self, config: Config):
        self.config = config
        self.update_queue: queue.Queue = queue.Queue()
        self.is_closing = threading.Event()
        self.scanner_thread: Optional[threading.Thread] = None
        self.csv_streaming = False
        self.csv_file = None
        self.csv_writer = None

    def start_scanner(self) -> threading.Thread:
        def loop() -> None:
            while not self.is_closing.is_set():
                try:
                    name, nws = scan()
                    self.update_queue.put((name, nws))
                except Exception as e:  # pragma: no cover - platform specific
                    logger.warning("scan failed: %s", e)
                sleep(max(0.05, self.config.scan_interval_ms / 1000.0))

        t = threading.Thread(target=loop, name="scanner", daemon=True)
        t.start()
        return t

    def to_series(self, nws: List[PyNetwork]) -> List[dict]:
        return series_from_networks(nws)

    def update(self, window, supported_bands: Dict[str, bool]) -> None:
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
                from datetime import datetime
                timestamp = datetime.now().isoformat()
                for nw in nws:
                    band = "2.4GHz" if nw.channel.channel_band == CHANNEL_BAND_24 else "5GHz" if nw.channel.channel_band == CHANNEL_BAND_5 else "6GHz"
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
                nws24 = [x for x in nws if x.channel.channel_band == CHANNEL_BAND_24]
                nws24 = sorted(nws24, key=lambda x: x.channel.channel_number)
                series24 = self.to_series(nws24)
                series_json24 = json.dumps(series24)
                window.evaluate_js(
                    "window.updateChart('{}',{})".format("24", series_json24)
                )

            if supported_bands["5"]:
                nws5 = [x for x in nws if x.channel.channel_band == CHANNEL_BAND_5]
                nws5 = sorted(nws5, key=lambda x: x.channel.channel_number)
                series5 = self.to_series(nws5)
                series_json5 = json.dumps(series5)
                window.evaluate_js("window.updateChart('{}',{})".format("5", series_json5))

            if supported_bands["6"]:
                nws6 = [x for x in nws if x.channel.channel_band == CHANNEL_BAND_6]
                nws6 = sorted(nws6, key=lambda x: x.channel.channel_number)
                series6 = self.to_series(nws6)
                series_json6 = json.dumps(series6)
                window.evaluate_js("window.updateChart('{}',{})".format("6", series_json6))

        except queue.Empty:
            pass

    def setup_client(self, window) -> None:
        supported_bands = get_supported_bands()
        # Filter bands based on config
        enabled_bands = {
            "24": supported_bands["24"] and self.config.show_24ghz,
            "5": supported_bands["5"] and self.config.show_5ghz,
            "6": supported_bands["6"] and self.config.show_6ghz,
        }
        # Pass supported bands separately so menu can show all options
        window.evaluate_js("window.supportedBands = {}".format(json.dumps(supported_bands)))
        window.evaluate_js("window.setDarkMode('{}')".format(self.config.dark_mode))
        window.evaluate_js("window.setDebugMode({})".format("true" if self.config.debug else "false"))
        window.evaluate_js("window.setRefreshInterval({})".format(self.config.update_interval_s))
        window.evaluate_js("window.init({})".format(json.dumps(enabled_bands)))
        window.evaluate_js("window.setLayout('{}')".format(self.config.layout))
        
        # Set up window resize handler
        window.evaluate_js("""
            window.addEventListener('resize', () => {
                if (window.pywebview) {
                    window.pywebview.api.save_config('window_width', window.outerWidth);
                    window.pywebview.api.save_config('window_height', window.outerHeight);
                }
            });
        """)

    def save_config_setting(self, key: str, value) -> None:
        """Save a single config setting"""
        setattr(self.config, key, value)
        config_path = os.path.expanduser("~/.config/tiny-wifi-analyzer/config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        self.config.save(config_path)

    def toggle_csv_streaming(self, enabled: bool) -> None:
        """Toggle CSV streaming on/off"""
        import csv
        from datetime import datetime
        
        self.csv_streaming = enabled
        
        if enabled:
            # Create CSV file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.expanduser(f"~/wifi_stream_{timestamp}.csv")
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            # Write header
            self.csv_writer.writerow(['timestamp', 'ssid', 'bssid', 'channel', 'rssi', 'band'])
            self.csv_file.flush()
            logger.info(f"Started CSV streaming to {filename}")
        else:
            # Close CSV file
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
                self.csv_writer = None
            logger.info("Stopped CSV streaming")

    def startup(self, window) -> None:
        if self.scanner_thread is None:
            self.scanner_thread = self.start_scanner()

        supported_bands = get_supported_bands()
        while not self.is_closing.is_set():
            self.update(window, supported_bands)
            sleep(self.config.update_interval_s)

    def on_closing(self) -> None:
        # Save window size before closing
        try:
            import webview
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
    def locationManagerDidChangeAuthorization_(self, manager):
        status = manager.authorizationStatus()
        if status in [
            CoreLocation.kCLAuthorizationStatusDenied,
            CoreLocation.kCLAuthorizationStatusNotDetermined,
        ]:
            self.show_dialog()

    def show_dialog(self):
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Location Services are disabled")
        alert.setInformativeText_(
            "On macOS 14 Sonoma and Later, Location Services permission is required to get Wi-Fi SSIDs.\n"
            + "Please enable Location Services in System Preferences > Security & Privacy > Privacy > Location Services."
        )
        alert.addButtonWithTitle_("Open Preferences")
        alert.addButtonWithTitle_("Ignore")
        alert.addButtonWithTitle_("Quit")
        response = alert.runModal()
        if response == AppKit.NSAlertFirstButtonReturn:
            AppKit.NSWorkspace.sharedWorkspace().openURL_(
                Foundation.NSURL.URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_LocationServices"
                )
            )
        elif response == AppKit.NSAlertSecondButtonReturn:
            pass
        else:
            AppKit.NSApplication.sharedApplication().terminate_(None)


def request_location_permission() -> None:
    location_manager = CoreLocation.CLLocationManager.alloc().init()
    delegate = LocationManagerDelegate.alloc().init()
    location_manager.setDelegate_(delegate)
    location_manager.requestWhenInUseAuthorization()
    for i in range(LOCATION_CHECK_ITERATIONS):
        status = location_manager.authorizationStatus()
        if not status == 0:
            break
        sleep(LOCATION_CHECK_SLEEP_S)


def main() -> None:
    config_path = os.path.expanduser("~/.config/tiny-wifi-analyzer/config.json")
    config = Config.load(config_path if os.path.exists(config_path) else None)

    logging.basicConfig(level=getattr(logging, config.log_level.upper()))

    os_version = AppKit.NSAppKitVersionNumber
    if os_version > AppKit.NSAppKitVersionNumber13_1:
        request_location_permission()

    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    analyzer = WifiAnalyzer(config)

    # Create API class for JavaScript to call
    class Api:
        def save_config(self, key, value):
            analyzer.save_config_setting(key, value)
        
        def toggle_csv_stream(self, enabled):
            analyzer.toggle_csv_streaming(enabled)

    # Get the correct path for bundled app or development
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in development
        base_path = os.path.dirname(__file__)
    
    index_html = os.path.join(base_path, "tiny_wifi_analyzer/view/index.html")
    
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
