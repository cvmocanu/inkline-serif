"""Family and style names in the name table."""

from fontTools.ttLib import TTFont

FAMILY_IDS = (1, 16)
STYLE_IDS = (2, 17)
UNIQUE_ID = 3
FULL_NAME_ID = 4
DESCRIPTION_ID = 10
POSTSCRIPT_NAME_ID = 6


def postscript_name(
    family: str,
    style: str,
) -> str:
    return family.replace(" ", "") + "-" + style.replace(" ", "")


def rename(
    font: TTFont,
    family: str,
    style: str,
) -> None:
    """Rewrites every existing family and style record, so the font never collides with its source on a device."""
    ps_name = postscript_name(family=family, style=style)
    for record in font["name"].names:
        if record.nameID in FAMILY_IDS:
            record.string = family
        elif record.nameID in STYLE_IDS:
            record.string = style
        elif record.nameID == UNIQUE_ID:
            record.string = f"{ps_name};modified"
        elif record.nameID == FULL_NAME_ID:
            record.string = f"{family} {style}"
        elif record.nameID == POSTSCRIPT_NAME_ID:
            record.string = ps_name


def description(font: TTFont) -> str:
    text = font["name"].getDebugName(DESCRIPTION_ID)
    if text is None:
        raise ValueError(f"the font {font['name'].getDebugName(FULL_NAME_ID)} has no description (name ID 10)")
    return text


def set_description(
    font: TTFont,
    text: str,
) -> None:
    font["name"].setName(text, DESCRIPTION_ID, 3, 1, 0x409)  # Windows, Unicode BMP, US English
