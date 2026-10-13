from fontTools.ttLib import TTFont

type AxisValue = tuple[str, float, str | None, int]


def axis_values(font: TTFont) -> set[AxisValue]:
    """Each STAT axis value as (axis tag, value, name, flags)."""
    stat = font["STAT"].table
    name = font["name"]
    tags = [axis.AxisTag for axis in stat.DesignAxisRecord.Axis]
    return {
        (tags[value.AxisIndex], value.Value, name.getDebugName(value.ValueNameID), value.Flags)
        for value in stat.AxisValueArray.AxisValue
    }


def elided_fallback_name(font: TTFont) -> str | None:
    return font["name"].getDebugName(font["STAT"].table.ElidedFallbackNameID)
