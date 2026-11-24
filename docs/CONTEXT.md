# FontVault — Context Map (Read First)

Gestor de tipografías para Windows (`Python 3.13`, `PySide6`, `fonttools`, `Pillow`, `httpx`).

## Estructura del Proyecto
- `src/fontvault/__init__.py` — `__version__`, `__app_name__`.
- `src/fontvault/__main__.py` — CLI (`--portable`, `--version`), AppUserModelID Windows, icono, arranque GUI.
- `src/fontvault/config.py` — `AppPaths` (incluye `logs_dir`), `AppSettings`, `resolve_paths()`, detección Portable vs Instalado.
- `src/fontvault/logging_setup.py` — `setup_logging()`, `install_qt_message_handler()`, `faulthandler` y hooks de excepciones.
- `src/fontvault/models.py` — `FontSource`, `FontItem`, `OnlineFontFamily`, `BackupResult`.
- `src/fontvault/core/metadata.py` — `parse_font_file()` con `fontTools.ttLib.TTFont`.
- `src/fontvault/core/scanner.py` — `FontScanner` (Windows Fonts, Personalizadas, De Aplicación + caché incremental).
- `src/fontvault/core/backup.py` — `export_fonts()` (ZIP/carpeta + `manifest.json` SHA-256), `import_fonts_to_custom()`.
- `src/fontvault/core/installer_win.py` — `install_font_user()`, `install_font_system()`, `uninstall_font_user()`, `delete_font_item()`, `is_admin()`.
- `src/fontvault/core/catalog.py` — `FreeFontCatalog` (Fontsource API + jsDelivr + vista previa `download_preview_ttf()` + URLs/ZIP anti zip-slip).
- `src/fontvault/ui/theme.py` — `DARK_STYLESHEET`, `LIGHT_STYLESHEET`, `get_stylesheet()` (`BatchBar`, `DangerBtn`).
- `src/fontvault/ui/widgets.py` — `FontLoaderCache` (`release_font()`), `FontCardWidget` (con checkbox), `LivePreviewPanel`.
- `src/fontvault/ui/catalog_tab.py` — Catálogo online con `OnlineFontCardWidget` (checkbox + vista previa), descargas individuales y en lote.
- `src/fontvault/ui/main_window.py` — `MainWindow`, navegación lateral, tema oscuro/claro, selección múltiple y operaciones en lote.
- `CHANGELOG.md` — Registro histórico de versiones SemVer (`Keep a Changelog`).
- `scripts/generate_assets.py` — Genera `assets/icon.png` y `assets/icon.ico` multi-resolución.
- `scripts/sign_binaries.ps1` — Firma Authenticode SHA-256 (`.pfx` o certificado dev en `Cert:\CurrentUser\My`).
- `scripts/build_all.ps1` — Pipeline completo: icono -> EXEs -> firma -> verificaciones.
- `packaging/` — `version_info.txt`, `portable.spec`, `app.spec`, `setup_wizard.py`, `installer.spec`, `installer.iss`.
- `tests/` — Pruebas pytest con fuentes sintetizadas dinámicamente (`FontBuilder`).

## Rutas de Datos (Portable vs Instalado)
- **Modo Portable** (`--portable`, `FONTVAULT_PORTABLE=1`, `portable.flag` o `bundled_portable.flag`): `<exe_dir>/data/` (`custom_fonts/`, `backups/`, `cache/`, `downloads/`, `logs/`, `settings.json`).
- **Modo Instalado**: `%LOCALAPPDATA%\FontVault\`.
