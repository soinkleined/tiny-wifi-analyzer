# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['../tiny_wifi_analyzer/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../tiny_wifi_analyzer/view', 'tiny_wifi_analyzer/view'),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.cocoa',
        'AppKit',
        'CoreLocation',
        'CoreWLAN',
        'Foundation',
        'objc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Tiny Wi-Fi Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Tiny Wi-Fi Analyzer',
)

app = BUNDLE(
    coll,
    name='Tiny Wi-Fi Analyzer.app',
    icon='assets/wifi-icon.icns',
    bundle_identifier='com.github.soinkleined.tiny-wifi-analyzer',
    version='0.7.0',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.15.0',
        'NSLocationWhenInUseUsageDescription': 'Location Services permission is required on macOS 14 Sonoma and later to scan Wi-Fi networks and display SSIDs.',
        'NSLocationUsageDescription': 'Location Services permission is required on macOS 14 Sonoma and later to scan Wi-Fi networks and display SSIDs.',
        'NSLocationAlwaysAndWhenInUseUsageDescription': 'Location Services permission is required on macOS 14 Sonoma and later to scan Wi-Fi networks and display SSIDs.',
        'LSApplicationCategoryType': 'public.app-category.utilities',
    },
)
