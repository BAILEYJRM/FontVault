"""Free online font catalog tab and custom URL/portal importer."""

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
from fontvault.models import OnlineFontFamily


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


class CatalogTab(QWidget):
    """UI tab for browsing, downloading, and installing free fonts."""

    fonts_downloaded = Signal(list, bool)
    status_message = Signal(str)

    def __init__(self, paths: AppPaths, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.paths = paths
        self.catalog_service = FreeFontCatalog(paths.cache_dir)
        self._families: list[OnlineFontFamily] = []
        self._filtered: list[OnlineFontFamily] = []
        self._visible_limit = 60
        self._fetch_worker: CatalogFetchWorker | None = None
        self._dl_worker: FontDownloadWorker | None = None

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
        self.search_input.setPlaceholderText("Buscar entre más de 1.600 familias gratuitas (Inter, Roboto, JetBrains Mono, Playfair...)...")
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
        self.count_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
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
        while self.list_layout.count() > 0:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        subset = self._filtered[: self._visible_limit]
        self.count_lbl.setText(
            f"Mostrando {len(subset)} de {len(self._filtered)} familias gratuitas encontradas"
        )
        self.load_more_btn.setVisible(len(self._filtered) > len(subset))

        for fam in subset:
            card = QFrame()
            card.setObjectName("FontCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setSpacing(10)

            info_col = QVBoxLayout()
            info_col.setSpacing(2)
            name_lbl = QLabel(fam.family)
            name_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #F8FAFC; background: transparent;")
            info_col.addWidget(name_lbl)

            weights_txt = ", ".join(str(w) for w in fam.weights[:6]) or "400"
            meta_lbl = QLabel(f"Categoría: {fam.category}  ·  Pesos: {weights_txt}  ·  Licencia libre")
            meta_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
            info_col.addWidget(meta_lbl)
            row.addLayout(info_col, 1)

            save_btn = QPushButton("Descargar a Personalizadas")
            save_btn.clicked.connect(
                lambda _c=False, fid=fam.id: self._download_family(fid, auto_install=False)
            )
            row.addWidget(save_btn)

            install_btn = QPushButton("Descargar e Instalar")
            install_btn.setObjectName("PrimaryBtn")
            install_btn.clicked.connect(
                lambda _c=False, fid=fam.id: self._download_family(fid, auto_install=True)
            )
            row.addWidget(install_btn)

            self.list_layout.addWidget(card)

        self.list_layout.addStretch(1)

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
