from builders import font
from font_inspection import axis_values, elided_fallback_name

from inkline_serif import naming
from inkline_serif.style_axes import ELIDABLE, set_style_axes


def test_describes_an_upright_as_roman_and_keeps_its_weight() -> None:
    bold = font(style="Bold", weight_value=700, weight_name="Bold")

    set_style_axes(font=bold, italic=False)

    assert axis_values(bold) == {("wght", 700, "Bold", 0), ("ital", 0, "Roman", ELIDABLE)}


def test_describes_an_italic_as_italic() -> None:
    bold_italic = font(style="Bold Italic", weight_value=700, weight_name="Bold")

    set_style_axes(font=bold_italic, italic=True)

    assert axis_values(bold_italic) == {("wght", 700, "Bold", 0), ("ital", 1, "Italic", 0)}


def test_lets_apps_elide_the_regular_weight() -> None:
    italic = font(style="Italic", weight_value=400, weight_name="Regular")

    set_style_axes(font=italic, italic=True)

    assert axis_values(italic) == {("wght", 400, "Regular", ELIDABLE), ("ital", 1, "Italic", 0)}


def test_falls_back_to_regular_when_every_value_is_elided() -> None:
    bold_italic = font(style="Bold Italic", weight_value=700, weight_name="Bold")

    set_style_axes(font=bold_italic, italic=True)

    assert elided_fallback_name(bold_italic) == "Regular"


def test_keeps_its_names_when_the_font_is_renamed() -> None:
    # The style name (name ID 2) of a Regular reads "Regular" too, until the font is renamed.
    regular = font(style="Regular", weight_value=400, weight_name="Regular")
    set_style_axes(font=regular, italic=False)

    naming.rename(font=regular, family="Any Family", style="Italic")

    assert axis_values(regular) == {("wght", 400, "Regular", ELIDABLE), ("ital", 0, "Roman", ELIDABLE)}
    assert elided_fallback_name(regular) == "Regular"
