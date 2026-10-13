import math

from builders import font, rectangle

from inkline_serif.synthetic_oblique import shear


def test_slants_right_about_the_baseline_and_keeps_the_advance() -> None:
    bar = font(glyphs={"bar": [rectangle(x_min=0, y_min=0, x_max=100, y_max=500)]})
    advance_before, _ = bar["hmtx"]["bar"]

    shear(font=bar, angle_deg=10)

    glyph = bar["glyf"]["bar"]
    top_shift = round(500 * math.tan(math.radians(10)))
    assert (glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax) == (0, 0, 100 + top_shift, 500)
    advance, _ = bar["hmtx"]["bar"]
    assert advance == advance_before


def test_slants_composites_like_the_glyphs_they_are_made_of() -> None:
    composite = font(
        glyphs={"bar": [rectangle(x_min=0, y_min=0, x_max=100, y_max=500)]},
        composites={"twin": ["bar"]},
    )

    shear(font=composite, angle_deg=10)

    glyf = composite["glyf"]
    assert not glyf["twin"].isComposite()
    assert (glyf["twin"].xMin, glyf["twin"].xMax) == (glyf["bar"].xMin, glyf["bar"].xMax)
