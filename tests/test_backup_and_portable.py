"""Tests for Portable/Installed paths, ZIP/folder backups, and import."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fontvault.config import load_settings, resolve_paths, save_settings, AppSettings
from fontvault.core.backup import export_fonts, import_fonts_to_custom
from fontvault.core.metadata import parse_font_file
from fontvault.models import FontSource
from tests.conftest import create_synthetic_ttf


def test_portable_vs_installed_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FONTVAULT_PORTABLE", raising=False)
    portable_flag = tmp_path / "portable.flag"
    portable_flag.write_text("1", encoding="utf-8")

    p_paths = resolve_paths(base_dir=tmp_path)
    assert p_paths.is_portable is True
    assert p_paths.root_dir == tmp_path / "data"
    assert p_paths.custom_fonts_dir.exists()

    portable_flag.unlink()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LocalAppData"))
    i_paths = resolve_paths(base_dir=tmp_path)
    assert i_paths.is_portable is False
    assert i_paths.root_dir == tmp_path / "LocalAppData" / "FontVault"


def test_settings_roundtrip(tmp_path: Path) -> None:
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    settings = AppSettings(custom_scan_dirs=[r"C:\MyFonts"], preview_text="Hola Mundo")
    save_settings(paths, settings)
    loaded = load_settings(paths)
    assert loaded.custom_scan_dirs == [r"C:\MyFonts"]
    assert loaded.preview_text == "Hola Mundo"


def test_export_zip_and_folder_with_manifest(tmp_path: Path) -> None:
    f1 = create_synthetic_ttf(tmp_path / "src" / "Alpha.ttf", family="Alpha")
    f2 = create_synthetic_ttf(tmp_path / "src" / "Beta.ttf", family="Beta")
    item1 = parse_font_file(f1, FontSource.INSTALLED_USER)
    item2 = parse_font_file(f2, FontSource.APPLICATION, app_name="FigmaDesktop")
    assert item1 and item2

    zip_dest = tmp_path / "out" / "fonts_backup.zip"
    zip_res = export_fonts([item1, item2], zip_dest, as_zip=True)
    assert zip_res.copied_count == 2
    assert zip_dest.exists()

    with zipfile.ZipFile(zip_dest, "r") as zf:
        names = set(zf.namelist())
        assert "installed_user/Alpha.ttf" in names
        assert "applications/FigmaDesktop/Beta.ttf" in names
        assert "manifest.json" in names
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        assert manifest["total_fonts"] == 2

    folder_dest = tmp_path / "out_folder"
    dir_res = export_fonts([item1, item2], folder_dest, as_zip=False)
    assert dir_res.copied_count == 2
    assert (folder_dest / "manifest.json").exists()
    assert (folder_dest / "installed_user" / "Alpha.ttf").exists()


def test_import_zip_blocks_zip_slip(tmp_path: Path) -> None:
    ttf = create_synthetic_ttf(tmp_path / "Valid.ttf", family="Valid")
    malicious_zip = tmp_path / "pack.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.write(ttf, arcname="../../evil/Valid.ttf")
        zf.writestr("readme.txt", "ignore me")

    vault = tmp_path / "vault"
    imported = import_fonts_to_custom(malicious_zip, vault)
    assert len(imported) == 1
    assert imported[0].parent == vault
    assert imported[0].name == "Valid.ttf"
