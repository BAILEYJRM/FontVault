"""Shared pytest fixtures synthesizing lightweight valid TTF fonts on the fly."""

from __future__ import annotations

from pathlib import Path
import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def create_synthetic_ttf(
    dest_path: Path,
    family: str = "TestFont",
    subfamily: str = "Regular",
) -> Path:
    """Create a minimal valid OpenType/TrueType font file using FontBuilder."""
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "A", "a"])
    fb.setupCharacterMap({65: "A", 97: "a"})

    pen = TTGlyphPen(None)
    pen.moveTo((100, 0))
    pen.lineTo((100, 700))
    pen.lineTo((500, 700))
    pen.lineTo((500, 0))
    pen.closePath()
    rect_glyph = pen.glyph()

    fb.setupGlyf({".notdef": rect_glyph, "A": rect_glyph, "a": rect_glyph})
    metrics = {".notdef": (600, 100), "A": (600, 100), "a": (600, 100)}
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({
        "familyName": family,
        "styleName": subfamily,
        "uniqueFontIdentifier": f"1.000;TEST;{family}-{subfamily}",
        "fullName": f"{family} {subfamily}",
        "psName": f"{family}-{subfamily}".replace(" ", ""),
        "version": "Version 1.000",
    })
    fb.setupOS2()
    fb.setupPost()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(str(dest_path))
    return dest_path


@pytest.fixture()
def sample_ttf(tmp_path: Path) -> Path:
    """Provide a single synthesized TTF file."""
    return create_synthetic_ttf(tmp_path / "SampleSans-Regular.ttf", family="SampleSans", subfamily="Regular")
