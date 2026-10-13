"""The STAT table, which tells apps where each font sits on the family's weight and italic axes.

Every font of the family declares the same axes, so apps can group the uprights and the italics as one family.
"""

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont

from inkline_serif.glyphs import font_name

WEIGHT_AXIS = "wght"
ITALIC_AXIS = "ital"
REGULAR_WEIGHT = 400
# Name IDs from here up belong to the font itself; the ones below have fixed meanings, such as the style name.
FIRST_FONT_NAME_ID = 256
# Axis value flag: apps leave the value's name out of composed style names ("Italic", not "Regular Italic").
ELIDABLE = 0x2


def set_style_axes(
    font: TTFont,
    italic: bool,
) -> None:
    """Rebuilds STAT with the font's weight, as the source STAT names it, and its place on the italic axis."""
    weight, weight_name = _weight(font)
    if italic:
        italic_value = {"value": 1, "name": _name_id(font=font, text="Italic")}
    else:
        italic_value = {"value": 0, "name": _name_id(font=font, text="Roman"), "flags": ELIDABLE, "linkedValue": 1}
    buildStatTable(
        font,
        axes=[
            {
                "tag": WEIGHT_AXIS,
                "name": _name_id(font=font, text="Weight"),
                "values": [
                    {
                        "value": weight,
                        "name": _name_id(font=font, text=weight_name),
                        "flags": ELIDABLE if weight == REGULAR_WEIGHT else 0,
                    }
                ],
            },
            {"tag": ITALIC_AXIS, "name": _name_id(font=font, text="Italic"), "values": [italic_value]},
        ],
        elidedFallbackName=_name_id(font=font, text="Regular"),
        macNames=False,
    )


def _weight(font: TTFont) -> tuple[float, str]:
    """The value and name of the font's weight, from its STAT."""
    if "STAT" not in font:
        raise ValueError(f"the font {font_name(font)} has no STAT table to take its weight from")
    stat = font["STAT"].table
    tags = [axis.AxisTag for axis in stat.DesignAxisRecord.Axis]
    for axis_value in stat.AxisValueArray.AxisValue:
        if tags[axis_value.AxisIndex] == WEIGHT_AXIS:
            name = font["name"].getDebugName(axis_value.ValueNameID)
            if name is None:
                raise ValueError(f"the weight value in the STAT table of the font {font_name(font)} has no name")
            return axis_value.Value, name
    raise ValueError(f"the STAT table of the font {font_name(font)} has no weight value")


def _name_id(
    font: TTFont,
    text: str,
) -> int:
    """
    A font-specific name record holding `text`, reused when one exists.
    Left to itself, fontTools would also reuse a record such as the style name, which the build later rewrites.
    """
    return font["name"].addMultilingualName({"en": text}, ttFont=font, mac=False, minNameID=FIRST_FONT_NAME_ID)
