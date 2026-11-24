# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
PAYLOAD_EXE = ROOT / "build" / "payload" / "FontVault.exe"

a = Analysis(
    [str(ROOT / "packaging" / "setup_wizard.py")],
    pathex=[str(ROOT / "packaging")],
    binaries=[],
    datas=[
        (str(PAYLOAD_EXE), "payload"),
        (str(ROOT / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "assets" / "icon.png"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "fontTools", "PIL", "httpx", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FontVault-Setup-win64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(ROOT / "assets" / "icon.ico"),
    version=str(ROOT / "packaging" / "version_info.txt"),
)
