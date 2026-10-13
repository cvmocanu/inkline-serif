"""Renders sample text at 10 pt and 300 ppi, quantized to the 16 grey levels of e-ink.

The fonts come in groups, such as before-and-after pairs, separated by a rule.

usage: inkline-preview OUT.png Label=font.ttf [Label=font.ttf ...] [--scale SCALE]   (one group)
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SAMPLE_LINES = (
    "She said, “I have read *that* book twice — naïve, really.”",
    "abcdefghijklmnopqrstuvwxyz áàâäãåæçéêëíïñóôöøúüß",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 (fig. 4) [a; b] {c}?!",
)
POINT_SIZE = 10
PPI = 300
WIDTH_PX = 1900
MARGIN_PX = 10
GREY_LEVELS = 16
LABEL_GREY = 120
RULE_GREY = 170
# Line heights and gaps, as multiples of the text size
LINE_HEIGHT = 1.5
LABEL_SIZE = 0.5
LABEL_HEIGHT = 0.8
FONT_GAP = 0.4
GROUP_GAP = 0.6


@dataclass(frozen=True)
class LabeledFont:
    label: str
    data: bytes


def main() -> None:
    parser = argparse.ArgumentParser(description="Render sample text the way e-ink shows it.")
    parser.add_argument("out", type=Path, help="the PNG to write")
    parser.add_argument("fonts", nargs="+", type=parse_labeled_font, help="Label=font.ttf; labels use the first font")
    parser.add_argument("--scale", type=float, default=1.0, help="magnification of the whole image")
    args = parser.parse_args()
    save_preview(path=args.out, groups=[args.fonts], scale=args.scale)


def parse_labeled_font(argument: str) -> LabeledFont:
    label, separator, path = argument.partition("=")
    if not separator:
        raise argparse.ArgumentTypeError(f"expected Label=font.ttf, got {argument!r}")
    return LabeledFont(label=label, data=Path(path).read_bytes())


def save_preview(
    path: Path,
    groups: Sequence[Sequence[LabeledFont]],
    scale: float = 1.0,
) -> None:
    render_preview(groups=groups, scale=scale).save(path)
    print("wrote", path)


def render_preview(
    groups: Sequence[Sequence[LabeledFont]],
    scale: float,
) -> Image.Image:
    size = int(POINT_SIZE * PPI / 72 * scale)
    font_height = int(size * LABEL_HEIGHT) + len(SAMPLE_LINES) * int(size * LINE_HEIGHT) + int(size * FONT_GAP)
    font_count = sum(len(group) for group in groups)
    height = 2 * MARGIN_PX + font_count * font_height + (len(groups) - 1) * int(size * GROUP_GAP)
    width = int(WIDTH_PX * scale)
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)
    label_font = ImageFont.truetype(BytesIO(groups[0][0].data), int(size * LABEL_SIZE))
    y = MARGIN_PX
    for index, group in enumerate(groups):
        if index > 0:
            rule_y = y + int(size * GROUP_GAP) // 2
            draw.line([(MARGIN_PX, rule_y), (width - MARGIN_PX, rule_y)], fill=RULE_GREY)
            y += int(size * GROUP_GAP)
        for font in group:
            draw.text((MARGIN_PX, y), font.label, font=label_font, fill=LABEL_GREY)
            y += int(size * LABEL_HEIGHT)
            text_font = ImageFont.truetype(BytesIO(font.data), size)
            for line in SAMPLE_LINES:
                draw.text((MARGIN_PX, y), line, font=text_font, fill=0)
                y += int(size * LINE_HEIGHT)
            y += int(size * FONT_GAP)
    return quantize(image)


def quantize(image: Image.Image) -> Image.Image:
    step = 255 // (GREY_LEVELS - 1)
    return image.point(lambda value: (value * (GREY_LEVELS - 1) // 255) * step)
