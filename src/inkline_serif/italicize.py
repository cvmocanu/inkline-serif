"""An optically corrected oblique, made from an upright TrueType font.

A pure shear thins stems by cos(angle). Part of the slant is therefore done by rotation, which keeps stem widths;
a vertical shear then restores the horizontals, and a horizontal shear brings the slant to the target angle.
"""

import math
from dataclasses import dataclass

import pathops
from fontTools.misc.transform import Transform
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from inkline_serif.glyphs import GlyphSet, bounds, glyph_name

# OS/2.fsSelection and head.macStyle bits
FS_ITALIC = 1 << 0
FS_BOLD = 1 << 5
FS_REGULAR = 1 << 6
MAC_BOLD = 1 << 0
MAC_ITALIC = 1 << 1

PAIR_ADJUSTMENT = 2  # GPOS lookup type
CARET_SLOPE_RISE = 1000


@dataclass(frozen=True)
class Slant:
    """
    The slant `angle_deg` is reached exactly, after `condense` narrows every glyph horizontally.
    `rotation_fraction` is the share of the angle done by rotation rather than by shear.
    """

    angle_deg: float
    rotation_fraction: float
    condense: float
    single_storey_a: bool


def italicize(
    font: TTFont,
    slant: Slant,
    bold: bool,
) -> None:
    glyph_set = font.getGlyphSet()
    x_height = bounds(font=font, char="x")[3]
    if slant.single_storey_a:
        cut_single_storey_a(font)
    # Slanting around half the x-height keeps the glyphs from drifting right.
    transform = slant_transform(slant=slant, pivot_y=x_height / 2)
    _decompose_transformed_components(font=font, glyph_set=glyph_set)
    _transform_glyphs(font=font, transform=transform, condense=slant.condense)
    _scale_pair_kerning(font=font, factor=slant.condense)
    set_italic_flags(font=font, angle_deg=slant.angle_deg, bold=bold)


def slant_transform(
    slant: Slant,
    pivot_y: float,
) -> Transform:
    r = math.radians(slant.angle_deg * slant.rotation_fraction)
    # The horizontal shear that, after the rotation and the condense, reaches exactly the target angle.
    k = math.tan(math.radians(slant.angle_deg)) / slant.condense - math.sin(r) * math.cos(r)
    rotate = Transform(math.cos(r), -math.sin(r), math.sin(r), math.cos(r), 0, 0)
    shear_vertically = Transform(1, math.tan(r), 0, 1, 0, 0)  # y += x tan r
    shear_horizontally = Transform(1, 0, k, 1, 0, 0)  # x += k y
    condense = Transform(slant.condense, 0, 0, 1, 0, 0)
    # a.transform(b) applies b first, so the steps below run bottom to top.
    transform = Transform().translate(0, pivot_y)
    for step in (condense, shear_horizontally, shear_vertically, rotate):
        transform = transform.transform(step)
    return transform.translate(0, -pivot_y)


def cut_single_storey_a(font: TTFont) -> None:
    """Replaces `a` with `d` cut at the height of `o`, overshoot included; accented a's are composites and follow."""
    glyph_set = font.getGlyphSet()
    d_name, a_name = glyph_name(font=font, char="d"), glyph_name(font=font, char="a")
    top = bounds(font=font, char="o")[3]
    d = pathops.Path()
    glyph_set[d_name].draw(d.getPen())
    below_top = pathops.Path()
    pen = below_top.getPen()
    pen.moveTo((-500, -500))
    pen.lineTo((-500, top))
    pen.lineTo((2000, top))
    pen.lineTo((2000, -500))
    pen.closePath()
    cut = pathops.op(d, below_top, pathops.PathOp.INTERSECTION)
    area_pen = AreaPen()
    cut.draw(area_pen)
    glyph_pen = TTGlyphPen(None)
    cut.draw(ReverseContourPen(glyph_pen) if area_pen.value > 0 else glyph_pen)
    glyf = font["glyf"]
    glyph = glyph_pen.glyph()
    glyf[a_name] = glyph
    glyph.recalcBounds(glyf)
    hmtx = font["hmtx"]
    hmtx[a_name] = (hmtx[d_name][0], glyph.xMin)


def _decompose_transformed_components(
    font: TTFont,
    glyph_set: GlyphSet,
) -> None:
    """Decomposes the composites with scaled or flipped components, whose offsets alone can't carry a slant."""
    glyf = font["glyf"]
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if glyph.isComposite() and any(hasattr(component, "transform") for component in glyph.components):
            recording = DecomposingRecordingPen(glyph_set)
            glyph_set[name].draw(recording)
            glyph_pen = TTGlyphPen(None)
            recording.replay(glyph_pen)
            glyf[name] = glyph_pen.glyph()


def _transform_glyphs(
    font: TTFont,
    transform: Transform,
    condense: float,
) -> None:
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    glyph_set = font.getGlyphSet()
    transformed = {}
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if not glyph.isComposite() and glyph.numberOfContours > 0:
            glyph_pen = TTGlyphPen(None)
            glyph_set[name].draw(TransformPen(glyph_pen, transform))
            transformed[name] = glyph_pen.glyph()
    for name, glyph in transformed.items():
        glyf[name] = glyph
    # The component outlines already moved with the translation about the pivot; offsets take the linear part only.
    linear = Transform(transform.xx, transform.xy, transform.yx, transform.yy, 0, 0)
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if glyph.isComposite():
            for component in glyph.components:
                x, y = linear.transformPoint((component.x, component.y))
                component.x, component.y = round(x), round(y)
        advance, _ = hmtx[name]
        glyph.recalcBounds(glyf)
        lsb = getattr(glyph, "xMin", 0) if glyph.numberOfContours else 0
        hmtx[name] = (round(advance * condense), lsb)


def _scale_pair_kerning(
    font: TTFont,
    factor: float,
) -> None:
    if "GPOS" not in font:
        return
    for lookup in font["GPOS"].table.LookupList.Lookup:
        for subtable in lookup.SubTable:
            pair_pos = getattr(subtable, "ExtSubTable", subtable)
            if pair_pos.LookupType != PAIR_ADJUSTMENT:
                continue
            if pair_pos.Format == 1:
                records = [record for pair_set in pair_pos.PairSet for record in pair_set.PairValueRecord]
            else:
                records = [record for class1 in pair_pos.Class1Record for record in class1.Class2Record]
            for record in records:
                _scale_value_record(value_record=record.Value1, factor=factor)
                _scale_value_record(value_record=record.Value2, factor=factor)


def _scale_value_record(
    value_record: object | None,
    factor: float,
) -> None:
    if value_record is None:
        return
    for attribute in ("XAdvance", "XPlacement"):
        if hasattr(value_record, attribute):
            setattr(value_record, attribute, round(getattr(value_record, attribute) * factor))


def set_italic_flags(
    font: TTFont,
    angle_deg: float,
    bold: bool,
) -> None:
    """Sets the slant and the style bits, which link the italic to its upright as one family."""
    # fontTools creates the attributes of these tables when it decompiles them, so the type checker can't see them.
    font["post"].italicAngle = -angle_deg  # pyrefly: ignore[missing-attribute]
    hhea = font["hhea"]
    hhea.caretSlopeRise = CARET_SLOPE_RISE  # pyrefly: ignore[missing-attribute]
    caret_slope_run = round(CARET_SLOPE_RISE * math.tan(math.radians(angle_deg)))
    hhea.caretSlopeRun = caret_slope_run  # pyrefly: ignore[missing-attribute]
    os2 = font["OS/2"]
    style_bits = FS_ITALIC | (FS_BOLD if bold else 0)
    fs_selection = (os2.fsSelection & ~(FS_REGULAR | FS_BOLD | FS_ITALIC)) | style_bits  # pyrefly: ignore[missing-attribute]
    os2.fsSelection = fs_selection  # pyrefly: ignore[missing-attribute]
    font["head"].macStyle = MAC_ITALIC | (MAC_BOLD if bold else 0)  # pyrefly: ignore[missing-attribute]
