use fontspector_checkapi::{prelude::*, skip, testfont, FileTypeConvert};
use fontations::skrifa::raw::{tables::os2::SelectionFlags, TableProvider};

use crate::network_conditions::is_listed_on_google_fonts;

#[check(
    id = "googlefonts/cjk_vertical_metrics",
    rationale = "
        
        CJK fonts have different vertical metrics when compared to Latin fonts.
        We follow the schema developed by dr Ken Lunde for Source Han Sans and
        the Noto CJK fonts.

        Our documentation includes further information:
        https://github.com/googlefonts/gf-docs/tree/main/Spec#cjk-vertical-metrics
    
    ",
    proposal = "https://github.com/fonttools/fontbakery/pull/2797",
    title = "Check font follows the Google Fonts CJK vertical metric schema"
)]
fn cjk_vertical_metrics(t: &Testable, context: &Context) -> CheckFnResult {
    let f = testfont!(t);
    let mut problems = vec![];
    let family_name = f
        .best_familyname()
        .ok_or(CheckError::Error("Font lacks a family name".to_string()))?;
    if !context.skip_network {
        skip!(
            is_listed_on_google_fonts(&family_name, context).map_err(CheckError::Error)?,
            "already-onboarded",
            "Not checking vertical metrics for fonts already onboarded to Google Fonts"
        );
    }
    skip!(
        !f.is_cjk_font(Some(context)),
        "non-cjk",
        "Not checking non-CJK fonts"
    );
    let metrics = f.vertical_metrics()?;
    if f.font()
        .os2()?
        .fs_selection()
        .contains(SelectionFlags::USE_TYPO_METRICS)
    {
        problems.push(Status::fail(
            "bad-fselection-bit7",
            "OS/2 fsSelection bit 7 must be disabled",
        ));
    }

    if metrics.os2_typo_ascender != (metrics.upm as f32 * 0.88).round() as i16 {
        problems.push(Status::fail(
            "bad-OS/2.sTypoAscender",
            &format!(
                "OS/2.sTypoAscender is {}; it should be {}",
                metrics.os2_typo_ascender,
                (metrics.upm as f32 * 0.88)
            ),
        ));
    }

    if metrics.os2_typo_descender != (metrics.upm as f32 * -0.12).round() as i16 {
        problems.push(Status::fail(
            "bad-OS/2.sTypoDescender",
            &format!(
                "OS/2.sTypoDescender is {}; it should be {}",
                metrics.os2_typo_descender,
                (metrics.upm as f32 * -0.12)
            ),
        ));
    }

    if metrics.os2_typo_linegap != 0 {
        problems.push(Status::fail(
            "bad-OS/2.sTypoLineGap",
            &format!(
                "OS/2.sTypoLineGap is {}; it should be 0",
                metrics.os2_typo_linegap
            ),
        ));
    }

    if metrics.hhea_linegap != 0 {
        problems.push(Status::fail(
            "bad-hhea.lineGap",
            &format!("hhea.lineGap is {}; it should be 0", metrics.hhea_linegap),
        ));
    }

    if metrics.hhea_ascent != metrics.os2_win_ascent as i16 {
        problems.push(Status::fail(
            "ascent-mismatch",
            "hhea.ascent must match OS/2.usWinAscent",
        ));
    }

    if metrics.hhea_descent.unsigned_abs() != metrics.os2_win_descent {
        problems.push(Status::fail(
            "descent-mismatch",
            "hhea.descent must match absolute value of OS/2.usWinDescent",
        ));
    }

    // Convert them all to f32 when adding to avoid potential overflow
    let hhea_sum = (metrics.hhea_ascent as f32
        + metrics.hhea_descent.abs() as f32
        + metrics.hhea_linegap as f32)
        / metrics.upm as f32;
    if !(1.1..=1.5).contains(&hhea_sum) {
        problems.push(Status::warn(
            "bad-hhea-range",
            &format!(
                "We recommend the absolute sum of the hhea metrics should be between 1.1-1.4x of the font's upm. This font has {}x",
                hhea_sum
            ),
        ));
    }
    return_result(problems)
}
