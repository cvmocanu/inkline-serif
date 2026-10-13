from io import BytesIO
from pathlib import Path

from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.ttLib import TTFont

from inkline_serif.build import hint

DOMINE_REGULAR = Path(__file__).parents[1] / "input" / "Domine-Regular.ttf"


def test_stamps_the_hinted_font_with_the_given_time_rather_than_now() -> None:
    epoch = 1_700_000_000

    hinted = TTFont(BytesIO(hint(font=DOMINE_REGULAR.read_bytes(), epoch=epoch)))

    assert hinted["head"].modified == timestampSinceEpoch(epoch)
