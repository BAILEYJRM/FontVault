"""Tests for metadata parsing, custom scanning, application scanning, and cache."""

from __future__ import annotations

from pathlib import Path

from fontvault.config import resolve_paths
from fontvault.core.metadata import parse_font_file
from fontvault.core.scanner import FontScanner
from fontvault.models import FontSource
from tests.conftest import create_synthetic_ttf


def test_parse_font_file_reads_opentype_names(sample_ttf: Path) -> None:
    item = parse_font_file(sample_ttf, source=FontSource.CUSTOM)
    assert item is not None
    assert item.family == "SampleSans"
    assert item.subfamily == "Regular"
    assert item.format == "TTF"
    assert item.file_size > 0


def test_parse_font_file_handles_corrupt_gracefully(tmp_path: Path) -> None:
    bad_font = tmp_path / "BrokenDisplay.ttf"
    bad_font.write_bytes(b"not-a-real-font")
    item = parse_font_file(bad_font, source=FontSource.CUSTOM)
    assert item is not None
    assert item.family == "BrokenDisplay"
    assert item.format == "TTF"


def test_scanner_custom_and_application_fonts(tmp_path: Path) -> None:
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    create_synthetic_ttf(paths.custom_fonts_dir / "CustomMono.ttf", family="CustomMono", subfamily="Bold")

    app_root = tmp_path / "ProgramFilesMock"
    create_synthetic_ttf(
        app_root / "DesignStudio" / "resources" / "fonts" / "StudioUI.ttf",
        family="StudioUI",
        subfamily="Regular",
    )
    # Noisy directory should be skipped.
    create_synthetic_ttf(
        app_root / "DesignStudio" / "node_modules" / "Ignored.ttf",
        family="Ignored",
    )

    scanner = FontScanner(paths)
    custom_items = scanner.scan_custom_fonts()
    assert len(custom_items) == 1
    assert custom_items[0].family == "CustomMono"

    app_items = scanner.scan_application_fonts(extra_app_dirs=[app_root])
    assert len(app_items) == 1
    assert app_items[0].family == "StudioUI"
    assert app_items[0].app_name == "DesignStudio"
    assert app_items[0].source == FontSource.APPLICATION

    # Verify incremental cache persistence and hit.
    scanner.save_cache()
    scanner2 = FontScanner(paths)
    cached_items = scanner2.scan_custom_fonts()
    assert len(cached_items) == 1
    assert cached_items[0].family == "CustomMono"
