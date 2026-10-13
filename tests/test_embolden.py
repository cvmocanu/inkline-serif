from builders import counter_clockwise, font, rectangle

from inkline_serif.embolden import Emboldening, embolden, embolden_contour


def test_grows_a_square_by_half_the_extra_width_on_each_side() -> None:
    square = rectangle(x_min=0, y_min=0, x_max=100, y_max=100)

    emboldened = embolden_contour(points=square, emboldening=Emboldening(x=10, y=20))

    assert emboldened == rectangle(x_min=-5, y_min=-10, x_max=105, y_max=110)


def test_shrinks_a_counter() -> None:
    # Inner contours run counter-clockwise, so moving them "outward" moves them into the counter.
    counter = counter_clockwise(rectangle(x_min=0, y_min=0, x_max=100, y_max=100))

    emboldened = embolden_contour(points=counter, emboldening=Emboldening(x=10, y=20))

    assert emboldened == counter_clockwise(rectangle(x_min=5, y_min=10, x_max=95, y_max=90))


def test_keeps_the_side_bearings_by_widening_the_advance() -> None:
    bar = font(glyphs={"bar": [rectangle(x_min=50, y_min=0, x_max=150, y_max=100)]})
    advance_before, lsb_before = bar["hmtx"]["bar"]

    embolden(font=bar, emboldening=Emboldening(x=10, y=20))

    glyph = bar["glyf"]["bar"]
    advance, lsb = bar["hmtx"]["bar"]
    assert (glyph.xMin, glyph.xMax) == (50, 160)
    assert lsb == lsb_before
    assert advance == advance_before + 10


def test_makes_a_reversed_glyph_bolder_rather_than_thinner() -> None:
    reversed_bar = font(glyphs={"bar": [counter_clockwise(rectangle(x_min=0, y_min=0, x_max=100, y_max=100))]})

    embolden(font=reversed_bar, emboldening=Emboldening(x=10, y=20))

    glyph = reversed_bar["glyf"]["bar"]
    assert (glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax) == (0, -10, 110, 110)
