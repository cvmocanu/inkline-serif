from builders import font

from inkline_serif import naming


def test_renames_family_style_and_derived_names() -> None:
    source = font(family="Source Family", style="Regular")

    naming.rename(font=source, family="New Family", style="Bold Italic")

    name = source["name"]
    assert name.getDebugName(1) == "New Family"
    assert name.getDebugName(2) == "Bold Italic"
    assert name.getDebugName(3) == "NewFamily-BoldItalic;modified"
    assert name.getDebugName(4) == "New Family Bold Italic"
    assert name.getDebugName(6) == "NewFamily-BoldItalic"


def test_replaces_the_description() -> None:
    described = font()
    naming.set_description(font=described, text="first")

    naming.set_description(font=described, text="second")

    assert naming.description(described) == "second"
