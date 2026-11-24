"""Tests for free font catalog, zip-slip download guard, Windows installer mock, and UI smoke."""

from __future__ import annotations

import os
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from fontvault.config import resolve_paths
from fontvault.core import installer_win
from fontvault.core.catalog import FreeFontCatalog, OFFLINE_FALLBACK_FONTS
from fontvault.models import OnlineFontFamily
from tests.conftest import create_synthetic_ttf


def test_catalog_offline_fallback(tmp_path: Path) -> None:
    catalog = FreeFontCatalog(tmp_path / "cache")
    with patch("fontvault.core.catalog.httpx.Client", side_effect=OSError("offline")):
        families = catalog.fetch_catalog(force_refresh=True)
    assert len(families) == len(OFFLINE_FALLBACK_FONTS)
    assert any(f.id == "inter" for f in families)


def test_catalog_download_custom_url_zip(tmp_path: Path) -> None:
    ttf = create_synthetic_ttf(tmp_path / "CoolFont.ttf", family="CoolFont")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.write(ttf, arcname="../nested/CoolFont.ttf")
    zip_bytes = buf.getvalue()

    mock_resp = MagicMock()
    mock_resp.content = zip_bytes
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    catalog = FreeFontCatalog(tmp_path / "cache")
    dest = tmp_path / "custom"
    with patch("fontvault.core.catalog.httpx.Client", return_value=mock_client):
        files = catalog.download_from_custom_url("https://example.com/cool.zip", dest)

    assert len(files) == 1
    assert files[0].parent == dest
    assert files[0].name == "CoolFont.ttf"


def test_install_font_user_mocked_registry(tmp_path: Path, monkeypatch) -> None:
    ttf = create_synthetic_ttf(tmp_path / "MyBrand.ttf", family="MyBrand", subfamily="Regular")
    fake_user_fonts = tmp_path / "WinUserFonts"
    monkeypatch.setattr(installer_win, "get_user_fonts_dir", lambda: fake_user_fonts)

    fake_key = MagicMock()
    fake_ctx = MagicMock()
    fake_ctx.__enter__.return_value = fake_key

    with (
        patch("fontvault.core.installer_win.winreg.CreateKeyEx", return_value=fake_ctx) as mock_reg,
        patch("fontvault.core.installer_win.winreg.SetValueEx") as mock_set,
        patch("fontvault.core.installer_win.ctypes.windll.gdi32.AddFontResourceW") as mock_add,
        patch("fontvault.core.installer_win._broadcast_font_change") as mock_bcast,
    ):
        installed_path = installer_win.install_font_user(ttf)

    assert installed_path == fake_user_fonts / "MyBrand.ttf"
    assert installed_path.exists()
    mock_reg.assert_called_once()
    mock_set.assert_called_once()
    assert "(TrueType)" in mock_set.call_args[0][1]
    mock_add.assert_called_once_with(str(installed_path))
    mock_bcast.assert_called_once()


def test_ui_offscreen_smoke(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from fontvault.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    create_synthetic_ttf(paths.custom_fonts_dir / "SmokeFont.ttf", family="SmokeFont")

    with patch("fontvault.ui.main_window.MainWindow.start_scan", return_value=None):
        win = MainWindow(paths)
        assert "FontVault" in win.windowTitle()
        win.close()
        win.deleteLater()
    app.processEvents()


def test_catalog_download_preview_ttf_and_cache_hit(tmp_path: Path) -> None:
    ttf = create_synthetic_ttf(tmp_path / "PreviewMock.ttf", family="PreviewMock")
    ttf_bytes = ttf.read_bytes()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = ttf_bytes

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.return_value = mock_resp

    catalog = FreeFontCatalog(tmp_path / "cache")
    fam = OnlineFontFamily(id="preview-mock", family="Preview Mock", category="sans-serif", weights=[400])

    with patch("fontvault.core.catalog.httpx.Client", return_value=mock_client):
        first_path = catalog.download_preview_ttf(fam)
        assert first_path.exists()
        assert first_path.parent == catalog.preview_cache_dir

    # Second call uses local cache without hitting network.
    with patch("fontvault.core.catalog.httpx.Client", side_effect=AssertionError("Should use cache")):
        second_path = catalog.download_preview_ttf(fam)
        assert second_path == first_path


def test_catalog_tab_renders_online_preview_card(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from fontvault.ui.catalog_tab import CatalogTab
    from fontvault.ui.widgets import FontLoaderCache

    app = QApplication.instance() or QApplication([])
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)
    tab = CatalogTab(paths, FontLoaderCache())

    fam = OnlineFontFamily(id="inter", family="Inter", category="sans-serif", weights=[400, 700])
    preview_ttf = create_synthetic_ttf(tab.catalog_service.preview_cache_dir / "inter.ttf", family="Inter")
    assert preview_ttf.exists()

    tab._on_catalog_loaded([fam])
    assert "inter" in tab._cards_by_id
    card = tab._cards_by_id["inter"]
    assert card._loaded_item is not None
    tab.stop_background_workers()
    tab.close()
    tab.deleteLater()
    app.processEvents()
    from PySide6.QtGui import QFontDatabase
    QFontDatabase.removeAllApplicationFonts()


def test_theme_toggle_persists_setting(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from fontvault.config import load_settings
    from fontvault.ui.main_window import MainWindow
    from fontvault.ui.theme import DARK_STYLESHEET, LIGHT_STYLESHEET, get_stylesheet

    assert get_stylesheet("dark") == DARK_STYLESHEET
    assert get_stylesheet("light") == LIGHT_STYLESHEET

    app = QApplication.instance() or QApplication([])
    paths = resolve_paths(portable_override=True, base_dir=tmp_path)

    with patch("fontvault.ui.main_window.MainWindow.start_scan", return_value=None):
        win = MainWindow(paths)
        assert win.settings.theme == "dark"
        assert "claro" in win.theme_btn.text().lower()

        win.toggle_theme()
        assert win.settings.theme == "light"
        assert "oscuro" in win.theme_btn.text().lower()
        assert load_settings(paths).theme == "light"

        win.toggle_theme()
        assert win.settings.theme == "dark"
        assert load_settings(paths).theme == "dark"

        win.close()
        win.deleteLater()
    app.processEvents()
