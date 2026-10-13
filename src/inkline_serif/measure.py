"""Compares stroke widths and rendered ink coverage of fonts.

The first font is the reference: the others are rendered at the size that matches its x-height.

usage: inkline-measure Name=font.ttf [Name=font.ttf ...]
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import override

import freetype
import numpy as np
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from freetype.ft_enums.ft_load_flags import FT_LOAD_FLAGS
from freetype.ft_enums.ft_load_targets import FT_LOAD_TARGETS

from inkline_serif.glyphs import GlyphSet, bounds, glyph_name

type Point = tuple[float, float]
type Contour = list[Point]

SAMPLE_TEXT = "the quick brown fox jumps over the lazy dog and reads a long book in the evening"
POINT_SIZES = (8, 10, 12)  # the usual Kindle range
PPI = 300
QUADRATIC_STEPS = 12
CUBIC_STEPS = 16
STEM_HEIGHT = 0.45  # share of the x-height where stems are measured, below the serifs
STEM_ROW = 0.6  # share of the rendered `l` bitmap's height where its stem row is sampled
MIN_STEM_COVERAGE = 0.02

RENDER_MODES = {
    "native hinting": FT_LOAD_FLAGS["FT_LOAD_NO_AUTOHINT"],
    "no hinting": FT_LOAD_FLAGS["FT_LOAD_NO_HINTING"],
    "autohint light": FT_LOAD_FLAGS["FT_LOAD_FORCE_AUTOHINT"] | FT_LOAD_TARGETS["FT_LOAD_TARGET_LIGHT"],
}


@dataclass(frozen=True)
class NamedFont:
    name: str
    path: Path


@dataclass(frozen=True)
class Strokes:
    """Stroke widths in font units."""

    x_height: float
    n_stem: float
    l_stem: float
    o_side: float
    o_top: float
    h_bar: float

    def widths(self) -> dict[str, float]:
        return {
            "n_stem": self.n_stem,
            "l_stem": self.l_stem,
            "o_side": self.o_side,
            "o_top": self.o_top,
            "H_bar": self.h_bar,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare stroke widths and ink coverage of fonts.")
    parser.add_argument("fonts", nargs="+", type=parse_named_font, help="Name=font.ttf; the first is the reference")
    args = parser.parse_args()
    report(args.fonts)


def parse_named_font(argument: str) -> NamedFont:
    name, separator, path = argument.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError(f"expected Name=font.ttf, got {argument!r}")
    return NamedFont(name=name, path=Path(path))


def report(fonts: Sequence[NamedFont]) -> None:
    strokes = {font.name: measure_strokes(font.path) for font in fonts}
    print("== Design (font units, and normalized to x-height)")
    for font in fonts:
        s = strokes[font.name]
        widths = "  ".join(f"{key}={value:.0f} ({value / s.x_height:.3f})" for key, value in s.widths().items())
        print(f"{font.name:10} {widths}")
    reference_x_height = strokes[fonts[0].name].x_height
    for point_size in POINT_SIZES:
        reference_ppem = point_size * PPI / 72
        print(
            f"\n== Rendering, {point_size} pt @ {PPI} ppi; {fonts[0].name} {reference_ppem:.1f} px/em,"
            " the others at matched x-height"
        )
        for mode, flags in RENDER_MODES.items():
            for font in fonts:
                ppem = reference_ppem * reference_x_height / strokes[font.name].x_height
                coverage, width = ink_coverage(path=font.path, ppem=ppem, flags=flags)
                stem = stem_row(path=font.path, ppem=ppem, flags=flags)
                print(
                    f"  {mode:15} {font.name:10} ppem={ppem:5.1f} ink/area={coverage:.4f}"
                    f"  line width={width:6.0f}px  'l' stem row: {stem}"
                )


def measure_strokes(path: Path) -> Strokes:
    font = TTFont(path)
    x_height = bounds(font=font, char="x")[3]
    stem_y = x_height * STEM_HEIGHT
    o_bounds = bounds(font=font, char="o")
    h_bounds = bounds(font=font, char="H")
    return Strokes(
        x_height=x_height,
        n_stem=_first_span(crossings(contours=_contours(font=font, char="n"), y=stem_y)),
        l_stem=_first_span(crossings(contours=_contours(font=font, char="l"), y=stem_y)),
        o_side=_first_span(crossings(contours=_contours(font=font, char="o"), y=x_height * 0.5)),
        o_top=_last_span(crossings(contours=_contours(font=font, char="o"), x=(o_bounds[0] + o_bounds[2]) / 2)),
        h_bar=_first_span(crossings(contours=_contours(font=font, char="H"), x=(h_bounds[0] + h_bounds[2]) / 2)),
    )


def crossings(
    contours: list[Contour],
    y: float | None = None,
    x: float | None = None,
) -> list[float]:
    """Where the contours cross the horizontal line at `y` (as x values) or the vertical line at `x` (as y values)."""
    found: list[float] = []
    for contour in contours:
        for (x0, y0), (x1, y1) in zip(contour, contour[1:] + contour[:1], strict=True):
            if y is not None and (y0 <= y < y1 or y1 <= y < y0):
                found.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            if x is not None and (x0 <= x < x1 or x1 <= x < x0):
                found.append(y0 + (x - x0) * (y1 - y0) / (x1 - x0))
    return sorted(found)


def ink_coverage(
    path: Path,
    ppem: float,
    flags: int,
) -> tuple[float, float]:
    """The ink per area of the rendered sample text (one em high), and the text's width in pixels."""
    face = _face(path=path, ppem=ppem)
    ink = 0.0
    width = 0.0
    for char in SAMPLE_TEXT:
        ink += _render(face=face, char=char, flags=flags).sum()
        width += face.glyph.advance.x / 64
    return ink / (width * ppem), width


def stem_row(
    path: Path,
    ppem: float,
    flags: int,
) -> str:
    """The coverage of the pixels across the rendered stem of `l`."""
    bitmap = _render(face=_face(path=path, ppem=ppem), char="l", flags=flags)
    row = bitmap[int(bitmap.shape[0] * STEM_ROW)]
    return " ".join(f"{value:.2f}" for value in row if value > MIN_STEM_COVERAGE)


class _FlatteningPen(BasePen):
    """Collects each contour as a polygon, approximating curves by straight segments."""

    def __init__(
        self,
        glyph_set: GlyphSet,
    ) -> None:
        super().__init__(glyph_set)
        self.contours: list[Contour] = []
        self._current: Contour = []

    @override
    def _moveTo(self, pt: Point) -> None:
        self._current = [pt]

    @override
    def _lineTo(self, pt: Point) -> None:
        self._current.append(pt)

    # pyrefly infers the untyped base method as returning Never, because its default implementation raises.
    @override
    def _qCurveToOne(  # pyrefly: ignore[bad-override]
        self, pt1: Point, pt2: Point
    ) -> None:
        p0 = self._current[-1]
        for t in np.linspace(0, 1, QUADRATIC_STEPS)[1:]:
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            self._current.append((a * p0[0] + b * pt1[0] + c * pt2[0], a * p0[1] + b * pt1[1] + c * pt2[1]))

    @override
    def _curveToOne(self, pt1: Point, pt2: Point, pt3: Point) -> None:
        p0 = self._current[-1]
        for t in np.linspace(0, 1, CUBIC_STEPS)[1:]:
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t**3
            self._current.append(
                (
                    a * p0[0] + b * pt1[0] + c * pt2[0] + d * pt3[0],
                    a * p0[1] + b * pt1[1] + c * pt2[1] + d * pt3[1],
                )
            )

    @override
    def _closePath(self) -> None:
        self.contours.append(self._current)
        self._current = []

    @override
    def _endPath(self) -> None:
        self._closePath()


def _contours(
    font: TTFont,
    char: str,
) -> list[Contour]:
    glyph_set = font.getGlyphSet()
    pen = _FlatteningPen(glyph_set)
    glyph_set[glyph_name(font=font, char=char)].draw(pen)
    return pen.contours


def _first_span(values: list[float]) -> float:
    return values[1] - values[0]


def _last_span(values: list[float]) -> float:
    return values[-1] - values[-2]


def _face(
    path: Path,
    ppem: float,
) -> freetype.Face:
    face = freetype.Face(str(path))
    face.set_char_size(int(ppem * 64), 0, 72, 72)  # at 72 dpi, the size in points is the size in pixels
    return face


def _render(
    face: freetype.Face,
    char: str,
    flags: int,
) -> np.ndarray:
    """The glyph's coverage, from 0 to 1 per pixel."""
    face.load_char(char, flags | FT_LOAD_FLAGS["FT_LOAD_RENDER"])
    bitmap = face.glyph.bitmap
    if not bitmap.rows:
        return np.zeros((0, 0))
    return np.array(bitmap.buffer, dtype=np.float64).reshape(bitmap.rows, bitmap.width) / 255
