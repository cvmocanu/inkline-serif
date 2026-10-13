"""The slant that renderers synthesize for a font without an italic, such as FreeType's FT_GlyphSlot_Oblique.

It is a plain shear about the baseline: it thins stems by cos(angle) and keeps the advance widths.
"""

import math

from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def shear(
    font: TTFont,
    angle_deg: float,
) -> None:
    """Slants every glyph by `angle_deg`; composites are decomposed, so their components slant about the baseline."""
    skew = Transform().skew(math.radians(angle_deg))  # x += y tan(angle)
    glyph_set = font.getGlyphSet()
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    sheared = {}
    for name in font.getGlyphOrder():
        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recording)
        glyph_pen = TTGlyphPen(None)
        recording.replay(TransformPen(glyph_pen, skew))
        sheared[name] = glyph_pen.glyph()
    for name, glyph in sheared.items():
        glyf[name] = glyph
        glyph.recalcBounds(glyf)
        advance, _ = hmtx[name]
        hmtx[name] = (advance, getattr(glyph, "xMin", 0) if glyph.numberOfContours else 0)
