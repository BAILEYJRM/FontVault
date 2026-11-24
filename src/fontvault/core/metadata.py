"""OpenType/TrueType metadata parser built on fontTools."""

from __future__ import annotations

from pathlib import Path
from fontTools.ttLib import TTFont

from fontvault.models import FontItem, FontSource


SUPPORTED_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}
FONT_MAGIC_HEADERS = (b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"true")


def is_valid_font_magic(header: bytes) -> bool:
    """Check whether the initial bytes match a TrueType/OpenType/TTC container."""
    return len(header) >= 4 and header[:4] in FONT_MAGIC_HEADERS


def _extract_name(name_table, name_id: int) -> str:
    """Extract preferred Unicode or Mac name record from an OpenType name table."""
    if name_table is None:
        return ""
    # Prefer Windows Unicode BMP / full Unicode, then Mac Roman, then any encoding.
    for platform_id, enc_ids in ((3, (1, 10, 0)), (0, (3, 4, 0)), (1, (0,))):
        for enc_id in enc_ids:
            for record in name_table.names:
                if (
                    record.nameID == name_id
                    and record.platformID == platform_id
                    and record.platEncID == enc_id
                ):
                    try:
                        text = record.toUnicode().strip()
                        if text:
                            return text
                    except UnicodeDecodeError:
                        continue
    for record in name_table.names:
        if record.nameID == name_id:
            try:
                text = record.toUnicode().strip()
                if text:
                    return text
            except UnicodeDecodeError:
                continue
    return ""


def parse_font_file(
    path: Path,
    source: FontSource,
    app_name: str = "",
) -> FontItem | None:
    """Parse font metadata without crashing on malformed or locked font files."""
    if not path.is_file():
        return None
    ext = path.suffix.lower()
    if ext not in SUPPORTED_FONT_EXTENSIONS:
        return None

    try:
        file_size = path.stat().st_size
    except OSError:
        return None

    fmt = ext.lstrip(".").upper()
    family = path.stem
    subfamily = "Regular"
    full_name = path.stem
    postscript_name = ""
    version = ""
    designer = ""
    license_info = ""

    open_kwargs: dict[str, object] = {"lazy": True}
    if ext == ".ttc":
        open_kwargs["fontNumber"] = 0

    try:
        with TTFont(str(path), **open_kwargs) as tt:
            name_table = tt.get("name")
            parsed_family = _extract_name(name_table, 16) or _extract_name(name_table, 1)
            parsed_subfamily = _extract_name(name_table, 17) or _extract_name(name_table, 2)
            parsed_full = _extract_name(name_table, 4)
            parsed_ps = _extract_name(name_table, 6)
            parsed_ver = _extract_name(name_table, 5)
            parsed_designer = _extract_name(name_table, 9)
            parsed_license = _extract_name(name_table, 13)

            if parsed_family:
                family = parsed_family
            if parsed_subfamily:
                subfamily = parsed_subfamily
            if parsed_full:
                full_name = parsed_full
            elif parsed_family:
                full_name = f"{parsed_family} {subfamily}".strip()
            postscript_name = parsed_ps
            version = parsed_ver
            designer = parsed_designer
            license_info = parsed_license[:240]
    except Exception:
        # Malformed or non-standard font tables still fall back cleanly to filename.
        pass

    return FontItem(
        path=path,
        family=family,
        subfamily=subfamily,
        full_name=full_name,
        postscript_name=postscript_name,
        version=version,
        designer=designer,
        license_info=license_info,
        format=fmt,
        source=source,
        app_name=app_name,
        file_size=file_size,
    )
