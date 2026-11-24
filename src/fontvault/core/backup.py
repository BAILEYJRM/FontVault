"""Backup, export, and import operations for font collections."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fontvault.core.metadata import SUPPORTED_FONT_EXTENSIONS, is_valid_font_magic
from fontvault.models import BackupResult, FontItem, FontSource


def _sanitize_segment(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", name.strip())
    return cleaned or "unknown"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bucket_rel_dir(item: FontItem) -> Path:
    if item.source == FontSource.APPLICATION:
        return Path("applications") / _sanitize_segment(item.app_name or "App")
    return Path(item.source.value)


def _unique_rel_path(used: set[str], rel_dir: Path, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = (rel_dir / filename).as_posix()
    counter = 1
    while candidate.lower() in used:
        candidate = (rel_dir / f"{stem} ({counter}){suffix}").as_posix()
        counter += 1
    used.add(candidate.lower())
    return candidate


def export_fonts(
    items: list[FontItem],
    destination: Path,
    as_zip: bool = True,
) -> BackupResult:
    """Back up selected fonts to a ZIP archive or folder with SHA-256 manifest."""
    used_rel_paths: set[str] = set()
    manifest_entries: list[dict] = []
    errors: list[str] = []
    copied_count = 0
    total_bytes = 0
    counts_by_source: dict[str, int] = {}

    if as_zip:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in items:
                if not item.path.is_file():
                    errors.append(f"No encontrado: {item.path}")
                    continue
                rel_path = _unique_rel_path(used_rel_paths, _bucket_rel_dir(item), item.path.name)
                try:
                    zf.write(item.path, arcname=rel_path)
                    size = item.path.stat().st_size
                    sha256 = _sha256_file(item.path)
                    copied_count += 1
                    total_bytes += size
                    counts_by_source[item.source.value] = counts_by_source.get(item.source.value, 0) + 1
                    manifest_entries.append({
                        "archive_path": rel_path,
                        "sha256": sha256,
                        **item.to_dict(),
                    })
                except OSError as exc:
                    errors.append(f"{item.path.name}: {exc}")

            manifest_payload = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "total_fonts": copied_count,
                "total_bytes": total_bytes,
                "counts_by_source": counts_by_source,
                "fonts": manifest_entries,
            }
            zf.writestr("manifest.json", json.dumps(manifest_payload, indent=2, ensure_ascii=False))
        manifest_path = destination
    else:
        destination.mkdir(parents=True, exist_ok=True)
        for item in items:
            if not item.path.is_file():
                errors.append(f"No encontrado: {item.path}")
                continue
            rel_path = _unique_rel_path(used_rel_paths, _bucket_rel_dir(item), item.path.name)
            target = destination / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(item.path, target)
                size = target.stat().st_size
                sha256 = _sha256_file(target)
                copied_count += 1
                total_bytes += size
                counts_by_source[item.source.value] = counts_by_source.get(item.source.value, 0) + 1
                manifest_entries.append({
                    "relative_path": rel_path,
                    "sha256": sha256,
                    **item.to_dict(),
                })
            except OSError as exc:
                errors.append(f"{item.path.name}: {exc}")

        manifest_path = destination / "manifest.json"
        manifest_payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_fonts": copied_count,
            "total_bytes": total_bytes,
            "counts_by_source": counts_by_source,
            "fonts": manifest_entries,
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return BackupResult(
        destination=destination,
        copied_count=copied_count,
        total_bytes=total_bytes,
        manifest_path=manifest_path,
        errors=errors,
    )


def _unique_dest_file(dest_dir: Path, filename: str) -> Path:
    safe_name = _sanitize_segment(Path(filename).name)
    candidate = dest_dir / safe_name
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while candidate.exists():
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def import_fonts_to_custom(source_path: Path, custom_dir: Path) -> list[Path]:
    """Import font files from a single font, folder, or ZIP archive into custom_dir."""
    custom_dir.mkdir(parents=True, exist_ok=True)
    imported: list[Path] = []

    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(source_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                member_name = Path(member.filename).name
                if not member_name or Path(member_name).suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
                    continue
                # Prevent zip-slip by resolving only against basename inside custom_dir.
                data = zf.read(member)
                if not is_valid_font_magic(data[:4]):
                    continue
                dest = _unique_dest_file(custom_dir, member_name)
                dest.write_bytes(data)
                imported.append(dest)
        return imported

    if source_path.is_file():
        if source_path.suffix.lower() in SUPPORTED_FONT_EXTENSIONS:
            dest = _unique_dest_file(custom_dir, source_path.name)
            shutil.copy2(source_path, dest)
            imported.append(dest)
        return imported

    if source_path.is_dir():
        for file_path in source_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_FONT_EXTENSIONS:
                dest = _unique_dest_file(custom_dir, file_path.name)
                shutil.copy2(file_path, dest)
                imported.append(dest)
    return imported
