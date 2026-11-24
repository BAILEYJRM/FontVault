"""Configuration and Portable vs Installed path resolution."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


DEFAULT_PREVIEW_TEXT = "El veloz murciélago hindú comía feliz cardillo y kiwi. 0123456789"


@dataclass(slots=True)
class AppPaths:
    """Resolved runtime storage directories for FontVault."""

    is_portable: bool
    root_dir: Path
    custom_fonts_dir: Path
    backups_dir: Path
    cache_dir: Path
    downloads_dir: Path
    settings_file: Path

    def ensure_dirs(self) -> None:
        """Create required application directories if missing."""
        for directory in (
            self.root_dir,
            self.custom_fonts_dir,
            self.backups_dir,
            self.cache_dir,
            self.downloads_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class AppSettings:
    """User-configurable FontVault preferences."""

    custom_scan_dirs: list[str] = field(default_factory=list)
    app_scan_dirs: list[str] = field(default_factory=list)
    preview_text: str = DEFAULT_PREVIEW_TEXT
    preview_size: int = 28
    sync_thumbnails_preview: bool = False
    theme: str = "dark"


def get_app_base_dir() -> Path:
    """Return executable directory when frozen, or project root in source mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def get_resource_path(relative_path: str) -> Path:
    """Locate bundled asset in PyInstaller _MEIPASS or source checkout."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / relative_path
        if candidate.exists():
            return candidate
    return get_app_base_dir() / relative_path


def detect_portable_mode(
    portable_override: bool | None = None,
    base_dir: Path | None = None,
) -> bool:
    """Determine whether FontVault runs in Portable Mode."""
    if portable_override is not None:
        return portable_override

    env_flag = os.environ.get("FONTVAULT_PORTABLE", "").strip().lower()
    if env_flag in {"1", "true", "yes"}:
        return True
    if env_flag in {"0", "false", "no"}:
        return False

    resolved_base = base_dir or get_app_base_dir()
    if (resolved_base / "portable.flag").exists():
        return True

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and (Path(meipass) / "bundled_portable.flag").exists():
        return True

    return False


def resolve_paths(
    portable_override: bool | None = None,
    base_dir: Path | None = None,
) -> AppPaths:
    """Build AppPaths for Portable (<exe>/data) or Installed (%LOCALAPPDATA%/FontVault)."""
    resolved_base = base_dir or get_app_base_dir()
    is_portable = detect_portable_mode(portable_override=portable_override, base_dir=resolved_base)

    if is_portable:
        root_dir = resolved_base / "data"
    else:
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        root_dir = local_appdata / "FontVault"

    paths = AppPaths(
        is_portable=is_portable,
        root_dir=root_dir,
        custom_fonts_dir=root_dir / "custom_fonts",
        backups_dir=root_dir / "backups",
        cache_dir=root_dir / "cache",
        downloads_dir=root_dir / "downloads",
        settings_file=root_dir / "settings.json",
    )
    paths.ensure_dirs()
    return paths


def load_settings(paths: AppPaths) -> AppSettings:
    """Load persisted JSON settings or return defaults on missing/corrupt file."""
    if not paths.settings_file.exists():
        return AppSettings()
    try:
        raw = json.loads(paths.settings_file.read_text(encoding="utf-8"))
        return AppSettings(
            custom_scan_dirs=list(raw.get("custom_scan_dirs", [])),
            app_scan_dirs=list(raw.get("app_scan_dirs", [])),
            preview_text=str(raw.get("preview_text", DEFAULT_PREVIEW_TEXT)) or DEFAULT_PREVIEW_TEXT,
            preview_size=int(raw.get("preview_size", 28)),
            sync_thumbnails_preview=bool(raw.get("sync_thumbnails_preview", False)),
            theme=str(raw.get("theme", "dark")),
        )
    except (OSError, ValueError, TypeError):
        return AppSettings()


def save_settings(paths: AppPaths, settings: AppSettings) -> None:
    """Persist settings JSON safely."""
    paths.ensure_dirs()
    paths.settings_file.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
