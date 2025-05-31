#![deny(clippy::unwrap_used, clippy::expect_used)]
mod checks;

use fontspector_checkapi::{ProfileBuilder, Registry};

pub struct Iso15009;
impl fontspector_checkapi::Plugin for Iso15009 {
    fn register(&self, cr: &mut Registry) -> Result<(), String> {
        let builder = ProfileBuilder::new()
            .add_section("iso15009 Fonts Checks")
            .add_and_register_check(checks::iso15009::intercharacter_spacing)
            .add_and_register_check(checks::iso15009::interline_spacing)
            .add_and_register_check(checks::iso15009::interword_spacing)
            .add_and_register_check(checks::iso15009::proportions)
            .add_and_register_check(checks::iso15009::stem_width);
        builder.build("iso15009", cr)
    }
}
