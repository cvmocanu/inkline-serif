"""Glyphs looked up by the character they draw."""

from collections.abc import Mapping
from typing import Any

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

type GlyphSet = Mapping[str, Any]
type Bounds = tuple[float, float, float, float]


def glyph_name(
    font: TTFont,
    char: str,
) -> str:
    cmap = font.getBestCmap()
    if cmap is None or ord(char) not in cmap:
        raise ValueError(f"the font {font_name(font)} has no glyph for {char!r}")
    return cmap[ord(char)]


def bounds(
    font: TTFont,
    char: str,
) -> Bounds:
    """The glyph's bounding box: x min, y min, x max, y max."""
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name(font=font, char=char)].draw(pen)
    if pen.bounds is None:
        raise ValueError(f"the glyph for {char!r} in the font {font_name(font)} is empty")
    return pen.bounds


def font_name(font: TTFont) -> str:
    return font["name"].getDebugName(4) or "without a name"
