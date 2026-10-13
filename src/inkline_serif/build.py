"""Builds the four Inkline Serif styles from the Domine sources, checks them and renders the previews.

Run from the project root: `uv run inkline-build`. The tuning values are the constants below.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from fontTools.ttLib import TTFont
from ttfautohint import ttfautohint
from ttfautohint.options import StemWidthMode

from inkline_serif import naming
from inkline_serif.embolden import Emboldening, embolden
from inkline_serif.italicize import Slant, italicize
from inkline_serif.outlines import find_bad_outlines
from inkline_serif.preview import LabeledFont, save_preview
from inkline_serif.style_axes import set_style_axes

FAMILY = "Inkline Serif"


@dataclass(frozen=True)
class Weight:
    source: str
    upright_style: str
    italic_style: str
    bold: bool
    emboldening: Emboldening


WEIGHTS = (
    Weight(
        source="Domine-Regular.ttf",
        upright_style="Regular",
        italic_style="Italic",
        bold=False,
        emboldening=Emboldening(x=6, y=22),
    ),
    Weight(
        source="Domine-Bold.ttf",
        upright_style="Bold",
        italic_style="Bold Italic",
        bold=True,
        emboldening=Emboldening(x=4, y=18),
    ),
)
SLANT = Slant(angle_deg=10, rotation_fraction=0.4, condense=0.97, single_storey_a=True)
# Snaps stems to full pixels in every rendering mode, up to 96 px per em.
HINTING_RANGE_MAX = 96
STEM_WIDTH_MODE = StemWidthMode.STRONG

INPUT_DIR = Path("input")
FONTS_DIR = Path("output/fonts")
PREVIEWS_DIR = Path("output/previews")
LICENSE = "OFL.txt"
# The fonts are stamped with the time of the last commit that changed these, so a rebuild of unchanged sources
# reproduces the committed fonts byte for byte, and a commit of only the output leaves that time alone.
BUILD_INPUTS = ("input", "src", "pyproject.toml", "uv.lock")


def main() -> None:
    if not INPUT_DIR.is_dir():
        sys.exit(f"the input directory {INPUT_DIR}/ is missing; run inkline-build from the project root")
    epoch = last_change_epoch()
    fonts: dict[str, bytes] = {}
    for weight in WEIGHTS:
        upright = build_upright(weight)
        fonts[weight.upright_style] = hint(font=upright, epoch=epoch)
        fonts[weight.italic_style] = hint(font=build_italic(upright=upright, weight=weight), epoch=epoch)

    failed = False
    for style, data in fonts.items():
        bad = find_bad_outlines(TTFont(BytesIO(data)))
        if bad:
            print(f"{style}: counter-clockwise or overlapping glyphs: {', '.join(bad)}", file=sys.stderr)
            failed = True
    if failed:
        sys.exit(1)

    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for style, data in fonts.items():
        path = font_path(style)
        path.write_bytes(data)
        print("wrote", path)
    # The OFL has to accompany any distribution of the fonts.
    shutil.copyfile(INPUT_DIR / LICENSE, FONTS_DIR / LICENSE)
    write_previews()


def build_upright(weight: Weight) -> bytes:
    font = TTFont(INPUT_DIR / weight.source)
    embolden(font=font, emboldening=weight.emboldening)
    naming.rename(font=font, family=FAMILY, style=weight.upright_style)
    set_style_axes(font=font, italic=False)
    e = weight.emboldening
    naming.set_description(
        font=font,
        text=f"Modified from Domine (OFL 1.1): horizontals +{e.y:g}u, verticals +{e.x:g}u",
    )
    return to_bytes(font)


def build_italic(
    upright: bytes,
    weight: Weight,
) -> bytes:
    font = TTFont(BytesIO(upright))
    italicize(font=font, slant=SLANT, bold=weight.bold)
    naming.rename(font=font, family=FAMILY, style=weight.italic_style)
    naming.set_description(
        font=font,
        text=naming.description(font) + f"; oblique {SLANT.angle_deg:g} deg, optically corrected",
    )
    return to_bytes(font)


def hint(
    font: bytes,
    epoch: int,
) -> bytes:
    """Autohints the font, and stamps it as modified at `epoch` (Unix seconds)."""
    return ttfautohint(
        in_buffer=font,
        epoch=epoch,
        hinting_range_max=HINTING_RANGE_MAX,
        gray_stem_width_mode=STEM_WIDTH_MODE,
        gdi_cleartype_stem_width_mode=STEM_WIDTH_MODE,
        dw_cleartype_stem_width_mode=STEM_WIDTH_MODE,
    )


def last_change_epoch() -> int:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%at", "--", *BUILD_INPUTS],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        sys.exit(f"git found no commit that changed {', '.join(BUILD_INPUTS)} to date the fonts by: {result.stderr}")
    return int(result.stdout)


def write_previews() -> None:
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    save_preview(
        path=PREVIEWS_DIR / "upright-10pt-300ppi.png",
        fonts=[
            LabeledFont(label="Domine", path=INPUT_DIR / "Domine-Regular.ttf"),
            LabeledFont(label=FAMILY, path=font_path("Regular")),
            LabeledFont(label=f"{FAMILY} Bold", path=font_path("Bold")),
        ],
    )
    save_preview(
        path=PREVIEWS_DIR / "italic-10pt-300ppi.png",
        fonts=[
            LabeledFont(label=f"{FAMILY} Italic", path=font_path("Italic")),
            LabeledFont(label=f"{FAMILY} Bold Italic", path=font_path("Bold Italic")),
        ],
    )


def font_path(style: str) -> Path:
    return FONTS_DIR / f"{naming.postscript_name(family=FAMILY, style=style)}.ttf"


def to_bytes(font: TTFont) -> bytes:
    buffer = BytesIO()
    font.save(buffer)
    return buffer.getvalue()
