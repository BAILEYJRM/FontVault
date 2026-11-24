"""Free online font catalog tab with live previews and custom URL/portal importer."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fontvault.config import AppPaths
from fontvault.core.catalog import COMMON_PORTALS, FreeFontCatalog
from fontvault.core.installer_win import install_font_user
from fontvault.core.metadata import parse_font_file
from fontvault.models import FontItem, FontSource, OnlineFontFamily
from fontvault.ui.widgets import FontLoaderCache, THUMBNAIL_DEFAULT


class CatalogFetchWorker(QThread):
    """Background worker loading free open-source font catalog."""

    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, catalog: FreeFontCatalog, force_refresh: bool = False) -> None:
        super().__init__()
        self.catalog = catalog
        self.force_refresh = force_refresh

    def run(self) -> None:
        try:
            families = self.catalog.fetch_catalog(force_refresh=self.force_refresh)
            self.finished_ok.emit(families)
        except Exception as exc:
            self.failed.emit(str(exc))


class FontDownloadWorker(QThread):
    """Background worker downloading font files from catalog or direct URL."""

    finished_ok = Signal(list, bool)
    failed = Signal(str)

    def __init__(
        self,
        catalog: FreeFontCatalog,
        dest_dir: Path,
        font_id: str | None = None,
        custom_url: str | None = None,
        auto_install: bool = False,
    ) -> None:
        super().__init__()
        self.catalog = catalog
        self.dest_dir = dest_dir
        self.font_id = font_id
        self.custom_url = custom_url
        self.auto_install = auto_install

    def run(self) -> None:
        try:
            if self.custom_url:
                files = self.catalog.download_from_custom_url(self.custom_url, self.dest_dir)
            elif self.font_id:
                files = self.catalog.download_family_ttf(self.font_id, self.dest_dir)
            else:
                raise ValueError("Origen de descarga no especificado.")

            if self.auto_install:
                for font_path in files:
                    install_font_user(font_path)

            self.finished_ok.emit(files, self.auto_install)
        except Exception as exc:
            self.failed.emit(str(exc))


class FontPreviewWorker(QThread):
    """Background worker fetching a single TTF to preview an online font before installing."""

    preview_loaded = Signal(str, object)
    failed = Signal(str)

    def __init__(self, catalog: FreeFontCatalog, family: OnlineFontFamily) -> None:
        super().__init__()
        self.catalog = catalog
        self.family = family

    def run(self) -> None:
        try:
            ttf_path = self.catalog.download_preview_ttf(self.family)
            item = parse_font_file(ttf_path, source=FontSource.ONLINE_PREVIEW)
            if item is None:
                raise RuntimeError(f"Archivo de vista previa inválido para '{self.family.family}'.")
            if not item.family or item.family == ttf_path.stem:
                item.family = self.family.family
                item.full_name = f"{self.family.family} {item.subfamily}".strip()
            self.preview_loaded.emit(self.family.id, item)
        except Exception as exc:
            self.failed.emit(str(exc))


class ThumbnailPrefetchWorker(QThread):
    """Background worker gently prefetching miniature previews for visible catalog cards."""

    thumbnail_ready = Signal(str, object)

    def __init__(self, catalog: FreeFontCatalog, families: list[OnlineFontFamily]) -> None:
        super().__init__()
        self.catalog = catalog
        self.families = families

    def run(self) -> None:
        for fam in self.families:
            if self.isInterruptionRequested():
                return
            if self.catalog.get_cached_preview(fam.id) is not None:
                continue
            try:
                path = self.catalog.download_preview_ttf(fam)
                if not self.isInterruptionRequested():
                    self.thumbnail_ready.emit(fam.id, path)
            except Exception:
                continue


class OnlineFontCardWidget(QFrame):
    """Catalog card with inline miniature preview and download/install actions."""

    preview_requested = Signal(object)
    download_requested = Signal(str, bool)

    def __init__(
        self,
        family: OnlineFontFamily,
        font_cache: FontLoaderCache,
        cached_path: Path | None = None,
        preview_text: str = THUMBNAIL_DEFAULT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.family = family
        self.font_cache = font_cache
        self._preview_text = preview_text or THUMBNAIL_DEFAULT
        self._loaded_item: FontItem | None = None

        self.setObjectName("FontCard")
        self.setProperty("selected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        name_lbl = QLabel(family.family)
        name_lbl.setObjectName("CardTitle")
        header.addWidget(name_lbl, 1)

        cat_badge = QLabel(family.category)
        cat_badge.setObjectName("Badge")
        header.addWidget(cat_badge)

        weights_txt = ", ".join(str(w) for w in family.weights[:6]) or "400"
        weights_lbl = QLabel(f"Pesos: {weights_txt}")
        weights_lbl.setObjectName("MutedText")
        header.addWidget(weights_lbl)
        layout.addLayout(header)

        self.specimen_lbl = QLabel()
        self.specimen_lbl.setObjectName("CardSpecimen")
        self.specimen_lbl.setWordWrap(False)
        self.specimen_lbl.setMinimumHeight(42)
        self.specimen_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.specimen_lbl)

        if cached_path is not None:
            self.apply_preview_font(cached_path, self._preview_text)
        else:
            self.specimen_lbl.setText("Haz clic en 'Vista previa' para cargar la muestra tipográfica...")

        footer = QHBoxLayout()
        footer.setSpacing(6)
        lic_lbl = QLabel("Licencia libre · Fontsource / Google Fonts")
        lic_lbl.setObjectName("MutedText")
        footer.addWidget(lic_lbl, 1)

        preview_btn = QPushButton("Vista previa")
        preview_btn.clicked.connect(lambda: self.preview_requested.emit(self.family))
        footer.addWidget(preview_btn)

        save_btn = QPushButton("Descargar a Personalizadas")
        save_btn.clicked.connect(lambda: self.download_requested.emit(self.family.id, False))
        footer.addWidget(save_btn)

        install_btn = QPushButton("Descargar e Instalar")
        install_btn.setObjectName("PrimaryBtn")
        install_btn.clicked.connect(lambda: self.download_requested.emit(self.family.id, True))
        footer.addWidget(install_btn)
        layout.addLayout(footer)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.preview_requested.emit(self.family)
        super().mousePressEvent(event)

    def apply_preview_font(self, font_path: Path, preview_text: str | None = None) -> None:
        """Render the card specimen label in the downloaded preview font."""
        if preview_text is not None:
            self._preview_text = preview_text or THUMBNAIL_DEFAULT
        item = FontItem(
            path=font_path,
            family=self.family.family,
            subfamily="Regular",
            full_name=self.family.family,
            postscript_name="",
            version="",
            designer="",
            license_info="",
            format="TTF",
            source=FontSource.ONLINE_PREVIEW,
        )
        self._loaded_item = item
        self.specimen_lbl.setFont(self.font_cache.qfont_for_item(item, 18))
        self.specimen_lbl.setText(self._preview_text)

    def set_preview_text(self, text: str) -> None:
        """Update displayed thumbnail text if this card already loaded its preview font."""
        self._preview_text = text.strip() or THUMBNAIL_DEFAULT
        if self._loaded_item is not None:
            self.specimen_lbl.setText(self._preview_text)

    def set_selected(self, is_selected: bool) -> None:
        self.setProperty("selected", "true" if is_selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class CatalogTab(QWidget):
    """UI tab for browsing, previewing, downloading, and installing free fonts."""

    fonts_downloaded = Signal(list, bool)
    preview_ready = Signal(object)
    status_message = Signal(str)

    def __init__(
        self,
        paths: AppPaths,
        font_cache: FontLoaderCache,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.paths = paths
        self.font_cache = font_cache
        self.catalog_service = FreeFontCatalog(paths.cache_dir)
        self._families: list[OnlineFontFamily] = []
        self._filtered: list[OnlineFontFamily] = []
        self._cards_by_id: dict[str, OnlineFontCardWidget] = {}
        self._selected_id: str | None = None
        self._thumbnail_text: str = THUMBNAIL_DEFAULT
        self._visible_limit = 60
        self._fetch_worker: CatalogFetchWorker | None = None
        self._dl_worker: FontDownloadWorker | None = None
        self._preview_worker: FontPreviewWorker | None = None
        self._prefetch_worker: ThumbnailPrefetchWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(12)

        # Portal shortcuts + Direct URL download bar
        portal_box = QFrame()
        portal_box.setObjectName("FontCard")
        portal_layout = QVBoxLayout(portal_box)
        portal_layout.setContentsMargins(12, 10, 12, 10)
        portal_layout.setSpacing(8)

        portal_hdr = QLabel("PÁGINAS COMUNES DE FUENTES GRATUITAS Y DESCARGA POR URL / ZIP")
        portal_hdr.setObjectName("SectionHeader")
        portal_layout.addWidget(portal_hdr)

        links_row = QHBoxLayout()
        links_row.setSpacing(6)
        for name, url in COMMON_PORTALS:
            btn = QPushButton(f"Abrir {name}")
            btn.clicked.connect(lambda _c=False, u=url: QDesktopServices.openUrl(QUrl(u)))
            links_row.addWidget(btn)
        links_row.addStretch(1)
        portal_layout.addLayout(links_row)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Pega una URL directa a un archivo .zip, .ttf o .otf (ej. enlace de descarga de Font Squirrel / DaFont / GitHub)..."
        )
        url_row.addWidget(self.url_input, 1)

        self.url_install_chk = QCheckBox("Instalar en Windows")
        self.url_install_chk.setChecked(True)
        url_row.addWidget(self.url_install_chk)

        self.url_dl_btn = QPushButton("Descargar URL")
        self.url_dl_btn.setObjectName("AccentBtn")
        self.url_dl_btn.clicked.connect(self._download_custom_url)
        url_row.addWidget(self.url_dl_btn)
        portal_layout.addLayout(url_row)
        root.addWidget(portal_box)

        # Catalog search & category filter
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Buscar entre más de 1.600 familias gratuitas (Inter, Roboto, JetBrains Mono, Playfair...)..."
        )
        self.search_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search_input, 1)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Todas", "sans-serif", "serif", "monospace", "display", "handwriting"])
        self.category_combo.currentTextChanged.connect(self._apply_filter)
        filter_row.addWidget(self.category_combo)

        self.refresh_btn = QPushButton("Actualizar catálogo")
        self.refresh_btn.clicked.connect(lambda: self.load_catalog(force_refresh=True))
        filter_row.addWidget(self.refresh_btn)
        root.addLayout(filter_row)

        self.count_lbl = QLabel("Cargando catálogo gratuito...")
        self.count_lbl.setObjectName("MutedText")
        root.addWidget(self.count_lbl)

        # Scrollable list of online font cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)
        root.addWidget(self.scroll, 1)

        self.load_more_btn = QPushButton("Mostrar más resultados")
        self.load_more_btn.setVisible(False)
        self.load_more_btn.clicked.connect(self._show_more)
        root.addWidget(self.load_more_btn)

    def stop_background_workers(self) -> None:
        """Stop thumbnail prefetch worker cleanly on widget/window close."""
        if self._prefetch_worker and self._prefetch_worker.isRunning():
            self._prefetch_worker.requestInterruption()
            self._prefetch_worker.wait(1500)

    def set_thumbnail_text(self, text: str) -> None:
        """Sync live typing preview text to all loaded online font miniatures."""
        self._thumbnail_text = text.strip() or THUMBNAIL_DEFAULT
        for card in self._cards_by_id.values():
            card.set_preview_text(self._thumbnail_text)

    def load_catalog(self, force_refresh: bool = False) -> None:
        if self._fetch_worker and self._fetch_worker.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.status_message.emit("Consultando catálogo gratuito de Fontsource / Google Fonts...")
        self._fetch_worker = CatalogFetchWorker(self.catalog_service, force_refresh=force_refresh)
        self._fetch_worker.finished_ok.connect(self._on_catalog_loaded)
        self._fetch_worker.failed.connect(self._on_catalog_failed)
        self._fetch_worker.start()

    def _on_catalog_loaded(self, families: list[OnlineFontFamily]) -> None:
        self.refresh_btn.setEnabled(True)
        self._families = families
        self._apply_filter()
        self.status_message.emit(f"Catálogo gratuito listo: {len(families)} familias disponibles.")

    def _on_catalog_failed(self, error: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.status_message.emit(f"Error cargando catálogo online: {error}")

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().lower()
        cat = self.category_combo.currentText()
        self._visible_limit = 60

        filtered = []
        for fam in self._families:
            if cat != "Todas" and fam.category.lower() != cat.lower():
                continue
            if query and query not in fam.family.lower() and query not in fam.id.lower():
                continue
            filtered.append(fam)
        self._filtered = filtered
        self._render_cards()

    def _show_more(self) -> None:
        self._visible_limit += 60
        self._render_cards()

    def _render_cards(self) -> None:
        self.stop_background_workers()
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards_by_id.clear()

        subset = self._filtered[: self._visible_limit]
        self.count_lbl.setText(
            f"Mostrando {len(subset)} de {len(self._filtered)} familias gratuitas encontradas"
        )
        self.load_more_btn.setVisible(len(self._filtered) > len(subset))

        to_prefetch: list[OnlineFontFamily] = []
        for fam in subset:
            cached = self.catalog_service.get_cached_preview(fam.id)
            if cached is None and len(to_prefetch) < 12:
                to_prefetch.append(fam)

            card = OnlineFontCardWidget(
                fam,
                self.font_cache,
                cached_path=cached,
                preview_text=self._thumbnail_text,
            )
            card.set_selected(self._selected_id == fam.id)
            card.preview_requested.connect(self._request_preview)
            card.download_requested.connect(self._download_family)
            self._cards_by_id[fam.id] = card
            self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

        if to_prefetch:
            self._prefetch_worker = ThumbnailPrefetchWorker(self.catalog_service, to_prefetch)
            self._prefetch_worker.thumbnail_ready.connect(self._on_thumbnail_prefetched)
            self._prefetch_worker.start()

    def _on_thumbnail_prefetched(self, font_id: str, path: Path) -> None:
        card = self._cards_by_id.get(font_id)
        if card is not None:
            card.apply_preview_font(path, self._thumbnail_text)

    def _request_preview(self, family: OnlineFontFamily) -> None:
        self._selected_id = family.id
        for fid, card in self._cards_by_id.items():
            card.set_selected(fid == family.id)

        self.status_message.emit(f"Cargando vista previa de '{family.family}'...")
        self._preview_worker = FontPreviewWorker(self.catalog_service, family)
        self._preview_worker.preview_loaded.connect(self._on_preview_loaded)
        self._preview_worker.failed.connect(
            lambda err: self.status_message.emit(f"No se pudo cargar vista previa: {err}")
        )
        self._preview_worker.start()

    def _on_preview_loaded(self, font_id: str, item: FontItem) -> None:
        card = self._cards_by_id.get(font_id)
        if card is not None:
            card.apply_preview_font(item.path, self._thumbnail_text)
        self.preview_ready.emit(item)

    def _download_family(self, font_id: str, auto_install: bool) -> None:
        if self._dl_worker and self._dl_worker.isRunning():
            QMessageBox.information(self, "Descarga en curso", "Espera a que termine la descarga actual.")
            return
        self.status_message.emit(f"Descargando '{font_id}'...")
        self._dl_worker = FontDownloadWorker(
            self.catalog_service,
            dest_dir=self.paths.custom_fonts_dir,
            font_id=font_id,
            auto_install=auto_install,
        )
        self._dl_worker.finished_ok.connect(self._on_download_done)
        self._dl_worker.failed.connect(self._on_download_failed)
        self._dl_worker.start()

    def _download_custom_url(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "URL vacía", "Introduce una URL directa a un archivo .zip, .ttf o .otf.")
            return
        if self._dl_worker and self._dl_worker.isRunning():
            QMessageBox.information(self, "Descarga en curso", "Espera a que termine la descarga actual.")
            return

        self.url_dl_btn.setEnabled(False)
        self.status_message.emit(f"Descargando desde URL: {url}")
        self._dl_worker = FontDownloadWorker(
            self.catalog_service,
            dest_dir=self.paths.custom_fonts_dir,
            custom_url=url,
            auto_install=self.url_install_chk.isChecked(),
        )
        self._dl_worker.finished_ok.connect(self._on_download_done)
        self._dl_worker.failed.connect(self._on_download_failed)
        self._dl_worker.start()

    def _on_download_done(self, files: list[Path], installed: bool) -> None:
        self.url_dl_btn.setEnabled(True)
        action_txt = "descargadas e instaladas en Windows" if installed else "guardadas en Personalizadas"
        names = ", ".join(p.name for p in files[:4])
        msg = f"{len(files)} fuente(s) {action_txt}: {names}"
        self.status_message.emit(msg)
        QMessageBox.information(self, "Descarga completada", msg)
        self.fonts_downloaded.emit(files, installed)

    def _on_download_failed(self, error: str) -> None:
        self.url_dl_btn.setEnabled(True)
        self.status_message.emit(f"Error en descarga: {error}")
        QMessageBox.warning(self, "Error de descarga", error)
