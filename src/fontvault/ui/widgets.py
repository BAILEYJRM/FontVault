"""Reusable UI widgets: lazy font loader, thumbnail card, and live typing preview."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from fontvault.config import DEFAULT_PREVIEW_TEXT
from fontvault.models import FontItem, FontSource


THUMBNAIL_DEFAULT = "Aa Bb Cc Gg 0123"


def format_bytes(size: int) -> str:
    """Format byte count into human-readable string."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


class FontLoaderCache:
    """Lazy QFontDatabase loader so uninstalled fonts render without startup lag."""

    def __init__(self) -> None:
        self._path_to_family: dict[str, str] = {}

    def family_for_item(self, item: FontItem) -> str:
        """Resolve Qt font family name, registering uninstalled font lazily on demand."""
        if item.source.is_installed:
            return item.family

        key = str(item.path).lower()
        if key in self._path_to_family:
            return self._path_to_family[key]

        font_id = QFontDatabase.addApplicationFont(str(item.path))
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self._path_to_family[key] = families[0]
                return families[0]

        self._path_to_family[key] = item.family
        return item.family

    def qfont_for_item(self, item: FontItem, point_size: int) -> QFont:
        """Return configured QFont instance for thumbnail or live preview."""
        family_name = self.family_for_item(item)
        qfont = QFont(family_name, point_size)
        sub = item.subfamily.lower()
        if "bold" in sub:
            qfont.setBold(True)
        if "italic" in sub or "oblique" in sub:
            qfont.setItalic(True)
        return qfont


class FontCardWidget(QFrame):
    """Card displaying a font's metadata badges, typographic thumbnail, and quick actions."""

    selected = Signal(object)
    backup_requested = Signal(object)
    install_requested = Signal(object)

    def __init__(
        self,
        item: FontItem,
        font_cache: FontLoaderCache,
        preview_text: str = THUMBNAIL_DEFAULT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.font_cache = font_cache
        self.setObjectName("FontCard")
        self.setProperty("selected", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header row: Family + Badges
        header = QHBoxLayout()
        header.setSpacing(6)

        title_lbl = QLabel(f"{item.family}  ·  {item.subfamily}")
        title_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #F8FAFC; background: transparent;")
        title_lbl.setWordWrap(False)
        header.addWidget(title_lbl, 1)

        source_text = (
            f"App: {item.app_name}"
            if item.source == FontSource.APPLICATION and item.app_name
            else item.source.label_es
        )
        source_badge = QLabel(source_text)
        source_badge.setObjectName("Badge")
        header.addWidget(source_badge)

        fmt_badge = QLabel(item.format)
        fmt_badge.setObjectName("FormatBadge")
        header.addWidget(fmt_badge)
        layout.addLayout(header)

        # Typographic Thumbnail Specimen
        self.specimen_lbl = QLabel(preview_text or THUMBNAIL_DEFAULT)
        self.specimen_lbl.setWordWrap(False)
        self.specimen_lbl.setMinimumHeight(46)
        self.specimen_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.specimen_lbl.setStyleSheet(
            "background-color: #0F172A; border-radius: 6px; padding: 6px 10px; color: #F1F5F9;"
        )
        self.specimen_lbl.setFont(self.font_cache.qfont_for_item(item, 19))
        layout.addWidget(self.specimen_lbl)

        # Footer row: size + action buttons
        footer = QHBoxLayout()
        footer.setSpacing(6)

        meta_lbl = QLabel(f"{format_bytes(item.file_size)}  ·  {item.path.name}")
        meta_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; background: transparent;")
        footer.addWidget(meta_lbl, 1)

        preview_btn = QPushButton("Vista previa")
        preview_btn.clicked.connect(lambda: self.selected.emit(self.item))
        footer.addWidget(preview_btn)

        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(lambda: self.backup_requested.emit(self.item))
        footer.addWidget(save_btn)

        if not item.source.is_installed:
            install_btn = QPushButton("Instalar")
            install_btn.setObjectName("PrimaryBtn")
            install_btn.clicked.connect(lambda: self.install_requested.emit(self.item))
            footer.addWidget(install_btn)

        layout.addLayout(footer)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.item)
        super().mousePressEvent(event)

    def set_selected(self, is_selected: bool) -> None:
        self.setProperty("selected", "true" if is_selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_preview_text(self, text: str) -> None:
        self.specimen_lbl.setText(text.strip() or THUMBNAIL_DEFAULT)


class LivePreviewPanel(QFrame):
    """Right-hand studio panel with metadata inspector and real-time typing preview."""

    live_text_changed = Signal(str)
    sync_thumbnails_toggled = Signal(bool)
    install_clicked = Signal(object)
    backup_clicked = Signal(object)

    def __init__(self, font_cache: FontLoaderCache, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.font_cache = font_cache
        self.current_item: FontItem | None = None
        self.setObjectName("PreviewPanel")
        self.setMinimumWidth(360)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        hdr = QLabel("VISTA PREVIA DE ESCRITURA")
        hdr.setObjectName("SectionHeader")
        root.addWidget(hdr)

        self.title_lbl = QLabel("Selecciona una tipografía")
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #F8FAFC;")
        self.title_lbl.setWordWrap(True)
        root.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("Haz clic en cualquier tarjeta para probarla en vivo.")
        self.meta_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.meta_lbl.setWordWrap(True)
        root.addWidget(self.meta_lbl)

        # Quick text presets
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        presets = [
            ("Pangrama ES", DEFAULT_PREVIEW_TEXT),
            ("Alfabeto", "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ abcdefghijklmnñopqrstuvwxyz"),
            ("Símbolos", "0123456789 !?@#%&€$+-*/=()[]{}"),
            ("Párrafo", "La tipografía da voz visual a cada palabra, interfaz y documento."),
        ]
        for label, text in presets:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _checked=False, t=text: self._apply_preset(t))
            preset_row.addWidget(btn)
        root.addLayout(preset_row)

        # Editable live text box
        self.text_input = QPlainTextEdit(DEFAULT_PREVIEW_TEXT)
        self.text_input.setMaximumHeight(72)
        self.text_input.setPlaceholderText("Escribe aquí para previsualizar en tiempo real...")
        self.text_input.textChanged.connect(self._on_text_changed)
        root.addWidget(self.text_input)

        # Size slider + sync checkbox
        size_row = QHBoxLayout()
        self.size_lbl = QLabel("Tamaño: 28 pt")
        self.size_lbl.setStyleSheet("color: #CBD5E1; font-weight: 600;")
        size_row.addWidget(self.size_lbl)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(12, 84)
        self.size_slider.setValue(28)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        size_row.addWidget(self.size_slider, 1)
        root.addLayout(size_row)

        self.sync_checkbox = QCheckBox("Sincronizar este texto en todas las miniaturas")
        self.sync_checkbox.toggled.connect(self.sync_thumbnails_toggled.emit)
        root.addWidget(self.sync_checkbox)

        # Live Specimen Box + Multi-size waterfall inside scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        specimen_container = QFrame()
        specimen_container.setObjectName("SpecimenBox")
        self._specimen_layout = QVBoxLayout(specimen_container)
        self._specimen_layout.setContentsMargins(14, 14, 14, 14)
        self._specimen_layout.setSpacing(12)

        self.main_specimen = QLabel(DEFAULT_PREVIEW_TEXT)
        self.main_specimen.setWordWrap(True)
        self.main_specimen.setStyleSheet("color: #F8FAFC; background: transparent;")
        self._specimen_layout.addWidget(self.main_specimen)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1E293B;")
        self._specimen_layout.addWidget(sep)

        waterfall_hdr = QLabel("ESCALA DE TAMAÑOS (WATERFALL)")
        waterfall_hdr.setObjectName("SectionHeader")
        self._specimen_layout.addWidget(waterfall_hdr)

        self._waterfall_rows: list[tuple[int, QLabel]] = []
        for pt in (14, 20, 28, 40):
            pt_lbl = QLabel(f"{pt} pt")
            pt_lbl.setStyleSheet("color: #64748B; font-size: 10px; background: transparent;")
            self._specimen_layout.addWidget(pt_lbl)

            sample_lbl = QLabel(DEFAULT_PREVIEW_TEXT)
            sample_lbl.setWordWrap(True)
            sample_lbl.setStyleSheet("color: #E2E8F0; background: transparent;")
            self._specimen_layout.addWidget(sample_lbl)
            self._waterfall_rows.append((pt, sample_lbl))

        self._specimen_layout.addStretch(1)
        scroll.setWidget(specimen_container)
        root.addWidget(scroll, 1)

        # Bottom action buttons
        actions = QHBoxLayout()
        self.backup_btn = QPushButton("Salvar esta fuente (.zip)")
        self.backup_btn.setEnabled(False)
        self.backup_btn.clicked.connect(
            lambda: self.current_item and self.backup_clicked.emit(self.current_item)
        )
        actions.addWidget(self.backup_btn)

        self.install_btn = QPushButton("Instalar en Windows")
        self.install_btn.setObjectName("PrimaryBtn")
        self.install_btn.setEnabled(False)
        self.install_btn.clicked.connect(
            lambda: self.current_item and self.install_clicked.emit(self.current_item)
        )
        actions.addWidget(self.install_btn)
        root.addLayout(actions)

    def _apply_preset(self, text: str) -> None:
        self.text_input.setPlainText(text)

    def _on_text_changed(self) -> None:
        text = self.text_input.toPlainText() or DEFAULT_PREVIEW_TEXT
        self.main_specimen.setText(text)
        for _pt, lbl in self._waterfall_rows:
            lbl.setText(text)
        self.live_text_changed.emit(text)

    def _on_size_changed(self, value: int) -> None:
        self.size_lbl.setText(f"Tamaño: {value} pt")
        self._refresh_specimen_fonts()

    def _refresh_specimen_fonts(self) -> None:
        if self.current_item is None:
            return
        pt = self.size_slider.value()
        self.main_specimen.setFont(self.font_cache.qfont_for_item(self.current_item, pt))
        for w_pt, lbl in self._waterfall_rows:
            lbl.setFont(self.font_cache.qfont_for_item(self.current_item, w_pt))

    def set_font(self, item: FontItem) -> None:
        """Bind selected FontItem to metadata display and live typing studio."""
        self.current_item = item
        self.title_lbl.setText(f"{item.family} ({item.subfamily})")

        origin = (
            f"Aplicación ({item.app_name})"
            if item.source == FontSource.APPLICATION and item.app_name
            else item.source.label_es
        )
        details = [
            f"<b>Origen:</b> {origin} · <b>Formato:</b> {item.format} · <b>Tamaño:</b> {format_bytes(item.file_size)}",
            f"<b>Ruta:</b> {item.path}",
        ]
        if item.designer:
            details.append(f"<b>Diseñador:</b> {item.designer}")
        if item.version:
            details.append(f"<b>Versión:</b> {item.version}")
        self.meta_lbl.setText("<br>".join(details))

        self.backup_btn.setEnabled(True)
        self.install_btn.setEnabled(not item.source.is_installed)
        self.install_btn.setText(
            "Ya instalada en Windows" if item.source.is_installed else "Instalar en Windows"
        )
        self._refresh_specimen_fonts()
