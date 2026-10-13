"""Validate outlines: every simple glyph must be clockwise (TrueType) and free of overlaps.

A glyph fails if its signed area is positive (counter-clockwise) or if removing
overlaps changes its area by more than 1 %.

usage: check_outlines.py FONT.ttf [FONT.ttf ...]     exit code 1 if any glyph fails
"""
import sys

import pathops
from fontTools.pens.areaPen import AreaPen
from fontTools.ttLib import TTFont

failed = False
for path in sys.argv[1:]:
    font = TTFont(path)
    gs = font.getGlyphSet()
    glyf = font["glyf"]
    bad = []
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        ap = AreaPen(gs)
        gs[name].draw(ap)
        p = pathops.Path()
        gs[name].draw(p.getPen())
        simplified = pathops.Path(p)
        simplified.simplify()
        if ap.value > 0 or abs(abs(ap.value) - abs(simplified.area)) > abs(ap.value) * 0.01:
            bad.append(name)
    print(f"{path}: {'OK' if not bad else 'FAIL ' + ', '.join(bad)}")
    failed |= bool(bad)
sys.exit(1 if failed else 0)
