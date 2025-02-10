# -*- mode: python ; coding: utf-8 -*-
import sys

# Determine the FFmpeg binary file based on the OS.
if sys.platform.startswith("win"):
    ffmpeg_binary = ("bin\\ffmpeg.exe", ".")  # For Windows, adjust path separator if needed.
else:
    ffmpeg_binary = ("bin/ffmpeg", ".")  # For Linux/macOS.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[ffmpeg_binary],
    datas=[('resources/favicon.ico', 'resources'), ('.env', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    icon='resources/favicon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
