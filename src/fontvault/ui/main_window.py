"""Main application window for FontVault."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fontvault import __app_name__, __version__
from fontvault.config import AppPaths, AppSettings, load_settings, save_settings
from fontvault.core.backup import export_fonts, import_fonts_to_custom
from fontvault.core.installer_win import delete_font_item, install_font_user
from fontvault.core.scanner import FontScanner
from fontvault.models import BackupResult, FontItem, FontSource
from fontvault.ui.catalog_tab import CatalogTab
from fontvault.ui.theme import get_stylesheet
from fontvault.ui.widgets import (
    THUMBNAIL_DEFAULT,
    FontCardWidget,
    FontLoaderCache,
    LivePreviewPanel,
    format_bytes,
)


logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Background thread scanning system, custom, and application font directories."""

    progress = Signal(str)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, scanner: FontScanner, settings: AppSettings) -> None:
        super().__init__()
        self.scanner = scanner
        self.settings = settings

    def run(self) -> None:
        try:
            items = self.scanner.scan_all(
                self.settings,
                include_apps=True,
                progress_cb=self.progress.emit,
            )
            self.finished_ok.emit(items)
        except Exception as exc:
            self.failed.emit(str(exc))


class BackupWorker(QThread):
    """Background thread exporting selected fonts to ZIP or directory."""

    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, items: list[FontItem], destination: Path, as_zip: bool) -> None:
        super().__init__()
        self.items = items
        self.destination = destination
        self.as_zip = as_zip

    def run(self) -> None:
        try:
            res = export_fonts(self.items, self.destination, as_zip=self.as_zip)
            self.finished_ok.emit(res)
        except Exception as exc:
            self.failed.emit(str(exc))


class BatchLibraryWorker(QThread):
    """Background worker applying bulk install or delete across checked fonts."""

    progress_msg = Signal(str)
    finished_batch = Signal(str, int, int, list)

    def __init__(self, action: str, items: list[FontItem]) -> None:
        super().__init__()
        self.action = action
        self.items = items

    def run(self) -> None:
        ok_count = 0
        skipped_count = 0
        errors: list[str] = []
        total = len(self.items)

        for idx, item in enumerate(self.items, start=1):
            if self.isInterruptionRequested():
                break
            self.progress_msg.emit(f"Procesando ({idx}/{total}): {item.family}...")
            try:
                if self.action == "install":
                    if item.source.is_installed:
                        skipped_count += 1
                        continue
                    install_font_user(item.path)
                    ok_count += 1
                elif self.action == "delete":
                    deleted, reason = delete_font_item(item)
                    if deleted:
                        ok_count += 1
                    else:
                        skipped_count += 1
                        logger.info("Omitida al eliminar '%s': %s", item.path, reason)
            except Exception as exc:
                errors.append(f"{item.path.name}: {exc}")
                logger.warning("Error en operación '%s' para %s: %s", self.action, item.path, exc)

        self.finished_batch.emit(self.action, ok_count, skipped_count, errors)


class MainWindow(QMainWindow):
    """Primary desktop window coordinating library views, backups, catalog, and preview."""

    PAGE_SIZE = 75

    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.settings = load_settings(paths)
        self.scanner = FontScanner(paths)
        self.font_cache = FontLoaderCache()

        self._all_fonts: list[FontItem] = []
        self._filtered_fonts: list[FontItem] = []
        self._cards: list[FontCardWidget] = []
        self._checked_paths: set[Path] = set()
        self._active_category = "all"
        self._visible_limit = self.PAGE_SIZE
        self._selected_path: Path | None = None
        self._sync_thumbnails = False
        self._live_preview_text = self.settings.preview_text

        self._active_workers: set[QThread] = set()
        self._scan_worker: ScanWorker | None = None
        self._backup_worker: BackupWorker | None = None
        self._batch_worker: BatchLibraryWorker | None = None

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self._apply_filter)

        self._settings_timer = QTimer(self)
        self._settings_timer.setSingleShot(True)
        self._settings_timer.setInterval(400)
        self._settings_timer.timeout.connect(self._flush_settings)

        mode_label = "Modo Portable" if paths.is_portable else "Modo Instalado"
        self.setWindowTitle(f"{__app_name__} v{__version__} — Gestor de Tipografías ({mode_label})")
        self.resize(1340, 820)

        self._build_ui()
        self.statusBar().showMessage(f"{mode_label} · Datos en: {self.paths.root_dir}")
        self.start_scan()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(250)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 16, 12, 14)
        sb_layout.setSpacing(6)

        brand = QLabel("FontVault")
        brand.setObjectName("BrandTitle")
        sb_layout.addWidget(brand)

        sub_brand = QLabel("Portable" if self.paths.is_portable else "Edición Windows")
        sub_brand.setObjectName("BrandSub")
        sb_layout.addWidget(sub_brand)

        self.theme_btn = QPushButton(self._theme_button_label())
        self.theme_btn.setObjectName("ThemeBtn")
        self.theme_btn.clicked.connect(self.toggle_theme)
        sb_layout.addWidget(self.theme_btn)
        sb_layout.addSpacing(8)

        bib_hdr = QLabel("BIBLIOTECA")
        bib_hdr.setObjectName("SectionHeader")
        sb_layout.addWidget(bib_hdr)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QPushButton] = {}
        nav_defs = [
            ("all", "Todas las fuentes"),
            ("installed", "Instaladas (Windows)"),
            ("custom", "Personalizadas (Bóveda)"),
            ("application", "De Aplicación (Apps)"),
            ("catalog", "Descargar Fuentes Gratis"),
        ]
        for key, label in nav_defs:
            btn = QPushButton(label)
            btn.setObjectName("NavBtn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _c=False, k=key: self._switch_section(k))
            self.nav_group.addButton(btn)
            self.nav_buttons[key] = btn
            sb_layout.addWidget(btn)
        self.nav_buttons["all"].setChecked(True)

        sb_layout.addSpacing(10)
        actions_hdr = QLabel("IMPORTAR Y ESCANEAR")
        actions_hdr.setObjectName("SectionHeader")
        sb_layout.addWidget(actions_hdr)

        import_btn = QPushButton("+ Importar fuente o ZIP")
        import_btn.clicked.connect(self._import_custom_files)
        sb_layout.addWidget(import_btn)

        add_custom_dir_btn = QPushButton("+ Carpeta personalizada")
        add_custom_dir_btn.clicked.connect(self._add_custom_folder)
        sb_layout.addWidget(add_custom_dir_btn)

        add_app_dir_btn = QPushButton("+ Carpeta de aplicación")
        add_app_dir_btn.clicked.connect(self._add_app_folder)
        sb_layout.addWidget(add_app_dir_btn)

        rescan_btn = QPushButton("Reescanear biblioteca")
        rescan_btn.clicked.connect(self.start_scan)
        sb_layout.addWidget(rescan_btn)

        sb_layout.addSpacing(10)
        backup_hdr = QLabel("SALVAR / COPIAS DE SEGURIDAD")
        backup_hdr.setObjectName("SectionHeader")
        sb_layout.addWidget(backup_hdr)

        for label, category in (
            ("Salvar Instaladas (.zip)", "installed"),
            ("Salvar Personalizadas (.zip)", "custom"),
            ("Salvar de Aplicación (.zip)", "application"),
            ("Salvar Todas (.zip)", "all"),
        ):
            b_btn = QPushButton(label)
            b_btn.clicked.connect(lambda _c=False, cat=category: self._backup_category(cat, as_zip=True))
            sb_layout.addWidget(b_btn)

        export_dir_btn = QPushButton("Exportar vista a carpeta...")
        export_dir_btn.clicked.connect(lambda: self._backup_category(self._active_category, as_zip=False))
        sb_layout.addWidget(export_dir_btn)

        logs_btn = QPushButton("Abrir carpeta de logs")
        logs_btn.clicked.connect(self._open_logs_folder)
        sb_layout.addWidget(logs_btn)

        sb_layout.addStretch(1)
        outer.addWidget(sidebar)

        # Main Center + Right Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, 1)

        # Center Stack (Library Grid vs Online Catalog)
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.stack = QStackedWidget()
        center_layout.addWidget(self.stack)

        # Page 0: Library View
        lib_page = QWidget()
        lib_layout = QVBoxLayout(lib_page)
        lib_layout.setContentsMargins(16, 14, 16, 14)
        lib_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por familia, estilo, formato o aplicación...")
        self.search_input.textChanged.connect(lambda _txt: self._search_timer.start())
        top_bar.addWidget(self.search_input, 1)

        self.count_lbl = QLabel("0 fuentes")
        self.count_lbl.setObjectName("CountLabel")
        top_bar.addWidget(self.count_lbl)
        lib_layout.addLayout(top_bar)

        # Bulk selection & actions bar
        batch_bar = QFrame()
        batch_bar.setObjectName("BatchBar")
        batch_layout = QHBoxLayout(batch_bar)
        batch_layout.setContentsMargins(10, 8, 10, 8)
        batch_layout.setSpacing(8)

        select_vis_btn = QPushButton("Seleccionar visibles")
        select_vis_btn.clicked.connect(self.select_visible)
        batch_layout.addWidget(select_vis_btn)

        clear_sel_btn = QPushButton("Limpiar")
        clear_sel_btn.clicked.connect(self.clear_selection)
        batch_layout.addWidget(clear_sel_btn)

        self.selection_lbl = QLabel("0 seleccionadas")
        self.selection_lbl.setObjectName("CountLabel")
        batch_layout.addWidget(self.selection_lbl)
        batch_layout.addStretch(1)

        self.batch_install_btn = QPushButton("Instalar seleccionadas")
        self.batch_install_btn.setObjectName("PrimaryBtn")
        self.batch_install_btn.setEnabled(False)
        self.batch_install_btn.clicked.connect(self._install_selected)
        batch_layout.addWidget(self.batch_install_btn)

        self.batch_backup_btn = QPushButton("Salvar seleccionadas (.zip)")
        self.batch_backup_btn.setEnabled(False)
        self.batch_backup_btn.clicked.connect(self._backup_selected)
        batch_layout.addWidget(self.batch_backup_btn)

        self.batch_delete_btn = QPushButton("Eliminar seleccionadas")
        self.batch_delete_btn.setObjectName("DangerBtn")
        self.batch_delete_btn.setEnabled(False)
        self.batch_delete_btn.clicked.connect(self._delete_selected)
        batch_layout.addWidget(self.batch_delete_btn)
        lib_layout.addWidget(batch_bar)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self.cards_scroll.setWidget(self.cards_container)
        lib_layout.addWidget(self.cards_scroll, 1)

        self.load_more_btn = QPushButton("Cargar más tipografías")
        self.load_more_btn.setVisible(False)
        self.load_more_btn.clicked.connect(self._load_more)
        lib_layout.addWidget(self.load_more_btn)

        self.stack.addWidget(lib_page)

        # Page 1: Free Font Catalog Tab
        self.catalog_tab = CatalogTab(self.paths, self.font_cache)
        self.catalog_tab.fonts_downloaded.connect(self._on_catalog_downloaded)
        self.catalog_tab.preview_ready.connect(self._preview_online_font)
        self.catalog_tab.status_message.connect(self.statusBar().showMessage)
        self.stack.addWidget(self.catalog_tab)

        splitter.addWidget(center_container)

        # Right Live Preview Panel
        self.preview_panel = LivePreviewPanel(self.font_cache)
        self.preview_panel.live_text_changed.connect(self._on_live_text_changed)
        self.preview_panel.sync_thumbnails_toggled.connect(self._on_sync_toggled)
        self.preview_panel.install_clicked.connect(self._install_single_font)
        self.preview_panel.backup_clicked.connect(self._backup_single_font)
        splitter.addWidget(self.preview_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

    def _register_worker(self, worker: QThread) -> None:
        self._active_workers.add(worker)

        def _cleanup() -> None:
            self._active_workers.discard(worker)
            worker.deleteLater()

        worker.finished.connect(_cleanup)

    def _flush_settings(self) -> None:
        save_settings(self.paths, self.settings)

    def _open_logs_folder(self) -> None:
        self.paths.logs_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.paths.logs_dir)))

    def start_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.statusBar().showMessage("Escaneando tipografías...")
        worker = ScanWorker(self.scanner, self.settings)
        self._scan_worker = worker
        self._register_worker(worker)
        worker.progress.connect(self.statusBar().showMessage)
        worker.finished_ok.connect(self._on_scan_finished)
        worker.failed.connect(self._on_scan_failed)
        worker.start()

    def _on_scan_failed(self, err: str) -> None:
        logger.error("Error durante escaneo: %s", err)
        self.statusBar().showMessage(f"Error durante escaneo: {err}")

    def _on_scan_finished(self, items: list[FontItem]) -> None:
        self._all_fonts = items
        self._update_nav_counts()
        self._apply_filter()
        mode = "Portable" if self.paths.is_portable else "Instalado"
        self.statusBar().showMessage(
            f"Listo ({mode}) · {len(items)} tipografías indexadas en {self.paths.root_dir}"
        )
        if self._filtered_fonts and self._selected_path is None:
            self._select_font(self._filtered_fonts[0])

    def _update_nav_counts(self) -> None:
        total = len(self._all_fonts)
        installed = sum(1 for f in self._all_fonts if f.source.is_installed)
        custom = sum(1 for f in self._all_fonts if f.source == FontSource.CUSTOM)
        apps = sum(1 for f in self._all_fonts if f.source == FontSource.APPLICATION)

        self.nav_buttons["all"].setText(f"Todas las fuentes ({total})")
        self.nav_buttons["installed"].setText(f"Instaladas Windows ({installed})")
        self.nav_buttons["custom"].setText(f"Personalizadas ({custom})")
        self.nav_buttons["application"].setText(f"De Aplicación ({apps})")

    def _switch_section(self, key: str) -> None:
        if key == "catalog":
            self.stack.setCurrentIndex(1)
            if not self.catalog_tab._families:
                self.catalog_tab.load_catalog()
            return
        self.stack.setCurrentIndex(0)
        self._active_category = key
        self._apply_filter()

    def _items_for_category(self, category: str) -> list[FontItem]:
        if category == "installed":
            return [f for f in self._all_fonts if f.source.is_installed]
        if category == "custom":
            return [f for f in self._all_fonts if f.source == FontSource.CUSTOM]
        if category == "application":
            return [f for f in self._all_fonts if f.source == FontSource.APPLICATION]
        return list(self._all_fonts)

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().lower()
        base = self._items_for_category(self._active_category)
        if query:
            self._filtered_fonts = [
                f for f in base
                if query in f.family.lower()
                or query in f.subfamily.lower()
                or query in f.app_name.lower()
                or query in f.format.lower()
                or query in f.path.name.lower()
            ]
        else:
            self._filtered_fonts = base
        self._visible_limit = self.PAGE_SIZE
        self._render_cards()

    def _load_more(self) -> None:
        self._visible_limit += self.PAGE_SIZE
        self._render_cards()

    def _render_cards(self) -> None:
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()

        subset = self._filtered_fonts[: self._visible_limit]
        self.count_lbl.setText(f"{len(subset)} de {len(self._filtered_fonts)} fuentes")
        self.load_more_btn.setVisible(len(self._filtered_fonts) > len(subset))

        thumb_text = self._live_preview_text if self._sync_thumbnails else THUMBNAIL_DEFAULT
        for font_item in subset:
            card = FontCardWidget(
                font_item,
                self.font_cache,
                preview_text=thumb_text,
                is_checked=font_item.path in self._checked_paths,
            )
            card.set_selected(self._selected_path == font_item.path)
            card.checked_changed.connect(self._on_card_checked)
            card.selected.connect(self._select_font)
            card.backup_requested.connect(self._backup_single_font)
            card.install_requested.connect(self._install_single_font)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

        self.cards_layout.addStretch(1)
        self._update_batch_bar()

    def _select_font(self, item: FontItem) -> None:
        self._selected_path = item.path
        for card in self._cards:
            card.set_selected(card.item.path == item.path)
        self.preview_panel.set_font(item)

    def _preview_online_font(self, item: FontItem) -> None:
        self._selected_path = item.path
        self.preview_panel.set_font(item)
        self.statusBar().showMessage(f"Vista previa online: {item.family} ({item.subfamily})")

    def _on_live_text_changed(self, text: str) -> None:
        self._live_preview_text = text
        self.settings.preview_text = text
        self._settings_timer.start()
        if self._sync_thumbnails:
            for card in self._cards:
                card.set_preview_text(text)
            self.catalog_tab.set_thumbnail_text(text)

    def _on_sync_toggled(self, enabled: bool) -> None:
        self._sync_thumbnails = enabled
        text = self._live_preview_text if enabled else THUMBNAIL_DEFAULT
        for card in self._cards:
            card.set_preview_text(text)
        self.catalog_tab.set_thumbnail_text(text)

    def _install_single_font(self, item: FontItem) -> None:
        try:
            source_path = item.path
            if item.source == FontSource.ONLINE_PREVIEW:
                imported = import_fonts_to_custom(item.path, self.paths.custom_fonts_dir)
                if imported:
                    clean_name = f"{item.family}-{item.subfamily}".replace(" ", "-") + item.path.suffix
                    clean_target = self.paths.custom_fonts_dir / clean_name
                    if not clean_target.exists():
                        imported[0].rename(clean_target)
                        source_path = clean_target
                    else:
                        source_path = imported[0]

            dest = install_font_user(source_path)
            QMessageBox.information(
                self,
                "Fuente instalada",
                f"'{item.family} ({item.subfamily})' instalada correctamente para tu usuario en:\n{dest}",
            )
            self.start_scan()
        except Exception as exc:
            QMessageBox.warning(self, "Error al instalar fuente", str(exc))

    def _backup_single_font(self, item: FontItem) -> None:
        default_name = f"FontVault-{item.family}-{datetime.now().strftime('%Y%m%d')}.zip"
        dest_str, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar tipografía como ZIP",
            str(self.paths.backups_dir / default_name),
            "Archivo ZIP (*.zip)",
        )
        if not dest_str:
            return
        self._run_backup([item], Path(dest_str), as_zip=True)

    def _backup_category(self, category: str, as_zip: bool) -> None:
        items = self._items_for_category(category)
        if not items:
            QMessageBox.information(
                self,
                "Sin fuentes",
                "No hay tipografías en esta categoría para respaldar.",
            )
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        if as_zip:
            default_path = self.paths.backups_dir / f"FontVault-Backup-{category}-{stamp}.zip"
            dest_str, _ = QFileDialog.getSaveFileName(
                self,
                f"Salvar fuentes ({category})",
                str(default_path),
                "Archivo ZIP (*.zip)",
            )
            if not dest_str:
                return
            dest = Path(dest_str)
        else:
            dest_str = QFileDialog.getExistingDirectory(
                self,
                "Seleccionar carpeta destino para exportar fuentes",
                str(self.paths.backups_dir),
            )
            if not dest_str:
                return
            dest = Path(dest_str) / f"FontVault-Backup-{category}-{stamp}"

        self._run_backup(items, dest, as_zip=as_zip)

    def _run_backup(self, items: list[FontItem], dest: Path, as_zip: bool) -> None:
        if self._backup_worker and self._backup_worker.isRunning():
            QMessageBox.information(self, "Backup en curso", "Espera a que termine la copia actual.")
            return
        self.statusBar().showMessage(f"Salvando {len(items)} tipografías en {dest}...")
        worker = BackupWorker(items, dest, as_zip=as_zip)
        self._backup_worker = worker
        self._register_worker(worker)
        worker.finished_ok.connect(self._on_backup_done)
        worker.failed.connect(
            lambda err: QMessageBox.warning(self, "Error en copia de seguridad", err)
        )
        worker.start()

    def _on_backup_done(self, result: BackupResult) -> None:
        msg = (
            f"Copia completada: {result.copied_count} fuentes salvadas "
            f"({format_bytes(result.total_bytes)}) en:\n{result.destination}"
        )
        if result.errors:
            msg += f"\n\nAvisos ({len(result.errors)}): " + "; ".join(result.errors[:3])
        self.statusBar().showMessage(f"Backup completado: {result.copied_count} fuentes.")
        QMessageBox.information(self, "Copia de seguridad completada", msg)

    def _import_custom_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar fuentes personalizadas o paquetes ZIP",
            str(Path.home()),
            "Fuentes y ZIP (*.ttf *.otf *.ttc *.zip)",
        )
        if not files:
            return
        total = 0
        for file_str in files:
            imported = import_fonts_to_custom(Path(file_str), self.paths.custom_fonts_dir)
            total += len(imported)
        QMessageBox.information(
            self,
            "Importación completada",
            f"Se importaron {total} archivo(s) de fuente a tu bóveda personalizada.",
        )
        self.start_scan()

    def _add_custom_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Añadir carpeta de fuentes personalizadas")
        if not folder:
            return
        if folder not in self.settings.custom_scan_dirs:
            self.settings.custom_scan_dirs.append(folder)
            save_settings(self.paths, self.settings)
        self.start_scan()

    def _add_app_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Añadir carpeta de aplicación a escanear")
        if not folder:
            return
        if folder not in self.settings.app_scan_dirs:
            self.settings.app_scan_dirs.append(folder)
            save_settings(self.paths, self.settings)
        self.start_scan()

    def _theme_button_label(self) -> str:
        return "🌙 Modo oscuro" if self.settings.theme == "light" else "☀ Modo claro"

    def toggle_theme(self) -> None:
        """Toggle between Dark and Light modes and persist preference."""
        self.settings.theme = "light" if self.settings.theme != "light" else "dark"
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_stylesheet(self.settings.theme))
        self.theme_btn.setText(self._theme_button_label())
        save_settings(self.paths, self.settings)
        mode_txt = "claro" if self.settings.theme == "light" else "oscuro"
        self.statusBar().showMessage(f"Tema cambiado a modo {mode_txt}.")

    def _on_card_checked(self, item: FontItem, checked: bool) -> None:
        if checked:
            self._checked_paths.add(item.path)
        else:
            self._checked_paths.discard(item.path)
        self._update_batch_bar()

    def select_visible(self) -> None:
        """Mark all currently visible library cards."""
        for card in self._cards:
            self._checked_paths.add(card.item.path)
            card.set_checked(True)
        self._update_batch_bar()

    def clear_selection(self) -> None:
        """Clear all checked library selections."""
        self._checked_paths.clear()
        for card in self._cards:
            card.set_checked(False)
        self._update_batch_bar()

    def _selected_library_items(self) -> list[FontItem]:
        return [item for item in self._all_fonts if item.path in self._checked_paths]

    def _update_batch_bar(self) -> None:
        valid_paths = {item.path for item in self._all_fonts}
        if self._all_fonts:
            self._checked_paths.intersection_update(valid_paths)
        count = len(self._checked_paths)
        self.selection_lbl.setText(f"{count} seleccionada{'s' if count != 1 else ''}")
        has_sel = count > 0
        self.batch_install_btn.setEnabled(has_sel)
        self.batch_backup_btn.setEnabled(has_sel)
        self.batch_delete_btn.setEnabled(has_sel)

    def _install_selected(self) -> None:
        items = self._selected_library_items()
        if not items:
            return
        if self._batch_worker and self._batch_worker.isRunning():
            QMessageBox.information(self, "Operación en curso", "Espera a que termine la operación actual.")
            return
        self._run_batch_library("install", items)

    def _backup_selected(self) -> None:
        items = self._selected_library_items()
        if not items:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        default_path = self.paths.backups_dir / f"FontVault-Seleccion-{stamp}.zip"
        dest_str, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar tipografías seleccionadas",
            str(default_path),
            "Archivo ZIP (*.zip)",
        )
        if not dest_str:
            return
        self._run_backup(items, Path(dest_str), as_zip=True)

    def _delete_selected(self) -> None:
        items = self._selected_library_items()
        if not items:
            return
        if self._batch_worker and self._batch_worker.isRunning():
            QMessageBox.information(self, "Operación en curso", "Espera a que termine la operación actual.")
            return

        deletable = [
            f for f in items if f.source in (FontSource.CUSTOM, FontSource.INSTALLED_USER)
        ]
        protected = len(items) - len(deletable)
        if not deletable:
            QMessageBox.information(
                self,
                "Fuentes protegidas",
                "Las fuentes del sistema (C:\\Windows\\Fonts) y de aplicaciones están protegidas y no se eliminan.",
            )
            return

        prompt = (
            f"Se eliminarán o desinstalarán {len(deletable)} fuente(s) "
            f"(Personalizadas y de Usuario)."
        )
        if protected:
            prompt += f"\nSe omitirán {protected} fuente(s) protegidas de Sistema o Aplicación."
        prompt += "\n\n¿Deseas continuar?"

        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Release Qt font handles before unlinking files on Windows.
        for item in deletable:
            self.font_cache.release_font(item.path)

        self._run_batch_library("delete", items)

    def _run_batch_library(self, action: str, items: list[FontItem]) -> None:
        self.batch_install_btn.setEnabled(False)
        self.batch_backup_btn.setEnabled(False)
        self.batch_delete_btn.setEnabled(False)
        worker = BatchLibraryWorker(action, items)
        self._batch_worker = worker
        self._register_worker(worker)
        worker.progress_msg.connect(self.statusBar().showMessage)
        worker.finished_batch.connect(self._on_batch_library_done)
        worker.start()

    def _on_batch_library_done(
        self,
        action: str,
        ok_count: int,
        skipped_count: int,
        errors: list[str],
    ) -> None:
        verb = "instaladas" if action == "install" else "eliminadas/desinstaladas"
        msg = f"Operación en lote completada: {ok_count} {verb}."
        if skipped_count:
            msg += f" Omitidas: {skipped_count}."
        if errors:
            msg += f"\n\nErrores ({len(errors)}): " + "; ".join(errors[:3])
        self.statusBar().showMessage(msg.splitlines()[0])
        QMessageBox.information(self, "Operación completada", msg)
        self.clear_selection()
        self.start_scan()

    def _on_catalog_downloaded(self, _files: list[Path], _installed: bool) -> None:
        self.start_scan()

    def closeEvent(self, event) -> None:
        if self._settings_timer.isActive():
            self._settings_timer.stop()
            self._flush_settings()
        self.catalog_tab.stop_background_workers()
        for worker in list(self._active_workers):
            if worker.isRunning():
                worker.requestInterruption()
                worker.wait(2500)
        super().closeEvent(event)
