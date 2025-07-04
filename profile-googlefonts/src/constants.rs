use std::sync::LazyLock;

use regex::Regex;

/// The Open Font License body text, used in the `googlefonts/license/OFL_body_text` check.
pub const OFL_BODY_TEXT: &str =
    "\nThis Font Software is licensed under the SIL Open Font License, Version 1.1.\n\
This license is copied below, and is also available with a FAQ at:\n\
https://openfontlicense.org\n\
\n\
\n\
-----------------------------------------------------------\n\
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n\
-----------------------------------------------------------\n\
\n\
PREAMBLE\n\
The goals of the Open Font License (OFL) are to stimulate worldwide\n\
development of collaborative font projects, to support the font creation\n\
efforts of academic and linguistic communities, and to provide a free and\n\
open framework in which fonts may be shared and improved in partnership\n\
with others.\n\
\n\
The OFL allows the licensed fonts to be used, studied, modified and\n\
redistributed freely as long as they are not sold by themselves. The\n\
fonts, including any derivative works, can be bundled, embedded,\n\
redistributed and/or sold with any software provided that any reserved\n\
names are not used by derivative works. The fonts and derivatives,\n\
however, cannot be released under any other type of license. The\n\
requirement for fonts to remain under this license does not apply\n\
to any document created using the fonts or their derivatives.\n\
\n\
DEFINITIONS\n\
\"Font Software\" refers to the set of files released by the Copyright\n\
Holder(s) under this license and clearly marked as such. This may\n\
include source files, build scripts and documentation.\n\
\n\
\"Reserved Font Name\" refers to any names specified as such after the\n\
copyright statement(s).\n\
\n\
\"Original Version\" refers to the collection of Font Software components as\n\
distributed by the Copyright Holder(s).\n\
\n\
\"Modified Version\" refers to any derivative made by adding to, deleting,\n\
or substituting -- in part or in whole -- any of the components of the\n\
Original Version, by changing formats or by porting the Font Software to a\n\
new environment.\n\
\n\
\"Author\" refers to any designer, engineer, programmer, technical\n\
writer or other person who contributed to the Font Software.\n\
\n\
PERMISSION & CONDITIONS\n\
Permission is hereby granted, free of charge, to any person obtaining\n\
a copy of the Font Software, to use, study, copy, merge, embed, modify,\n\
redistribute, and sell modified and unmodified copies of the Font\n\
Software, subject to the following conditions:\n\
\n\
1) Neither the Font Software nor any of its individual components,\n\
in Original or Modified Versions, may be sold by itself.\n\
\n\
2) Original or Modified Versions of the Font Software may be bundled,\n\
redistributed and/or sold with any software, provided that each copy\n\
contains the above copyright notice and this license. These can be\n\
included either as stand-alone text files, human-readable headers or\n\
in the appropriate machine-readable metadata fields within text or\n\
binary files as long as those fields can be easily viewed by the user.\n\
\n\
3) No Modified Version of the Font Software may use the Reserved Font\n\
Name(s) unless explicit written permission is granted by the corresponding\n\
Copyright Holder. This restriction only applies to the primary font name as\n\
presented to the users.\n\
\n\
4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font\n\
Software shall not be used to promote, endorse or advertise any\n\
Modified Version, except to acknowledge the contribution(s) of the\n\
Copyright Holder(s) and the Author(s) or with their explicit written\n\
permission.\n\
\n\
5) The Font Software, modified or unmodified, in part or in whole,\n\
must be distributed entirely under this license, and must not be\n\
distributed under any other license. The requirement for fonts to\n\
remain under this license does not apply to any document created\n\
using the Font Software.\n\
\n\
TERMINATION\n\
This license becomes null and void if any of the above conditions are\n\
not met.\n\
\n\
DISCLAIMER\n\
THE FONT SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND,\n\
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF\n\
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT\n\
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE\n\
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,\n\
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL\n\
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING\n\
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM\n\
OTHER DEALINGS IN THE FONT SOFTWARE.";

/// The most recent release of ttfautohint. Keep me up to date!
pub const LATEST_TTFAUTOHINT_VERSION: &str = "1.8.4";

// example string:
// 'Version 1.000; ttfautohint (v0.93) -l 8 -r 50 -G 200 -x 14 -w "G"
#[allow(clippy::unwrap_used)]
pub(crate) static TTFAUTOHINT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"ttfautohint \(v(.*)\) ([^;]*)").unwrap());

pub(crate) static EXPECTED_COPYRIGHT_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    #[allow(clippy::unwrap_used)]
        Regex::new(
            r#"copyright \d{4}(-\d{4})?(,\s*\d{4}(-\d{4})?)*,? (the .* project authors \([^\@]*\)|google llc. all rights reserved)"#,
        ).unwrap()
});
