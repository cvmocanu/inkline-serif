from builders import counter_clockwise, font, rectangle

from inkline_serif.outlines import find_bad_outlines, normalize_outlines


def test_accepts_clockwise_glyphs_without_overlaps() -> None:
    clean = font(glyphs={"clean": [rectangle(x_min=0, y_min=0, x_max=100, y_max=100)]})

    assert find_bad_outlines(clean) == []


def test_reports_counter_clockwise_and_overlapping_glyphs() -> None:
    bad = font(
        glyphs={
            "reversed": [counter_clockwise(rectangle(x_min=0, y_min=0, x_max=100, y_max=100))],
            "overlapping": [
                rectangle(x_min=0, y_min=0, x_max=100, y_max=100),
                rectangle(x_min=50, y_min=0, x_max=150, y_max=100),
            ],
        }
    )

    assert find_bad_outlines(bad) == ["reversed", "overlapping"]


def test_normalized_outlines_pass_the_check() -> None:
    bad = font(
        glyphs={
            "reversed": [counter_clockwise(rectangle(x_min=0, y_min=0, x_max=100, y_max=100))],
            "overlapping": [
                rectangle(x_min=0, y_min=0, x_max=100, y_max=100),
                rectangle(x_min=50, y_min=0, x_max=150, y_max=100),
            ],
        }
    )

    normalize_outlines(bad)

    assert find_bad_outlines(bad) == []
