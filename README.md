# Inkline Serif

A version of [Domine](https://github.com/googlefonts/domine) modified to read better on e-ink (Kindle).
It keeps Domine's large x-height and overall look, but adds the stroke weight and hinting that make
Bookerly look darker, plus a generated Italic and Bold Italic, which Domine lacks.

The fonts are in [`output/fonts/`](output/fonts/). To install them, copy the `.ttf` files into the Kindle's `fonts/` folder.
[The preview](output/previews/domine-vs-inkline-serif-10pt-300ppi.png) sets each style under its Domine counterpart, at 10 pt and 300 ppi,
quantized to e-ink's 16 grey levels. Domine has no italic, so its italics there are synthetic: sheared by the same angle,
the way a renderer slants a font that lacks one.

## Why: Domine vs Bookerly

The question was why Domine looks lighter than Bookerly at the same weight level. Measured with `inkline-measure`
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

The tuning values are the constants at the top of [`build.py`](src/inkline_serif/build.py).

1. **Thicken strokes, more horizontally than vertically** ([`embolden.py`](src/inkline_serif/embolden.py)).
   - Port of FreeType's `FT_Outline_EmboldenXY`: each point moves outward along the corner bisector, so stems grow by `Emboldening.x` units and horizontal strokes by `Emboldening.y`. Counters shrink.
   - Before that, it merges overlapping contours and forces clockwise contours. **This step is required:** 29 Domine glyphs (`five`, parentheses, `circumflex`, `caron`, `breve`, `germandbls`…) have reversed contours, and others (`oslash`, `dcroat`, `hbar`, `Tbar`…) have overlaps. Without the fix those glyphs get *thinner*.
   - Shifts outlines right by half the extra stem width and widens advances by all of it, so side bearings and letter spacing are preserved.
   - Composites aren't emboldened directly; their components already are. Only offsets and advances are adjusted.
   - Drops the source's hinting tables and renames the family (see License).
2. **Make an optically corrected oblique** ([`italicize.py`](src/inkline_serif/italicize.py)). This is not a true italic; the letterforms are not redrawn.
   - Transform: rotate by part of the angle (`Slant.rotation_fraction`), then a vertical shear to restore horizontals, then a horizontal shear to reach exactly `Slant.angle_deg`, then condense x by `Slant.condense`. It pivots around half the x-height so glyphs don't drift right.
   - A pure shear thins stems by cos(angle); the rotation part compensates for that.
   - Composites with scaled or flipped components (5 glyphs in Domine) are decomposed first. Other composites get their offsets mapped through the linear part of the transform.
   - GPOS pair-kerning values are scaled by the condense factor.
   - `Slant.single_storey_a`: replaces `a` with `d` cut at the `o` overshoot height (pathops intersection), re-oriented clockwise. Accented a's follow automatically because they are composites. `g` stays two-storey.
   - Sets `post.italicAngle`, the `hhea` caret slope, the `OS/2.fsSelection` italic/bold bits (clearing REGULAR) and `head.macStyle`, so the four files link as one family.
   - Every style gets a STAT table with a weight and an italic axis ([`style_axes.py`](src/inkline_serif/style_axes.py)), so apps that read STAT group the uprights and italics as one family. Domine's own STAT has a weight axis only.
3. **Hint with ttfautohint**, with strong stem widths in every rendering mode, which snaps stems to full pixels.
4. **Check the outlines** ([`outlines.py`](src/inkline_serif/outlines.py)): the build fails, and writes nothing, if any glyph is counter-clockwise or has overlaps.
5. **Write** the fonts with a copy of `OFL.txt` to `output/fonts/`, then render the preview to `output/previews/`.

## Layout

```
input/                Domine-Regular.ttf, Domine-Bold.ttf (unmodified static Google Fonts builds) and their OFL.txt
output/               build output (committed)
  fonts/              the four Inkline Serif styles and OFL.txt: the folder to distribute
  previews/           Domine vs Inkline Serif, style by style, at 10 pt @ 300 ppi, quantized like e-ink
src/inkline_serif/
  build.py            the pipeline and its tuning values (inkline-build)
  embolden.py         anisotropic emboldening
  italicize.py        the oblique and its style flags
  naming.py           family and style names
  style_axes.py       the STAT weight and italic axes
  outlines.py         contour direction and overlap normalization and checks
  glyphs.py           glyph lookup by character
  measure.py          stroke widths and FreeType ink coverage (inkline-measure)
  preview.py          e-ink-like sample renderings (inkline-preview)
  synthetic_oblique.py  the plain shear that renderers apply to fonts without an italic
tests/
check.sh              format, lint, type check and tests
```

## Build

Requires [uv](https://docs.astral.sh/uv/). From the project root:

```bash
uv run inkline-build    # rebuilds output/
./check.sh              # format, lint, type check, tests
```

The fonts are stamped with the author date of the last commit that changed `input/`, `src/`, `pyproject.toml` or `uv.lock`,
so rebuilding unchanged sources reproduces the committed `output/` byte for byte. After committing such a change,
rebuild and commit the output, or amend it into the same commit.

## Compare against Bookerly

Bookerly isn't redistributable, so it isn't included. Download it from Amazon's
[Echo identity guidelines – typography](https://developer.amazon.com/en-US/alexa/branding/echo-guidelines/identity-guidelines/typography), then:

```bash
uv run inkline-measure Bookerly=/path/Bookerly-Regular.ttf Domine=input/Domine-Regular.ttf Inkline=output/fonts/InklineSerif-Regular.ttf
uv run inkline-preview vs-bookerly.png Bookerly=/path/Bookerly-Regular.ttf Inkline=output/fonts/InklineSerif-Regular.ttf
```

`inkline-measure` renders every font after the first at the size that matches the first font's x-height.

## License

The code is under the [MIT License](LICENSE). The fonts are under the SIL Open Font License 1.1, which they inherit from Domine ([`OFL.txt`](input/OFL.txt)):

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

- Test on device at several sizes. Tune the Regular's `Emboldening.y`, the main lever for darkness, and possibly its `Emboldening.x`.
- Try ttfautohint's x-height increase limit and stem width modes, and compare on device.
- Italic: a single-storey `g`, a `y`/`v`/`w` with italic tails, a narrower `f` with descender, and exit strokes on `n`/`m`/`h`/`u`. Each needs hand-drawn or pathops-built outlines.
- Per-glyph emboldening exceptions if a glyph fills in at small sizes (watch `e`, `a`, `s`, `ß`, `@`).
- Add a smoke test that `inkline-measure` ink coverage stays within a target band after tuning.
