"""Main application window for FontVault."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
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
from fontvault.core.installer_win import install_font_user
from fontvault.core.scanner import FontScanner
from fontvault.models import BackupResult, FontItem, FontSource
from fontvault.ui.catalog_tab import CatalogTab
from fontvault.ui.widgets import (
    THUMBNAIL_DEFAULT,
    FontCardWidget,
    FontLoaderCache,
    LivePreviewPanel,
    format_bytes,
)


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
        self._active_category = "all"
        self._visible_limit = self.PAGE_SIZE
        self._selected_path: Path | None = None
        self._sync_thumbnails = False
        self._live_preview_text = self.settings.preview_text

        self._scan_worker: ScanWorker | None = None
        self._backup_worker: BackupWorker | None = None

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
        brand.setStyleSheet("font-size: 20px; font-weight: 800; color: #F8FAFC; padding-left: 6px;")
        sb_layout.addWidget(brand)

        sub_brand = QLabel("Portable" if self.paths.is_portable else "Edición Windows")
        sub_brand.setStyleSheet("font-size: 11px; color: #38BDF8; padding-left: 6px; margin-bottom: 10px;")
        sb_layout.addWidget(sub_brand)

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
        self.search_input.textChanged.connect(self._apply_filter)
        top_bar.addWidget(self.search_input, 1)

        self.count_lbl = QLabel("0 fuentes")
        self.count_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        top_bar.addWidget(self.count_lbl)
        lib_layout.addLayout(top_bar)

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

    def start_scan(self) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.statusBar().showMessage("Escaneando tipografías...")
        self._scan_worker = ScanWorker(self.scanner, self.settings)
        self._scan_worker.progress.connect(self.statusBar().showMessage)
        self._scan_worker.finished_ok.connect(self._on_scan_finished)
        self._scan_worker.failed.connect(
            lambda err: self.statusBar().showMessage(f"Error durante escaneo: {err}")
        )
        self._scan_worker.start()

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
            card = FontCardWidget(font_item, self.font_cache, preview_text=thumb_text)
            card.set_selected(self._selected_path == font_item.path)
            card.selected.connect(self._select_font)
            card.backup_requested.connect(self._backup_single_font)
            card.install_requested.connect(self._install_single_font)
            self.cards_layout.addWidget(card)
            self._cards.append(card)

        self.cards_layout.addStretch(1)

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
        save_settings(self.paths, self.settings)
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
        self._backup_worker = BackupWorker(items, dest, as_zip=as_zip)
        self._backup_worker.finished_ok.connect(self._on_backup_done)
        self._backup_worker.failed.connect(
            lambda err: QMessageBox.warning(self, "Error en copia de seguridad", err)
        )
        self._backup_worker.start()

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

    def _on_catalog_downloaded(self, _files: list[Path], _installed: bool) -> None:
        self.start_scan()

    def closeEvent(self, event) -> None:
        self.catalog_tab.stop_background_workers()
        super().closeEvent(event)
