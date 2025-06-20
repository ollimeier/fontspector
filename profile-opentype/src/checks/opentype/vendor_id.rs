use fontations::skrifa::raw::TableProvider;
use fontspector_checkapi::{prelude::*, testfont, FileTypeConvert};

#[check(
    id = "opentype/vendor_id",
    rationale = "
        When a font project's Vendor ID is specified explicitly on FontBakery's
        configuration file, all binaries must have a matching vendor identifier
        value in the OS/2 table.
    ",
    proposal = "https://github.com/fonttools/fontbakery/pull/3941",
    title = "Check OS/2 achVendID against configuration"
)]
fn vendor_id(f: &Testable, context: &Context) -> CheckFnResult {
    let font = testfont!(f);
    let config = context.local_config("opentype/vendor_id");
    let expected_vendor_id = config.get("vendor_id")
        .ok_or(FontspectorError::skip(
            "no-vendor-id",
            "Add the `vendor_id` key to a `fontspector.toml` file on your font project directory to enable this check.\nYou'll also need to use the `--configuration` flag when invoking fontspector",
        ))?
        .as_str()
        .ok_or(FontspectorError::skip(
            "invalid-vendor-id",
            "The `vendor_id` key in the configuration file must be a string.",
        ))?;
    let os2_vendor_id = font.font().os2()?.ach_vend_id().to_string();
    if os2_vendor_id.as_str() == expected_vendor_id {
        Ok(Status::just_one_pass())
    } else {
        Ok(Status::just_one_fail(
            "bad-vendor-id",
            &format!(
                "OS/2 achVendID value '{}' does not match configuration value '{}'",
                os2_vendor_id, expected_vendor_id
            ),
        ))
    }
}
