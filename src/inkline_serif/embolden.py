"""Anisotropic emboldening of a TrueType (glyf) font.

Port of FreeType's FT_Outline_EmboldenXY: every point is pushed outward along the
corner bisector, so stems grow by `xs` font units and horizontal strokes by `ys`.
Counters shrink accordingly (inner contours have opposite orientation).

usage: embolden.py IN.ttf OUT.ttf XS YS "Family Name" "Style"
"""
import math
import sys

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates

src, dst, XS, YS, family, style = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]

f = TTFont(src)
glyf = f["glyf"]
hmtx = f["hmtx"]

# Normalize outlines: merge overlapping contours, then force TrueType (clockwise) direction.
from fontTools.ttLib.removeOverlaps import removeOverlaps
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.reverseContourPen import ReverseContourPen

removeOverlaps(f)
gs = f.getGlyphSet()
for gname in f.getGlyphOrder():
    g = glyf[gname]
    if g.isComposite() or g.numberOfContours <= 0:
        continue
    ap = AreaPen(gs); gs[gname].draw(ap)
    if ap.value > 0:  # counter-clockwise overall -> reverse
        tp = TTGlyphPen(gs); gs[gname].draw(ReverseContourPen(tp))
        glyf[gname] = tp.glyph()
gs = f.getGlyphSet()


def embolden_contour(pts, xs, ys):
    """pts: list of (x, y); TrueType orientation (outer contours clockwise)."""
    n = len(pts)
    if n < 3:
        return pts
    xs, ys = xs / 2, ys / 2
    out_pts = []

    def unit(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        l = math.hypot(dx, dy)
        return (dx / l, dy / l) if l else (0.0, 0.0)

    for j in range(n):
        prev, cur, nxt = pts[j - 1], pts[j], pts[(j + 1) % n]
        # skip zero-length neighbours
        k = 1
        while pts[j - k] == cur and k < n:
            k += 1
        prev = pts[j - k]
        k = 1
        while pts[(j + k) % n] == cur and k < n:
            k += 1
        nxt = pts[(j + k) % n]
        vin, vout = unit(prev, cur), unit(cur, nxt)
        d = vin[0] * vout[0] + vin[1] * vout[1]
        if d > -0.9375:
            d += 1
            sx = -(vin[1] + vout[1])  # TrueType orientation
            sy = vin[0] + vout[0]
            q = -(vout[0] * vin[1] - vout[1] * vin[0])
            l = min(xs, ys)
            if q <= l * d:
                sx, sy = sx * xs / d, sy * ys / d
            else:
                sx, sy = sx * l / q, sy * l / q
        else:
            sx = sy = 0.0
        out_pts.append((cur[0] + sx, cur[1] + sy))
    return out_pts


for name in f.getGlyphOrder():
    g = glyf[name]
    adv, lsb = hmtx[name]
    if g.isComposite():
        # components are emboldened in their own glyphs; keep spacing consistent
        for c in g.components:
            c.x += round(XS / 2)
        hmtx[name] = (adv + round(XS), lsb)
        continue
    if g.numberOfContours <= 0:
        hmtx[name] = (adv + round(XS) if adv else adv, lsb)
        continue
    coords = list(g.coordinates)
    new = []
    start = 0
    for end in g.endPtsOfContours:
        new.extend(embolden_contour(coords[start:end + 1], XS, YS))
        start = end + 1
    # shift right by XS/2 so side bearings are preserved, widen advance by XS
    g.coordinates = GlyphCoordinates([(round(x + XS / 2), round(y)) for x, y in new])
    g.program = None
    if hasattr(g, "program"):
        from fontTools.ttLib.tables import ttProgram
        g.program = ttProgram.Program(); g.program.fromBytecode(b"")
    g.recalcBounds(glyf)
    hmtx[name] = (adv + round(XS), g.xMin)

# drop old (empty) hinting tables; ttfautohint adds its own later
for t in ("fpgm", "prep", "cvt ", "hdmx", "LTSH", "VDMX"):
    if t in f:
        del f[t]

# rename so it never collides with the original Domine on a device
name = f["name"]
ps = family.replace(" ", "") + "-" + style.replace(" ", "")
for rec in list(name.names):
    if rec.nameID in (1, 16):
        rec.string = family
    elif rec.nameID in (2, 17):
        rec.string = style
    elif rec.nameID == 3:
        rec.string = f"{ps};modified"
    elif rec.nameID == 4:
        rec.string = f"{family} {style}"
    elif rec.nameID == 6:
        rec.string = ps
name.setName(f"Modified from Domine (OFL 1.1): horizontals +{YS:g}u, verticals +{XS:g}u", 10, 3, 1, 0x409)
f["head"].fontRevision = f["head"].fontRevision
f.save(dst)
print("wrote", dst)
