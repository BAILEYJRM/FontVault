"""Online free font catalog (Fontsource / Google Fonts) and custom URL importer."""

from __future__ import annotations

import json
import re
import time
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import httpx

from fontvault.core.metadata import SUPPORTED_FONT_EXTENSIONS, is_valid_font_magic
from fontvault.models import OnlineFontFamily


USER_AGENT = "FontVault/1.0 (Windows NT 10.0; Win64; x64)"
FONTSOURCE_LIST_URL = "https://api.fontsource.org/v1/fonts?subsets=latin"
FONTSOURCE_DETAIL_URL = "https://api.fontsource.org/v1/fonts/{font_id}"
JSDELIVR_TTF_URL = "https://cdn.jsdelivr.net/fontsource/fonts/{font_id}@latest/latin-{weight}-normal.ttf"

CACHE_TTL_SECONDS = 86400  # 24 hours

COMMON_PORTALS: list[tuple[str, str]] = [
    ("Google Fonts", "https://fonts.google.com/"),
    ("Font Squirrel", "https://www.fontsquirrel.com/"),
    ("DaFont", "https://www.dafont.com/"),
    ("1001 Fonts", "https://www.1001fonts.com/"),
    ("Velvetyne", "https://velvetyne.fr/"),
]

OFFLINE_FALLBACK_FONTS: list[OnlineFontFamily] = [
    OnlineFontFamily("inter", "Inter", "sans-serif", [300, 400, 500, 600, 700]),
    OnlineFontFamily("roboto", "Roboto", "sans-serif", [300, 400, 500, 700]),
    OnlineFontFamily("open-sans", "Open Sans", "sans-serif", [400, 600, 700]),
    OnlineFontFamily("montserrat", "Montserrat", "sans-serif", [400, 600, 700]),
    OnlineFontFamily("lato", "Lato", "sans-serif", [400, 700]),
    OnlineFontFamily("poppins", "Poppins", "sans-serif", [400, 500, 600, 700]),
    OnlineFontFamily("fira-code", "Fira Code", "monospace", [400, 500, 700]),
    OnlineFontFamily("jetbrains-mono", "JetBrains Mono", "monospace", [400, 500, 700]),
    OnlineFontFamily("playfair-display", "Playfair Display", "serif", [400, 600, 700]),
    OnlineFontFamily("merriweather", "Merriweather", "serif", [400, 700]),
    OnlineFontFamily("nunito", "Nunito", "sans-serif", [400, 600, 700]),
    OnlineFontFamily("raleway", "Raleway", "sans-serif", [400, 600, 700]),
]


def _safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip() or "font"


class FreeFontCatalog:
    """Fetches, caches, and downloads free open-source fonts for Windows."""

    def __init__(self, cache_dir: Path, timeout: float = 15.0) -> None:
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.cache_file = cache_dir / "catalog_latin.json"

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT}

    @staticmethod
    def _parse_catalog_entries(raw_list: list[dict]) -> list[OnlineFontFamily]:
        families: list[OnlineFontFamily] = []
        for entry in raw_list:
            font_id = str(entry.get("id", "")).strip()
            family = str(entry.get("family", "")).strip()
            if not font_id or not family:
                continue
            families.append(
                OnlineFontFamily(
                    id=font_id,
                    family=family,
                    category=str(entry.get("category", "sans-serif")),
                    weights=[int(w) for w in entry.get("weights", [400]) if isinstance(w, int)],
                    styles=list(entry.get("styles", ["normal"])),
                    subsets=list(entry.get("subsets", ["latin"])),
                    source_provider=str(entry.get("type", "Fontsource / Google Fonts")),
                )
            )
        return families

    def fetch_catalog(self, force_refresh: bool = False) -> list[OnlineFontFamily]:
        """Load Fontsource catalog with 24h cache and built-in offline fallback."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not force_refresh and self.cache_file.exists():
            try:
                age = time.time() - self.cache_file.stat().st_mtime
                if age < CACHE_TTL_SECONDS:
                    cached = json.loads(self.cache_file.read_text(encoding="utf-8"))
                    parsed = self._parse_catalog_entries(cached)
                    if parsed:
                        return parsed
            except (OSError, ValueError, TypeError):
                pass

        try:
            with httpx.Client(headers=self._headers(), follow_redirects=True, timeout=self.timeout) as client:
                resp = client.get(FONTSOURCE_LIST_URL)
                resp.raise_for_status()
                raw_data = resp.json()
                if isinstance(raw_data, list) and raw_data:
                    self.cache_file.write_text(
                        json.dumps(raw_data, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    parsed = self._parse_catalog_entries(raw_data)
                    if parsed:
                        return parsed
        except Exception:
            # Fall back to stale cache if present before returning offline defaults.
            if self.cache_file.exists():
                try:
                    cached = json.loads(self.cache_file.read_text(encoding="utf-8"))
                    parsed = self._parse_catalog_entries(cached)
                    if parsed:
                        return parsed
                except Exception:
                    pass

        return list(OFFLINE_FALLBACK_FONTS)

    def download_family_ttf(
        self,
        font_id: str,
        dest_dir: Path,
        weights: list[int] | None = None,
    ) -> list[Path]:
        """Download TrueType (.ttf) files for a Fontsource family into dest_dir."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        target_weights = weights or [400, 700]
        downloaded: list[Path] = []

        with httpx.Client(headers=self._headers(), follow_redirects=True, timeout=self.timeout) as client:
            family_label = font_id
            variants: dict = {}
            try:
                detail_resp = client.get(FONTSOURCE_DETAIL_URL.format(font_id=font_id))
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    family_label = str(detail.get("family", font_id))
                    variants = detail.get("variants", {}) or {}
            except Exception:
                variants = {}

            # Ensure at least weight 400 or first available weight is attempted.
            if not variants and not weights:
                target_weights = [400]
            elif variants:
                avail_weights = [int(w) for w in variants.keys() if str(w).isdigit()]
                chosen = [w for w in target_weights if w in avail_weights]
                if not chosen and avail_weights:
                    chosen = [avail_weights[0]]
                target_weights = chosen or [400]

            for weight in target_weights:
                ttf_url = ""
                w_key = str(weight)
                if w_key in variants:
                    normal_map = variants[w_key].get("normal", {})
                    subset_entry = normal_map.get("latin") or next(iter(normal_map.values()), {})
                    ttf_url = (subset_entry.get("url", {}) or {}).get("ttf", "")

                if not ttf_url:
                    ttf_url = JSDELIVR_TTF_URL.format(font_id=font_id, weight=weight)

                resp = client.get(ttf_url)
                if resp.status_code != 200:
                    continue
                content = resp.content
                if not is_valid_font_magic(content[:4]):
                    continue

                out_name = f"{_safe_filename(family_label)}-{weight}.ttf"
                out_path = dest_dir / out_name
                out_path.write_bytes(content)
                downloaded.append(out_path)

        if not downloaded:
            raise RuntimeError(f"No se pudieron descargar archivos TTF válidos para '{font_id}'.")
        return downloaded

    def download_from_custom_url(self, url: str, dest_dir: Path) -> list[Path]:
        """Download a direct .ttf/.otf/.ttc or .zip font package from a URL safely."""
        parsed_url = urlparse(url.strip())
        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("La URL debe comenzar por http:// o https://")

        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted: list[Path] = []

        with httpx.Client(headers=self._headers(), follow_redirects=True, timeout=30.0) as client:
            resp = client.get(url.strip())
            resp.raise_for_status()
            payload = resp.content

        # Check ZIP magic PK\x03\x04 or .zip extension.
        if payload[:4] == b"PK\x03\x04" or parsed_url.path.lower().endswith(".zip"):
            with zipfile.ZipFile(BytesIO(payload), "r") as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    member_name = Path(member.filename).name
                    if not member_name or Path(member_name).suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
                        continue
                    data = zf.read(member)
                    if not is_valid_font_magic(data[:4]):
                        continue
                    out_path = dest_dir / _safe_filename(member_name)
                    out_path.write_bytes(data)
                    extracted.append(out_path)
            if not extracted:
                raise RuntimeError("El archivo ZIP descargado no contiene fuentes válidas (.ttf/.otf/.ttc).")
            return extracted

        if is_valid_font_magic(payload[:4]):
            url_name = Path(parsed_url.path).name or "downloaded_font.ttf"
            if Path(url_name).suffix.lower() not in SUPPORTED_FONT_EXTENSIONS:
                url_name += ".ttf"
            out_path = dest_dir / _safe_filename(url_name)
            out_path.write_bytes(payload)
            extracted.append(out_path)
            return extracted

        raise RuntimeError(
            "La URL no devolvió un archivo de fuente (.ttf/.otf/.ttc) ni un paquete .zip válido."
        )
