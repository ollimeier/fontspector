import io
import os
import pytest

import fontTools.ttLib
from fontTools.ttLib import TTFont
import fontTools.subset

from fontbakery.status import INFO, WARN, FAIL, PASS, ERROR
from fontbakery.codetesting import (
    assert_PASS,
    assert_SKIP,
    assert_results_contain,
    portable_path,
    TEST_FILE,
    MockFont,
)
from conftest import check_id


mada_fonts = [
    TEST_FILE("mada/Mada-Black.ttf"),
    TEST_FILE("mada/Mada-ExtraLight.ttf"),
    TEST_FILE("mada/Mada-Medium.ttf"),
    TEST_FILE("mada/Mada-SemiBold.ttf"),
    TEST_FILE("mada/Mada-Bold.ttf"),
    TEST_FILE("mada/Mada-Light.ttf"),
    TEST_FILE("mada/Mada-Regular.ttf"),
]


@pytest.fixture
def mada_ttFonts():
    return [TTFont(path) for path in mada_fonts]


cabin_fonts = [
    TEST_FILE("cabin/Cabin-BoldItalic.ttf"),
    TEST_FILE("cabin/Cabin-Bold.ttf"),
    TEST_FILE("cabin/Cabin-Italic.ttf"),
    TEST_FILE("cabin/Cabin-MediumItalic.ttf"),
    TEST_FILE("cabin/Cabin-Medium.ttf"),
    TEST_FILE("cabin/Cabin-Regular.ttf"),
    TEST_FILE("cabin/Cabin-SemiBoldItalic.ttf"),
    TEST_FILE("cabin/Cabin-SemiBold.ttf"),
]


@check_id("opentype/family/panose_familytype")
def test_check_family_panose_familytype(check, mada_ttFonts):
    """Fonts have consistent PANOSE family type ?"""
    assert_PASS(check(mada_ttFonts), "with good family.")

    # introduce a wrong value in one of the font files:
    value = mada_ttFonts[0]["OS/2"].panose.bFamilyType
    incorrect_value = value + 1
    mada_ttFonts[0]["OS/2"].panose.bFamilyType = incorrect_value

    assert_results_contain(
        check(mada_ttFonts), WARN, "inconsistency", "with inconsistent family."
    )


@check_id("opentype/xavgcharwidth")
def test_check_xavgcharwidth(check):
    """Check if OS/2 xAvgCharWidth is correct."""

    test_font_path = TEST_FILE("nunito/Nunito-Regular.ttf")

    test_font = TTFont(test_font_path)
    assert_PASS(check(test_font))

    test_font["OS/2"].xAvgCharWidth = 556
    assert_results_contain(check(test_font), INFO, "xAvgCharWidth-close")

    test_font["OS/2"].xAvgCharWidth = 500
    assert_results_contain(
        check(test_font), WARN, "xAvgCharWidth-wrong"
    )  # FIXME: This needs a message keyword

    # XXX We can't actually save an *empty* postv4 font

    test_font = TTFont(test_font_path)
    subsetter = fontTools.subset.Subsetter()
    subsetter.populate(
        glyphs=[
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
            "space",
        ]
    )
    subsetter.subset(test_font)
    test_font["OS/2"].xAvgCharWidth = 447
    test_font["OS/2"].version = 2
    temp_file = io.BytesIO()
    test_font.save(temp_file)
    test_font = TTFont(temp_file)
    test_font.reader.file.name = "foo.ttf"
    assert_PASS(check(test_font))

    test_font["OS/2"].xAvgCharWidth = 450
    assert_results_contain(check(test_font), INFO, "xAvgCharWidth-close")

    test_font["OS/2"].xAvgCharWidth = 500
    assert_results_contain(check(test_font), WARN, "xAvgCharWidth-wrong")

    test_font = TTFont(temp_file)
    test_font.reader.file.name = "foo.ttf"
    subsetter = fontTools.subset.Subsetter()
    subsetter.populate(
        glyphs=[
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
            "space",
        ]
    )
    subsetter.subset(test_font)
    assert list(check(test_font))[0].status == ERROR


@check_id("opentype/fsselection")
def test_check_fsselection_matches_macstyle(check):
    """Check if OS/2 fsSelection matches head macStyle bold and italic bits."""
    from fontbakery.constants import FsSelection

    test_font_path = TEST_FILE("nunito/Nunito-Regular.ttf")

    # try a regular (not bold, not italic) font
    test_font = TTFont(test_font_path)
    assert_PASS(check(test_font))

    # now turn on bold in OS/2.fsSelection, but not in head.macStyle
    test_font["OS/2"].fsSelection |= FsSelection.BOLD
    message = assert_results_contain(
        check(test_font), FAIL, "fsselection-macstyle-bold"
    )
    assert "Bold" in message

    # now turn off bold in OS/2.fsSelection so we can focus on italic
    test_font["OS/2"].fsSelection &= ~FsSelection.BOLD

    # now turn on italic in OS/2.fsSelection, but not in head.macStyle
    test_font["OS/2"].fsSelection |= FsSelection.ITALIC
    message = assert_results_contain(
        check(test_font), FAIL, "fsselection-macstyle-italic"
    )
    assert "Italic" in message


@check_id("opentype/family/bold_italic_unique_for_nameid1")
def test_check_family_bold_italic_unique_for_nameid1(check):
    """Check that OS/2.fsSelection bold/italic settings are unique within each
    Compatible Family group (i.e. group of up to 4 with same NameID1)"""
    from fontbakery.constants import FsSelection

    base_path = portable_path("data/test/source-sans-pro/OTF")

    # these fonts have the same NameID1
    font_names = [
        "SourceSansPro-Regular.otf",
        "SourceSansPro-Bold.otf",
        "SourceSansPro-Italic.otf",
        "SourceSansPro-BoldItalic.otf",
    ]
    font_paths = [os.path.join(base_path, n) for n in font_names]
    ttFonts = [TTFont(x) for x in font_paths]

    # the family should be correctly constructed
    assert_PASS(check(ttFonts))

    # now hack the italic font to also have the bold bit set
    ttFonts[2]["OS/2"].fsSelection |= FsSelection.BOLD

    # we should get a failure due to two fonts with both bold & italic set
    message = assert_results_contain(check(ttFonts), FAIL, "unique-fsselection")

    base_path = portable_path("data/test/cabin")
    font_names = [
        "Cabin-Regular.ttf",
        "Cabin-Bold.ttf",
        "Cabin-Italic.ttf",
        "Cabin-BoldItalic.ttf",
        "CabinCondensed-Regular.ttf",
        "CabinCondensed-Bold.ttf",
    ]
    font_paths = [os.path.join(base_path, n) for n in font_names]
    ttFonts = [TTFont(x) for x in font_paths]
    assert_PASS(check(ttFonts))


@check_id("opentype/code_pages")
def test_check_code_pages(check):
    """Check code page character ranges"""

    ttFont = TTFont(TEST_FILE("merriweather/Merriweather-Regular.ttf"))
    assert (
        ttFont["OS/2"].ulCodePageRange1 != 0 or ttFont["OS/2"].ulCodePageRange2 != 0
    )  # It has got at least 1 code page range declared
    assert_PASS(check(ttFont), "with good font.")

    ttFont["OS/2"].ulCodePageRange1 = 0  # remove all code pages to make the check FAIL
    ttFont["OS/2"].ulCodePageRange2 = 0
    assert_results_contain(
        check(ttFont), FAIL, "no-code-pages", "with a font with no code page declared."
    )


@check_id("opentype/vendor_id")
def test_check_vendor_id(check):
    """Check vendor id against the configured value"""

    ttFont = TTFont(TEST_FILE("merriweather/Merriweather-Regular.ttf"))
    assert ttFont["OS/2"].achVendID == "STC "

    # If there is no configured vendor_id value, SKIP the check
    assert_SKIP(check(ttFont))

    config = {"opentype/vendor_id": {"vendor_id": "STC "}}
    assert_PASS(check(ttFont, config=config))

    ttFont["OS/2"].achVendID = "TEST"
    assert_results_contain(
        check(ttFont, config=config),
        FAIL,
        "bad-vendor-id",
        "OS/2 VendorID is 'TEST', but should be 'STC '",
    )


@check_id("opentype/fsselection")
def test_check_fsselection(check):
    """Checking OS/2 fsSelection value."""
    from fontbakery.constants import FsSelection

    ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))

    # fsSelection-value, style, expected, expected_message
    test_cases = [
        [FsSelection.REGULAR, "Regular", PASS, None],
        [
            FsSelection.REGULAR,
            "Italic",
            "bad-REGULAR",
            "OS/2 fsSelection REGULAR bit should be unset.",
        ],
        [
            FsSelection.REGULAR,
            "Italic",
            "bad-ITALIC",
            "OS/2 fsSelection ITALIC bit should be set.",
        ],
        [FsSelection.ITALIC, "Italic", PASS, None],
        [
            FsSelection.ITALIC,
            "Thin",
            "bad-ITALIC",
            "OS/2 fsSelection ITALIC bit should be unset.",
        ],
        [FsSelection.BOLD, "Bold", PASS, None],
        [
            FsSelection.BOLD,
            "Regular",
            "bad-REGULAR",
            "OS/2 fsSelection REGULAR bit should be set.",
        ],
        [
            FsSelection.BOLD,
            "Regular",
            "bad-BOLD",
            "OS/2 fsSelection BOLD bit should be unset.",
        ],
        [
            FsSelection.BOLD,
            "Thin",
            "bad-BOLD",
            "OS/2 fsSelection BOLD bit should be unset.",
        ],
        [FsSelection.BOLD | FsSelection.ITALIC, "BoldItalic", PASS, None],
        [
            FsSelection.BOLD | FsSelection.ITALIC,
            "Italic",
            "bad-BOLD",
            "OS/2 fsSelection BOLD bit should be unset.",
        ],
        [
            FsSelection.BOLD | FsSelection.ITALIC,
            "Bold",
            "bad-ITALIC",
            "OS/2 fsSelection ITALIC bit should be unset.",
        ],
        [
            FsSelection.BOLD,
            "BoldItalic",
            "bad-ITALIC",
            "OS/2 fsSelection ITALIC bit should be set.",
        ],
        [
            FsSelection.ITALIC,
            "BoldItalic",
            "bad-BOLD",
            "OS/2 fsSelection BOLD bit should be set.",
        ],
    ]

    for fsSelection_value, style, expected, _expected_message in test_cases:
        ttFont["OS/2"].fsSelection = fsSelection_value

        ttFont.reader.file.name = f"Test-{style}.ttf"
        print(f"Testing {ttFont.reader.file.name}...")
        if expected == PASS:
            results = list(check(ttFont))
            # Only care about results which refer to the old FontBakery test here
            results = [r for r in results if "fsselection" not in r.message.code]
            assert_PASS(
                results,
                "with fsSelection:{fsSelection_value} style:{style}...",
            )
        else:
            message = assert_results_contain(
                check(ttFont),
                FAIL,
                expected,
                f"with fsSelection:{fsSelection_value} style:{style}...",
            )
