"""Contour direction and overlaps of TrueType outlines.

TrueType expects outer contours clockwise; a glyph whose overall signed area is positive is counter-clockwise.
"""

import pathops
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import removeOverlaps

from inkline_serif.glyphs import GlyphSet

# The share by which removing overlaps may change a glyph's area before the glyph counts as overlapping.
OVERLAP_TOLERANCE = 0.01


def outline_glyph_names(font: TTFont) -> list[str]:
    """The glyphs drawn by their own contours: neither composite nor empty."""
    glyf = font["glyf"]
    return [name for name in font.getGlyphOrder() if not glyf[name].isComposite() and glyf[name].numberOfContours > 0]


def normalize_outlines(font: TTFont) -> None:
    """Merges overlapping contours, then reverses every counter-clockwise glyph."""
    removeOverlaps(font)
    glyph_set = font.getGlyphSet()
    glyf = font["glyf"]
    for name in outline_glyph_names(font):
        if signed_area(glyph_set, name) > 0:
            pen = TTGlyphPen(None)
            glyph_set[name].draw(ReverseContourPen(pen))
            glyf[name] = pen.glyph()


def find_bad_outlines(font: TTFont) -> list[str]:
    """The glyphs that are counter-clockwise or have overlapping contours."""
    glyph_set = font.getGlyphSet()
    bad: list[str] = []
    for name in outline_glyph_names(font):
        area = signed_area(glyph_set, name)
        path = pathops.Path()
        glyph_set[name].draw(path.getPen())
        path.simplify()
        if area > 0 or abs(abs(area) - abs(path.area)) > abs(area) * OVERLAP_TOLERANCE:
            bad.append(name)
    return bad


def signed_area(
    glyph_set: GlyphSet,
    name: str,
) -> float:
    pen = AreaPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.value
