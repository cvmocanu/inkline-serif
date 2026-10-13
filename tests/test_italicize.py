import math
from typing import Any

import pytest
from builders import font

from inkline_serif.italicize import (
    FS_BOLD,
    FS_ITALIC,
    FS_REGULAR,
    MAC_BOLD,
    MAC_ITALIC,
    Slant,
    set_italic_flags,
    slant_transform,
)


@pytest.mark.parametrize("rotation_fraction", [0.0, 0.4, 1.0])
@pytest.mark.parametrize("condense", [0.9, 0.97, 1.0])
def test_slants_verticals_by_exactly_the_angle_and_keeps_horizontals_level(
    rotation_fraction: float,
    condense: float,
) -> None:
    slant = Slant(angle_deg=10, rotation_fraction=rotation_fraction, condense=condense, single_storey_a=False)

    transform = slant_transform(slant=slant, pivot_y=0)

    vertical_x, vertical_y = transform.transformPoint((0, 1))
    horizontal_x, horizontal_y = transform.transformPoint((1, 0))
    assert math.degrees(math.atan2(vertical_x, vertical_y)) == pytest.approx(10)
    assert math.degrees(math.atan2(horizontal_y, horizontal_x)) == pytest.approx(0, abs=1e-9)


def test_leaves_the_pivot_height_in_place() -> None:
    slant = Slant(angle_deg=10, rotation_fraction=0.4, condense=0.97, single_storey_a=False)

    transform = slant_transform(slant=slant, pivot_y=250)

    assert transform.transformPoint((0, 250)) == pytest.approx((0, 250))


def test_condenses_horizontally() -> None:
    slant = Slant(angle_deg=10, rotation_fraction=0.4, condense=0.9, single_storey_a=False)

    transform = slant_transform(slant=slant, pivot_y=0)

    horizontal_x, _ = transform.transformPoint((1, 0))
    # The rotation shortens horizontals by cos(r); the vertical shear only levels them again.
    rotation_shortening = math.cos(math.radians(10 * 0.4))
    assert horizontal_x == pytest.approx(0.9 * rotation_shortening)


@pytest.mark.parametrize(
    ("bold", "fs_selection", "mac_style"),
    [
        (False, FS_ITALIC, MAC_ITALIC),
        (True, FS_ITALIC | FS_BOLD, MAC_ITALIC | MAC_BOLD),
    ],
)
def test_marks_the_font_italic_and_clears_regular(
    bold: bool,
    fs_selection: int,
    mac_style: int,
) -> None:
    regular = font()
    # fontTools creates the attributes of these tables at runtime, so the type checker can't see them.
    os2: Any = regular["OS/2"]
    head: Any = regular["head"]
    post: Any = regular["post"]
    hhea: Any = regular["hhea"]
    os2.fsSelection = FS_REGULAR

    set_italic_flags(font=regular, angle_deg=10, bold=bold)

    assert os2.fsSelection == fs_selection
    assert head.macStyle == mac_style
    assert post.italicAngle == -10
    assert hhea.caretSlopeRun / hhea.caretSlopeRise == pytest.approx(math.tan(math.radians(10)), abs=1e-3)
