//! `render_peek` — the Rust port of `peek.py`'s single `peek(entity, depth)`
//! stat-plate renderer (S7 design canon, plan Task 14).
//!
//! S7: *"A single `peek(entity, depth)` renderer producing a compact stat
//! plate implements, at different sizes: Vic3 nested tooltips, Obsidian
//! hover preview, page transclusion, and watchlist rows."* [`render_peek`]
//! is that one renderer, painting directly into a ratatui [`Frame`] rather
//! than returning a `rich` renderable (the Python original's own return
//! type) — this crate has no `rich` dependency, and painting into the frame
//! is this client's native idiom.
//!
//! **Depth is a size selector**, matching the Python original's four fixed
//! verbosity tiers one-to-one:
//!
//! | `depth` | Context                             | Stat rows shown |
//! |---------|--------------------------------------|------------------|
//! | `0`     | watchlist row                         | at most 1        |
//! | `1`     | Obsidian-style hover preview           | at most 3        |
//! | `2`     | Vic3-style nested tooltip               | at most 6        |
//! | `3`     | page transclusion                       | every present field |
//!
//! **Depth clamps rather than errors** — a deliberate deviation from
//! `peek.py`, which raises `ValueError` outside `[0, MAX_DEPTH]`. This
//! function has no `Result` in its signature (it paints a frame; there is
//! no caller-visible failure channel to report through) and production
//! rendering code never panics, so an out-of-range `depth` clamps to
//! [`MAX_DEPTH`] instead of raising — the honest-absence discipline
//! (Constitution III.11) applied to a caller bug rather than to missing
//! data.
//!
//! **JSON `null` → honest absence**, never a fabricated placeholder: the
//! host returns the literal string `"null"` from `subject_view_json` when
//! it cannot resolve a subject (`host.rs`'s own doc comment); this module
//! renders that as a loud, explicit "no view available" plate rather than
//! an empty one.
//!
//! **Field walk order is alphabetical, not declaration order** — another
//! deliberate deviation from `peek.py`, which walks `model_fields`
//! insertion order. `serde_json::Value::Object` is backed by a `BTreeMap`
//! (this crate's `serde_json` has no `preserve_order` feature — house style
//! prefers `BTreeMap`/`BTreeSet` wherever iteration order reaches output,
//! `CLAUDE.md`'s Power-of-10 gloss), so key order is alphabetical and fully
//! deterministic; it will differ from the Python original's field order for
//! any view with more than one field. This is a determinism-preserving
//! trade, not a data-fidelity gap — every present field still renders,
//! just in a different (still deterministic) order.

use ratatui::layout::Rect;
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};
use ratatui::Frame;
use serde_json::Value;

/// The hard upper bound on `depth` (mirrors `peek.py::MAX_DEPTH`).
pub const MAX_DEPTH: u8 = 3;

/// Stat-row cap per depth `0..=MAX_DEPTH`; `None` means uncapped — indexed
/// directly by depth (mirrors `peek.py::_FIELD_CAP_BY_DEPTH`).
const FIELD_CAP_BY_DEPTH: [Option<usize>; (MAX_DEPTH as usize) + 1] =
    [Some(1), Some(3), Some(6), None];

/// Identity-field suffixes tried against a view's own `kind`, in order
/// (mirrors `peek.py::_IDENTITY_SUFFIXES` — `CountyView.county_fips` is
/// `"county" + "_fips"`).
const IDENTITY_SUFFIXES: [&str; 2] = ["_fips", "_id"];

/// Fields every view carries by the keel convention, folded into the header
/// rather than walked as stat rows (mirrors `peek.py::_UNIVERSAL_FIELDS`).
const UNIVERSAL_FIELDS: [&str; 2] = ["kind", "verified_tick"];

/// Header used when `subject_view_json` is JSON `null` (host-level honest
/// absence — no `kind` is available to build a real header from).
const NO_VIEW_HEADER: &str = "(no view available)";

const CRIMSON: Color = Color::Rgb(220, 20, 60);
const GOLD: Color = Color::Rgb(255, 215, 0);
const BONE: Color = Color::Rgb(232, 232, 232);
const DIM: Color = Color::Rgb(64, 64, 64);

/// Find `view`'s own identity field name by the `{kind}_fips`/`{kind}_id`
/// convention, or `None` if `view` has no string `kind` or no field
/// matches either suffix (mirrors `peek.py::_identity_field_name`).
fn identity_field_name(view: &Value) -> Option<String> {
    let kind = view.get("kind")?.as_str()?;
    let object = view.as_object()?;
    IDENTITY_SUFFIXES
        .iter()
        .map(|suffix| format!("{kind}{suffix}"))
        .find(|candidate| object.contains_key(candidate))
}

/// One JSON leaf value rendered for display: a JSON float formats to six
/// decimals (mirroring `peek.py::_format_scalar`'s float branch); a JSON
/// integer, string, or bool formats as its own natural text. Booleans
/// render lowercase (`"true"`/`"false"`) rather than the Python original's
/// `str(True)` == `"True"` — a JSON-vs-Python-native deviation, documented
/// here since no known `ProjectionRecord` field is boolean today.
fn format_scalar(value: &Value) -> String {
    match value {
        Value::String(s) => s.clone(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => {
            if n.is_i64() || n.is_u64() {
                n.to_string()
            } else {
                format!("{:.6}", n.as_f64().unwrap_or(0.0))
            }
        }
        // Arrays/objects never appear as ProjectionRecord leaf fields in
        // the Python original; falling back to compact JSON keeps this
        // renderer total rather than panicking on an unexpected shape.
        other => other.to_string(),
    }
}

/// Resolve one field into zero, one, or several `(label, value)` rows.
///
/// `null` contributes nothing; a nested JSON object flattens into one
/// dotted row per present sub-field (mirrors a `pydantic.BaseModel` nested
/// field in the Python original); anything else is one scalar row.
fn format_field(name: &str, value: &Value) -> Vec<(String, String)> {
    if value.is_null() {
        return Vec::new();
    }
    if let Some(object) = value.as_object() {
        return object
            .iter()
            .filter(|(_, sub_value)| !sub_value.is_null())
            .map(|(sub_name, sub_value)| (format!("{name}.{sub_name}"), format_scalar(sub_value)))
            .collect();
    }
    vec![(name.to_string(), format_scalar(value))]
}

/// Build the plate header: `"{kind}/{identity} @ T{tick:04}"`, degrading
/// field-by-field when a piece is missing (mirrors `peek.py::_header`).
fn header_of(view: &Value) -> String {
    let mut label = view
        .get("kind")
        .and_then(Value::as_str)
        .unwrap_or("entity")
        .to_string();

    if let Some(identity_name) = identity_field_name(view) {
        if let Some(identity_value) = view.get(&identity_name).filter(|v| !v.is_null()) {
            label = format!("{label}/{}", format_scalar(identity_value));
        }
    }

    match view.get("verified_tick").and_then(Value::as_u64) {
        Some(tick) => format!("{label} @ T{tick:04}"),
        None => label,
    }
}

/// Walk every non-identity, non-universal field of `view` into ordered stat
/// rows (mirrors `peek.py::_stat_rows`; see the module docs for the
/// alphabetical-vs-declaration-order deviation).
fn stat_rows(view: &Value) -> Vec<(String, String)> {
    let Some(object) = view.as_object() else {
        return Vec::new();
    };
    let identity_name = identity_field_name(view);
    let mut rows = Vec::new();
    for (name, value) in object {
        if UNIVERSAL_FIELDS.contains(&name.as_str()) {
            continue;
        }
        if identity_name.as_deref() == Some(name.as_str()) {
            continue;
        }
        rows.extend(format_field(name, value));
    }
    rows
}

/// The honest-absence marker line shown when a plate has no populated
/// field, or no view at all (mirrors `peek.py::_absence_text`).
fn absence_line(header: &str) -> Line<'static> {
    Line::from(Span::styled(
        format!("▌ {header} — no attributed data"),
        Style::new().fg(CRIMSON).add_modifier(Modifier::BOLD),
    ))
}

/// The depth-0 plate: one unadorned line, no border (mirrors
/// `peek.py::_watchlist_row`).
fn watchlist_line(header: &str, rows: &[(String, String)]) -> Line<'static> {
    match rows.first() {
        None => absence_line(header),
        Some((label, value)) => Line::from(Span::styled(
            format!("{header}  {label}={value}"),
            Style::new().fg(BONE),
        )),
    }
}

/// Render a compact stat plate for the view-model in `subject_view_json`
/// into `area`, at the given size tier.
///
/// `subject_view_json` is the JSON the host's `subject_view_json` method
/// returns: an object, or the literal `null` when the host has no view for
/// the subject. `depth` selects the size tier (`0` most compact, up to
/// [`MAX_DEPTH`] most detailed) and clamps rather than errors outside that
/// range — see the module docs.
pub fn render_peek(frame: &mut Frame, area: Rect, subject_view_json: &str, depth: u8) {
    let depth = depth.min(MAX_DEPTH);
    let parsed: Value = serde_json::from_str(subject_view_json).unwrap_or(Value::Null);

    let (header, mut rows) = match parsed.as_object() {
        Some(_) => (header_of(&parsed), stat_rows(&parsed)),
        None => (NO_VIEW_HEADER.to_string(), Vec::new()),
    };
    if let Some(cap) = FIELD_CAP_BY_DEPTH[usize::from(depth)] {
        rows.truncate(cap);
    }

    if depth == 0 {
        frame.render_widget(Paragraph::new(watchlist_line(&header, &rows)), area);
        return;
    }

    let block = Block::bordered()
        .title(Line::styled(
            header.clone(),
            Style::new().fg(GOLD).add_modifier(Modifier::BOLD),
        ))
        .border_style(Style::new().fg(CRIMSON));

    let paragraph = if rows.is_empty() {
        Paragraph::new(absence_line(&header)).block(block)
    } else {
        let lines: Vec<Line> = rows
            .iter()
            .map(|(label, value)| {
                Line::from(vec![
                    Span::styled(format!("{label:<24}"), Style::new().fg(DIM)),
                    Span::styled(value.clone(), Style::new().fg(BONE)),
                ])
            })
            .collect();
        Paragraph::new(lines).block(block)
    };
    frame.render_widget(paragraph, area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    const FIXTURE: &str = r#"{"kind":"county","county_fips":"26163","verified_tick":42,
        "wealth":1234.5,"population":98765}"#;

    const FIXTURE_ABSENT: &str = r#"{"kind":"county","county_fips":"26163","verified_tick":1}"#;

    fn draw(json: &str, depth: u8) -> ratatui::buffer::Buffer {
        // Wide enough that the longest absence line ("▌ county/26163 @
        // T0001 — no attributed data", 43 cells) fits inside a border.
        let backend = TestBackend::new(60, 8);
        let mut terminal = Terminal::new(backend).unwrap();
        terminal
            .draw(|frame| {
                let area = frame.area();
                render_peek(frame, area, json, depth);
            })
            .unwrap();
        terminal.backend().buffer().clone()
    }

    fn buffer_text(buffer: &ratatui::buffer::Buffer) -> String {
        let area = buffer.area;
        (0..area.height)
            .map(|row| {
                (0..area.width)
                    .map(|col| buffer[(col, row)].symbol())
                    .collect::<String>()
                    .trim_end()
                    .to_string()
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    #[test]
    fn depth_0_renders_bare_line_with_first_row_only() {
        let buffer = draw(FIXTURE, 0);
        let text = buffer_text(&buffer);
        assert!(text.starts_with("county/26163 @ T0042  population=98765"));
    }

    #[test]
    fn depth_1_renders_bordered_plate_capped_at_three_rows() {
        let buffer = draw(FIXTURE, 1);
        let text = buffer_text(&buffer);
        assert!(text.contains("county/26163 @ T0042"));
        assert!(text.contains("population"));
        assert!(text.contains("98765"));
        assert!(text.contains("wealth"));
        assert!(text.contains("1234.500000"));
    }

    #[test]
    fn depth_2_renders_bordered_plate_capped_at_six_rows() {
        let buffer = draw(FIXTURE, 2);
        let text = buffer_text(&buffer);
        assert!(text.contains("county/26163 @ T0042"));
        assert!(text.contains("wealth"));
        assert!(text.contains("population"));
    }

    #[test]
    fn depth_3_renders_bordered_plate_uncapped() {
        let buffer = draw(FIXTURE, 3);
        let text = buffer_text(&buffer);
        assert!(text.contains("county/26163 @ T0042"));
        assert!(text.contains("wealth"));
        assert!(text.contains("population"));
    }

    #[test]
    fn absent_fields_render_the_honest_absence_marker_in_the_panel() {
        let buffer = draw(FIXTURE_ABSENT, 2);
        let text = buffer_text(&buffer);
        assert!(text.contains("county/26163 @ T0001 — no attributed data"));
    }

    #[test]
    fn depth_0_absence_renders_bare_marker_line_no_border() {
        let buffer = draw(FIXTURE_ABSENT, 0);
        let text = buffer_text(&buffer);
        assert!(text.starts_with("▌ county/26163 @ T0001 — no attributed data"));
        // No border box-drawing character on the bare watchlist line.
        assert!(!text.contains('┌'));
    }

    #[test]
    fn null_view_renders_honest_absence_not_a_fabricated_plate() {
        let buffer = draw("null", 2);
        let text = buffer_text(&buffer);
        assert!(text.contains("(no view available) — no attributed data"));
    }

    #[test]
    fn out_of_range_depth_clamps_to_max_depth_rather_than_panicking() {
        let buffer = draw(FIXTURE, 200);
        let text = buffer_text(&buffer);
        assert!(text.contains("county/26163 @ T0042"));
        assert!(text.contains("wealth"));
    }
}
