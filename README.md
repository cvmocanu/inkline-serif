# Inkline Serif

A version of [Domine](https://github.com/googlefonts/domine) modified to read better on e-ink (Kindle).
It keeps Domine's large x-height and overall look, but adds the stroke weight and hinting that make
Bookerly look darker, plus a generated Italic and Bold Italic, which Domine lacks.

Styles: `fonts/InklineSerif-{Regular,Bold,Italic,BoldItalic}.ttf`. To install, copy all four into the Kindle's `fonts/` folder.

## Why: Domine vs Bookerly

The question was why Domine looks lighter than Bookerly at the same weight level. Measured with `tools/measure.py`
(Bookerly-Regular from Amazon's Alexa/Echo branding kit, not included here):

| Metric (Regular) | Bookerly | Domine | Inkline Serif |
|---|---|---|---|
| x-height (em) | 0.511 | 0.540 | ~0.55 |
| Vertical stem `n`/`l` (units; ÷ x-height) | 99 (0.194) | 97 (0.180) | 103 (0.187) |
| Horizontal stroke `o` top | 76 (0.149) | 52 (0.096) | 74 (0.134) |
| `H` crossbar | 74 (0.145) | 58 (0.107) | 80 (0.145) |
| Stroke contrast `o` side ÷ top | 1.37 | 2.06 | ~1.5 |
| TrueType hinting | 84 KB of glyph instructions | none | ttfautohint |
| Ink per text area, 10 pt @ 300 ppi, matched x-height | 0.220 | 0.200 | 0.231 |

Findings:
- **Main cause: stroke contrast.** Domine's horizontal strokes are about 40% thinner relative to its x-height. At 10 pt / 300 ppi they're only about 2 px wide, so on greyscale e-ink they render grey instead of black.
- **Hinting:** Bookerly is heavily hinted and Domine has no hinting at all (it is *not* ttfautohinted). FreeType v40 ignores horizontal hints, so the simulation can't show how much this matters on a Kindle, whose renderer is undocumented.
- **BookerlyLCD:** Amazon also ships `BookerlyLCD_*`, which is unhinted and slightly thinner (stem ÷ x-height 0.181). The regular build is the heavier, hinted one. Whether the Kindle's own Bookerly file matches the branding-kit one is **unverified**.

## What the build does

1. **`tools/embolden.py`: thicken strokes, more horizontally than vertically.**
   - Port of FreeType's `FT_Outline_EmboldenXY`: each point moves outward along the corner bisector, so stems grow by `XS` units and horizontal strokes by `YS`. Counters shrink.
   - Before that, it runs `removeOverlaps` and forces clockwise contours. **This step is required:** 29 Domine glyphs (`five`, parentheses, `circumflex`, `caron`, `breve`, `germandbls`…) have reversed contours, and others (`oslash`, `dcroat`, `hbar`, `Tbar`…) have overlaps. Without the fix those glyphs get *thinner*, and on the first attempt the "5" visibly did.
   - Shifts outlines right by `XS/2` and widens advances by `XS`, so side bearings and letter spacing are preserved.
   - Composites aren't emboldened directly; their components already are. Only offsets and advances are adjusted.
   - Drops the old `fpgm`/`prep`/`cvt`/`hdmx`/`LTSH`/`VDMX` tables and renames the family (see License).
   - Current values: Regular `XS=6 YS=22`, Bold `XS=4 YS=18`.
2. **`tools/italicize.py`: an optically corrected oblique.** This is not a true italic; the letterforms are not redrawn.
   - Transform: rotate by `ROT × ANGLE`, then a vertical shear to restore horizontals, then a horizontal shear to reach exactly `ANGLE`, then condense x by `CONDENSE`. It pivots around half the x-height so glyphs don't drift right.
   - A pure shear thins stems by cos(angle); the rotation part compensates for that. The script prints a sanity line, which should read `vertical -> 10.00 deg, horizontal tilt 0.000 deg`.
   - Composites with scaled or flipped components (5 glyphs) are decomposed first. Other composites get their offsets mapped through the linear part of the transform.
   - GPOS pair-kerning values are scaled by `CONDENSE`.
   - `--single-storey-a`: replaces `a` with `d` cut at the `o` overshoot height (pathops intersection), re-oriented clockwise. Accented a's follow automatically because they are composites. `g` stays two-storey.
   - Sets `post.italicAngle`, the `hhea` caret slope, the `OS/2.fsSelection` italic/bold bits (clearing REGULAR) and `head.macStyle`, so the four files link as one family.
   - Current values: `ANGLE=10 ROT=0.4 CONDENSE=0.97`.
3. **`ttfautohint`** with `--stem-width-mode=sss --hinting-range-max=96` (snaps stems to full pixels).
4. **`tools/check_outlines.py`** fails the build if any glyph is counter-clockwise or has overlaps.
5. **`tools/preview.py`** renders 10 pt at 300 ppi, quantized to 16 grey levels like e-ink, into `docs/*.png`.

## Layout

```
build.sh              one-command rebuild; all tuning values are at the top
requirements.txt      pinned Python deps (built with Python 3.13)
source/               Domine-Regular.ttf, Domine-Bold.ttf (unmodified static Google Fonts builds, OFL)
tools/
  embolden.py         IN OUT XS YS "Family" Style
  italicize.py        IN OUT ANGLE ROT_FRACTION CONDENSE Style [--single-storey-a]
  check_outlines.py   FONT...    -> exit 1 on bad contours
  measure.py          Name=font.ttf ...   stems + FreeType ink coverage at 8/10/12 pt @ 300 ppi
                      (first font is the reference; others are scaled to its x-height)
  preview.py          OUT.png SCALE Name=font.ttf ...
fonts/                build output (committed)
docs/                 preview images
OFL.txt               Domine's license (must ship with the fonts)
```

## Build

```bash
pip install -r requirements.txt     # add --break-system-packages on Debian/Ubuntu system Python
./build.sh
```

`build.sh` runs Python with `-I`, so the scripts must be invoked by path, as `build.sh` does.
A clean build reproduces the delivered fonts with identical outlines (verified).

## Compare against Bookerly

Bookerly isn't redistributable, so it isn't included. Download it from Amazon's
[Echo identity guidelines – typography](https://developer.amazon.com/en-US/alexa/branding/echo-guidelines/identity-guidelines/typography), then:

```bash
python3 -I tools/measure.py Bookerly=/path/Bookerly-Regular.ttf Domine=source/Domine-Regular.ttf Inkline=fonts/InklineSerif-Regular.ttf
python3 -I tools/preview.py docs/vs-bookerly.png 1 Bookerly=/path/Bookerly-Regular.ttf Inkline=fonts/InklineSerif-Regular.ttf
```

## License

- Domine is SIL OFL 1.1 with **Reserved Font Name "Domine"** (stated in `OFL.txt`, *not* in the font's name table). Modified versions **must not** use "Domine" in the font name, which is why the family is "Inkline Serif".
- Name ID 10 (description) records the modification. Mentioning Domine there as attribution is fine.
- `OFL.txt` must accompany any distribution. The fonts can't be sold on their own.

## Known limitations / open questions

- **No on-device testing yet.** Everything is simulated with FreeType and Pillow; the Kindle's rasterizer is undocumented.
- **Whether the Kindle uses TrueType hints at all is unknown.** If it doesn't, ttfautohint is harmless.
- **The italic is an oblique.** Only `a` changes shape. A true italic would need redrawn `e`, `f`, `g`, `k`, `v`/`w`/`y`, entry and exit strokes, and so on.
- **The cut `a`** has a flat stem top (it matches `q`). The bowl comes from `d`, so spacing and kerning use `d`'s advance. Kerning pairs that involve `a` were not re-tuned.
- **Not done:** the variable font (`Domine-VariableFont_wght.ttf`) and the Medium/SemiBold statics. The Kindle only uses the four styles.
- **Unverified:** how the Kindle behaves with sideloaded fonts that lack an italic (synthetic slant vs. plain Regular).

## Ideas for next steps

- Test on device at several sizes. Tune `REG_Y`, the main lever for darkness, and possibly `REG_X`.
- Try ttfautohint `--x-height-increase-limit` and `--stem-width-mode` variants, and compare on device.
- Italic: a single-storey `g`, a `y`/`v`/`w` with italic tails, a narrower `f` with descender, and exit strokes on `n`/`m`/`h`/`u`. Each needs hand-drawn or pathops-built outlines.
- Per-glyph emboldening exceptions if a glyph fills in at small sizes (watch `e`, `a`, `s`, `ß`, `@`).
- Add a smoke test that `measure.py` ink coverage stays within a target band after tuning.
