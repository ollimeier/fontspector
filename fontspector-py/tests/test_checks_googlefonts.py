import glob
import math
import os
from pathlib import Path
import shutil
import tempfile

import pytest
import requests
from conftest import check_id
from fontTools.ttLib import TTFont

from fontbakery.checks.vendorspecific.googlefonts.conditions import (
    expected_font_names,
)
from fontbakery.codetesting import (
    TEST_FILE,
    MockFont,
    assert_PASS,
    assert_results_contain,
    assert_SKIP,
    portable_path,
    MockContext,
)
from fontbakery.constants import (
    OFL_BODY_TEXT,
    MacintoshEncodingID,
    MacintoshLanguageID,
    NameID,
    PlatformID,
    WindowsEncodingID,
    WindowsLanguageID,
)
from fontbakery.status import DEBUG, ERROR, FAIL, FATAL, INFO, PASS, SKIP, WARN
from fontbakery.testable import Font

check_statuses = (ERROR, FAIL, SKIP, PASS, WARN, INFO, DEBUG)

OVERRIDE_SUFFIX = ""

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

cabin_condensed_fonts = [
    TEST_FILE("cabincondensed/CabinCondensed-Regular.ttf"),
    TEST_FILE("cabincondensed/CabinCondensed-Medium.ttf"),
    TEST_FILE("cabincondensed/CabinCondensed-Bold.ttf"),
    TEST_FILE("cabincondensed/CabinCondensed-SemiBold.ttf"),
]

rosarivo_fonts = [
    TEST_FILE("rosarivo_metadata/Rosarivo-Italic.ttf"),
    TEST_FILE("rosarivo_metadata/Rosarivo-Regular.ttf"),
]

cjk_font = TEST_FILE("cjk/NotoSansJP[wght].ttf")


@pytest.fixture
def cabin_ttFonts():
    return [TTFont(path) for path in cabin_fonts]


@pytest.fixture
def vf_ttFont():
    path = TEST_FILE("varfont/Oswald-VF.ttf")
    return TTFont(path)


def change_name_table_id(ttFont, nameID, newEntryString, platEncID=0):
    for i, nameRecord in enumerate(ttFont["name"].names):
        if nameRecord.nameID == nameID and nameRecord.platEncID == platEncID:
            ttFont["name"].names[i].string = newEntryString


def delete_name_table_id(ttFont, nameID):
    delete = []
    for i, nameRecord in enumerate(ttFont["name"].names):
        if nameRecord.nameID == nameID:
            delete.append(i)
    for i in sorted(delete, reverse=True):
        del ttFont["name"].names[i]


@pytest.fixture
def cabin_regular_path():
    return portable_path("data/test/cabin/Cabin-Regular.ttf")


def fake_mdpb(tmp_path, md):
    _fake_mdpb = tmp_path / "METADATA.pb"
    from google.protobuf import text_format

    textproto = text_format.MessageToString(md, as_utf8=True)
    _fake_mdpb.write_text(textproto, encoding="utf-8")
    return str(_fake_mdpb)


def read_mdpb(md):
    from fontbakery.checks.vendorspecific.googlefonts.utils import (
        get_FamilyProto_Message,
    )

    return get_FamilyProto_Message(md)


@pytest.mark.parametrize(
    """fp,result""",
    [
        (TEST_FILE("montserrat/Montserrat-Thin.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-Light.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-Regular.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-Medium.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-SemiBold.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-Bold.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraBold.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-Black.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-ThinItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraLightItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-LightItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-Italic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-MediumItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-SemiBoldItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraBoldItalic.ttf"), PASS),
        (TEST_FILE("montserrat/Montserrat-BlackItalic.ttf"), PASS),
        (TEST_FILE("cabinvfbeta/CabinVFBeta-Italic[wght].ttf"), PASS),
        (TEST_FILE("cabinvfbeta/CabinVFBeta.ttf"), FAIL),
        (TEST_FILE("cabinvfbeta/Cabin-Italic.ttf"), FAIL),
        (TEST_FILE("cabinvfbeta/Cabin-Roman.ttf"), FAIL),
        (TEST_FILE("cabinvfbeta/Cabin-Italic-VF.ttf"), FAIL),
        (TEST_FILE("cabinvfbeta/Cabin-Roman-VF.ttf"), FAIL),
        (TEST_FILE("cabinvfbeta/Cabin-VF.ttf"), FAIL),
        # axis tags are sorted
        (TEST_FILE("cabinvfbeta/CabinVFBeta[wdth,wght].ttf"), PASS),
        # axis tags are NOT sorted
        (TEST_FILE("cabinvfbeta/CabinVFBeta[wght,wdth].ttf"), FAIL),
    ],
)
@check_id("googlefonts/canonical_filename")
def test_check_canonical_filename(check, fp, result):
    """Files are named canonically."""
    ttFont = TTFont(fp)

    if result == PASS:
        assert_PASS(check(ttFont), f'with "{ttFont.reader.file.name}" ...')
    else:
        assert_results_contain(
            check(ttFont), FAIL, "bad-filename", f'with "{ttFont.reader.file.name}" ...'
        )


@check_id("googlefonts/description/broken_links")
def test_check_description_broken_links(check, tmp_path):
    """Does DESCRIPTION file contain broken links ?"""

    font = TEST_FILE("cabin/DESCRIPTION.en_us.html")
    assert_PASS(check(font), "with description file that has no links...")

    p = tmp_path / "DESCRIPTION.en_us.html"

    good_desc = open(font).read()
    good_desc += (
        "<a href='http://example.com'>Good Link</a>"
        "<a href='http://fonts.google.com'>Another Good One</a>"
    )
    p.write_text(good_desc, encoding="utf-8")

    assert_PASS(
        check(str(p)),
        "with description file that has good links...",
    )

    bad_desc = (
        good_desc + "<a href='mailto:juca@members.fsf.org'>An example mailto link</a>"
    )
    p.write_text(bad_desc, encoding="utf-8")

    assert_results_contain(
        check(str(p)),
        FAIL,
        "email",
        'with a description file containing "mailto" links...',
    )

    bad_desc = (
        good_desc
        + "<a href='http://thisisanexampleofabrokenurl.com/'>This is a Bad Link</a>"
    )
    p.write_text(bad_desc, encoding="utf-8")

    assert_results_contain(
        check(str(p)),
        FAIL,
        "broken-links",
        "with a description file containing a known-bad URL...",
    )

    # Sadly we can't currently mock a timeout

    # bad_desc = (
    #     good_desc
    #     + "<a href='http://timeout.example.invalid/'>This is a link that times out</a>"
    # )
    # p.write_text(bad_desc, encoding="utf-8")

    # assert_results_contain(
    #     check(str(p)),
    #     WARN,
    #     "timeout",
    #     "with a description file containing a URL that times out...",
    # )


@check_id("googlefonts/description/git_url")
def test_check_description_git_url(check, tmp_path):
    """Does DESCRIPTION file contain an upstream Git repo URL?"""

    # TODO: test INFO 'url-found'

    font = TEST_FILE("cabin/DESCRIPTION.en_us.html")
    assert_results_contain(
        check(font),
        FAIL,
        "lacks-git-url",
        "with description file that has no git repo URLs...",
    )

    p = tmp_path / "DESCRIPTION.en_us.html"

    good_desc = open(font).read()
    good_desc += (
        "<a href='https://github.com/uswds/public-sans'>Good URL</a>"
        "<a href='https://gitlab.com/smc/fonts/uroob'>Another Good One</a>"
    )

    p.write_text(good_desc, encoding="utf-8")

    assert_PASS(
        check(str(p)),
        "with description file that has good links...",
    )

    bad_desc = "<a href='https://v2.designsystem.digital.gov'>Bad URL</a>"
    p.write_text(bad_desc, encoding="utf-8")

    assert_results_contain(
        check(str(p)),
        FAIL,
        "lacks-git-url",
        "with description file that has false git in URL...",
    )


@check_id("googlefonts/description/valid_html")
def test_check_description_valid_html(check, tmp_path):
    """DESCRIPTION file is a propper HTML snippet ?"""

    font = TEST_FILE("nunito/DESCRIPTION.en_us.html")
    assert_PASS(
        check(font), "with description file that contains a good HTML snippet..."
    )

    p = tmp_path / "DESCRIPTION.en_us.html"
    contents = open(TEST_FILE("cabin/FONTLOG.txt")).read()
    p.write_text(contents, encoding="utf-8")
    assert_results_contain(
        check(str(p)),
        FAIL,
        "lacks-paragraph",
        "with a known-bad file (without HTML paragraph tags)...",
    )

    bad_desc = "<html>foo</html>"
    p = tmp_path / "DESCRIPTION.en_us.html"
    p.write_text(bad_desc, encoding="utf-8")
    assert_results_contain(
        check(str(p)),
        FAIL,
        "html-tag",
        "with description file that contains the <html> tag...",
    )

    good_desc = (
        "<p>This example has the & caracter,"
        " and does not escape it with an HTML entity code."
        " It could use &amp; instead, but that's not strictly necessary."
        "</p>"
    )
    p = tmp_path / "DESCRIPTION.en_us.html"
    p.write_text(good_desc, encoding="utf-8")

    # See discussion at https://github.com/fonttools/fontbakery/issues/3840
    assert_PASS(
        check(str(p)),
        "with a file containing ampersand char without HTML entity syntax...",
    )


@check_id("googlefonts/description/min_length")
def test_check_description_min_length(check, tmp_path):
    """DESCRIPTION.en_us.html must have more than 200 bytes."""
    p = tmp_path / "DESCRIPTION.en_us.html"
    p.write_text("a" * 199, encoding="utf-8")
    assert_results_contain(
        check(str(p)),
        FAIL,
        "too-short",
        "with 199-byte buffer...",
    )

    p.write_text("a" * 200, encoding="utf-8")
    assert_results_contain(
        check(str(p)),
        FAIL,
        "too-short",
        "with 200-byte buffer...",
    )

    p.write_text("a" * 201, encoding="utf-8")
    assert_PASS(check(str(p)), "with 201-byte buffer...")


@check_id("googlefonts/description/eof_linebreak")
def test_check_description_eof_linebreak(check, tmp_path):
    """DESCRIPTION.en_us.html should end in a linebreak."""
    p = tmp_path / "DESCRIPTION.en_us.html"

    bad = (
        "We want to avoid description files\n"
        "without an end-of-file linebreak\n"
        "like this one."
    )
    p.write_text(bad, encoding="utf-8")
    assert_results_contain(
        check(str(p)),
        WARN,
        "missing-eof-linebreak",
        "when we lack an end-of-file linebreak...",
    )

    p.write_text("On the other hand, this one\nis good enough.\n", encoding="utf-8")
    assert_PASS(check(str(p)), "when we add one...")


@check_id("googlefonts/name/line_breaks")
def test_check_name_line_breaks(check):
    """Name table entries should not contain line-breaks."""

    # Our reference Mada Regular font is good here:
    ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))

    # So it must PASS the check:
    assert_PASS(check(ttFont), "with a good font...")

    num_entries = len(ttFont["name"].names)
    for i in range(num_entries):
        ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))
        encoding = ttFont["name"].names[i].getEncoding()
        ttFont["name"].names[i].string = "bad\nstring".encode(encoding)
        assert_results_contain(
            check(ttFont),
            FAIL,
            "line-break",
            f"with name entries containing a linebreak ({i}/{num_entries})...",
        )


@check_id("googlefonts/name/rfn")
def test_check_name_rfn(check):
    """Name table strings must not contain 'Reserved Font Name'."""

    ttFont = TTFont(TEST_FILE("nunito/Nunito-Regular.ttf"))
    assert_PASS(check(ttFont))

    # The OFL text contains the term 'Reserved Font Name',
    # which should not cause a FAIL:
    ttFont["name"].setName(
        OFL_BODY_TEXT,
        NameID.LICENSE_DESCRIPTION,
        PlatformID.WINDOWS,
        WindowsEncodingID.UNICODE_BMP,
        WindowsLanguageID.ENGLISH_USA,
    )
    assert_PASS(check(ttFont), "with the OFL full text...")

    # NOTE: This is not a real copyright statement. It is only meant to test the check.
    with_nunito_rfn = (
        "Copyright 2022 The Nunito Project Authors"
        " (https://github.com/googlefonts/NunitoSans),"
        " with Reserved Font Name Nunito."
    )
    ttFont["name"].setName(
        with_nunito_rfn,
        NameID.VERSION_STRING,
        PlatformID.WINDOWS,
        WindowsEncodingID.UNICODE_BMP,
        WindowsLanguageID.ENGLISH_USA,
    )
    assert_results_contain(
        check(ttFont),
        FAIL,
        "rfn",
        'with "Reserved Font Name Nunito" on a name table entry...',
    )

    # NOTE: This is not a real copyright statement. It is only meant to test the check.
    with_other_familyname_rfn = (
        "Copyright 2022 The FooBar Project Authors"
        " (https://github.com/foo/bar),"
        " with Reserved Font Name FooBar."
    )
    ttFont["name"].setName(
        with_other_familyname_rfn,
        NameID.VERSION_STRING,
        PlatformID.WINDOWS,
        WindowsEncodingID.UNICODE_BMP,
        WindowsLanguageID.ENGLISH_USA,
    )
    msg = assert_results_contain(
        check(ttFont),
        WARN,
        "legacy-familyname",
        'with "Reserved Font Name" that references an older'
        " familyname not being used in this font project...",
    )
    assert "(FooBar)" in msg


@check_id("googlefonts/name/family_name_compliance")
def test_check_name_family_name_compliance(check):
    """Check family name for GF Guide compliance."""

    def set_name(font, nameID, string):
        for record in font["name"].names:
            if record.nameID == nameID:
                old_string = record.toUnicode()
                if string != old_string:
                    font["name"].setName(
                        string,
                        record.nameID,
                        record.platformID,
                        record.platEncID,
                        record.langID,
                    )

    # CAMEL CASE
    ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))
    assert_PASS(check(ttFont), "with a good font...")

    # FAIL with a CamelCased name:
    set_name(ttFont, 1, "GollyGhost")
    assert_results_contain(
        check(ttFont), FAIL, "camelcase", "with a bad font name (CamelCased)..."
    )
    set_name(ttFont, 1, "KonKhmer_SleokChher")
    assert_results_contain(
        check(ttFont), FAIL, "camelcase", "with a bad font name (CamelCased)..."
    )

    # PASS with a known CamelCased exception:
    set_name(ttFont, 1, "KoHo")
    assert_PASS(check(ttFont))

    # ABBREVIATIONS
    set_name(ttFont, 1, "DTL Prokyon")
    assert_results_contain(check(ttFont), FAIL, "abbreviation", "with a bad font name")
    set_name(ttFont, 1, "PT Sans")
    assert_PASS(check(ttFont))
    # Allow SC ending
    set_name(ttFont, 1, "Amatic SC")
    assert_PASS(check(ttFont), "with a good font...")

    # FORBIDDEN CHARACTERS
    set_name(ttFont, 1, "KonKhmer_SleokChher")
    message = assert_results_contain(
        check(ttFont), FAIL, "forbidden-characters", "with a bad font name"
    )
    assert message == (
        '"KonKhmer_SleokChher" contains the following characters'
        ' which are not allowed: "_".'
    )
    set_name(ttFont, 1, "Kon*Khmer_Sleok-Chher")
    message = assert_results_contain(
        check(ttFont), FAIL, "forbidden-characters", "with a bad font name"
    )
    assert message == (
        '"Kon*Khmer_Sleok-Chher" contains the following characters'
        ' which are not allowed: "*-_".'
    )

    # STARTS WITH UPPERCASE
    set_name(ttFont, 1, "cabin")
    message = assert_results_contain(
        check(ttFont), FAIL, "starts-with-not-uppercase", "with a bad font name"
    )

    # # And we also make sure the check PASSes with a few known good names:
    set_name(ttFont, 1, "VT323")
    assert_PASS(check(ttFont), "with a good font...")


@check_id("googlefonts/metadata/validate")
def test_check_metadata_validate(check):
    """Check METADATA.pb parse correctly."""

    good = TEST_FILE("stixtwomath/METADATA.pb")
    assert_PASS(check(good), "with a good METADATA.pb file...")

    bad = TEST_FILE("broken_metadata/METADATA.pb")
    assert list(check(bad))[0].status == ERROR


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/designer_values")
def test_check_metadata_designer_values(check):
    """Multiple values in font designer field in
    METADATA.pb must be separated by commas."""

    font = TEST_FILE("merriweather/Merriweather-Regular.ttf")
    assert_PASS(check(font), "with a good METADATA.pb file...")

    md = Font(font).family_metadata
    md.designer = "Pentagram, MCKL"
    assert_PASS(
        check(MockFont(file=font, family_metadata=md)),
        "with a good multiple-designers string...",
    )

    md.designer = "Pentagram / MCKL"  # This actually happened on an
    # early version of the Red Hat Text family
    assert_results_contain(
        check(MockFont(file=font, family_metadata=md)),
        FAIL,
        "slash",
        "with a bad multiple-designers string (names separated by a slash char)...",
    )


@check_id("googlefonts/metadata/validate")
def test_check_metadata_date_added(check, tmp_path):
    """Validate 'date_added' field on METADATA.pb."""

    md_file = TEST_FILE("cabinvf/METADATA.pb")
    md = read_mdpb(md_file)
    assert_PASS(check(md_file), "with a good METADATA.pb file...")

    md.date_added = "2021-07-11"
    assert_PASS(
        check(fake_mdpb(tmp_path, md)),
        "with a good date_added field...",
    )

    md.date_added = ""
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        ERROR,
        "date-empty",
        "with an empty string on date_added field...",
    )

    md.date_added = "2020, Oct 1st"  # This is not the YYYY-MM-DD format we expect.
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        ERROR,
        "date-malformed",
        "with a bad date string on date_added field...",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/undeclared_fonts")
def test_check_metadata_undeclared_fonts(check):
    """Ensure METADATA.pb lists all font binaries."""

    # Our reference Nunito family is know to be good here.
    font = TEST_FILE("nunito/Nunito-Regular.ttf")
    assert_PASS(check(font))

    # Our reference Cabin family has files that are not declared in its METADATA.pb:
    # - CabinCondensed-Medium.ttf
    # - CabinCondensed-SemiBold.ttf
    # - CabinCondensed-Regular.ttf
    # - CabinCondensed-Bold.ttf
    font = TEST_FILE("cabin/Cabin-Regular.ttf")
    assert_results_contain(check(font), FAIL, "file-not-declared")

    # We placed an additional file on a subdirectory of our reference
    # OverpassMono family with the name "another_directory/ThisShouldNotBeHere.otf"
    font = TEST_FILE("overpassmono/OverpassMono-Regular.ttf")
    assert_results_contain(check(font), WARN, "font-on-subdir")

    # We do accept statics folder though!
    # Jura is an example:
    font = TEST_FILE("varfont/jura/Jura[wght].ttf")
    assert_PASS(check(font))


@check_id("googlefonts/family/equal_codepoint_coverage")
def test_check_family_equal_codepoint_coverage(check, mada_ttFonts, cabin_ttFonts):
    """Fonts have equal codepoint coverage?"""

    # our reference Cabin family is know to be good here.
    assert_PASS(check(cabin_ttFonts), "with a good family.")

    # Let's de-encode some glyphs
    del cabin_ttFonts[1]["cmap"].tables[0].cmap[8730]
    assert_results_contain(
        check(cabin_ttFonts),
        FAIL,
        "glyphset-diverges",
        "with fonts that diverge.",
    )


@check_id("googlefonts/fstype")
def test_check_fstype(check):
    """Checking OS/2 fsType"""

    # our reference Cabin family is know to be good here.
    ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))
    assert_PASS(check(ttFont), "with a good font without DRM.")

    # modify the OS/2 fsType value to something different than zero:
    ttFont["OS/2"].fsType = 1

    assert_results_contain(
        check(ttFont),
        FAIL,
        "drm",
        "with fonts that enable DRM restrictions via non-zero fsType bits.",
    )


@check_id("googlefonts/vendor_id")
def test_check_vendor_id(check):
    """Checking OS/2 achVendID"""

    # Let's start with our reference Merriweather Regular
    ttFont = TTFont(TEST_FILE("merriweather/Merriweather-Regular.ttf"))

    bad_vids = ["UKWN", "ukwn", "PfEd", "PYRS"]
    for bad_vid in bad_vids:
        ttFont["OS/2"].achVendID = bad_vid
        assert_results_contain(check(ttFont), WARN, "bad", f'with bad vid "{bad_vid}".')

    # ttFont["OS/2"].achVendID = None
    # assert_results_contain(
    #     check(ttFont), WARN, "not-set", "with font missing vendor id info."
    # )

    ttFont["OS/2"].achVendID = "????"
    assert_results_contain(check(ttFont), WARN, "unknown", "with unknwon vendor id.")

    # we now change the fields into a known good vendor id:
    ttFont["OS/2"].achVendID = "APPL"
    assert_PASS(check(ttFont), "with a good font.")

    # And let's also make sure it works here:
    ttFont["OS/2"].achVendID = "GOOG"
    assert_PASS(check(ttFont), "with a good font.")


@check_id("googlefonts/glyph_coverage")
def test_check_glyph_coverage(check):
    """Check glyph coverage."""

    # Our reference Cabin Regular is known to be bad here.
    ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))

    # Deactivating this for now as GF_TransLatin_Arabic isn't available under
    # the new glyphset setup yet.
    # TODO: Reactivate this:
    # assert_results_contain(
    #     check(ttFont),
    #     WARN,
    #     "missing-codepoints",
    #     "GF_TransLatin_Arabic is almost fulfilled.",
    # )

    # Let's fix it then...
    # cmap = ttFont.getBestCmap()
    # cmap[0x1E34] = 0x1E34  # (LATIN CAPITAL LETTER K WITH LINE BELOW)
    # cmap[0x1E35] = 0x1E35  # (LATIN SMALL LETTER K WITH LINE BELOW)
    # cmap[0x1E96] = 0x1E96  # (LATIN SMALL LETTER H WITH LINE BELOW)
    # cmap[0x02BD] = 0x02BD  # (MODIFIER LETTER REVERSED COMMA)
    assert_PASS(check(ttFont), "with a good font.")

    # Moirai is Korean, so only needs kernel
    ttFont = TTFont(TEST_FILE("moiraione/MoiraiOne-Regular.ttf"))
    assert 0x02C7 not in ttFont.getBestCmap()  # This is in core but not kernel
    assert_PASS(
        check([ttFont, TEST_FILE("moiraione/METADATA.pb")]), "with a good font."
    )


@check_id("googlefonts/weightclass")
def test_check_weightclass(check):
    """Checking OS/2 usWeightClass."""

    # Our reference Mada Regular is know to be bad here.
    font = TEST_FILE("mada/Mada-Regular.ttf")
    ttFont = TTFont(font)
    assert_results_contain(
        check(ttFont), FAIL, "bad-value", f'with bad font "{font}" ...'
    )

    # All fonts in our reference Cabin family are know to be good here.
    for font in cabin_fonts:
        ttFont = TTFont(font)
        assert_PASS(check(ttFont), f'with good font "{font}"...')

    # Check otf Thin == 250 and ExtraLight == 275
    font = TEST_FILE("rokkitt/Rokkitt-Thin.otf")
    ttFont = TTFont(font)
    assert_results_contain(
        check(ttFont), FAIL, "bad-value", f'with bad font "{font}"...'
    )

    ttFont["OS/2"].usWeightClass = 250
    assert_PASS(check(ttFont), f'with good font "{font}" (usWeightClass = 250) ...')

    font = TEST_FILE("rokkitt/Rokkitt-ExtraLight.otf")
    ttFont = TTFont(font)
    assert_results_contain(
        check(ttFont), FAIL, "bad-value", f'with bad font "{font}" ...'
    )

    ttFont["OS/2"].usWeightClass = 275
    assert_PASS(check(ttFont), f'with good font "{font}" (usWeightClass = 275) ...')

    # TODO: test italic variants to ensure we do not get regressions of
    #       this bug: https://github.com/fonttools/fontbakery/issues/2650

    # Check with VF font reported in issue:
    # https://github.com/fonttools/fontbakery/issues/4113
    font = TEST_FILE("playfair/Playfair-Italic[opsz,wdth,wght].ttf")
    ttFont = TTFont(font)
    assert_PASS(check(ttFont), f'with good font "{font}" (usWeightClass = 300) ...')

    ttFont["OS/2"].usWeightClass = 400
    assert_results_contain(
        check(ttFont), FAIL, "bad-value", f'with bad font "{font}"...'
    )


def test_family_directory_condition():
    assert Font("some_directory/Foo.ttf").family_directory == "some_directory"
    assert (
        Font("some_directory/subdir/Foo.ttf").family_directory
        == "some_directory/subdir"
    )
    assert (
        Font("Foo.ttf").family_directory == "."
    )  # This is meant to ensure license files
    # are correctly detected on the current
    # working directory.


@check_id("googlefonts/family/has_license")
def test_check_family_has_license(check, tmp_path):
    """Check font project has a license."""

    def make_fake_gf_repo(dir):
        """Create a fake Google Fonts repository with the given files."""
        repo_path = tmp_path / "ofl" / "some_family"
        shutil.rmtree(repo_path, ignore_errors=True)  # Clean up any previous runs
        repo_path.mkdir(parents=True)
        files = list(Path(dir).glob("*"))
        for file in files:
            shutil.copy(file, repo_path)
        return [str(repo_path / Path(file).name) for file in files]

    def licenses_for_test(path):
        return glob.glob(path + "/LICENSE.txt") + glob.glob(path + "/OFL.txt")

    detected_licenses = licenses_for_test(portable_path("data/test/028/multiple"))
    assert len(detected_licenses) > 1
    assert_results_contain(
        check(make_fake_gf_repo(portable_path("data/test/028/multiple"))),
        FAIL,
        "multiple",
        "with multiple licenses...",
    )

    detected_licenses = licenses_for_test(portable_path("data/test/028/none"))
    assert_results_contain(
        check(make_fake_gf_repo(portable_path("data/test/028/none"))),
        FAIL,
        "no-license",
        "with no license...",
    )

    detected_licenses = licenses_for_test(portable_path("data/test/028/pass_ofl"))
    assert_PASS(
        check(make_fake_gf_repo(portable_path("data/test/028/pass_ofl"))),
        "with a single OFL license...",
    )

    detected_licenses = licenses_for_test(portable_path("data/test/028/pass_apache"))
    assert_PASS(
        check(make_fake_gf_repo(portable_path("data/test/028/pass_apache"))),
        "with a single Apache license...",
    )


@check_id("googlefonts/license/OFL_copyright")
def test_check_license_ofl_copyright(check, tmp_path):
    """Check license file has good copyright string."""

    # And Mada has a bad copyright string format:
    license_file = TEST_FILE("mada/OFL.txt")
    assert_results_contain(
        check(license_file), FAIL, "bad-format", "with bad string formatting."
    )

    # so we fix it:
    SOME_GOOD_TEXT = (
        "Copyright 2019 The Montserrat Project Authors"
        " (https://github.com/julietaula/montserrat)\n"
    )
    fake_ofl = tmp_path / "OFL.txt"
    fake_ofl.write_text(SOME_GOOD_TEXT, encoding="utf-8")
    assert_PASS(
        check(str(fake_ofl)),
        "with good license contents.",
    )


@check_id("googlefonts/license/OFL_body_text")
def test_check_license_ofl_body_text(check, tmp_path):
    """Check OFL.txt contains correct body text."""

    # Our reference Montserrat family is know to have
    # a proper OFL.txt license file.
    # NOTE: This is currently considered good
    #       even though it uses an "http://" URL
    license_file = TEST_FILE("montserrat/OFL.txt")
    license_contents = open(license_file).read()

    assert_PASS(
        check(license_file),
        'with a good OFL.txt license with "http://" url.',
    )

    # using "https://" is also considered good:
    fake_ofl = tmp_path / "OFL.txt"
    license_contents = license_contents.replace("http://", "https://")
    fake_ofl.write_text(license_contents, encoding="utf-8")

    assert_PASS(
        check(str(fake_ofl)),
        'with a good OFL.txt license with "https://" url.',
    )

    # modify a tiny bit of the license text, to trigger the FAIL:
    license_contents = license_contents.replace(
        "SIL OPEN FONT LICENSE Version 1.1", "SOMETHING ELSE :-P Version Foo"
    )
    license_contents = license_contents.replace("http://", "https://")
    fake_ofl.write_text(license_contents, encoding="utf-8")
    assert_results_contain(
        check(str(fake_ofl)),
        WARN,
        "incorrect-ofl-body-text",
        "with incorrect ofl body text",
    )


@check_id("googlefonts/name/license")
def test_check_name_license(check, mada_ttFonts):
    """Check copyright namerecords match license file."""

    ofl_license = TEST_FILE("mada/OFL.txt")
    apache_license = TEST_FILE("source-sans-pro/LICENSE.txt")

    # Our reference Mada family has its copyright name records properly set
    # identifying it as being licensed under the Open Font License.
    for font in mada_fonts:
        assert_PASS(check([font, ofl_license]), "with good fonts ...")

    for font in mada_fonts:
        assert_results_contain(
            check([font, apache_license]),
            FAIL,
            "wrong",
            "with wrong entry values ...",
        )

    for ttFont in mada_ttFonts:
        delete_name_table_id(ttFont, NameID.LICENSE_DESCRIPTION)
        assert_results_contain(
            check([ttFont, TEST_FILE("mada/OFL.txt")]),
            FAIL,
            "missing",
            "with missing copyright namerecords ...",
        )

    # TODO:
    # WARN, "http" / "http-in-description"


@check_id("googlefonts/name/description_max_length")
def test_check_name_description_max_length(check):
    """Description strings in the name table must not exceed 200 characters."""

    # Our reference Mada Regular is know to be good here.
    ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))
    assert_PASS(check(ttFont), "with a good font...")

    # Here we add strings to NameID.DESCRIPTION with exactly 100 chars,
    # so it should still PASS:
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.DESCRIPTION:
            ttFont["name"].names[i].string = ("a" * 200).encode(name.getEncoding())
    assert_PASS(check(ttFont), "with a 200 char string...")

    # And here we make the strings longer than 200 chars
    # in order to make the check emit a WARN:
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.DESCRIPTION:
            ttFont["name"].names[i].string = ("a" * 201).encode(name.getEncoding())
    assert_results_contain(
        check(ttFont), WARN, "too-long", "with a too long description string..."
    )


@check_id("googlefonts/name/version_format")
def test_check_name_version_format(check):
    """Version format is correct in 'name' table ?"""

    # Our reference Mada Regular font is good here:
    ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))

    # So it must PASS the check:
    assert_PASS(check(ttFont), "with a good font...")

    # then we introduce bad strings in all version-string entries:
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.VERSION_STRING:
            invalid = "invalid-version-string".encode(name.getEncoding())
            ttFont["name"].names[i].string = invalid
    assert_results_contain(
        check(ttFont),
        FAIL,
        "bad-version-strings",
        "with bad version format in name table...",
    )

    # and finally we remove all version-string entries:
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.VERSION_STRING:
            del ttFont["name"].names[i]
    assert_results_contain(
        check(ttFont),
        FAIL,
        "no-version-string",
        "with font lacking version string entries in name table...",
    )


@pytest.mark.parametrize(
    "expected_status,expected_keyword,reason,font",
    [
        (
            FAIL,
            "lacks-ttfa-params",
            "with a font lacking ttfautohint params on its version strings "
            "on the name table.",
            TEST_FILE("coveredbyyourgrace/CoveredByYourGrace.ttf"),
        ),
        (
            SKIP,
            "not-hinted",
            "with a font which appears to our heuristic as not hinted using "
            "ttfautohint.",
            TEST_FILE("mada/Mada-Regular.ttf"),
        ),
        (
            INFO,
            "ok",
            "with a font that has ttfautohint params"
            ' (-l 6 -r 36 -G 0 -x 10 -H 350 -D latn -f cyrl -w "" -X "")',
            TEST_FILE("merriweather/Merriweather-Regular.ttf"),
        ),
    ],
)
@check_id("googlefonts/has_ttfautohint_params")
def test_check_has_ttfautohint_params(
    check, expected_status, expected_keyword, reason, font
):
    """Font has ttfautohint params?"""
    assert_results_contain(check(font), expected_status, expected_keyword, reason)


@check_id("googlefonts/name/familyname_first_char")
def test_check_name_familyname_first_char(check):
    """Make sure family name does not begin with a digit."""

    # Our reference Mada Regular is known to be good
    ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))

    # So it must PASS the check:
    assert_PASS(check(ttFont), "with a good font...")

    # alter the family-name prepending a digit:
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.FONT_FAMILY_NAME:
            ttFont["name"].names[i].string = "1badname".encode(name.getEncoding())

    # and make sure the check FAILs:
    assert_results_contain(
        check(ttFont),
        FAIL,
        "begins-with-digit",
        "with a font in which the family name begins with a digit...",
    )


@check_id("googlefonts/metadata/validate")
def test_check_metadata_unique_full_name_values(check, tmp_path):
    """METADATA.pb: check if fonts field only has unique "full_name" values."""

    # Our reference FamilySans family is good:
    md_file = TEST_FILE("familysans/METADATA.pb")
    md_contents = read_mdpb(md_file)
    assert_PASS(check(md_file), "with a good family...")

    # then duplicate a full_name entry to make it FAIL:
    md_contents.fonts[0].full_name = md_contents.fonts[1].full_name
    assert_results_contain(
        check(fake_mdpb(tmp_path, md_contents)),
        FAIL,
        "duplicated",
        "with a duplicated full_name entry.",
    )


@check_id("googlefonts/metadata/validate")
def test_check_metadata_unique_weight_style_pairs(check, tmp_path):
    """METADATA.pb: check if fonts field only contains unique style:weight pairs."""

    # Our reference FamilySans family is good:
    font = TEST_FILE("familysans/FamilySans-Regular.ttf")

    # then duplicate a pair of style & weight entries to make it FAIL:
    md = Font(font).family_metadata
    assert_PASS(check(fake_mdpb(tmp_path, md)), "with a good family...")
    md.fonts[0].style = md.fonts[1].style
    md.fonts[0].weight = md.fonts[1].weight
    assert_results_contain(
        check([fake_mdpb(tmp_path, md)]),
        FAIL,
        "duplicated",
        "with a duplicated pair of style & weight entries",
    )


@check_id("googlefonts/metadata/license")
def test_check_metadata_license(check):
    """METADATA.pb license is "APACHE2", "UFL" or "OFL"?"""

    # Let's start with our reference FamilySans family:
    font = TEST_FILE("familysans/METADATA.pb")

    good_licenses = ["APACHE2", "UFL", "OFL"]
    some_bad_values = ["APACHE", "Apache", "Ufl", "Ofl", "Open Font License"]

    check(font)
    contents = open(font, "r").read()
    import re

    with tempfile.TemporaryDirectory() as tmpdirname:
        dest = tmpdirname + "/METADATA.pb"
        for good in good_licenses:
            contents = re.sub(r'license:\s*".*"', f'license: "{good}"', contents)
            with open(dest, "w") as f:
                f.write(contents)
            assert_PASS(check(dest), f": {good}")

        for bad in some_bad_values:
            contents = re.sub(r'license:\s*".*"', f'license: "{bad}"', contents)
            with open(dest, "w") as f:
                f.write(contents)
            assert_results_contain(
                check(dest),
                FAIL,
                "bad-license",
                f": {bad}",
            )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/menu_and_latin")
def test_check_metadata_menu_and_latin(check):
    """METADATA.pb should contain at least "menu" and "latin" subsets."""

    # Let's start with our reference FamilySans family:
    font = TEST_FILE("familysans/FamilySans-Regular.ttf")

    good_cases = [
        ["menu", "latin"],
        ["menu", "cyrillic", "latin"],
    ]

    bad_cases = [["menu"], ["latin"], [""], ["latin", "cyrillyc"], ["khmer"]]

    md = Font(font).family_metadata
    for good in good_cases:
        del md.subsets[:]
        md.subsets.extend(good)
        assert_PASS(
            check(MockFont(file=font, family_metadata=md)), f"with subsets = {good}"
        )

    for bad in bad_cases:
        del md.subsets[:]
        md.subsets.extend(bad)
        assert_results_contain(
            check(MockFont(file=font, family_metadata=md)),
            FAIL,
            "missing",
            f"with subsets = {bad}",
        )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/subsets_order")
def test_check_metadata_subsets_order(check):
    """METADATA.pb subsets should be alphabetically ordered."""

    # Let's start with our reference FamilySans family:
    font = TEST_FILE("familysans/FamilySans-Regular.ttf")

    good_cases = [
        ["latin", "menu"],
        ["cyrillic", "latin", "menu"],
        ["cyrillic", "khmer", "latin", "menu"],
    ]

    bad_cases = [
        ["menu", "latin"],
        ["latin", "cyrillic", "menu"],
        ["cyrillic", "menu", "khmer", "latin"],
    ]

    md = Font(font).family_metadata
    for good in good_cases:
        del md.subsets[:]
        md.subsets.extend(good)
        assert_PASS(
            check(MockFont(file=font, family_metadata=md)), f"with subsets = {good}"
        )

    md = Font(font).family_metadata
    for bad in bad_cases:
        del md.subsets[:]
        md.subsets.extend(bad)
        assert_results_contain(
            check(MockFont(file=font, family_metadata=md)),
            FAIL,
            "not-sorted",
            f"with subsets = {bad}",
        )


@check_id("googlefonts/metadata/includes_production_subsets")
def test_check_metadata_includes_production_subsets(check, tmp_path):
    """Check METADATA.pb has production subsets."""

    mdpb = TEST_FILE("cabinvf/METADATA.pb")
    assert_PASS(check(mdpb), "with a good METADATA.pb for this family...")

    md = read_mdpb(mdpb)
    # Then we induce the problem by removing a subset:
    md.subsets.pop()
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        FAIL,
        "missing-subsets",
        "with a bad METADATA.pb (last subset has been removed)...",
    )


@check_id("googlefonts/metadata/subsets_correct")
def test_check_metadata_single_cjk_subset(check, tmp_path):
    """Check METADATA.pb file only contains a single CJK subset"""

    font = TEST_FILE("familysans/FamilySans-Regular.ttf")
    md = Font(font).family_metadata

    # I've taken a hatchet to the other test cases here, because other parts of
    # subsets_correct will find other problems (no latin in METADATA.pb, but if
    # you add Latin, subsets_correct will complain about missing coverage in the font)
    md.subsets.append("korean")
    results = check([fake_mdpb(tmp_path, md), font])
    assert_PASS(filter(lambda r: r.message.code == "multiple-cjk-subsets", results))
    md.subsets.append("japanese")
    assert_results_contain(
        check([fake_mdpb(tmp_path, md), font]),
        ERROR,
        "multiple-cjk-subsets",
        "METADATA.pb has multiple cjk subsets...",
    )


@check_id("googlefonts/metadata/copyright")
def test_check_metadata_copyright(check):
    """METADATA.pb: Copyright notice is the same in all fonts?"""

    # Let's start with our reference FamilySans family:
    mdpb = TEST_FILE("familysans/METADATA.pb")

    # We know its copyright notices are consistent:
    assert_PASS(check(mdpb), "with consistent copyright notices on FamilySans...")

    # Now we make them diverge:
    mdpb = TEST_FILE("familysans/bad-METADATA.pb")
    # To ensure the problem is detected:
    assert_results_contain(
        check(mdpb),
        FAIL,
        "inconsistency",
        "with diverging copyright notice strings...",
    )


@check_id("googlefonts/metadata/familyname")
def test_check_metadata_familyname(check, tmp_path):
    """Check that METADATA.pb family values are all the same."""

    # Let's start with our reference FamilySans family:
    font = TEST_FILE("familysans/FamilySans-Regular.ttf")
    good_mdpb = TEST_FILE("familysans/METADATA.pb")

    # We know its family name entries on METADATA.pb are consistent:
    assert_PASS(check(good_mdpb), "with consistent family name...")

    # Now we make them diverge:
    md = Font(font).family_metadata
    md.fonts[1].name = md.fonts[0].name + " arbitrary suffix!"  # to make it different

    # To ensure the problem is detected:
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        FAIL,
        "inconsistency",
        "With diverging Family name metadata entries...",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/has_regular")
def test_check_metadata_has_regular(check):
    """METADATA.pb: According Google Fonts standards,
    families should have a Regular style."""

    # Let's start with our reference FamilySans family:
    font = TEST_FILE("familysans/FamilySans-Regular.ttf")

    # We know that Family Sans has got a regular declares in its METADATA.pb file:
    assert_PASS(check(font), "with Family Sans, a family with a regular style...")

    # We remove the regular:
    md = Font(font).family_metadata
    for i in range(len(md.fonts)):
        if md.fonts[i].filename == "FamilySans-Regular.ttf":
            del md.fonts[i]
            break

    # and make sure the check now FAILs:
    assert_results_contain(
        check(MockFont(file=font, family_metadata=md)),
        FAIL,
        "lacks-regular",
        "with a METADATA.pb file without a regular...",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/regular_is_400")
def test_check_metadata_regular_is_400(check):
    """METADATA.pb: Regular should be 400."""

    # Let's start with the METADATA.pb file from our reference FamilySans family:
    font = TEST_FILE("familysans/FamilySans-Regular.ttf")

    # We know that Family Sans' Regular has a weight value equal to 400,
    # so the check should PASS:
    assert_PASS(check(font), "with Family Sans, a family with regular=400...")

    md = Font(font).family_metadata
    # Then we swap the values of the Regular and Medium:
    for i in range(len(md.fonts)):
        if md.fonts[i].filename == "FamilySans-Regular.ttf":
            md.fonts[i].weight = 500
        if md.fonts[i].filename == "FamilySans-Medium.ttf":
            md.fonts[i].weight = 400

    # and make sure the check now FAILs:
    assert_results_contain(
        check(MockFont(file=font, family_metadata=md)),
        FAIL,
        "not-400",
        "with METADATA.pb with regular=500...",
    )

    # Now we change the value of the Medium back to 500. The check will be skipped
    # because the family now has no Regular style.
    for i in range(len(md.fonts)):
        if md.fonts[i].filename == "FamilySans-Medium.ttf":
            md.fonts[i].weight = 500
    msg = assert_results_contain(
        check(MockFont(file=font, family_metadata=md)), SKIP, "unfulfilled-conditions"
    )
    assert "Unfulfilled Conditions: has_regular_style" in msg


@check_id("googlefonts/metadata/consistent_with_fonts")
def test_check_metadata_nameid_post_script_name(check, tmp_path):
    """Checks METADATA.pb font.post_script_name matches
    postscript name declared on the name table."""

    # Let's start with the METADATA.pb file from Moirai One, since it only has one font
    font = TEST_FILE("moiraione/MoiraiOne-Regular.ttf")
    md = Font(font).family_metadata

    # We know that the postscript name is good here:
    assert_PASS(check([font, fake_mdpb(tmp_path, md)]))

    # Then cause it to fail:
    md.fonts[0].post_script_name = "Foo"
    assert_results_contain(check([font, fake_mdpb(tmp_path, md)]), FAIL, "mismatch")

    # TODO: the failure-mode below seems more generic than the scope
    #       of this individual check. This could become a check by itself!
    #
    # code-paths:
    # - FAIL code="missing", "Font lacks a POSTSCRIPT_NAME"


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/nameid/font_name")
def test_check_metadata_nameid_font_name(check):
    """METADATA.pb font.name value should be same as the family name declared
    on the name table."""

    # Our reference Merriweather-Regular is know to have good fullname metadata
    font = TEST_FILE("merriweather/Merriweather-Regular.ttf")
    ttFont = TTFont(font)
    assert_PASS(check(ttFont), "with a good font...")

    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.FONT_FAMILY_NAME:
            good = name.string.decode(
                name.getEncoding()
            )  # keep a copy of the good value
            ttFont["name"].names[i].string = (good + "bad-suffix").encode(
                name.getEncoding()
            )
            assert_results_contain(
                check(ttFont),
                FAIL,
                "mismatch",
                f"with a bad FULL_FONT_NAME entry ({i})...",
            )
            ttFont["name"].names[i].string = good  # restore good value

    # We also want to make sure that name id 16, whenever present,
    # is used to compute the expected familyname.
    # Tiro Devanagari Hindi is a good exampmle of this:
    font = TEST_FILE("tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf")
    assert_PASS(check(font), "with a good font containing name id 16...")

    # Good font with other language name entries
    font = TEST_FILE("bizudpmincho-nameonly/BIZUDPMincho-Regular.ttf")

    assert_PASS(check(font), "with a good font with other languages...")

    # TODO:
    # FAIL, "lacks-entry"


@check_id("googlefonts/metadata/validate")
def test_check_metadata_match_fullname_postscript(check, tmp_path):
    """METADATA.pb family.full_name and family.post_script_name
    fields have equivalent values ?"""

    regular_font = TEST_FILE("merriweather/Merriweather-Regular.ttf")
    assert_results_contain(
        check(TEST_FILE("merriweather/METADATA.pb")),
        FAIL,
        "mismatch",
        "with bad entries (Merriweather-Regular)...",
    )
    #                       post_script_name: "Merriweather-Regular"
    #                       full_name:        "Merriweather"

    # fix the regular metadata:
    md = Font(regular_font).family_metadata
    md.fonts[2].full_name = "Merriweather Regular"

    assert_PASS(
        check(fake_mdpb(tmp_path, md)),
        "with good entries (Merriweather-Regular after full_name fix)...",
    )
    #            post_script_name: "Merriweather-Regular"
    #            full_name:        "Merriweather Regular"

    # introduce an error in the metadata:
    md.fonts[2].full_name = "MistakenFont Regular"

    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        FAIL,
        "mismatch",
        "with a mismatch...",
    )
    #                       post_script_name: "Merriweather-Regular"
    #                       full_name:        "MistakenFont Regular"


MONTSERRAT_RIBBI = [
    TEST_FILE("montserrat/Montserrat-Regular.ttf"),
    TEST_FILE("montserrat/Montserrat-Italic.ttf"),
    TEST_FILE("montserrat/Montserrat-Bold.ttf"),
    TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"),
]
MONTSERRAT_NON_RIBBI = [
    TEST_FILE("montserrat/Montserrat-BlackItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-Black.ttf"),
    TEST_FILE("montserrat/Montserrat-ExtraBoldItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-ExtraBold.ttf"),
    TEST_FILE("montserrat/Montserrat-ExtraLightItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"),
    TEST_FILE("montserrat/Montserrat-LightItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-Light.ttf"),
    TEST_FILE("montserrat/Montserrat-MediumItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-Medium.ttf"),
    TEST_FILE("montserrat/Montserrat-SemiBoldItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-SemiBold.ttf"),
    TEST_FILE("montserrat/Montserrat-ThinItalic.ttf"),
    TEST_FILE("montserrat/Montserrat-Thin.ttf"),
]


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/valid_full_name_values")
def test_check_metadata_valid_full_name_values(check):
    """METADATA.pb font.full_name field contains font name in right format?"""

    # Our reference Montserrat family is a good 18-styles family:
    # properly described in its METADATA.pb file:
    for font in MONTSERRAT_RIBBI:
        # So it must PASS the check:
        assert_PASS(check(font), "with a good RIBBI font ({fontfile})...")

        # And fail if the full familyname in METADATA.pb diverges
        # from the name inferred from the name table:
        assert_results_contain(
            check(MockFont(file=font, font_familynames=["WrongFamilyName"])),
            FAIL,
            "mismatch",
            f"with a bad RIBBI font ({font})...",
        )

    # We do the same for NON-RIBBI styles:
    for font in MONTSERRAT_NON_RIBBI:
        # So it must PASS the check:
        assert_PASS(check(font), f"with a good NON-RIBBI font ({font})...")

        # Unless when not matching typographic familyname from the name table:
        assert_results_contain(
            check(MockFont(file=font, typographic_familynames=["WrongFamilyName"])),
            FAIL,
            "mismatch",
            f"with a bad NON-RIBBI font ({font})...",
        )

    # Good font with other language name entries
    font = TEST_FILE("bizudpmincho-nameonly/BIZUDPMincho-Regular.ttf")

    assert_PASS(check(font), "with a good font with other languages...")


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/valid_filename_values")
def test_check_metadata_valid_filename_values(check):
    """METADATA.pb font.filename field contains font name in right format?"""

    # Our reference Montserrat family is a good 18-styles family:
    for font in MONTSERRAT_RIBBI + MONTSERRAT_NON_RIBBI:
        # So it must PASS the check:
        assert_PASS(check(font), f"with a good font ({font})...")

        # And fail if it finds a bad filename:
        meta = Font(font).family_metadata
        for i in range(len(meta.fonts)):
            meta.fonts[i].filename = "WrongFileName"
        assert_results_contain(
            check(MockFont(file=font, family_metadata=meta)),
            FAIL,
            "bad-field",
            f'with bad filename metadata ("WrongFileName")'
            f' for fontfile "{font}"...',
        )


@check_id("googlefonts/metadata/consistent_with_fonts")
def test_check_metadata_valid_post_script_name_values(check, tmp_path):
    """METADATA.pb font.post_script_name field contains font name in right format?"""

    # Our reference Montserrat family is a good 18-styles family:
    # So it must PASS the check:
    files = (
        MONTSERRAT_RIBBI + MONTSERRAT_NON_RIBBI + [TEST_FILE("montserrat/METADATA.pb")]
    )
    assert_PASS(check(files), "with a good font...")
    # And fail if it finds a bad filename:
    md = Font(files[0]).family_metadata
    md.fonts[0].post_script_name = "WrongPSName"
    assert_results_contain(
        check(MONTSERRAT_RIBBI + MONTSERRAT_NON_RIBBI + [fake_mdpb(tmp_path, md)]),
        FAIL,
        "mismatch",
        "with a bad font...",
    )


@check_id("googlefonts/metadata/valid_nameid25")
def test_check_metadata_valid_nameid25(check):
    """Check name ID 25 to end with "Italic" for Italic VFs"""

    # PASS
    ttFont = TTFont(TEST_FILE("shantell/ShantellSans[BNCE,INFM,SPAC,wght].ttf"))
    assert_PASS(check(ttFont), f"with a good font ({ttFont})...")

    ttFont = TTFont(TEST_FILE("shantell/ShantellSans-Italic[BNCE,INFM,SPAC,wght].ttf"))
    assert_PASS(check(ttFont), f"with a good font ({ttFont})...")

    def set_name(font, nameID, string):
        for record in font["name"].names:
            if record.nameID == nameID:
                old_string = record.toUnicode()
                if string != old_string:
                    font["name"].setName(
                        string,
                        record.nameID,
                        record.platformID,
                        record.platEncID,
                        record.langID,
                    )

    # FAIL
    fontpath = TEST_FILE("shantell/ShantellSans-Italic[BNCE,INFM,SPAC,wght].ttf")
    ttFont = TTFont(fontpath)
    set_name(ttFont, 25, "ShantellSans")
    assert_results_contain(
        check(ttFont),
        FAIL,
        "nameid25-missing-italic",
        f"with a bad font ({ttFont})...",
    )

    set_name(ttFont, 25, "ShantellSans Italic")
    assert_results_contain(
        check(ttFont),
        FAIL,
        "nameid25-has-spaces",
        f"with a bad font ({ttFont})...",
    )


# note: The copyright checks do not actually verify that the project name is correct.
#       They only focus on the string format.
GOOD_COPYRIGHT_NOTICE_STRINGS = (
    (
        "Copyright 2017 The Archivo Black Project Authors"
        " (https://github.com/Omnibus-Type/ArchivoBlack)"
    ),
    (
        "Copyright 2017-2018 The YearRange Project Authors"
        " (https://github.com/Looks/Good)"
    ),
    (
        "Copyright 2012-2014, 2016, 2019-2021, 2023 The MultiYear Project Authors"
        " (https://github.com/With/ManyRanges)"
    ),
    # We also ignore case, so these should also PASS:
    (
        "COPYRIGHT 2017 THE ARCHIVO BLACK PROJECT AUTHORS"
        " (HTTPS://GITHUB.COM/OMNIBUS-TYPE/ARCHIVOBLACK)"
    ),
    (
        "copyright 2017 the archivo black project authors"
        " (https://github.com/omnibus-type/archivoblack)"
    ),
)


@check_id("googlefonts/font_copyright")
def test_check_font_copyright(check, tmp_path):
    """Copyright notice on METADATA.pb matches canonical pattern ?"""

    # Our reference Cabin Regular is known to be bad
    # Since it provides an email instead of a git URL.
    # Also the check should work fine without a METADATA.pb file.
    font = TEST_FILE("cabin/Cabin-Regular.ttf")
    assert_results_contain(
        check(font), FAIL, "bad-notice-format", "with a bad copyright notice string..."
    )

    ttFont = TTFont(font)

    # Then, to make the check PASS, we change it into a few good strings:
    for good_string in GOOD_COPYRIGHT_NOTICE_STRINGS:
        for i, entry in enumerate(ttFont["name"].names):
            if entry.nameID == NameID.COPYRIGHT_NOTICE:
                ttFont["name"].names[i].string = good_string.encode(entry.getEncoding())

        md = Font(font).family_metadata
        md.fonts[0].copyright = good_string

        assert_PASS(
            check([ttFont, fake_mdpb(tmp_path, md)]),
            "with a good copyright notice string...",
        )

        too_long = good_string + "x" * (501 - len(good_string))
        md.fonts[0].copyright = too_long
        for i, entry in enumerate(ttFont["name"].names):
            if entry.nameID == NameID.COPYRIGHT_NOTICE:
                ttFont["name"].names[i].string = too_long.encode(entry.getEncoding())

        assert_results_contain(
            check([ttFont, fake_mdpb(tmp_path, md)]),
            FAIL,
            "max-length",
            "with a 501-char copyright notice string...",
        )

    # Now let's make them different
    md.fonts[0].copyright = good_string
    assert_results_contain(
        check([ttFont, fake_mdpb(tmp_path, md)]),
        FAIL,
        "mismatch",
        "with a bad METADATA.pb (with a copyright string not matching this font)...",
    )


@pytest.mark.skip("Check is not passing and needs a code-review.")
@check_id("googlefonts/metadata/reserved_font_name")
def test_check_metadata_reserved_font_name(check, tmp_path):
    """Copyright notice on METADATA.pb should not contain Reserved Font Name."""

    font = TEST_FILE("cabin/Cabin-Regular.ttf")
    good_mdpb = TEST_FILE("cabin/METADATA.pb")
    assert_PASS(check(good_mdpb), "with a good copyright notice string...")

    # Then we make it bad:
    md = Font(font).font_metadata
    md.copyright += "Reserved Font Name"
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        WARN,
        "rfn",
        'with a notice containing "Reserved Font Name"...',
    )


@check_id("googlefonts/metadata/consistent_with_fonts")
def test_check_metadata_filenames(check):
    """METADATA.pb: Font filenames match font.filename entries?"""

    rosarivo_fonts_plus_mdpb = rosarivo_fonts + [TEST_FILE("rosarivo/METADATA.pb")]

    assert_PASS(check(rosarivo_fonts_plus_mdpb), "with matching list of font files...")

    # make sure missing files are detected by the check:
    fonts = rosarivo_fonts_plus_mdpb
    # drop one font file from check in order to trigger the FAIL
    assert_results_contain(
        check(fonts[1:]), FAIL, "file-not-found", "with missing font files..."
    )

    # From all TTFs in Cabin's directory, the condensed ones are not
    # listed on METADATA.pb, so the check must FAIL.
    assert_results_contain(
        check(
            list(glob.glob("data/test/cabin/*ttf")) + [TEST_FILE("cabin/METADATA.pb")]
        ),
        FAIL,
        "file-not-declared",
        "with some font files not declared...",
    )


@check_id("googlefonts/metadata/consistent_with_fonts")
def test_check_metadata_nameid_family_and_full_names(check):
    """METADATA.pb font.name and font.full_name fields
    match the values declared on the name table?"""

    rosarivo_fonts_plus_mdpb = [TTFont(x) for x in rosarivo_fonts] + [
        TEST_FILE("rosarivo/METADATA.pb")
    ]
    assert_PASS(check(rosarivo_fonts_plus_mdpb), "with a good font...")

    # There we go again!
    # Breaking FULL_FONT_NAME entries:
    ttFont = rosarivo_fonts_plus_mdpb[0]
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.FULL_FONT_NAME:
            backup = name.string
            ttFont["name"].names[i].string = "This is utterly wrong!".encode(
                name.getEncoding()
            )
            assert_results_contain(
                check(rosarivo_fonts_plus_mdpb),
                FAIL,
                "fullname-mismatch",
                "with a METADATA.pb / FULL_FONT_NAME mismatch...",
            )
            # and restore the good value:
            ttFont["name"].names[i].string = backup

    # And then we do the same with FONT_FAMILY_NAME entries:
    for i, name in enumerate(ttFont["name"].names):
        if name.nameID == NameID.FONT_FAMILY_NAME:
            backup = name.string
            ttFont["name"].names[i].string = (
                "I'm listening to" " The Players with Hiromasa Suzuki - Galaxy (1979)"
            ).encode(name.getEncoding())
            assert_results_contain(
                check(rosarivo_fonts_plus_mdpb),
                FAIL,
                "familyname-mismatch",
                "with a METADATA.pb / FONT_FAMILY_NAME mismatch...",
            )
            # and restore the good value:
            ttFont["name"].names[i].string = backup


@check_id("googlefonts/metadata/validate")
def test_check_metadata_match_name_familyname(check, tmp_path):
    """METADATA.pb: Check font name is the same as family name."""

    # Our reference Cabin is known to be good
    font = TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")
    mdbp = TEST_FILE("cabinvf/METADATA.pb")
    assert_PASS(check(mdbp), "with a good font...")

    # Then we FAIL with mismatching names:
    family_md = Font(font).family_metadata
    family_md.name = "Some Fontname"
    family_md.fonts[0].name = "Something Else"
    assert_results_contain(
        check(fake_mdpb(tmp_path, family_md)),
        FAIL,
        "mismatch",
        "with bad font/family name metadata...",
    )


@check_id("googlefonts/metadata/validate")
def test_check_check_metadata_canonical_weight_value(check, tmp_path):
    """METADATA.pb: Check that font weight has a canonical value."""

    font = TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")
    check([font, TEST_FILE("cabinvf/METADATA.pb")])
    md = Font(font).family_metadata

    for w in [100, 200, 300, 400, 500, 600, 700, 800, 900]:
        # md.fonts[0].weight = str(w)
        assert_PASS(
            check(fake_mdpb(tmp_path, md)),
            f"with a good weight value ({w})...",
        )

    for w in [150, 250, 350, 450, 550, 650, 750, 850]:
        md.fonts[0].weight = w
        assert_results_contain(
            check(fake_mdpb(tmp_path, md)),
            FAIL,
            "bad-weight",
            "with a bad weight value ({w})...",
        )


@check_id("googlefonts/metadata/weightclass")
def test_check_metadata_weightclass(check, tmp_path):
    """Checking OS/2 usWeightClass matches weight specified at METADATA.pb"""

    # === test cases for Variable Fonts ===
    # Our reference Jura is known to be good
    font = TEST_FILE("varfont/jura/Jura[wght].ttf")
    mdpb = TEST_FILE("varfont/jura/METADATA.pb")
    assert_PASS(check([font, mdpb]), "with a good metadata...")

    # Should report if a bad weight value is ifound though:
    md = Font(font).family_metadata
    good_value = md.fonts[0].weight
    bad_value = good_value + 100
    md.fonts[0].weight = bad_value

    assert_results_contain(
        check([font, fake_mdpb(tmp_path, md)]),
        FAIL,
        "mismatch",
        "with a bad metadata...",
    )

    font = TEST_FILE("leaguegothic-vf/LeagueGothic[wdth].ttf")
    mdpb = TEST_FILE("leaguegothic-vf/METADATA.pb")
    assert_PASS(check([font, mdpb]), 'with a good VF that lacks a "wght" axis....')
    # See: https://github.com/fonttools/fontbakery/issues/3529

    # === test cases for Static Fonts ===
    # Our reference Montserrat family is a good 18-styles family:
    for fontfile in MONTSERRAT_RIBBI + MONTSERRAT_NON_RIBBI:
        ttFont = TTFont(fontfile)
        mdpb = TEST_FILE("montserrat/METADATA.pb")
        assert_PASS(check([ttFont, mdpb]), f"with a good font ({fontfile})...")

        # but should report bad weight values:
        md = Font(fontfile).family_metadata
        changed = False
        for font in md.fonts:
            if font.filename == os.path.basename(fontfile):
                good_value = font.weight
                bad_value = good_value + 50
                font.weight = bad_value
                changed = True
        assert changed, fontfile
        assert_results_contain(
            check([fontfile, fake_mdpb(tmp_path, md)]),
            FAIL,
            "mismatch",
            f"with bad metadata for {fontfile}...",
        )

        # If font is Thin or ExtraLight, ensure that this check can
        # accept both 100, 250 for Thin and 200, 275 for ExtraLight
        if "Thin" in fontfile:
            ttFont["OS/2"].usWeightClass = 100
            assert_PASS(
                check([ttFont, mdpb]), f"with weightclass 100 on ({fontfile})..."
            )

            ttFont["OS/2"].usWeightClass = 250
            assert_PASS(
                check([ttFont, mdpb]), f"with weightclass 250 on ({fontfile})..."
            )

        if "ExtraLight" in fontfile:
            ttFont["OS/2"].usWeightClass = 200
            assert_PASS(
                check([ttFont, mdpb]), f"with weightClass 200 on ({fontfile})..."
            )

            ttFont["OS/2"].usWeightClass = 275
            assert_PASS(
                check([ttFont, mdpb]), f"with weightClass 275 on ({fontfile})..."
            )


@check_id("googlefonts/metadata/consistent_repo_urls")
def test_check_metadata_consistent_repo_urls(check, tmp_path):
    """METADATA.pb: Check URL on copyright string
    is the same as in repository_url field."""

    # The problem was first seen on a project with these diverging values:
    # copyright: "Copyright 2022 The Delicious Handrawn Project Authors
    #             (https://github.com/duartp/gloock)"
    # repository_url: "https://github.com/alphArtype/Delicious-Handrawn"
    md_file = TEST_FILE("delicioushandrawn/METADATA.pb")
    assert_results_contain(check([md_file]), FAIL, "mismatch", "with different URLs...")

    family_md = read_mdpb(md_file)
    # so we fix it:
    assert (
        family_md.source.repository_url
        == "https://github.com/alphArtype/Delicious-Handrawn"
    )
    family_md.fonts[0].copyright = (
        "Copyright 2022 The Delicious Handrawn Project Authors"
        " (https://github.com/alphArtype/Delicious-Handrawn)"
    )
    assert_PASS(check(fake_mdpb(tmp_path, family_md)))

    family_md.source.repository_url = ""
    assert_results_contain(
        check(fake_mdpb(tmp_path, family_md)),
        FAIL,
        "lacks-repo-url",
        "when the field is either empty or completley missing...",
    )

    # League Gothic got a bad repo in DESCRIPTION.en.html
    league_files = [
        TEST_FILE("leaguegothic-vf/METADATA.pb"),
        TEST_FILE("leaguegothic-vf/DESCRIPTION.en_us.html"),
    ]
    assert_results_contain(
        check(league_files), FAIL, "mismatch", "with different URLs..."
    )

    # CabinVF got a bad repo in OFL.txt
    cabin_files = [TEST_FILE("cabinvf/METADATA.pb"), TEST_FILE("cabinvf/OFL.txt")]
    assert_results_contain(
        check(cabin_files), FAIL, "mismatch", "with different URLs..."
    )


@check_id("googlefonts/metadata/primary_script")
def test_check_metadata_primary_script(check, tmp_path):
    """METADATA.pb: Check for primary_script"""

    font = TEST_FILE("notosanskhudawadi/NotoSansKhudawadi-Regular.ttf")
    mdpb_file = TEST_FILE("notosanskhudawadi/METADATA.pb")
    assert_PASS(check([font, mdpb_file]))

    family_md = read_mdpb(mdpb_file)
    family_md.primary_script = ""
    assert_results_contain(
        check([font, fake_mdpb(tmp_path, family_md)]),
        WARN,
        "missing-primary-script",
    )
    family_md.primary_script = "Arab"
    assert_results_contain(
        check([font, fake_mdpb(tmp_path, family_md)]),
        WARN,
        "wrong-primary-script",
    )
    assert_PASS(
        check(
            [
                TEST_FILE("merriweather/Merriweather-Regular.ttf"),
                TEST_FILE("merriweather/METADATA.pb"),
            ]
        )
    )


@check_id("googlefonts/unitsperem")
def test_check_unitsperem(check):
    """Stricter unitsPerEm criteria for Google Fonts."""

    ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))

    PASS_VALUES = [
        16,
        32,
        64,
        128,
        256,
        512,
        1024,
    ]  # Good for better performance on legacy renderers
    PASS_VALUES.extend([500, 1000])  # or common typical values
    PASS_VALUES.extend([2000, 2048])  # not so common, but still ok

    FAIL_LARGE_VALUES = [4096, 16385]  # uncommon and large,
    # and finally the bad ones, including:
    FAIL_BAD_VALUES = [0, 1, 2, 4, 8, 15]  # simply invalid

    for pass_value in PASS_VALUES:
        ttFont["head"].unitsPerEm = pass_value
        assert_PASS(check(ttFont), f"with unitsPerEm = {pass_value}...")

    for warn_value in FAIL_LARGE_VALUES:
        ttFont["head"].unitsPerEm = warn_value
        assert_results_contain(
            check(ttFont), FAIL, "large-value", f"with unitsPerEm = {warn_value}..."
        )

    for fail_value in FAIL_BAD_VALUES:
        ttFont["head"].unitsPerEm = fail_value
        assert_results_contain(
            check(ttFont), FAIL, "bad-value", f"with unitsPerEm = {fail_value}..."
        )


# FIXME!
# GFonts hosted Cabin files seem to have changed in ways
# that break some of the assumptions in the code-test below.
# More info at https://github.com/fonttools/fontbakery/issues/2581
@pytest.mark.xfail(strict=True)
@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/production_encoded_glyphs")
def test_check_production_encoded_glyphs(check, cabin_ttFonts):
    """Check glyphs are not missing when compared to version on fonts.google.com"""

    for font in cabin_fonts:
        # Cabin font hosted on fonts.google.com contains
        # all the glyphs for the font in data/test/cabin
        assert_PASS(check(font), f"with '{font}'")

        ttFont = TTFont(font)
        # Take A glyph out of font
        ttFont["cmap"].getcmap(3, 1).cmap.pop(ord("A"))
        ttFont["glyf"].glyphs.pop("A")
        assert_results_contain(check(ttFont), FAIL, "lost-glyphs")


@check_id("googlefonts/metadata/category")
def test_check_metadata_category(check, tmp_path):
    """Category field for this font on METADATA.pb is valid?"""

    # Our reference Cabin family...
    font = TEST_FILE("cabin/Cabin-Regular.ttf")
    check(font)
    md = Font(font).family_metadata
    assert md.category == ["SANS_SERIF"]  # ...is known to be good ;-)
    assert_PASS(check([font, fake_mdpb(tmp_path, md)]), "with a good METADATA.pb...")

    # We then report a problem with this sample of bad values:
    for bad_value in ["SAN_SERIF", "MONO_SPACE", "sans_serif", "monospace"]:
        md.category[:] = [bad_value]
        assert_results_contain(
            check([font, fake_mdpb(tmp_path, md)]),
            FAIL,
            "bad-value",
            f'with a bad category "{bad_value}"...',
        )

    # And we accept the good ones:
    for good_value in ["MONOSPACE", "SANS_SERIF", "SERIF", "DISPLAY", "HANDWRITING"]:
        md.category[:] = [good_value]
        assert_PASS(check([font, fake_mdpb(tmp_path, md)]), f'with "{good_value}"...')


@pytest.mark.parametrize(
    """fp,mod,result""",
    [
        # tests from test_check_name_familyname:
        (TEST_FILE("cabin/Cabin-Regular.ttf"), {}, PASS),
        (
            TEST_FILE("cabin/Cabin-Regular.ttf"),
            {NameID.FONT_FAMILY_NAME: "Wrong"},
            FAIL,
        ),
        (TEST_FILE("overpassmono/OverpassMono-Regular.ttf"), {}, PASS),
        (TEST_FILE("overpassmono/OverpassMono-Bold.ttf"), {}, PASS),
        (TEST_FILE("overpassmono/OverpassMono-Regular.ttf"), {1: "Foo"}, FAIL),
        (TEST_FILE("merriweather/Merriweather-Black.ttf"), {}, PASS),
        (TEST_FILE("merriweather/Merriweather-LightItalic.ttf"), {}, PASS),
        (
            TEST_FILE("merriweather/Merriweather-LightItalic.ttf"),
            {NameID.FONT_FAMILY_NAME: "Merriweather Light Italic"},
            FAIL,
        ),
        (TEST_FILE("abeezee/ABeeZee-Regular.ttf"), {}, PASS),
        # tests from test_check_name_subfamilyname
        (TEST_FILE("overpassmono/OverpassMono-Regular.ttf"), {}, PASS),
        (TEST_FILE("overpassmono/OverpassMono-Bold.ttf"), {}, PASS),
        (TEST_FILE("merriweather/Merriweather-Black.ttf"), {}, PASS),
        (TEST_FILE("merriweather/Merriweather-LightItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-BlackItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Black.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Bold.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraBoldItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraBold.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraLightItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Italic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-LightItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Light.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-MediumItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Medium.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Regular.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-SemiBoldItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-SemiBold.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-ThinItalic.ttf"), {}, PASS),
        (TEST_FILE("montserrat/Montserrat-Thin.ttf"), {}, PASS),
        (
            TEST_FILE("montserrat/Montserrat-ThinItalic.ttf"),
            {NameID.FONT_SUBFAMILY_NAME: "Not a proper style"},
            FAIL,
        ),
        # tests from test_check_name_fullfontname
        (TEST_FILE("cabin/Cabin-Regular.ttf"), {}, PASS),
        # warn should be raised since full name is missing Regular
        (TEST_FILE("cabin/Cabin-Regular.ttf"), {4: "Cabin"}, WARN),
        (TEST_FILE("cabin/Cabin-BoldItalic.ttf"), {}, PASS),
        (
            TEST_FILE("cabin/Cabin-BoldItalic.ttf"),
            {NameID.FULL_FONT_NAME: "Make it fail"},
            FAIL,
        ),
        (TEST_FILE("abeezee/ABeeZee-Regular.ttf"), {}, PASS),
        # tests from test_check_name_typographicfamilyname
        (TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"), {}, PASS),
        (
            TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"),
            {NameID.TYPOGRAPHIC_FAMILY_NAME: "Arbitrary name"},
            FAIL,
        ),
        (TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"), {}, PASS),
        (
            TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"),
            {NameID.TYPOGRAPHIC_FAMILY_NAME: "Foo"},
            FAIL,
        ),
        (
            TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"),
            {NameID.TYPOGRAPHIC_FAMILY_NAME: None},
            FAIL,
        ),
        # tests from test_check_name_typographicsubfamilyname
        (TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"), {}, PASS),
        (
            TEST_FILE("montserrat/Montserrat-BoldItalic.ttf"),
            {NameID.TYPOGRAPHIC_SUBFAMILY_NAME: "Foo"},
            FAIL,
        ),
        (TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"), {}, PASS),
        (
            TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"),
            {NameID.TYPOGRAPHIC_SUBFAMILY_NAME: None},
            FAIL,
        ),
        (
            TEST_FILE("montserrat/Montserrat-ExtraLight.ttf"),
            {NameID.TYPOGRAPHIC_SUBFAMILY_NAME: "Generic Name"},
            FAIL,
        ),
        # variable font checks
        (TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"), {}, PASS),
        # Open Sans' origin is Light so this should pass
        (
            TEST_FILE("varfont/OpenSans[wdth,wght].ttf"),
            {
                NameID.FONT_SUBFAMILY_NAME: "Regular",
                NameID.TYPOGRAPHIC_SUBFAMILY_NAME: "Light",
            },
            PASS,
        ),
        (
            TEST_FILE("varfont/OpenSans[wdth,wght].ttf"),
            {
                NameID.FONT_SUBFAMILY_NAME: "Regular",
                NameID.TYPOGRAPHIC_SUBFAMILY_NAME: "Condensed Light",
            },
            FAIL,
        ),
        (TEST_FILE("varfont/RobotoSerif[GRAD,opsz,wdth,wght].ttf"), {}, FAIL),
        # Roboto Serif has an opsz axes so this should pass
        (
            TEST_FILE("varfont/RobotoSerif[GRAD,opsz,wdth,wght].ttf"),
            {
                NameID.FONT_FAMILY_NAME: "Roboto Serif",
                NameID.FONT_SUBFAMILY_NAME: "Regular",
                NameID.FULL_FONT_NAME: "Roboto Serif Regular",
                NameID.POSTSCRIPT_NAME: "RobotoSerif-Regular",
                NameID.TYPOGRAPHIC_FAMILY_NAME: None,
                NameID.TYPOGRAPHIC_SUBFAMILY_NAME: None,
            },
            PASS,
        ),
        (TEST_FILE("varfont/Georama[wdth,wght].ttf"), {}, PASS),
        # Georama's default fvar vals are wdth=62.5, wght=100
        # which means ExtraCondensed Thin should appear in the family name
        (
            TEST_FILE("varfont/Georama[wdth,wght].ttf"),
            {
                NameID.FONT_FAMILY_NAME: "Georama ExtraCondensed Thin",
                NameID.FONT_SUBFAMILY_NAME: "Regular",
                NameID.TYPOGRAPHIC_FAMILY_NAME: "Georama",
                NameID.TYPOGRAPHIC_SUBFAMILY_NAME: "ExtraCondensed Thin",
            },
            PASS,
        ),
    ],
)
@check_id("googlefonts/font_names")
def test_check_font_names(check, fp, mod, result):
    """Check font names are correct"""
    # Please note: This check was introduced in
    # https://github.com/fonttools/fontbakery/pull/3800 which has replaced
    # the following checks:
    #   googlefonts/name/familyname
    #   googlefonts/name/subfamilyname
    #   googlefonts/name/typographicfamilyname
    #   googlefonts/name/typographicsubfamilyname
    #
    # It works by simply using the nametable builder which is found in the
    # axis registry,
    # https://github.com/googlefonts/axisregistry/blob/main/Lib/axisregistry/__init__.py#L232
    # this repository already has good unit tests but this check will also include the
    # previous test cases found in fontbakery.
    # https://github.com/googlefonts/axisregistry/blob/main/tests/test_names.py

    ttFont = TTFont(fp)
    # get the expecteed font names now before we modify them
    expected = expected_font_names(ttFont, [])
    if mod:
        for k, v in mod.items():
            if v is None:
                ttFont["name"].removeNames(k)
            else:
                ttFont["name"].setName(v, k, 3, 1, 0x409)

    if result == PASS:
        assert_PASS(
            check(ttFont),
            "with a good font...",
        )
    elif result == WARN:
        assert_results_contain(
            check(ttFont),
            WARN,
            "lacks-regular",
            "with bad names",
        )
    else:
        assert_results_contain(
            check(ttFont),
            FAIL,
            "bad-names",
            "with bad names",
        )


@check_id("googlefonts/name/mandatory_entries")
def test_check_name_mandatory_entries(check):
    """Font has all mandatory 'name' table entries ?"""

    # We'll check both RIBBI and non-RIBBI fonts
    # so that we cover both cases for FAIL/PASS scenarios

    # === First with a RIBBI font: ===
    # Our reference Cabin Regular is known to be good
    ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))
    assert_PASS(check(ttFont), "with a good RIBBI font...")

    mandatory_entries = [
        NameID.FONT_FAMILY_NAME,
        NameID.FONT_SUBFAMILY_NAME,
        NameID.FULL_FONT_NAME,
        NameID.POSTSCRIPT_NAME,
    ]

    # then we "remove" each mandatory entry one by one:
    for mandatory in mandatory_entries:
        ttFont = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))
        for i, name in enumerate(ttFont["name"].names):
            if name.nameID == mandatory:
                ttFont["name"].names[
                    i
                ].nameID = 0  # not really removing it, but replacing it
                # by something else completely irrelevant
                # for the purposes of this specific check
        assert_results_contain(
            check(ttFont),
            FAIL,
            "missing-entry",
            f"with a missing madatory (RIBBI) name entry (id={mandatory})...",
        )

    # === And now a non-RIBBI font: ===
    # Our reference Merriweather Black is known to be good
    ttFont = TTFont(TEST_FILE("merriweather/Merriweather-Black.ttf"))
    assert_PASS(check(ttFont), "with a good non-RIBBI font...")

    mandatory_entries = [
        NameID.FONT_FAMILY_NAME,
        NameID.FONT_SUBFAMILY_NAME,
        NameID.FULL_FONT_NAME,
        NameID.POSTSCRIPT_NAME,
        NameID.TYPOGRAPHIC_FAMILY_NAME,
        NameID.TYPOGRAPHIC_SUBFAMILY_NAME,
    ]

    # then we (again) "remove" each mandatory entry one by one:
    for mandatory in mandatory_entries:
        ttFont = TTFont(TEST_FILE("merriweather/Merriweather-Black.ttf"))
        for i, name in enumerate(ttFont["name"].names):
            if name.nameID in mandatory_entries:
                ttFont["name"].names[
                    i
                ].nameID = 0  # not really removing it, but replacing it
                # by something else completely irrelevant
                # for the purposes of this specific check
        assert_results_contain(
            check(ttFont),
            FAIL,
            "missing-entry",
            "with a missing madatory (non-RIBBI) name entry (id={mandatory})...",
        )


def test_condition_familyname_with_spaces():
    assert MockFont(familyname="OverpassMono").familyname_with_spaces == "Overpass Mono"
    assert (
        MockFont(familyname="BodoniModa11").familyname_with_spaces == "Bodoni Moda 11"
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/varfont/generate_static")
def test_check_varfont_generate_static(check):
    """Check a static ttf can be generated from a variable font."""

    ttFont = TTFont(TEST_FILE("cabinvfbeta/CabinVFBeta.ttf"))
    assert_PASS(check(ttFont))

    # Mangle the coordinates of the first named instance
    # to deliberately break the variable font.
    ttFont["fvar"].instances[0].coordinates = {"fooo": 400.0, "baar": 100.0}
    msg = assert_results_contain(check(ttFont), FAIL, "varlib-mutator")
    assert "fontTools.varLib.mutator failed" in msg

    # Now delete the fvar table to exercise a SKIP result due an unfulfilled condition.
    del ttFont["fvar"]
    msg = assert_results_contain(check(ttFont), SKIP, "unfulfilled-conditions")
    assert "Unfulfilled Conditions: is_variable_font" in msg


@check_id("googlefonts/varfont/has_HVAR")
def test_check_varfont_has_HVAR(check):
    """Check that variable fonts have an HVAR table."""

    # Our reference Cabin Variable Font contains an HVAR table.
    ttFont = TTFont(TEST_FILE("cabinvfbeta/CabinVFBeta.ttf"))

    # So the check must PASS.
    assert_PASS(check(ttFont))

    # Introduce the problem by removing the HVAR table:
    del ttFont["HVAR"]
    assert_results_contain(check(ttFont), FAIL, "lacks-HVAR")


@check_id("googlefonts/fvar_instances")
def test_check_fvar_instances__another_test(check):  # TODO: REVIEW THIS.
    """Check variable font instances."""

    ttFont = TTFont(TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"))

    # rename the first fvar instance so the font is broken
    ttFont["name"].setName("foo", 258, 3, 1, 0x409)

    # So it must FAIL the check:
    assert_results_contain(
        check(ttFont), FAIL, "bad-fvar-instances", "with a bad font..."
    )

    # rename the first fvar instance so it is correct
    ttFont["name"].setName("Regular", 258, 3, 1, 0x409)

    assert_PASS(check(ttFont), "with a good font...")


@check_id("googlefonts/fvar_instances")
def test_check_fvar_instances__yet_another_test(check):  # TODO: REVIEW THIS.
    """A variable font must have named instances."""

    # ExpletusVF does have instances.
    # Note: The "broken" in the path name refers to something else.
    #       (See test_check_fvar_name_entries)
    ttFont = TTFont(TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"))

    # So it must PASS the check:
    assert_PASS(check(ttFont), "with a good font...")

    # If we delete all instances, then it must FAIL:
    while len(ttFont["fvar"].instances):
        del ttFont["fvar"].instances[0]

    assert_results_contain(
        check(ttFont), FAIL, "bad-fvar-instances", "with a bad font..."
    )


@check_id("googlefonts/fvar_instances")
def test_check_fvar_instances__whats_going_on_here(check):  # TODO: REVIEW THIS.
    """Variable font weight coordinates must be multiples of 100."""

    # This copy of Markazi Text has an instance with
    # a 491 'wght' coordinate instead of 500.
    ttFont = TTFont(TEST_FILE("broken_markazitext/MarkaziText-VF.ttf"))

    # So it must FAIL the check:
    assert_results_contain(
        check(ttFont), FAIL, "bad-fvar-instances", "with a bad font..."
    )

    # Let's then change the weight coordinates to make it PASS the check:
    # instances are from 400-700 (Regular-Bold) so set start to 400
    wght_val = 400
    for i, instance in enumerate(ttFont["fvar"].instances):
        ttFont["fvar"].instances[i].coordinates["wght"] = wght_val
        wght_val += 100

    assert_PASS(check(ttFont), "with a good font...")


@check_id("googlefonts/family/italics_have_roman_counterparts")
def test_check_family_italics_have_roman_counterparts(check):
    """Ensure Italic styles have Roman counterparts."""

    fonts = [
        TEST_FILE("merriweather/Merriweather-BlackItalic.ttf"),
        TEST_FILE("merriweather/Merriweather-Black.ttf"),
        TEST_FILE("merriweather/Merriweather-BoldItalic.ttf"),
        TEST_FILE("merriweather/Merriweather-Bold.ttf"),
        TEST_FILE("merriweather/Merriweather-Italic.ttf"),
        TEST_FILE("merriweather/Merriweather-LightItalic.ttf"),
        TEST_FILE("merriweather/Merriweather-Light.ttf"),
        TEST_FILE("merriweather/Merriweather-Regular.ttf"),
    ]

    assert_PASS(check(fonts), "with a good family...")

    fonts.pop(-1)  # remove the last one, which is the Regular
    assert_results_contain(
        check(fonts),
        FAIL,
        "missing-roman",
        "with a family that has an Italic but lacks a Regular.",
    )

    shutil.copy(
        TEST_FILE("merriweather/Merriweather-Italic.ttf"),
        TEST_FILE("merriweather/MerriweatherItalic.ttf"),
    )
    fonts.append(TEST_FILE("merriweather/MerriweatherItalic.ttf"))
    assert_results_contain(
        check(fonts),
        WARN,
        "bad-filename",
        "with a family that has a non-canonical italic filename.",
    )
    os.unlink(TEST_FILE("merriweather/MerriweatherItalic.ttf"))

    # This check must also be able to deal with variable fonts!
    fonts = [
        TEST_FILE("cabinvf/Cabin-Italic[wdth,wght].ttf"),
        TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"),
    ]
    assert_PASS(check(fonts), "with a good set of varfonts...")

    fonts = [TEST_FILE("cabinvf/Cabin-Italic[wdth,wght].ttf")]
    assert_results_contain(
        check(fonts),
        FAIL,
        "missing-roman",
        "with an Italic varfont that lacks a Roman counterpart.",
    )


@check_id("googlefonts/repo/dirname_matches_nameid_1")
def test_check_repo_dirname_matches_nameid_1(check, tmp_path):
    FONT_FAMILY_NAME = "rosarivo"

    # Create a temporary directory that mimics the folder structure of the Google Fonts
    # repository, and copy into it a test family that is known to have all the necessary
    # files.
    tmp_gf_dir = tmp_path / f"ofl/{FONT_FAMILY_NAME}"
    src_family = portable_path(f"data/test/{FONT_FAMILY_NAME}")
    shutil.copytree(src_family, tmp_gf_dir, dirs_exist_ok=True)

    # PASS result; only check regular as we get skips for non-Regular
    fonts = [str(tmp_gf_dir / "Rosarivo-Regular.ttf")]
    assert_PASS(check(fonts))

    # Get the path of the Regular font; it will be used for deleting the file later.
    reg_font_path = next((pth for pth in fonts if "Regular" in pth), None)

    # Now rename the temporary directory to make the check fail.
    new_dir_name = f"not_{FONT_FAMILY_NAME}"
    renamed_tmp_gf_dir = tmp_gf_dir.with_name(new_dir_name)
    os.replace(tmp_gf_dir, renamed_tmp_gf_dir)

    # FAIL ("mismatch") result
    fonts = [str(renamed_tmp_gf_dir / "Rosarivo-Regular.ttf")]
    msg = assert_results_contain(check(fonts), FAIL, "mismatch")
    assert msg == (
        f"Family name on the name table ('{FONT_FAMILY_NAME.title()}')"
        f" does not match directory name in the repo structure ('{new_dir_name}')."
        f" Expected '{FONT_FAMILY_NAME}'."
    )

    # Rename the temporary directory back to the original name,
    # and delete the Regular font file to make the check fail.
    os.replace(renamed_tmp_gf_dir, tmp_gf_dir)
    os.remove(reg_font_path)


@check_id("googlefonts/repo/vf_has_static_fonts")
def test_check_repo_vf_has_static_fonts(check, tmp_path):
    """Check VF family dirs in google/fonts contain static fonts"""

    # in order for this check to work, we need to
    # mimic the folder structure of the Google Fonts repository
    dir_path = "ofl/foo/bar"
    tmp_gf_dir = tmp_path / "repo_vf_has_static_fonts"
    tmp_gf_dir.mkdir()
    family_dir = tmp_gf_dir / "ofl/testfamily"
    src_family = portable_path("data/test/varfont/inter")

    shutil.copytree(src_family, family_dir, dirs_exist_ok=True)

    assert_PASS(
        check([str(x) for x in family_dir.glob("**/*") if x.is_file()]),
        "for a VF family which does not have a static dir.",
    )

    static_dir = family_dir / "static"
    static_dir.mkdir()
    static_fonts = portable_path("data/test/ibmplexsans-vf")
    shutil.rmtree(static_dir)
    shutil.copytree(static_fonts, static_dir)
    assert_PASS(
        check([str(x) for x in family_dir.glob("**/*") if x.is_file()]),
        "for a VF family which has a static dir and manually hinted static fonts",
    )

    static_fonts = portable_path("data/test/overpassmono")
    shutil.rmtree(static_dir)
    static_dir.mkdir()
    shutil.copyfile(
        os.path.join(static_fonts, "OverpassMono-Regular.ttf"),
        static_dir / "OverpassMono-Regular.ttf",
    )

    assert_results_contain(
        check([str(x) for x in family_dir.glob("**/*") if x.is_file()]),
        WARN,
        "not-manually-hinted",
        "for a VF family which has a static dir but no manually hinted static fonts",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/repo/upstream_yaml_has_required_fields")
def test_check_repo_upstream_yaml_has_required_fields(check):
    """Check upstream.yaml has all required fields"""

    upstream_yaml = {
        "branch": "main",
        "files": {"TestFamily-Regular.ttf": "TestFamily-Regular.ttf"},
    }
    # Pass if upstream.yaml file contains all fields
    assert_PASS(
        check(MockFont(upstream_yaml=upstream_yaml)),
        "for an upstream.yaml which contains all fields",
    )

    # Fail if it doesn't
    upstream_yaml.pop("files")
    assert_results_contain(
        check(MockFont(upstream_yaml=upstream_yaml)),
        FAIL,
        "missing-fields",
        "for an upsream.yaml which doesn't contain all fields",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/repo/fb_report")
def test_check_repo_fb_report(check, tmp_path):
    """A font repository should not include FontBakery report files"""

    family_dir = tmp_path / "repo_fb_report"
    family_dir.mkdir()
    src_family = portable_path("data/test/varfont")

    shutil.copytree(src_family, family_dir, dirs_exist_ok=True)

    assert_PASS(
        check(MockFont(family_directory=family_dir)),
        "for a repo without FontBakery report files.",
    )

    assert_PASS(
        check(MockFont(family_directory=family_dir)),
        "with a json file that is not a FontBakery report.",
    )

    # Add a json file that is not a FB report
    open(os.path.join(family_dir, "something_else.json"), "w+", encoding="utf-8").write(
        "this is not a FB report"
    )

    FB_REPORT_SNIPPET = """
{
    "result": {
        "INFO": 8,
        "PASS": 81,
        "SKIP": 74,
        "WARN": 4
    },
    "sections": [
    """
    # Report files must be detected even if placed on subdirectories and the check code
    # should not rely only on filename (such as "Jura-Regular.fb-report.json")
    # but should instead inspect the contents of the file:
    open(
        os.path.join(family_dir, "jura", "static", "my_fontfamily_name.json"),
        "w+",
        encoding="utf-8",
    ).write(FB_REPORT_SNIPPET)
    assert_results_contain(
        check(MockFont(family_directory=family_dir)),
        WARN,
        "fb-report",
        "with an actual snippet of a report.",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/repo/zip_files")
def test_check_repo_zip_files(check, tmp_path):
    """A font repository should not include ZIP files"""

    family_dir = tmp_path / "repo_zip_files"
    family_dir.mkdir()
    src_family = portable_path("data/test/varfont")

    shutil.copytree(src_family, family_dir, dirs_exist_ok=True)

    assert_PASS(
        check(MockFont(family_directory=family_dir)), "for a repo without ZIP files."
    )

    for ext in ["zip", "rar", "7z"]:
        # ZIP files must be detected even if placed on subdirectories:
        filepath = os.path.join(family_dir, "jura", "static", f"fonts-release.{ext}")
        # create an empty file. The check won't care about the contents:
        open(filepath, "w+", encoding="utf-8")
        assert_results_contain(
            check(MockFont(family_directory=family_dir)),
            FAIL,
            "zip-files",
            f"when a {ext} file is found.",
        )
        # remove the file before testing the next one ;-)
        os.remove(filepath)


@check_id("googlefonts/vertical_metrics")
def test_check_vertical_metrics(check):
    font = TEST_FILE("akshar/Akshar[wght].ttf")
    assert_results_contain(check(font), SKIP, "already-onboarded")

    # Defeat the 'not listed_on_gfonts_api' condition.
    # linegap is not 0
    assert_results_contain(
        check(font, skip_network=True),
        FAIL,
        "bad-hhea.lineGap",
        'hhea.lineGap is "150" it should be 0',
    )
    ttFont = TTFont(font)

    # hhea sum is above 2000 -> FAIL
    ttFont["hhea"].lineGap = 0
    ttFont["OS/2"].sTypoLineGap = 0
    ttFont["hhea"].descent = -2000
    ttFont["OS/2"].sTypoDescender = -2000
    assert_results_contain(
        check(ttFont, skip_network=True),
        FAIL,
        "bad-hhea-range",
        "hhea sum is above 2000",
    )

    # hhea sum is below 1200 -> FAIL
    ttFont["hhea"].descent = 0
    ttFont["OS/2"].sTypoDescender = 0
    assert_results_contain(
        check(ttFont, skip_network=True),
        FAIL,
        "bad-hhea-range",
        "hhea sum is below 1200",
    )

    # hhea sum is above 1500 -> WARN
    ttFont["hhea"].descent = -700
    ttFont["OS/2"].sTypoDescender = -700
    assert_results_contain(
        check(ttFont, skip_network=True),
        WARN,
        "bad-hhea-range",
        "hhea sum is above 1500",
    )

    # hhea sum is in range
    ttFont["hhea"].descent = -300
    ttFont["OS/2"].sTypoDescender = -300
    assert_PASS(check(ttFont, skip_network=True))

    # reset
    def reset_metrics():
        ttFont["hhea"].ascent = 900
        ttFont["hhea"].descent = -300
        ttFont["OS/2"].sTypoAscender = 900
        ttFont["OS/2"].sTypoDescender = -300
        ttFont["hhea"].lineGap = 0
        ttFont["OS/2"].sTypoLineGap = 0
        ttFont["OS/2"].usWinAscent = 900
        ttFont["OS/2"].usWinDescent = 300

    # ascenders are negative -> FAIL
    reset_metrics()
    ttFont["OS/2"].sTypoAscender = -900
    assert_results_contain(
        check(ttFont, skip_network=True),
        FAIL,
        "typo-ascender",
        "typo ascender is negative",
    )
    reset_metrics()
    ttFont["hhea"].ascent = -900
    assert_results_contain(
        check(ttFont, skip_network=True),
        FAIL,
        "hhea-ascent",
        "hhea ascent is negative",
    )

    # descenders are positive -> FAIL
    reset_metrics()
    ttFont["OS/2"].sTypoDescender = 300
    assert_results_contain(
        check(ttFont, skip_network=True),
        FAIL,
        "typo-descender",
        "typo descender is positive",
    )
    reset_metrics()
    ttFont["hhea"].descent = 300
    assert_results_contain(
        check(ttFont, skip_network=True),
        FAIL,
        "hhea-descent",
        "hhea descent is positive",
    )

    # This can't happen in a font binary, since they're unsigned values.

    # # winascent is negative -> FAIL
    # reset_metrics()
    # ttFont["OS/2"].usWinAscent = -900
    # assert_results_contain(
    #     check(MockFont(file=font, listed_on_gfonts_api=False, ttFont=ttFont)),
    #     FAIL,
    #     "win-ascent",
    #     "OS/2.usWinAscent is negative",
    # )

    # # windescent is negative -> FAIL
    # reset_metrics()
    # ttFont["OS/2"].usWinDescent = -300
    # assert_results_contain(
    #     check(MockFont(file=font, listed_on_gfonts_api=False, ttFont=ttFont)),
    #     FAIL,
    #     "win-descent",
    #     "OS/2.usWinDescent is negative",
    # )


@check_id("googlefonts/vertical_metrics_regressions")
def test_check_vertical_metrics_regressions(check):
    def new_context():
        context = MockContext(
            testables=[Font(x) for x in cabin_fonts], config={"skip_network": False}
        )
        for testable in context.testables:
            testable.context = context
        return context

    # Cabin test family should match by default
    context = new_context()
    assert_PASS(check([TEST_FILE("cabin/Cabin-Regular.ttf")]), "with a good family...")

    # FAIL with changed vertical metric values
    local_regular = TTFont(TEST_FILE("cabin/Cabin-Regular.ttf"))
    local_regular["OS/2"].sTypoAscender = 0
    assert_results_contain(
        check([local_regular]),
        FAIL,
        "bad-typo-ascender",
        "with a family which has an incorrect typoAscender...",
    )

    local_regular["OS/2"].sTypoDescender = 0
    assert_results_contain(
        check([local_regular]),
        FAIL,
        "bad-typo-descender",
        "with a family which has an incorrect typoDescender...",
    )

    local_regular["hhea"].ascent = 0
    assert_results_contain(
        check([local_regular]),
        FAIL,
        "bad-hhea-ascender",
        "with a family which has an incorrect hhea ascender...",
    )

    local_regular["hhea"].descent = 0
    assert_results_contain(
        check([local_regular]),
        FAIL,
        "bad-hhea-descender",
        "with a family which has an incorrect hhea descender...",
    )


@check_id("googlefonts/cjk_vertical_metrics")
def test_check_cjk_vertical_metrics(check):

    # Iansui was built with our new vertical metrics schema, so should work
    ttFont = TTFont(TEST_FILE("cjk/Iansui-Regular.ttf"))
    assert_PASS(check(ttFont, skip_network=True), "for Iansui")

    # Noto Sans was built with our old vertical metrics schema, so won't
    ttFont = TTFont(cjk_font)
    results = check(ttFont, skip_network=True)
    assert_results_contain(
        results,
        FAIL,
        "bad-fselection-bit7",
        "for font where OS/2 fsSelection bit 7 is enabled",
    )

    assert_results_contain(
        results,
        FAIL,
        "bad-OS/2.sTypoAscender",
        "for font with bad OS/2.sTypoAscender",
    )

    assert_results_contain(
        results,
        FAIL,
        "bad-OS/2.sTypoDescender",
        "for font with bad OS/2.sTypoDescender",
    )


@check_id("googlefonts/cjk_vertical_metrics_regressions")
def test_check_cjk_vertical_metrics_regressions(check):
    # TODO: try to remove deepcopy usage
    from copy import deepcopy

    ttFont = TTFont(TEST_FILE("cjk/YujiBoku-Regular.ttf"))
    assert_PASS(
        check(TEST_FILE("cjk/YujiBoku-Regular.ttf")),
        "for Yuji Boku",
    )

    # Change a single metric
    ttFont2 = deepcopy(ttFont)
    ttFont2["hhea"].ascent = 0
    assert_results_contain(
        check(ttFont2),
        FAIL,
        "cjk-metric-regression",
        "hhea ascent is 0 when it should be 880",
    )

    # Change upm of font being checked
    ttFont3 = deepcopy(ttFont)
    ttFont3["head"].unitsPerEm = 2000
    assert_results_contain(
        check(ttFont3),
        FAIL,
        "cjk-metric-regression",
        "upm is 2000 and vert metrics values are not updated",
    )

    # Change upm of checked font and update vert metrics
    ttFont4 = deepcopy(ttFont)
    ttFont4["head"].unitsPerEm = 2000
    for tbl, attrib in [
        ("OS/2", "sTypoAscender"),
        ("OS/2", "sTypoDescender"),
        ("OS/2", "sTypoLineGap"),
        ("OS/2", "usWinAscent"),
        ("OS/2", "usWinDescent"),
        ("hhea", "ascent"),
        ("hhea", "descent"),
        ("hhea", "lineGap"),
    ]:
        current_val = getattr(ttFont4[tbl], attrib)
        setattr(ttFont4[tbl], attrib, current_val * 2)
    assert_PASS(
        check(ttFont4),
        "for Yuji Boku with doubled upm and doubled vert metrics",
    )


@check_id("googlefonts/fvar_instances")
def test_check_varfont_instance_coordinates(check, vf_ttFont):
    # OpenSans-Roman-VF is correct
    assert_PASS(
        check(vf_ttFont), "with a variable font which has correct instance coordinates."
    )

    from copy import copy

    vf_ttFont2 = copy(vf_ttFont)
    for instance in vf_ttFont2["fvar"].instances:
        for axis in instance.coordinates.keys():
            instance.coordinates[axis] = 0
    assert_results_contain(
        check(vf_ttFont2),
        FAIL,
        "bad-fvar-instances",
        "with a variable font which does not have correct instance coordinates.",
    )


@check_id("googlefonts/fvar_instances")
def test_check_varfont_instance_names(check, vf_ttFont):
    assert_PASS(
        check(vf_ttFont), "with a variable font which has correct instance names."
    )

    from copy import copy

    vf_ttFont2 = copy(vf_ttFont)
    for instance in vf_ttFont2["fvar"].instances:
        instance.subfamilyNameID = 300
    broken_name = "ExtraBlack Condensed 300pt"
    vf_ttFont2["name"].setName(
        broken_name,
        300,
        PlatformID.MACINTOSH,
        MacintoshEncodingID.ROMAN,
        MacintoshLanguageID.ENGLISH,
    )
    vf_ttFont2["name"].setName(
        broken_name,
        300,
        PlatformID.WINDOWS,
        WindowsEncodingID.UNICODE_BMP,
        WindowsLanguageID.ENGLISH_USA,
    )
    assert_results_contain(
        check(vf_ttFont2),
        FAIL,
        "bad-fvar-instances",
        "with a variable font which does not have correct instance names.",
    )
    # Let's see if the check is skipped if a font contains a MORF axis.
    # We allow fonts with a MORF axis to have custom fvar instances.
    from fontTools.ttLib.tables._f_v_a_r import Axis

    vf_ttFont3 = copy(vf_ttFont)
    morf_axis = Axis()
    morf_axis.axisTag = "MORF"
    vf_ttFont3["fvar"].axes.append(morf_axis)
    for instance in vf_ttFont3["fvar"].instances:
        instance.coordinates["MORF"] = 0
    assert_SKIP(check(vf_ttFont3))


@check_id("googlefonts/metadata/axes")
def test_check_gfaxisregistry_bounds(check, tmp_path):
    """Validate METADATA.pb axes values are within gf_axisregistry bounds."""

    # Our reference varfont, CabinVF, has good axes bounds:
    font = TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")
    assert_PASS(check([font, TEST_FILE("cabinvf/METADATA.pb")]))

    # The first axis declared in this family is 'wdth' (Width)
    # And the GF Axis Registry expects this axis to have a range
    # not broader than min: 25 / max: 200
    # So...
    md = Font(font).family_metadata
    md.axes[0].min_value = 20
    assert_results_contain(
        check([font, fake_mdpb(tmp_path, md)]), FAIL, "bad-axis-range"
    )

    md.axes[0].min_value = 25
    md.axes[0].max_value = 250
    assert_results_contain(
        check([font, fake_mdpb(tmp_path, md)]), FAIL, "bad-axis-range"
    )


@check_id("googlefonts/metadata/axes")
def test_check_gf_axisregistry_valid_tags(check, tmp_path):
    """Validate METADATA.pb axes tags are defined in gf_axisregistry."""

    # The axis tags in our reference varfont, CabinVF,
    # are properly defined in the registry:
    font = TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")
    assert_PASS(check([font, TEST_FILE("cabinvf/METADATA.pb")]))

    md = Font(font).family_metadata
    md.axes[0].tag = (
        "crap"  # I'm pretty sure this one wont ever be included in the registry
    )
    assert_results_contain(check([font, fake_mdpb(tmp_path, md)]), FAIL, "bad-axis-tag")


@check_id("googlefonts/axisregistry/fvar_axis_defaults")
def test_check_gf_axisregistry_fvar_axis_defaults(check):
    """Validate METADATA.pb axes tags are defined in gf_axisregistry."""

    # The default value for the axes in this reference varfont
    # are properly registered in the registry:
    ttFont = TTFont(TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"))
    assert_PASS(check(ttFont))

    # And this value surely doen't map to a fallback name in the registry
    ttFont["fvar"].axes[0].defaultValue = 123
    assert_results_contain(check(ttFont), FAIL, "not-registered")


@check_id("googlefonts/STAT/axisregistry")
def test_check_STAT_gf_axisregistry(check):
    """Validate STAT particle names and values
    match the fallback names in GFAxisRegistry."""
    from fontTools.otlLib.builder import buildStatTable

    # Our reference varfont, CabinVF,
    # has "Regular", instead of "Roman" in its 'ital' axis on the STAT table:
    ttFont = TTFont(TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"))
    assert_results_contain(check(ttFont), FAIL, "invalid-name")

    # LibreCaslonText is good though:
    ttFont = TTFont(TEST_FILE("librecaslontext/LibreCaslonText[wght].ttf"))
    assert_PASS(check(ttFont))

    # Let's break it by setting an invalid coordinate for "Bold":
    assert (
        ttFont["STAT"].table.AxisValueArray.AxisValue[3].ValueNameID
        == ttFont["name"].names[4].nameID
    )
    assert ttFont["name"].names[4].toUnicode() == "Bold"
    # instead of the expected 700
    # Note: I know it is AxisValue[3] and names[4]
    # because I inspected the font using ttx.
    ttFont["STAT"].table.AxisValueArray.AxisValue[3].Value = 800
    assert_results_contain(check(ttFont), FAIL, "bad-coordinate")

    # Let's remove all Axis Values. This will fail since we Google Fonts
    # requires them.
    ttFont["STAT"].table.AxisValueArray = None
    assert_results_contain(check(ttFont), FAIL, "missing-axis-values")

    # Let's add a MORF Axis with custom axisvalues
    stat = [
        {
            "tag": "MORF",
            "name": "Morph",
            "values": [
                {"name": "Foo", "value": 0},
                {"name": "Bar", "value": 100},
            ],
        },
        {
            "tag": "wght",
            "name": "Weight",
            "values": [
                {"name": "Regular", "value": 400, "flags": 0x2},
                {"name": "Bold", "value": 700},
            ],
        },
    ]
    buildStatTable(ttFont, stat)
    assert_PASS(check(ttFont))

    # Let's make a weight axisvalue incorrect.
    stat[1]["values"][1]["value"] = 800
    buildStatTable(ttFont, stat)
    assert_results_contain(check(ttFont), FAIL, "bad-coordinate")


@check_id("googlefonts/metadata/axes")
def test_check_metadata_consistent_axis_enumeration(check, tmp_path):
    """Validate VF axes match the ones declared on METADATA.pb."""

    # The axis tags of CabinVF,
    # are properly declared on its METADATA.pb:
    font = TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")
    assert_PASS(check([font, TEST_FILE("cabinvf/METADATA.pb")]))

    md = Font(font).family_metadata
    md.axes[1].tag = (
        "wdth"  # this effectively removes the "wght" axis while not adding an extra one
    )
    assert_results_contain(check([font, fake_mdpb(tmp_path, md)]), FAIL, "missing-axes")

    md.axes[1].tag = "ouch"  # and this is an unwanted extra axis
    assert_results_contain(check([font, fake_mdpb(tmp_path, md)]), FAIL, "extra-axes")


@check_id("googlefonts/STAT/axis_order")
def test_check_STAT_axis_order(check):
    """Check axis ordering on the STAT table."""

    fonts = [TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")]
    assert_results_contain(check(fonts), INFO, "summary")

    fonts = [TEST_FILE("merriweather/Merriweather-Regular.ttf")]
    assert_results_contain(check(fonts), SKIP, "missing-STAT")


@check_id("googlefonts/metadata/escaped_strings")
def test_check_metadata_escaped_strings(check):
    """Ensure METADATA.pb does not use escaped strings."""

    good = [
        TEST_FILE("issue_2932/good/SomeFont-Regular.ttf"),
        TEST_FILE("issue_2932/good/METADATA.pb"),
    ]
    assert_PASS(check(good))

    bad = [
        TEST_FILE("issue_2932/bad/SomeFont-Regular.ttf"),
        TEST_FILE("issue_2932/bad/METADATA.pb"),
    ]
    assert_results_contain(check(bad), FAIL, "escaped-strings")


@pytest.mark.skip("This check is ported, but we can't mock the requests.")
@check_id("googlefonts/metadata/designer_profiles")
def test_check_metadata_designer_profiles(check, requests_mock):
    """METADATA.pb: Designer is listed with the correct name on
    the Google Fonts catalog of designers?"""

    requests_mock.get(
        "https://raw.githubusercontent.com/google/fonts/master/"
        "catalog/designers/delvewithrington/info.pb",
        status_code=404,
    )
    sorkintype_info = """
        designer: "Sorkin Type"
        link: ""
        avatar {
          file_name: "sorkin_type.png"
        }
        """
    requests_mock.get(
        "https://raw.githubusercontent.com/google/fonts/master/"
        "catalog/designers/sorkintype/info.pb",
        text=sorkintype_info,
    )
    requests_mock.get(
        "https://raw.githubusercontent.com/google/fonts/master/"
        "catalog/designers/sorkintype/sorkin_type.png",
        content=b"\x89PNG\x0d\x0a\x1a\x0a",
    )

    # Delve Withrington is still not listed on the designers catalog.
    font = TEST_FILE("overpassmono/OverpassMono-Regular.ttf")
    assert_results_contain(check(font), WARN, "profile-not-found")

    # Cousine lists designers: "Multiple Designers"
    font = TEST_FILE("cousine/Cousine-Regular.ttf")
    assert_results_contain(check(font), FAIL, "multiple-designers")

    # This reference Merriweather font family lists "Sorkin Type" in its METADATA.pb
    # file. And this foundry has a good profile on the catalog.
    font = TEST_FILE("merriweather/Merriweather-Regular.ttf")
    assert_PASS(check(font))

    # TODO: FAIL, "mismatch"
    # TODO: FAIL, "link-field"
    # TODO: FAIL, "missing-avatar"
    # TODO: FAIL, "bad-avatar-filename"


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/description/family_update")
def test_check_description_family_update(check, requests_mock):
    """On a family update, the DESCRIPTION.en_us.html
    file should ideally also be updated."""

    font = TEST_FILE("abeezee/ABeeZee-Regular.ttf")
    ABEEZEE_DESC = (
        "https://github.com/google/fonts/raw/main/ofl/abeezee/DESCRIPTION.en_us.html"
    )

    desc = "<html>My fake description.</html>"
    requests_mock.get(ABEEZEE_DESC, text=desc)

    assert_results_contain(
        check(MockFont(file=font, description=desc)), WARN, "description-not-updated"
    )

    assert_PASS(check(MockFont(file=font, description=desc + "\nSomething else...")))


@check_id("googlefonts/use_typo_metrics")
def test_check_use_typo_metrics(check):
    """All non-CJK fonts checked with the googlefonts profile
    should have OS/2.fsSelection bit 7 (USE TYPO METRICS) set."""

    ttFont = TTFont(TEST_FILE("abeezee/ABeeZee-Regular.ttf"))
    fsel = ttFont["OS/2"].fsSelection

    # set bit 7
    ttFont["OS/2"].fsSelection = fsel | (1 << 7)
    assert_PASS(check(ttFont))

    # clear bit 7
    ttFont["OS/2"].fsSelection = fsel & ~(1 << 7)
    assert_results_contain(check(ttFont), FAIL, "missing-os2-fsselection-bit7")


@check_id("googlefonts/use_typo_metrics")
def test_check_use_typo_metrics_with_cjk(check):
    """All CJK fonts checked with the googlefonts profile should skip this check"""

    tt_pass_clear = TTFont(cjk_font)
    tt_pass_set = TTFont(cjk_font)

    fs_selection = 0

    # test skip with font that contains cleared bit
    tt_pass_clear["OS/2"].fsSelection = fs_selection
    # test skip with font that contains set bit
    tt_pass_set["OS/2"].fsSelection = fs_selection | (1 << 7)

    assert_SKIP(check(tt_pass_clear))
    assert_SKIP(check(tt_pass_set))


@check_id("googlefonts/meta/script_lang_tags")
def test_check_meta_script_lang_tags(check):
    """Ensure font has ScriptLangTags in the 'meta' table."""

    # This sample font from the Noto project declares
    # the script/lang tags in the meta table correctly:
    ttFont = TTFont(TEST_FILE("meta_tag/NotoSansPhagsPa-Regular-with-meta.ttf"))
    assert_results_contain(check(ttFont), INFO, "dlng-tag")
    assert_results_contain(check(ttFont), INFO, "slng-tag")

    del ttFont["meta"].data["dlng"]
    assert_results_contain(check(ttFont), FAIL, "missing-dlng-tag")

    del ttFont["meta"].data["slng"]
    assert_results_contain(check(ttFont), FAIL, "missing-slng-tag")

    del ttFont["meta"]
    assert_results_contain(check(ttFont), WARN, "lacks-meta-table")


@check_id("googlefonts/metadata/family_directory_name")
def test_check_metadata_family_directory_name(check, tmp_path):
    """Check family directory name."""

    mdpb = TEST_FILE("overpassmono/METADATA.pb")
    assert_PASS(check(mdpb))

    # Copy it to a temp directory where it won't have the correct parent name
    shutil.copy(mdpb, tmp_path / "METADATA.pb")
    assert_results_contain(
        check(str(tmp_path / "METADATA.pb")),
        FAIL,
        "bad-directory-name",
    )


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/repo/sample_image")
def test_check_repo_sample_image(check):
    """Check README.md has a sample image."""

    # That's what we'd like to see:
    # README.md including a sample image and highlighting it in the
    # upper portion of the document (no more than 10 lines from the top).
    readme = TEST_FILE("issue_2898/good/README.md")
    assert_PASS(check(readme))

    # This one is still good, but places the sample image too late in the page:
    readme = TEST_FILE("issue_2898/not-ideal-placement/README.md")
    assert_results_contain(check(readme), WARN, "not-ideal-placement")

    # Here's a README.md in a project completely lacking such sample image.
    # This will likely become a FAIL in the future:
    readme = TEST_FILE("issue_2898/no-sample/README.md")
    assert_results_contain(check(readme), WARN, "no-sample")  # FIXME: Make this a FAIL!

    # This is really broken, as it references an image that is not available:
    readme = TEST_FILE("issue_2898/image-missing/README.md")
    assert_results_contain(check(readme), FAIL, "image-missing")

    # An here a README.md that does not include any sample image,
    # while an image file can be found within the project's directory tree.
    # This image could potentially be a font sample, so we let the user know
    # that it might be the case:
    readme = TEST_FILE("issue_2898/image-not-displayed/README.md")
    assert_results_contain(check(readme), WARN, "image-not-displayed")


@check_id("googlefonts/metadata/can_render_samples")
def test_check_metadata_can_render_samples(check, tmp_path):
    """Check README.md has a sample image."""
    font = TEST_FILE("cabin/Cabin-Regular.ttf")
    mdpb = TEST_FILE("cabin/METADATA.pb")
    assert_results_contain(check([font, mdpb]), SKIP, "no-languages")

    # This will try to render using strings provided by the gflanguages package
    # Available at https://pypi.org/project/gflanguages/
    md = Font(font).family_metadata
    md.languages.append("non_Runr")  # Cabin does not support Old Nordic Runic
    assert_results_contain(check([font, fake_mdpb(tmp_path, md)]), FAIL, "sample-text")

    # TODO: expand the check to also validate rendering of
    #       text provided explicitely on the sample_text field of METADATA.pb


@check_id("googlefonts/description/urls")
def test_check_description_urls(check, tmp_path):
    """URLs on DESCRIPTION file must not display http(s) prefix."""

    desc = TEST_FILE("librecaslontext/DESCRIPTION.en_us.html")
    assert_PASS(check(desc))

    desc = TEST_FILE("cabinvfbeta/DESCRIPTION.en_us.html")
    assert_results_contain(check(desc), FAIL, "prefix-found")

    p = tmp_path / "DESCRIPTION.en_us.html"
    good_desc = open(desc).read()
    bad_desc = good_desc.replace(">https://", ">")
    p.write_text(bad_desc, encoding="utf-8")
    assert_PASS(check(str(p)))

    bad_desc = bad_desc.replace(">github.com/impallari/Cabin<", "><")
    p.write_text(bad_desc, encoding="utf-8")
    assert_results_contain(check(str(p)), FAIL, "empty-link-text")


@pytest.mark.skip("Check not ported yet.")
@check_id("googlefonts/metadata/unsupported_subsets")
def test_check_metadata_unsupported_subsets(check):
    """Check for METADATA subsets with zero support."""

    font = TEST_FILE("librecaslontext/LibreCaslonText[wght].ttf")
    assert_PASS(check(font))

    md = Font(font).family_metadata
    md.subsets.extend(["foo"])
    assert_results_contain(
        check(MockFont(file=font, family_metadata=md)), FAIL, "unknown-subset"
    )

    del md.subsets[:]
    md.subsets.extend(["cyrillic"])
    assert_results_contain(
        check(MockFont(file=font, family_metadata=md)), FAIL, "unsupported-subset"
    )


@check_id("googlefonts/metadata/validate")
def test_check_metadata_category_hints(check, tmp_path):
    """Check if category on METADATA.pb matches
    what can be inferred from the family name."""

    font = TEST_FILE("cabinvf/Cabin[wdth,wght].ttf")
    assert_PASS(
        check(TEST_FILE("cabinvf/METADATA.pb")),
        "with a familyname without any of the keyword hints...",
    )

    md = Font(font).family_metadata
    md.name = "Seaweed Script"
    md.category[:] = ["DISPLAY"]
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        WARN,
        "inferred-category",
        f'with a bad category "{md.category}" for familyname "{md.name}"...',
    )

    md.name = "Red Hat Display"
    md.category[:] = ["SANS_SERIF"]
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        WARN,
        "inferred-category",
        f'with a bad category "{md.category}" for familyname "{md.name}"...',
    )

    md.name = "Seaweed Script"
    md.category[:] = ["HANDWRITING"]
    results = check(fake_mdpb(tmp_path, md))
    assert not any(
        [result.message.code == "inferred-category" for result in results]
    ), f'with a good category "{md.category}" for familyname "{md.name}"...'

    md.name = "Red Hat Display"
    md.category[:] = ["DISPLAY"]
    assert not any(
        [result.message.code == "inferred-category" for result in results]
    ), f'with a good category "{md.category}" for familyname "{md.name}"...'


@pytest.mark.parametrize(
    """fp,mod,result""",
    [
        # font includes condensed fvar instances so it should fail
        (TEST_FILE("cabinvfbeta/CabinVFBeta.ttf"), [], FAIL),
        # official fonts have been fixed so this should pass
        (TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"), [], PASS),
        (TEST_FILE("cabinvf/Cabin-Italic[wdth,wght].ttf"), [], PASS),
        # lets inject an instance which is not a multiple of 100
        (TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"), [("Book", 450)], FAIL),
    ],
)
@check_id("googlefonts/fvar_instances")
def test_check_fvar_instances(check, fp, mod, result):
    """Check font fvar instances are correct"""
    from fontTools.ttLib.tables._f_v_a_r import NamedInstance

    ttFont = TTFont(fp)
    expected = expected_font_names(ttFont, [])
    if mod:
        for name, wght_val in mod:
            inst = NamedInstance()
            inst.subfamilyNameID = ttFont["name"].addName(name)
            inst.coordinates = {"wght": wght_val, "wdth": 100}
            ttFont["fvar"].instances.append(inst)

    if result == PASS:
        assert_PASS(check(ttFont), "with a good font")
    elif result == FAIL:
        assert_results_contain(
            check(ttFont),
            FAIL,
            "bad-fvar-instances",
            "with a bad font",
        )


@pytest.mark.parametrize(
    """fp,mod,result,code""",
    [
        (TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"), [], PASS, None),
        # Drop weight has so this should fail since gf version has it
        (
            TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"),
            ["wght", None, None],
            FAIL,
            "missing-axes",
        ),
        # Change ranges of weight axis to 500-600, this should fail since gf version has 400-700
        (
            TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"),
            ["wght", 500, None],
            FAIL,
            "axis-min-out-of-range",
        ),
        (
            TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"),
            ["wght", None, 600],
            FAIL,
            "axis-max-out-of-range",
        ),
    ],
)
@check_id("googlefonts/axes_match")
def test_check_axes_match(check, fp, mod, result, code):
    """Check if the axes match between the font and the Google Fonts version."""

    ttFont = TTFont(fp)
    mdpb = TEST_FILE("cabinvf/METADATA.pb")
    if mod:
        name, min_val, max_val = mod
        if not min_val and not max_val:
            ttFont["fvar"].axes = [a for a in ttFont["fvar"].axes if a.axisTag != name]
        else:
            axis = next(a for a in ttFont["fvar"].axes if a.axisTag == name)
            axis.minValue = min_val or axis.minValue
            axis.maxValue = max_val or axis.maxValue

    if result == PASS:
        assert_PASS(check([ttFont, mdpb]), "with a good font")
    elif result == FAIL:
        assert_results_contain(
            check([ttFont, mdpb]),
            FAIL,
            code,
            "with a bad font",
        )


@pytest.mark.parametrize(
    """fps,new_stat,result""",
    [
        # Fail (we didn't really know what we were doing at this stage)
        (
            [
                TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"),
                TEST_FILE("cabinvf/Cabin-Italic[wdth,wght].ttf"),
            ],
            [],
            FAIL,
        ),
        # Fix previous test for Cabin[wdth,wght].ttf
        (
            [
                TEST_FILE("cabinvf/Cabin[wdth,wght].ttf"),
                TEST_FILE("cabinvf/Cabin-Italic[wdth,wght].ttf"),
            ],
            # STAT for Cabin[wdth,wght].ttf
            [
                {
                    "name": "Weight",
                    "tag": "wght",
                    "values": [
                        {
                            "value": 400,
                            "name": "Regular",
                            "linkedValue": 700.0,
                            "flags": 0x2,
                        },
                        {"value": 500, "name": "Medium"},
                        {"value": 600, "name": "SemiBold"},
                        {"value": 700, "name": "Bold"},
                    ],
                },
                {
                    "name": "Width",
                    "tag": "wdth",
                    "values": [
                        {"value": 75, "name": "Condensed"},
                        {"value": 87.5, "name": "SemiCondensed"},
                        {"value": 100, "name": "Normal", "flags": 0x2},
                    ],
                },
                {
                    "name": "Italic",
                    "tag": "ital",
                    "values": [
                        {
                            "value": 0.0,
                            "name": "Normal",
                            "linkedValue": 1.0,
                            "flags": 0x2,
                        }
                    ],
                },
            ],
            PASS,
        ),
    ],
)
@check_id("googlefonts/STAT/compulsory_axis_values")
def test_check_STAT(check, fps, new_stat, result):
    """Check STAT table Axis Values are correct"""
    # more comprehensive checks are available in the axisregistry:
    # https://github.com/googlefonts/axisregistry/blob/main/tests/test_names.py#L442
    # this check merely exists to check that everything is hooked up correctly
    from fontTools.otlLib.builder import buildStatTable

    ttFonts = [TTFont(f) for f in fps]
    ttFont = ttFonts[0]
    if new_stat:
        buildStatTable(ttFont, new_stat)

    if result == PASS:
        assert_PASS(
            check(ttFont),
            "with a good font",
        )
    elif result == FAIL:
        assert_results_contain(
            check(ttFont),
            FAIL,
            "bad-axis-values",
            "with a bad font",
        )


@check_id("googlefonts/description/has_article")
def test_check_description_has_article(check):
    """Noto fonts must have an ARTICLE.en_us.html file, others with an
    article should have an empty DESCRIPTION"""

    files = TEST_FILE("notosanskhudawadi/**/*.*")
    assert_PASS(check(list(glob.glob(files, recursive=True))), "with a good font")

    files = TEST_FILE("noto_sans_tamil_supplement/**/*.*")
    assert_results_contain(
        check(list(glob.glob(files, recursive=True))),
        FAIL,
        "missing-article",
        "with a bad font",
    )

    files = TEST_FILE("tirodevanagarihindi/**/*.*")
    assert_results_contain(
        check(list(glob.glob(files, recursive=True))),
        FAIL,
        "description-and-article",
        "with a font with description and article",
    )


@check_id("googlefonts/description/has_unsupported_elements")
def test_check_description_has_unsupported_elements(check):
    """Check the description doesn't contain unsupported html elements"""

    font = TEST_FILE("librecaslontext/DESCRIPTION.en_us.html")
    assert_PASS(check(font))

    font = TEST_FILE("unsupported_html_elements/DESCRIPTION.en_us.html")
    results = check(font)
    assert_results_contain(results, ERROR, "unsupported-elements", "with a bad font")
    font = TEST_FILE("unsupported_html_elements/article/ARTICLE.en_us.html")
    results = check(font)
    assert_results_contain(results, ERROR, "video-tag-needs-src", "with a bad font")


@check_id("googlefonts/metadata/unreachable_subsetting")
def test_check_metadata_unreachable_subsetting(check):
    """Check for codepoints not covered by METADATA subsetting"""

    font = TEST_FILE("notosanskhudawadi/NotoSansKhudawadi-Regular.ttf")
    assert_PASS(check(font), "with a good font")

    font = TEST_FILE("cabin/Cabin-Regular.ttf")
    mdpb = TEST_FILE("cabin/METADATA.pb")
    assert_results_contain(
        check([font, mdpb]), WARN, "unreachable-subsetting", "with a bad font"
    )

    font = TEST_FILE("playfair/Playfair-Italic[opsz,wdth,wght].ttf")
    assert_results_contain(
        check(font),
        WARN,
        "unreachable-subsetting",
        "with a bad font and no METADATA.pb",
    )


@check_id("googlefonts/glyphsets/shape_languages")
def test_check_shape_languages(check):
    """Shapes languages in all GF glyphsets."""

    test_font = TTFont(TEST_FILE("BadGrades/BadGrades-VF.ttf"))
    assert_results_contain(check(test_font), FAIL, "no-glyphset-supported")

    test_font = TTFont(TEST_FILE("annie/AnnieUseYourTelescope-Regular.ttf"))
    assert_results_contain(check(test_font), FAIL, "failed-language-shaping")


@check_id("googlefonts/metadata/validate")
def test_check_metadata_minisite_url(check, tmp_path):
    """Validate minisite_url field"""

    MD_FILE = TEST_FILE("cabinvf/METADATA.pb")
    md = read_mdpb(MD_FILE)
    assert_results_contain(check(MD_FILE), INFO, "lacks-minisite-url")

    md.minisite_url = "a_good_one.com"
    assert_PASS(check(fake_mdpb(tmp_path, md)), "with a good one")

    md.minisite_url = "some_url/"
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        FAIL,
        "trailing-clutter",
        "with a minisite_url with unnecessary trailing forward-slash",
    )

    md.minisite_url = "some_url/index.htm"
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        FAIL,
        "trailing-clutter",
        "with a minisite_url with unnecessary trailing /index.htm",
    )

    md.minisite_url = "some_url/index.html"
    assert_results_contain(
        check(fake_mdpb(tmp_path, md)),
        FAIL,
        "trailing-clutter",
        "with a minisite_url with unnecessary trailing /index.html",
    )


@check_id("googlefonts/render_own_name")
def test_check_render_own_name(check):
    """Check family directory name."""
    ttFont = TEST_FILE("overpassmono/OverpassMono-Regular.ttf")
    assert_PASS(check(ttFont))

    ttFont = TEST_FILE("noto_sans_tamil_supplement/NotoSansTamilSupplement-Regular.ttf")
    assert_results_contain(check(ttFont), FAIL, "render-own-name")


@check_id("googlefonts/gasp")
def test_check_gasp(check):
    """Check TFF has gasp table."""
    ttFont = TTFont(TEST_FILE("montserrat/Montserrat-Black.ttf"))
    assert_PASS(check(ttFont))

    cffFont = TTFont(TEST_FILE("source-sans-pro/OTF/SourceSansPro-Black.otf"))
    msg = assert_results_contain(check(cffFont), SKIP, "not-ttf")
