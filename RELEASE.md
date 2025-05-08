# Release management

We're still working this out, but...

* Install `cargo-smart-release`
* Release dependencies of fontspector with:

    cargo smart-release fontspector-checkhelper fontspector-profile-opentype fontspector-profile-googlefonts fontspector-profile-universal --no-changelog-preview --allow-fully-generated-changelogs --allow-empty-release-message --execute --update-crates-index --no-changelog-github-release

* Manually bump the fontspector-cli version (since there are unlikely to be code changes)
* Run `cargo smart-release fontspector --execute`; add release message; run it again.
