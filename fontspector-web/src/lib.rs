use std::collections::HashMap;

use js_sys::{Reflect, Uint8Array};
use wasm_bindgen::prelude::*;
extern crate console_error_panic_hook;
use fontspector_checkapi::{
    Check, CheckResult, Context, Plugin, Profile, Registry, Testable, TestableCollection,
    TestableType,
};
use profile_adobe::Adobe;
use profile_googlefonts::GoogleFonts;
use profile_iso15008::Iso15008;
use profile_iso15009::Iso15009;
use profile_microsoft::Microsoft;
use profile_opentype::OpenType;
use profile_universal::Universal;

#[wasm_bindgen]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

#[wasm_bindgen]
pub fn check_fonts(fonts: &JsValue, profile: &str) -> Result<String, JsValue> {
    console_error_panic_hook::set_once();

    let mut registry = Registry::new();
    OpenType
        .register(&mut registry)
        .expect("Couldn't register opentype profile, fontspector bug");
    Universal
        .register(&mut registry)
        .expect("Couldn't register universal profile, fontspector bug");
    GoogleFonts
        .register(&mut registry)
        .expect("Couldn't register googlefonts profile, fontspector bug");
    Iso15008
        .register(&mut registry)
        .expect("Couldn't register iso15008 profile, fontspector bug");
    Iso15009
        .register(&mut registry)
        .expect("Couldn't register iso15009 profile, fontspector bug");
    Adobe
        .register(&mut registry)
        .expect("Couldn't register Adobe profile, fontspector bug");
    Microsoft
        .register(&mut registry)
        .expect("Couldn't register Microsoft profile, fontspector bug");

    for (name, toml) in [
        ("fontbureau", include_str!("../../profiles/fontbureau.toml")),
        ("fontwerk", include_str!("../../profiles/fontwerk.toml")),
    ] {
        let profile = Profile::from_toml(toml).expect("Couldn't load profile, fontspector bug");
        registry
            .register_profile(name, profile)
            .expect("Couldn't register profile, fontspector bug");
    }

    let testables: Vec<Testable> = Reflect::own_keys(fonts)?
        .into_iter()
        .map(|filename| {
            let file: JsValue = Reflect::get(fonts, &filename).unwrap();
            let contents = Uint8Array::new(&file).to_vec();

            Testable {
                filename: filename.as_string().unwrap().into(),
                source: None,
                contents,
            }
        })
        .collect();
    let collection = TestableCollection::from_testables(testables, None);

    let profile = registry
        .get_profile(profile)
        .ok_or_else(|| format!("Could not find profile {:?}", profile))?;
    let context = Context {
        skip_network: true,
        network_timeout: None,
        configuration: HashMap::new(),
        check_metadata: serde_json::Value::Null,
        full_lists: false,
        cache: Default::default(),
        overrides: vec![],
    };
    let all_testables: Vec<TestableType> = collection.collection_and_files().collect();

    let checkorder: Vec<(String, &TestableType, &Check, Context)> = profile.check_order(
        &[],
        &[],
        &registry,
        context,
        &HashMap::new(),
        &all_testables,
    );

    let results: Vec<CheckResult> = checkorder
        .iter()
        .map(|(sectionname, testable, check, context)| {
            (
                testable,
                check,
                check.run(testable, context, Some(sectionname)),
            )
        })
        .flat_map(|(_, _, result)| result)
        .collect();
    serde_json::to_string(&results).map_err(|e| e.to_string().into())
}
