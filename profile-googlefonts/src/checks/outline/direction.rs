use super::name_and_bezglyph;
use fontspector_checkapi::{prelude::*, testfont, FileTypeConvert};
use kurbo::{Rect, Shape};

// Although this check is per-glyph, the problem of contours being oriented
// the wrong way by the compiler tends to affect all glyphs in a font.
// It's generally caused by something like passing --keep-direction in
// fontmake when doing things with cubic sources.
#[check(
    id = "outline_direction",
    rationale = "
        
        In TrueType fonts, the outermost contour of a glyph should be oriented
        clockwise, while the inner contours should be oriented counter-clockwise.
        Getting the path direction wrong can lead to rendering issues in some
        software.
    
    ",
    proposal = "https://github.com/fonttools/fontbakery/issues/2056",
    title = "Check the direction of the outermost contour in each glyph"
)]
fn direction(t: &Testable, context: &Context) -> CheckFnResult {
    let f = testfont!(t);
    let mut problems = vec![];
    let mut all_warnings = vec![];
    for (name, result) in name_and_bezglyph(&f) {
        let pen = result?;
        let bounds: Vec<Rect> = pen.iter().map(|path| path.bounding_box()).collect();
        let mut is_within = vec![vec![]; bounds.len()];
        for (i, my_bounds) in bounds.iter().enumerate() {
            if my_bounds.is_zero_area() {
                all_warnings.push(format!(
                    "{name} has a path with no bounds (probably a single point)"
                ));
                continue;
            }
            for (j, their_bounds) in bounds.iter().enumerate() {
                if i == j {
                    continue;
                }
                if their_bounds.is_zero_area() {
                    continue;
                }
                if my_bounds.contains_rect(*their_bounds) {
                    #[allow(clippy::indexing_slicing)]
                    // is_within is initialized with the same length as bounds
                    is_within[j].push(i);
                }
            }
        }
        for (i, path) in pen.iter().enumerate() {
            #[allow(clippy::indexing_slicing)]
            // is_within is initialized with the same length as bounds
            if is_within[i].is_empty() && path.area() > 0.0 {
                all_warnings.push(format!("{name} has a counter-clockwise outer contour"));
            }
        }
    }
    if !all_warnings.is_empty() {
        problems.push(Status::warn(
            "ccw-outer-contour",
            &format!(
                "The following glyphs have a counter-clockwise outer contour:\n\n{}",
                bullet_list(context, all_warnings)
            ),
        ));
    }

    return_result(problems)
}
