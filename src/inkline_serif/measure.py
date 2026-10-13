import sys
import numpy as np
import freetype
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.basePen import BasePen

FONTS = dict(arg.split("=", 1) for arg in sys.argv[1:])
TEXT = "the quick brown fox jumps over the lazy dog and reads a long book in the evening"


class Flatten(BasePen):
    def __init__(self, gs):
        super().__init__(gs); self.contours = []; self.cur = []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 12)[1:]:
            self.cur.append(((1-t)**2*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0], (1-t)**2*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]))
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, 16)[1:]:
            a, b, c, d = (1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3
            self.cur.append((a*p0[0]+b*p1[0]+c*p2[0]+d*p3[0], a*p0[1]+b*p1[1]+c*p2[1]+d*p3[1]))
    def _closePath(self): self.contours.append(self.cur); self.cur = []
    _endPath = _closePath


def crossings(contours, y=None, x=None):
    out = []
    for c in contours:
        for (x0, y0), (x1, y1) in zip(c, c[1:] + c[:1]):
            if y is not None and (y0 <= y < y1 or y1 <= y < y0):
                out.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            if x is not None and (x0 <= x < x1 or x1 <= x < x0):
                out.append(y0 + (x - x0) * (y1 - y0) / (x1 - x0))
    return sorted(out)


def stems(path):
    f = TTFont(path); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    def contours(ch):
        pen = Flatten(gs); gs[cmap[ord(ch)]].draw(pen); return pen.contours
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(gs); gs[cmap[ord("x")]].draw(bp); xh = bp.bounds[3]
    r = {"xh": xh}
    xs = crossings(contours("n"), y=xh * 0.45); r["n_stem"] = xs[1] - xs[0]
    xs = crossings(contours("l"), y=xh * 0.45); r["l_stem"] = xs[1] - xs[0]
    xs = crossings(contours("o"), y=xh * 0.5); r["o_side"] = xs[1] - xs[0]
    b = BoundsPen(gs); gs[cmap[ord("o")]].draw(b); cx = (b.bounds[0] + b.bounds[2]) / 2
    ys = crossings(contours("o"), x=cx); r["o_top"] = ys[-1] - ys[-2]
    b = BoundsPen(gs); gs[cmap[ord("H")]].draw(b)
    ys = crossings(contours("H"), x=(b.bounds[0] + b.bounds[2]) / 2)
    r["H_bar"] = ys[1] - ys[0]
    return r


def render(path, px_per_em, flags):
    face = freetype.Face(path)
    face.set_char_size(int(px_per_em * 64), 0, 72, 72)  # 72 dpi => size in px
    pen_x = 0; ink = 0.0; pixels_black = 0
    for ch in TEXT:
        face.load_char(ch, flags | freetype.FT_LOAD_RENDER)
        bm = face.glyph.bitmap
        a = np.array(bm.buffer, dtype=np.float64).reshape(bm.rows, bm.width) / 255 if bm.rows else np.zeros((0, 0))
        ink += a.sum(); pixels_black += (a > 0.85).sum()
        pen_x += face.glyph.advance.x / 64
    line_h = px_per_em  # ink per (advance width x 1 em) of text
    return ink / (pen_x * line_h), ink, pen_x


def stem_px(path, px_per_em, flags, ch="l"):
    face = freetype.Face(path); face.set_char_size(int(px_per_em * 64), 0, 72, 72)
    face.load_char(ch, flags | freetype.FT_LOAD_RENDER)
    bm = face.glyph.bitmap
    a = np.array(bm.buffer, dtype=np.float64).reshape(bm.rows, bm.width) / 255
    row = a[int(bm.rows * 0.6)]  # a row through the stem, below the serif zone
    return " ".join(f"{v:.2f}" for v in row if v > 0.02)


MODES = {
    "native hinting": freetype.FT_LOAD_NO_AUTOHINT,
    "no hinting": freetype.FT_LOAD_NO_HINTING,
    "autohint light": freetype.FT_LOAD_FORCE_AUTOHINT | freetype.FT_LOAD_TARGET_LIGHT,
}

print("== Design (font units, and normalized to x-height)")
for name, p in FONTS.items():
    s = stems(p); xh = s["xh"]
    print(f"{name:10} " + "  ".join(f"{k}={v:.0f} ({v/xh:.3f})" for k, v in s.items() if k != "xh"))

# 300 ppi, Kindle sizes: ~8pt..12pt  -> px/em = pt * 300/72
for pt in (8, 10, 12):
    ppem_book = pt * 300 / 72
    print(f"\n== Rendering, {pt} pt @ 300 ppi; Bookerly {ppem_book:.1f} px/em, Domine at matched x-height")
    xh = {n: stems(p)["xh"] for n, p in FONTS.items()}
    ref = list(FONTS)[0]
    for mode, fl in MODES.items():
        for name, p in FONTS.items():
            ppem = ppem_book * xh[ref] / xh[name]
            cov, ink, width = render(p, ppem, fl)
            print(f"  {mode:15} {name:10} ppem={ppem:5.1f} ink/area={cov:.4f}  line width={width:6.0f}px  'l' stem row: {stem_px(p, ppem, fl)}")
