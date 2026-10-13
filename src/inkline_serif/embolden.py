"""Anisotropic emboldening of a TrueType font.

A port of FreeType's FT_Outline_EmboldenXY: every point moves outward along the corner bisector, so stems grow by
`x` font units and horizontal strokes by `y`. Counters shrink, because inner contours run the opposite way.
"""

import math
from dataclasses import dataclass

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program

from inkline_serif.outlines import normalize_outlines

type Point = tuple[float, float]

# Hinting tables of the source font; they no longer match the outlines, and ttfautohint writes its own.
STALE_HINTING_TABLES = ("fpgm", "prep", "cvt ", "hdmx", "LTSH", "VDMX")

# Corners sharper than this (cosine between the incoming and outgoing direction) are left in place.
SHARPEST_CORNER_COS = -0.9375


@dataclass(frozen=True)
class Emboldening:
    """Extra stroke thickness, in font units: `x` for vertical stems, `y` for horizontal strokes."""

    x: float
    y: float


def embolden(
    font: TTFont,
    emboldening: Emboldening,
) -> None:
    """Thickens every glyph, keeping its side bearings by shifting it right by half the extra stem width."""
    # Reversed or overlapping contours would get thinner instead of bolder.
    normalize_outlines(font)
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    shift = emboldening.x / 2
    extra_advance = round(emboldening.x)
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        advance, lsb = hmtx[name]
        if glyph.isComposite():
            # The components are emboldened in their own glyphs; only the placement follows.
            for component in glyph.components:
                component.x += round(shift)
            hmtx[name] = (advance + extra_advance, lsb)
        elif glyph.numberOfContours <= 0:
            hmtx[name] = (advance + extra_advance if advance else advance, lsb)
        else:
            points = list(glyph.coordinates)
            emboldened: list[Point] = []
            start = 0
            for end in glyph.endPtsOfContours:
                emboldened.extend(embolden_contour(points=points[start : end + 1], emboldening=emboldening))
                start = end + 1
            glyph.coordinates = GlyphCoordinates([(round(x + shift), round(y)) for x, y in emboldened])
            glyph.program = Program()
            glyph.program.fromBytecode(b"")
            glyph.recalcBounds(glyf)
            hmtx[name] = (advance + extra_advance, glyph.xMin)
    for tag in STALE_HINTING_TABLES:
        if tag in font:
            del font[tag]


def embolden_contour(
    points: list[Point],
    emboldening: Emboldening,
) -> list[Point]:
    """Moves each point of a closed contour outward; the contour must run clockwise, as TrueType outer contours do."""
    count = len(points)
    if count < 3:
        return points
    half_x, half_y = emboldening.x / 2, emboldening.y / 2
    shift_limit = min(half_x, half_y)
    moved: list[Point] = []
    for j, current in enumerate(points):
        previous = _neighbor(points=points, index=j, step=-1)
        following = _neighbor(points=points, index=j, step=1)
        in_x, in_y = _unit(start=previous, end=current)
        out_x, out_y = _unit(start=current, end=following)
        cos = in_x * out_x + in_y * out_y
        if cos > SHARPEST_CORNER_COS:
            d = cos + 1
            shift_x, shift_y = -(in_y + out_y), in_x + out_x
            q = -(out_x * in_y - out_y * in_x)
            if q <= shift_limit * d:
                shift_x, shift_y = shift_x * half_x / d, shift_y * half_y / d
            else:
                shift_x, shift_y = shift_x * shift_limit / q, shift_y * shift_limit / q
        else:
            shift_x = shift_y = 0.0
        moved.append((current[0] + shift_x, current[1] + shift_y))
    return moved


def _neighbor(
    points: list[Point],
    index: int,
    step: int,
) -> Point:
    """The nearest point in the direction `step` that differs from the point at `index`."""
    count = len(points)
    offset = 1
    while points[(index + offset * step) % count] == points[index] and offset < count:
        offset += 1
    return points[(index + offset * step) % count]


def _unit(
    start: Point,
    end: Point,
) -> Point:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)
