"""Font discovery across Windows, custom folders, and installed applications."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Callable

from fontvault.config import AppPaths, AppSettings
from fontvault.core.metadata import SUPPORTED_FONT_EXTENSIONS, parse_font_file
from fontvault.models import FontItem, FontSource


logger = logging.getLogger(__name__)


SKIP_DIR_NAMES = {
    "windows",
    "winsxs",
    "system32",
    "syswow64",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "$recycle.bin",
    "system volume information",
    "temp",
    "tmp",
    "cache",
    "gpucache",
    "code cache",
    "shadercache",
    "crashpad",
}


class FontScanner:
    """Scans system, user, custom, and application font directories with caching."""

    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths
        self._cache_file = paths.cache_dir / "font_index.json"
        self._index_cache: dict[str, dict] = self._load_cache()

    def _load_cache(self) -> dict[str, dict]:
        if not self._cache_file.exists():
            return {}
        try:
            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_cache(self) -> None:
        """Persist incremental metadata index to disk."""
        self.paths.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._cache_file.write_text(
                json.dumps(self._index_cache, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _parse_with_cache(
        self,
        path: Path,
        source: FontSource,
        app_name: str = "",
    ) -> FontItem | None:
        try:
            stat = path.stat()
        except OSError:
            return None

        cache_key = f"{str(path).lower()}|{source.value}"
        cached = self._index_cache.get(cache_key)
        if (
            cached
            and cached.get("mtime_ns") == stat.st_mtime_ns
            and cached.get("size") == stat.st_size
            and cached.get("app_name", "") == app_name
        ):
            try:
                return FontItem.from_dict(cached["item"])
            except Exception:
                pass

        item = parse_font_file(path, source=source, app_name=app_name)
        if item is not None:
            self._index_cache[cache_key] = {
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "app_name": app_name,
                "item": item.to_dict(),
            }
        return item

    def _scan_dir_flat_or_recursive(
        self,
        directory: Path,
        source: FontSource,
        recursive: bool = True,
        app_name: str = "",
    ) -> list[FontItem]:
        if not directory.exists() or not directory.is_dir():
            return []
        items: list[FontItem] = []
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        try:
            for candidate in iterator:
                if candidate.suffix.lower() in SUPPORTED_FONT_EXTENSIONS and candidate.is_file():
                    parsed = self._parse_with_cache(candidate, source=source, app_name=app_name)
                    if parsed is not None:
                        items.append(parsed)
        except OSError:
            pass
        return items

    def scan_installed_fonts(self) -> list[FontItem]:
        """Scan Windows system and per-user installed font directories."""
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))

        system_dir = windir / "Fonts"
        user_dir = local_appdata / "Microsoft" / "Windows" / "Fonts"

        items: list[FontItem] = []
        items.extend(self._scan_dir_flat_or_recursive(system_dir, FontSource.INSTALLED_SYSTEM, recursive=False))
        items.extend(self._scan_dir_flat_or_recursive(user_dir, FontSource.INSTALLED_USER, recursive=True))
        return items

    def scan_custom_fonts(self, extra_dirs: list[Path] | None = None) -> list[FontItem]:
        """Scan FontVault's custom vault directory plus user-added custom folders."""
        dirs: list[Path] = [self.paths.custom_fonts_dir]
        if extra_dirs:
            dirs.extend(extra_dirs)

        seen_paths: set[str] = set()
        items: list[FontItem] = []
        for directory in dirs:
            for item in self._scan_dir_flat_or_recursive(directory, FontSource.CUSTOM, recursive=True):
                norm = str(item.path).lower()
                if norm not in seen_paths:
                    seen_paths.add(norm)
                    items.append(item)
        return items

    def scan_application_fonts(
        self,
        extra_app_dirs: list[Path] | None = None,
        max_files: int = 600,
        max_depth: int = 4,
    ) -> list[FontItem]:
        """Scan installed application folders for bundled fonts with bounded depth."""
        roots: list[Path] = []
        if extra_app_dirs is not None:
            roots.extend(extra_app_dirs)
        else:
            local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            for env_dir in (
                local_appdata / "Programs",
                Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
            ):
                if env_dir.exists():
                    roots.append(env_dir)

        items: list[FontItem] = []
        seen_paths: set[str] = set()

        for root in roots:
            if not root.exists() or not root.is_dir():
                continue
            root_parts_len = len(root.parts)
            for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda _e: None):
                current = Path(dirpath)
                depth = len(current.parts) - root_parts_len
                # Prune noisy or overly deep directories.
                if depth >= max_depth:
                    dirnames[:] = []
                else:
                    dirnames[:] = [
                        d for d in dirnames
                        if d.lower() not in SKIP_DIR_NAMES and not d.startswith(".")
                    ]

                for fname in filenames:
                    if Path(fname).suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
                        continue
                    font_path = current / fname
                    norm = str(font_path).lower()
                    if norm in seen_paths:
                        continue
                    seen_paths.add(norm)

                    rel_parts = font_path.relative_to(root).parts
                    app_name = rel_parts[0] if len(rel_parts) > 1 else root.name
                    parsed = self._parse_with_cache(
                        font_path,
                        source=FontSource.APPLICATION,
                        app_name=app_name,
                    )
                    if parsed is not None:
                        items.append(parsed)
                        if len(items) >= max_files:
                            return items
        return items

    def scan_all(
        self,
        settings: AppSettings,
        include_apps: bool = True,
        progress_cb: Callable[[str], None] | None = None,
    ) -> list[FontItem]:
        """Execute full scan across all categories and update incremental cache."""
        results: list[FontItem] = []

        if progress_cb:
            progress_cb("Escaneando fuentes instaladas en Windows...")
        results.extend(self.scan_installed_fonts())

        if progress_cb:
            progress_cb("Escaneando fuentes personalizadas...")
        extra_custom = [Path(p) for p in settings.custom_scan_dirs if p]
        results.extend(self.scan_custom_fonts(extra_dirs=extra_custom))

        if include_apps:
            if progress_cb:
                progress_cb("Buscando fuentes de aplicaciones...")
            extra_apps = [Path(p) for p in settings.app_scan_dirs if p] or None
            results.extend(self.scan_application_fonts(extra_app_dirs=extra_apps))

        self.save_cache()
        results.sort(key=lambda item: (item.family.lower(), item.subfamily.lower()))
        logger.info("Escaneo completado: %d fuentes detectadas (include_apps=%s)", len(results), include_apps)
        return results
