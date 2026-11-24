"""Tests for rotating/crash logging, QThread safety, and bulk font operations."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from fontvault.config import resolve_paths
from fontvault.logging_setup import setup_logging
from fontvault.models import OnlineFontFamily
from tests.conftest import create_synthetic_ttf


def test_setup_logging_creates_log_and_crash_files(tmp_path: Path) -> None:
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    log_path = setup_logging(paths)

    logger = logging.getLogger("fontvault.test")
    logger.info("Mensaje de prueba FontVault")
    for handler in logging.getLogger("fontvault").handlers:
        handler.flush()

    assert log_path.exists()
    assert (paths.logs_dir / "crash_faulthandler.log").exists()
    content = log_path.read_text(encoding="utf-8")
    assert "Mensaje de prueba FontVault" in content


def test_catalog_rapid_preview_and_search_debounce_safe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from fontvault.ui.catalog_tab import CatalogTab
    from fontvault.ui.widgets import FontLoaderCache

    app = QApplication.instance() or QApplication([])
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    tab = CatalogTab(paths, FontLoaderCache())

    fams = [
        OnlineFontFamily(id="inter", family="Inter", category="sans-serif", weights=[400]),
        OnlineFontFamily(id="roboto", family="Roboto", category="sans-serif", weights=[400]),
    ]
    for fam in fams:
        create_synthetic_ttf(tab.catalog_service.preview_cache_dir / f"{fam.id}.ttf", family=fam.family)

    tab._on_catalog_loaded(fams)
    # Rapidly request previews back-to-back without crashing.
    tab._request_preview(fams[0])
    tab._request_preview(fams[1])
    tab.search_input.setText("rob")
    app.processEvents()

    tab.stop_background_workers()
    tab.close()
    tab.deleteLater()
    app.processEvents()
    QFontDatabase.removeAllApplicationFonts()
