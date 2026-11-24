"""Tests for rotating/crash logging, QThread safety, and bulk font operations."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from fontvault.config import resolve_paths
from fontvault.core import installer_win
from fontvault.core.installer_win import delete_font_item
from fontvault.core.metadata import parse_font_file
from fontvault.logging_setup import setup_logging
from fontvault.models import FontSource, OnlineFontFamily
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


def test_delete_font_item_protections_and_custom_delete(tmp_path: Path, monkeypatch) -> None:
    custom_ttf = create_synthetic_ttf(tmp_path / "vault" / "CustomDel.ttf", family="CustomDel")
    custom_item = parse_font_file(custom_ttf, FontSource.CUSTOM)
    assert custom_item is not None
    ok, _msg = delete_font_item(custom_item)
    assert ok is True
    assert not custom_ttf.exists()

    sys_ttf = create_synthetic_ttf(tmp_path / "sys" / "SysKeep.ttf", family="SysKeep")
    sys_item = parse_font_file(sys_ttf, FontSource.INSTALLED_SYSTEM)
    assert sys_item is not None
    ok_sys, msg_sys = delete_font_item(sys_item)
    assert ok_sys is False
    assert "Protegida" in msg_sys
    assert sys_ttf.exists()

    app_ttf = create_synthetic_ttf(tmp_path / "app" / "AppKeep.ttf", family="AppKeep")
    app_item = parse_font_file(app_ttf, FontSource.APPLICATION, app_name="SomeApp")
    assert app_item is not None
    ok_app, _ = delete_font_item(app_item)
    assert ok_app is False
    assert app_ttf.exists()

    user_fonts_dir = tmp_path / "UserFonts"
    user_ttf = create_synthetic_ttf(user_fonts_dir / "UserFont.ttf", family="UserFont")
    user_item = parse_font_file(user_ttf, FontSource.INSTALLED_USER)
    assert user_item is not None
    monkeypatch.setattr(installer_win, "get_user_fonts_dir", lambda: user_fonts_dir)

    with (
        patch("fontvault.core.installer_win.ctypes.windll.gdi32.RemoveFontResourceW"),
        patch("fontvault.core.installer_win.winreg.OpenKey", side_effect=OSError("no key")),
        patch("fontvault.core.installer_win._broadcast_font_change"),
    ):
        ok_user, _ = delete_font_item(user_item)
    assert ok_user is True
    assert not user_ttf.exists()


def test_mainwindow_and_catalog_batch_selection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication
    from fontvault.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    f1 = create_synthetic_ttf(paths.custom_fonts_dir / "One.ttf", family="One")
    f2 = create_synthetic_ttf(paths.custom_fonts_dir / "Two.ttf", family="Two")
    items = [parse_font_file(f1, FontSource.CUSTOM), parse_font_file(f2, FontSource.CUSTOM)]
    items = [i for i in items if i is not None]

    with patch("fontvault.ui.main_window.MainWindow.start_scan", return_value=None):
        win = MainWindow(paths)
        win._on_scan_finished(items)
        assert win.batch_install_btn.isEnabled() is False

        win.select_visible()
        assert len(win._checked_paths) == 2
        assert win.selection_lbl.text() == "2 seleccionadas"
        assert win.batch_install_btn.isEnabled() is True
        assert win.batch_backup_btn.isEnabled() is True
        assert win.batch_delete_btn.isEnabled() is True

        win.clear_selection()
        assert len(win._checked_paths) == 0
        assert win.batch_delete_btn.isEnabled() is False

        fams = [
            OnlineFontFamily(id="inter", family="Inter", category="sans-serif", weights=[400]),
            OnlineFontFamily(id="lato", family="Lato", category="sans-serif", weights=[400]),
        ]
        for fam in fams:
            create_synthetic_ttf(win.catalog_tab.catalog_service.preview_cache_dir / f"{fam.id}.ttf", family=fam.family)
        win.catalog_tab._on_catalog_loaded(fams)
        win.catalog_tab.select_visible()
        assert len(win.catalog_tab._checked_ids) == 2
        assert win.catalog_tab.batch_download_btn.isEnabled() is True
        assert win.catalog_tab.batch_install_btn.isEnabled() is True

        win.catalog_tab.clear_selection()
        assert len(win.catalog_tab._checked_ids) == 0
        assert win.catalog_tab.batch_download_btn.isEnabled() is False

        win.close()
        win.deleteLater()
    app.processEvents()
    QFontDatabase.removeAllApplicationFonts()
