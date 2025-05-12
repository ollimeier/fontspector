use fontspector_checkapi::{prelude::*, FileTypeConvert, TestFont};
use fontations::skrifa::string::StringId;

fn is_manually_hinted(font: &TestFont) -> bool {
    let is_hinted = font.has_table(b"fpgm");
    let is_vtt_hinted = font.has_table(b"TSI5");
    if !is_hinted {
        return false;
    }
    if is_vtt_hinted {
        return true;
    }
    !font
        .get_name_entry_strings(StringId::VERSION_STRING)
        .any(|name| name.contains("ttfautohint"))
}

#[check(
    id = "googlefonts/repo/vf_has_static_fonts",
    rationale = "
        Variable font family directories kept in the google/fonts git repo may include
        a static/ subdir containing static fonts, if manual hinting is used on
        these fonts. Otherwise, the directory should be removed.
    ",
    proposal = "https://github.com/fonttools/fontbakery/issues/2654",
    title = "A static fonts directory, if present, must contain manually hinted fonts",
    implementation = "all"
)]
fn vf_has_static_fonts(c: &TestableCollection, _context: &Context) -> CheckFnResult {
    let statics = c
        .iter()
        .filter(|t| t.filename.components().any(|c| c.as_os_str() == "static"))
        .collect::<Vec<_>>();
    if !statics.is_empty()
        && statics
            .iter()
            .filter_map(|t| TTF.from_testable(t))
            .any(|t| !is_manually_hinted(&t))
    {
        return Ok(Status::just_one_warn("not-manually-hinted",
            "There is a 'static' dir but it contains fonts which are not manually hinted. Delete the directory."));
    }
    Ok(Status::just_one_pass())
}
