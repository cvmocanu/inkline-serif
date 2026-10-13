from fontTools.fontBuilder import FontBuilder
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

type Point = tuple[float, float]
type Contour = list[Point]

UNITS_PER_EM = 1000


def font(
    glyphs: dict[str, list[Contour]] | None = None,
    composites: dict[str, list[str]] | None = None,
    family: str = "Any Family",
    style: str = "Regular",
    weight_value: float = 400,
    weight_name: str = "Regular",
) -> TTFont:
    """
    A TrueType font whose glyphs are drawn as polygons; `.notdef` is added empty.
    Each composite places its components, named by glyph, at the origin.
    Its STAT has a weight axis only, as static Google Fonts builds do.
    """
    drawn = {".notdef": TTGlyphPen(None).glyph()}
    for name, contours in (glyphs or {}).items():
        pen = TTGlyphPen(None)
        for contour in contours:
            pen.moveTo(contour[0])
            for point in contour[1:]:
                pen.lineTo(point)
            pen.closePath()
        drawn[name] = pen.glyph()
    for name, components in (composites or {}).items():
        pen = TTGlyphPen(dict(drawn))
        for component in components:
            pen.addComponent(component, (1, 0, 0, 1, 0, 0))
        drawn[name] = pen.glyph()
    builder = FontBuilder(UNITS_PER_EM, isTTF=True)
    builder.setupGlyphOrder(list(drawn))
    builder.setupCharacterMap({})
    builder.setupGlyf(drawn)
    builder.setupHorizontalMetrics(
        {name: (UNITS_PER_EM // 2, getattr(glyph, "xMin", 0)) for name, glyph in drawn.items()}
    )
    builder.setupHorizontalHeader()
    ps_name = f"{family}-{style}".replace(" ", "")
    builder.setupNameTable(
        {
            "familyName": family,
            "styleName": style,
            "uniqueFontIdentifier": ps_name,
            "fullName": f"{family} {style}",
            "psName": ps_name,
        }
    )
    builder.setupOS2()
    builder.setupPost()
    buildStatTable(
        builder.font,
        axes=[{"tag": "wght", "name": "Weight", "values": [{"value": weight_value, "name": weight_name}]}],
        macNames=False,
    )
    return builder.font


def rectangle(
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
) -> Contour:
    """A clockwise rectangle, as TrueType draws outer contours."""
    return [(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)]


def counter_clockwise(contour: Contour) -> Contour:
    return contour[::-1]
