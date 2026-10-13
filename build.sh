#!/usr/bin/env bash
# Rebuild all four Inkline Serif styles from the Domine sources.
# Tuning values live here; see README.md for what each one does.
set -euo pipefail
cd "$(dirname "$0")"

FAMILY="Inkline Serif"
# embolden: extra width of vertical stems / horizontal strokes, in font units (UPM 1000)
REG_X=6;  REG_Y=22
BOLD_X=4; BOLD_Y=18
# italicize: slant angle (deg), share of the angle done by rotation, horizontal condense
ANGLE=10; ROT=0.4; CONDENSE=0.97
# ttfautohint
HINT_ARGS=(--stem-width-mode=sss --hinting-range-max=96)

PY="python3 -I"
BUILD=build
mkdir -p "$BUILD" fonts

$PY tools/embolden.py  source/Domine-Regular.ttf "$BUILD/Regular.ttf"    $REG_X  $REG_Y  "$FAMILY" Regular
$PY tools/embolden.py  source/Domine-Bold.ttf    "$BUILD/Bold.ttf"       $BOLD_X $BOLD_Y "$FAMILY" Bold
$PY tools/italicize.py "$BUILD/Regular.ttf"      "$BUILD/Italic.ttf"     $ANGLE $ROT $CONDENSE "Italic"      --single-storey-a
$PY tools/italicize.py "$BUILD/Bold.ttf"         "$BUILD/BoldItalic.ttf" $ANGLE $ROT $CONDENSE "Bold Italic" --single-storey-a

for s in Regular Bold Italic BoldItalic; do
  python3 -m ttfautohint "${HINT_ARGS[@]}" "$BUILD/$s.ttf" "fonts/InklineSerif-$s.ttf"
done

$PY tools/check_outlines.py fonts/InklineSerif-*.ttf
$PY tools/preview.py docs/upright-10pt-300ppi.png 1 \
  "Domine=source/Domine-Regular.ttf" \
  "Inkline Serif=fonts/InklineSerif-Regular.ttf" \
  "Inkline Serif Bold=fonts/InklineSerif-Bold.ttf"
$PY tools/preview.py docs/italic-10pt-300ppi.png 1 \
  "Inkline Serif Italic=fonts/InklineSerif-Italic.ttf" \
  "Inkline Serif Bold Italic=fonts/InklineSerif-BoldItalic.ttf"
echo "done: fonts/ and docs/ updated"
