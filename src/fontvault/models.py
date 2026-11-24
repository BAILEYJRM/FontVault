"""Domain models for FontVault."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FontSource(str, Enum):
    """Origin category of a discovered font file."""

    INSTALLED_SYSTEM = "installed_system"
    INSTALLED_USER = "installed_user"
    CUSTOM = "custom"
    APPLICATION = "application"

    @property
    def label_es(self) -> str:
        """Return localized Spanish badge text for the font source."""
        labels = {
            FontSource.INSTALLED_SYSTEM: "Sistema",
            FontSource.INSTALLED_USER: "Usuario",
            FontSource.CUSTOM: "Personalizada",
            FontSource.APPLICATION: "Aplicación",
        }
        return labels[self]

    @property
    def is_installed(self) -> bool:
        """Whether the font is already registered in Windows."""
        return self in (FontSource.INSTALLED_SYSTEM, FontSource.INSTALLED_USER)


@dataclass(slots=True)
class FontItem:
    """Metadata and location of a single font file."""

    path: Path
    family: str
    subfamily: str
    full_name: str
    postscript_name: str
    version: str
    designer: str
    license_info: str
    format: str
    source: FontSource
    app_name: str = ""
    file_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize item to JSON-friendly dictionary."""
        return {
            "path": str(self.path),
            "family": self.family,
            "subfamily": self.subfamily,
            "full_name": self.full_name,
            "postscript_name": self.postscript_name,
            "version": self.version,
            "designer": self.designer,
            "license_info": self.license_info,
            "format": self.format,
            "source": self.source.value,
            "app_name": self.app_name,
            "file_size": self.file_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FontItem:
        """Reconstruct FontItem from cached JSON dictionary."""
        return cls(
            path=Path(data["path"]),
            family=data.get("family", ""),
            subfamily=data.get("subfamily", "Regular"),
            full_name=data.get("full_name", ""),
            postscript_name=data.get("postscript_name", ""),
            version=data.get("version", ""),
            designer=data.get("designer", ""),
            license_info=data.get("license_info", ""),
            format=data.get("format", "TTF"),
            source=FontSource(data["source"]),
            app_name=data.get("app_name", ""),
            file_size=int(data.get("file_size", 0)),
        )


@dataclass(slots=True)
class OnlineFontFamily:
    """Metadata entry for a free downloadable online font family."""

    id: str
    family: str
    category: str
    weights: list[int] = field(default_factory=lambda: [400])
    styles: list[str] = field(default_factory=lambda: ["normal"])
    subsets: list[str] = field(default_factory=lambda: ["latin"])
    source_provider: str = "Fontsource / Google Fonts"


@dataclass(slots=True)
class BackupResult:
    """Summary returned after exporting or backing up fonts."""

    destination: Path
    copied_count: int
    total_bytes: int
    manifest_path: Path
    errors: list[str] = field(default_factory=list)
