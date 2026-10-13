"""Make an optically corrected oblique ("italic") from an upright TrueType font.

Transform = rotate by r, vertical shear to restore horizontals, horizontal shear
to reach the target angle, plus a slight horizontal condense. Pure shear thins
stems by cos(angle); the rotation component compensates.

usage: italicize.py IN.ttf OUT.ttf ANGLE_DEG ROT_FRACTION CONDENSE STYLE [--single-storey-a]
"""
import math
import sys

import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.transform import Transform
from fontTools.ttLib import TTFont

src, dst = sys.argv[1], sys.argv[2]
ANGLE, ROTF, CONDENSE, STYLE = float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
SINGLE_A = "--single-storey-a" in sys.argv

f = TTFont(src)
glyf, hmtx = f["glyf"], f["hmtx"]
gs = f.getGlyphSet()
cmap = f.getBestCmap()

bp = BoundsPen(gs); gs[cmap[ord("x")]].draw(bp)
XH = bp.bounds[3]

# --- optional: single-storey 'a' built from 'd' cut at x-height -------------
if SINGLE_A:
    dname, aname = cmap[ord("d")], cmap[ord("a")]
    bp = BoundsPen(gs); gs[cmap[ord("o")]].draw(bp)
    top = bp.bounds[3]  # x-height incl. overshoot of round letters
    d = pathops.Path(); gs[dname].draw(d.getPen())
    box = pathops.Path(); pen = box.getPen()
    pen.moveTo((-500, -500)); pen.lineTo((-500, top)); pen.lineTo((2000, top)); pen.lineTo((2000, -500)); pen.closePath()
    cut = pathops.op(d, box, pathops.PathOp.INTERSECTION)
    from fontTools.pens.areaPen import AreaPen
    from fontTools.pens.reverseContourPen import ReverseContourPen
    ap = AreaPen(); cut.draw(ap)
    tp = TTGlyphPen(None)
    cut.draw(ReverseContourPen(tp) if ap.value > 0 else tp)  # TrueType wants clockwise
    g = tp.glyph()
    glyf[aname] = g
    g.recalcBounds(glyf)
    hmtx[aname] = (hmtx[dname][0], g.xMin)

# --- the slant transform ------------------------------------------------------
r = math.radians(ANGLE * ROTF)
k = math.tan(math.radians(ANGLE)) / CONDENSE - math.sin(r) * math.cos(r)  # exact ANGLE after condense
rot = Transform(math.cos(r), -math.sin(r), math.sin(r), math.cos(r), 0, 0)  # (x,y)->(x cos+y sin, -x sin+y cos)
vshear = Transform(1, math.tan(r), 0, 1, 0, 0)                               # y += x tan r
hshear = Transform(1, 0, k, 1, 0, 0)                                         # x += k y
cond = Transform(CONDENSE, 0, 0, 1, 0, 0)
c = XH / 2  # slant around half x-height so glyphs don't drift right
# a.transform(b) applies b first: order = -c, rot, vshear, hshear, condense, +c
T = Transform().translate(0, c)
for t in (cond, hshear, vshear, rot):
    T = T.transform(t)
T = T.translate(0, -c)
lin = Transform(T.xx, T.xy, T.yx, T.yy, 0, 0)

# sanity: vertical maps to ANGLE, horizontal stays horizontal
vx, vy = lin.transformPoint((0, 1)); hx, hy = lin.transformPoint((1, 0))
print(f"vertical -> {math.degrees(math.atan2(vx, vy)):.2f} deg, horizontal tilt {math.degrees(math.atan2(hy, hx)):.3f} deg")

# composites whose components are scaled/flipped can't be slanted via offsets: decompose them
for name in f.getGlyphOrder():
    g = glyf[name]
    if g.isComposite() and any(hasattr(cp, "transform") for cp in g.components):
        rp = DecomposingRecordingPen(gs); gs[name].draw(rp)
        tp = TTGlyphPen(None); rp.replay(tp)
        glyf[name] = tp.glyph()
gs = f.getGlyphSet()

new = {}
for name in f.getGlyphOrder():
    g = glyf[name]
    if g.isComposite():
        continue
    if g.numberOfContours <= 0:
        continue
    tp = TTGlyphPen(gs)
    gs[name].draw(TransformPen(tp, T))
    new[name] = tp.glyph()
for name, g in new.items():
    glyf[name] = g
for name in f.getGlyphOrder():
    g = glyf[name]
    if g.isComposite():
        for comp in g.components:
            # component outlines already transformed (incl. translation about c);
            # offsets must be mapped by the linear part only
            comp.x, comp.y = (round(v) for v in lin.transformPoint((comp.x, comp.y)))
    adv, _ = hmtx[name]
    g.recalcBounds(glyf)
    hmtx[name] = (round(adv * CONDENSE), getattr(g, "xMin", 0) if g.numberOfContours else 0)

# kerning/positioning values scale with the condense
if "GPOS" in f:
    from fontTools.ttLib.tables.otBase import BaseTable
    def scale_vr(vr):
        if vr is None: return
        for a in ("XAdvance", "XPlacement"):
            if hasattr(vr, a): setattr(vr, a, round(getattr(vr, a) * CONDENSE))
    for lk in f["GPOS"].table.LookupList.Lookup:
        for st in lk.SubTable:
            st = getattr(st, "ExtSubTable", st)
            if st.LookupType == 2:
                if st.Format == 1:
                    for ps in st.PairSet:
                        for pvr in ps.PairValueRecord: scale_vr(pvr.Value1); scale_vr(pvr.Value2)
                else:
                    for c1 in st.Class1Record:
                        for c2 in c1.Class2Record: scale_vr(c2.Value1); scale_vr(c2.Value2)

# --- style flags & names ------------------------------------------------------
f["post"].italicAngle = -ANGLE
f["hhea"].caretSlopeRise = 1000
f["hhea"].caretSlopeRun = round(1000 * math.tan(math.radians(ANGLE)))
os2 = f["OS/2"]
bold = "Bold" in STYLE
os2.fsSelection = (os2.fsSelection & ~(1 << 6) & ~(1 << 5) & ~1) | 1 | ((1 << 5) if bold else 0)
f["head"].macStyle = 2 | (1 if bold else 0)
name = f["name"]
fam = name.getDebugName(1)
ps = fam.replace(" ", "") + "-" + STYLE.replace(" ", "")
for rec in name.names:
    if rec.nameID == 2: rec.string = STYLE
    elif rec.nameID == 3: rec.string = f"{ps};modified"
    elif rec.nameID == 4: rec.string = f"{fam} {STYLE}"
    elif rec.nameID == 6: rec.string = ps
name.setName(name.getDebugName(10) + f"; oblique {ANGLE:g} deg, optically corrected", 10, 3, 1, 0x409)
f.save(dst)
print("wrote", dst)
