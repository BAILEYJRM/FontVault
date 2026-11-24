"""Windows font installation and uninstallation (HKCU per-user & HKLM system)."""

from __future__ import annotations

import ctypes
import os
import shutil
import winreg
from pathlib import Path

from fontvault.core.metadata import SUPPORTED_FONT_EXTENSIONS, parse_font_file
from fontvault.models import FontSource


HWND_BROADCAST = 0xFFFF
WM_FONTCHANGE = 0x001D
SMTO_ABORTIFHUNG = 0x0002

REG_FONTS_SUBKEY = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"


def is_admin() -> bool:
    """Return True if the current process holds Windows Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def get_user_fonts_dir() -> Path:
    """Return per-user Windows font directory (%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts)."""
    local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_appdata / "Microsoft" / "Windows" / "Fonts"


def get_system_fonts_dir() -> Path:
    """Return system-wide Windows font directory (C:\\Windows\\Fonts)."""
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    return windir / "Fonts"


def _registry_font_label(font_path: Path) -> str:
    item = parse_font_file(font_path, source=FontSource.CUSTOM)
    base_name = item.full_name if item and item.full_name else font_path.stem
    ext = font_path.suffix.lower()
    if ext == ".otf":
        return f"{base_name} (OpenType)"
    return f"{base_name} (TrueType)"


def _broadcast_font_change() -> None:
    try:
        ctypes.windll.gdi32.SendMessageTimeoutW  # noqa: B018
    except AttributeError:
        pass
    try:
        result = ctypes.c_ulong(0)
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_FONTCHANGE,
            0,
            0,
            SMTO_ABORTIFHUNG,
            1000,
            ctypes.byref(result),
        )
    except Exception:
        pass


def install_font_user(font_path: Path) -> Path:
    """Install a font for the current Windows user without requiring Admin UAC."""
    if not font_path.is_file() or font_path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
        raise ValueError(f"Archivo de fuente no válido: {font_path}")

    dest_dir = get_user_fonts_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / font_path.name
    if font_path.resolve() != dest_path.resolve():
        shutil.copy2(font_path, dest_path)

    reg_label = _registry_font_label(dest_path)
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, REG_FONTS_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, reg_label, 0, winreg.REG_SZ, str(dest_path))

    ctypes.windll.gdi32.AddFontResourceW(str(dest_path))
    _broadcast_font_change()
    return dest_path


def install_font_system(font_path: Path) -> Path:
    """Install a font system-wide in C:\\Windows\\Fonts (requires Admin)."""
    if not is_admin():
        raise PermissionError(
            "Se requieren permisos de administrador para instalar fuentes en todo el sistema."
        )
    if not font_path.is_file() or font_path.suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
        raise ValueError(f"Archivo de fuente no válido: {font_path}")

    dest_dir = get_system_fonts_dir()
    dest_path = dest_dir / font_path.name
    if font_path.resolve() != dest_path.resolve():
        shutil.copy2(font_path, dest_path)

    reg_label = _registry_font_label(dest_path)
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, REG_FONTS_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, reg_label, 0, winreg.REG_SZ, dest_path.name)

    ctypes.windll.gdi32.AddFontResourceW(str(dest_path))
    _broadcast_font_change()
    return dest_path


def uninstall_font_user(font_path: Path) -> bool:
    """Uninstall a per-user Windows font from HKCU and user Fonts directory."""
    user_dir = get_user_fonts_dir().resolve()
    resolved = font_path.resolve()
    if resolved.parent != user_dir:
        raise PermissionError(
            "Por seguridad, solo se permite desinstalar fuentes del usuario actual."
        )

    ctypes.windll.gdi32.RemoveFontResourceW(str(resolved))

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_FONTS_SUBKEY,
            0,
            winreg.KEY_READ | winreg.KEY_SET_VALUE,
        ) as key:
            idx = 0
            to_delete: list[str] = []
            while True:
                try:
                    val_name, val_data, _ = winreg.EnumValue(key, idx)
                    if str(val_data).lower() == str(resolved).lower():
                        to_delete.append(val_name)
                    idx += 1
                except OSError:
                    break
            for val_name in to_delete:
                winreg.DeleteValue(key, val_name)
    except OSError:
        pass

    removed = False
    if resolved.exists():
        try:
            resolved.unlink()
            removed = True
        except OSError:
            removed = False

    _broadcast_font_change()
    return removed
