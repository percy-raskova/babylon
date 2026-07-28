//! Frame-content tests for `babylon_tui::views::map`'s choropleth render
//! (M5 contract `docs/superpowers/specs/2026-07-28-m5-maps-contracts.md`
//! §2/§5 — the explicit-assert lane: CONTENT asserts over `TestBackend`
//! buffers with band COLORS read off cell styles, never just titles (the
//! golden-certifies-what-you-render scar; `insta` cannot assert color, the
//! ruled golden split).

use babylon_tui::theme::{BONE, CRIMSON, DIM, GOLD};
use babylon_tui::views::map::MapView;
use babylon_tui::views::topology::PANEL;
use ratatui::backend::TestBackend;
use ratatui::style::Color;
use ratatui::Terminal;

/// Renders the view into a fresh backend of the given size.
fn draw(view: &mut MapView, width: u16, height: u16) -> Terminal<TestBackend> {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| view.render(frame, frame.area()))
        .unwrap();
    terminal
}

/// Dumps the buffer's visible text, rows joined with newlines.
fn buffer_text(terminal: &Terminal<TestBackend>) -> String {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    (area.top()..area.bottom())
        .map(|y| {
            (area.left()..area.right())
                .map(|x| buffer[(x, y)].symbol())
                .collect::<String>()
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// Whether ANY buffer cell carries `color` as foreground or background —
/// `Marker::HalfBlock` colors the upper half-pixel via fg and the lower
/// via bg, so a filled region shows up in either channel.
fn any_cell_colored(terminal: &Terminal<TestBackend>, color: Color) -> bool {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    (area.top()..area.bottom()).any(|y| {
        (area.left()..area.right()).any(|x| {
            let cell = &buffer[(x, y)];
            cell.fg == color || cell.bg == color
        })
    })
}

/// The fg color of `needle`'s first character anywhere in the buffer
/// (the `chronicle_view` whole-buffer convention — each asserted line
/// appears exactly once per frame here).
fn fg_of(terminal: &Terminal<TestBackend>, needle: &str) -> Color {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    for y in area.top()..area.bottom() {
        let row: String = (area.left()..area.right())
            .map(|x| buffer[(x, y)].symbol())
            .collect();
        if let Some(byte_pos) = row.find(needle) {
            let char_index = row[..byte_pos].chars().count();
            return buffer[(area.left() + char_index as u16, y)].fg;
        }
    }
    panic!(
        "substring {needle:?} not found in buffer:\n{}",
        buffer_text(terminal)
    );
}

const OVERLAY_ABSENT: &str =
    "national overlay ruled (ADR171); Phase-0 incidence artifact not yet built";

/// Three squares spanning the VALUE bands: `2.5` → crimson, `0.5` → dim,
/// `null` → the PANEL absence fill.
fn tri_band_envelope() -> String {
    format!(
        r#"{{
        "tier": "county", "lens": "value", "verified_tick": 3,
        "bands": [[null, "panel"], [1.0, "dim"], [2.0, "gold"], [null, "crimson"]],
        "overlay_absent": "{OVERLAY_ABSENT}",
        "cells": [
            {{"region_id": "26163", "value": 2.5,
             "wkt": "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))", "centroid": null}},
            {{"region_id": "01001", "value": 0.5,
             "wkt": "POLYGON((12 0, 22 0, 22 10, 12 10, 12 0))", "centroid": null}},
            {{"region_id": "02002", "value": null,
             "wkt": "POLYGON((24 0, 34 0, 34 10, 24 10, 24 0))", "centroid": null}}
        ]
    }}"#
    )
}

#[test]
fn band_colored_cells_and_labels_render() {
    let mut view = MapView::default();
    view.ingest_choropleth(&tri_band_envelope());
    let terminal = draw(&mut view, 72, 24);
    assert!(
        any_cell_colored(&terminal, CRIMSON),
        "crimson band cell missing:\n{}",
        buffer_text(&terminal)
    );
    assert!(any_cell_colored(&terminal, DIM), "dim band cell missing");
    assert!(
        any_cell_colored(&terminal, PANEL),
        "absence (panel) fill missing"
    );
    let text = buffer_text(&terminal);
    assert!(text.contains("26163"), "label missing:\n{text}");
    assert_eq!(fg_of(&terminal, "26163"), BONE);
}

#[test]
fn unreadable_wire_is_the_loud_crimson_line() {
    let mut view = MapView::default();
    view.ingest_choropleth("{not json");
    let terminal = draw(&mut view, 60, 8);
    let text = buffer_text(&terminal);
    assert!(
        text.contains("map UNREADABLE — malformed host data"),
        "{text}"
    );
    assert_eq!(fg_of(&terminal, "map UNREADABLE"), CRIMSON);
}

#[test]
fn null_reply_is_honest_absence_naming_the_tier() {
    let mut view = MapView::default();
    view.ingest_choropleth("null");
    let terminal = draw(&mut view, 76, 8);
    let text = buffer_text(&terminal);
    assert!(text.contains("no county map"), "{text}");
    assert!(
        text.contains("no county-bearing territories"),
        "the absence line must name the cause:\n{text}"
    );
    assert_eq!(fg_of(&terminal, "no county map"), DIM);
}

#[test]
fn lens_absent_reason_is_a_crimson_banner() {
    let mut view = MapView::default();
    view.ingest_choropleth(&format!(
        r#"{{
        "tier": "county", "lens": "tension", "verified_tick": 3,
        "bands": [[null, "panel"], [-0.15, "crimson"], [0.15, "dim"], [null, "gold"]],
        "lens_absent_reason": "no county bears honest data this tick — no norm exists",
        "overlay_absent": "{OVERLAY_ABSENT}",
        "cells": []
    }}"#
    ));
    let terminal = draw(&mut view, 76, 8);
    let text = buffer_text(&terminal);
    assert!(text.contains("no county bears honest data"), "{text}");
    assert_eq!(fg_of(&terminal, "no county bears"), CRIMSON);
}

#[test]
fn cells_without_geometry_render_the_honest_line() {
    let mut view = MapView::default();
    view.ingest_choropleth(&format!(
        r#"{{
        "tier": "county", "lens": "value", "verified_tick": 3,
        "bands": [[null, "panel"], [1.0, "dim"], [2.0, "gold"], [null, "crimson"]],
        "overlay_absent": "{OVERLAY_ABSENT}",
        "cells": [
            {{"region_id": "26163", "value": 2.5, "wkt": null, "centroid": null}}
        ]
    }}"#
    ));
    let terminal = draw(&mut view, 90, 8);
    let text = buffer_text(&terminal);
    assert!(text.contains("no geometry on the wire"), "{text}");
    assert_eq!(fg_of(&terminal, "no geometry"), DIM);
}

#[test]
fn fog_lens_paints_categorical_bands() {
    let mut view = MapView::default();
    view.ingest_choropleth(&format!(
        r#"{{
        "tier": "county", "lens": "fog", "verified_tick": 3,
        "bands": [["exact", "gold"], ["approximate", "dim"], ["unknown", "panel"]],
        "overlay_absent": "{OVERLAY_ABSENT}",
        "cells": [
            {{"region_id": "26163", "value": "exact",
             "wkt": "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))", "centroid": null}},
            {{"region_id": "01001", "value": "unknown",
             "wkt": "POLYGON((12 0, 22 0, 22 10, 12 10, 12 0))", "centroid": null}}
        ]
    }}"#
    ));
    let terminal = draw(&mut view, 72, 24);
    assert!(
        any_cell_colored(&terminal, GOLD),
        "exact (gold) cell missing"
    );
    assert!(
        any_cell_colored(&terminal, PANEL),
        "unknown (panel) cell missing"
    );
}

#[test]
fn centroid_dot_cell_is_always_labeled() {
    let mut view = MapView::default();
    // One WKT square plus one no-WKT cell carrying only a centroid: the
    // dot cell labels UNCONDITIONALLY (contract §2's "labeled centroid
    // dot"), even where a polygon of that size would suppress its label.
    view.ingest_choropleth(&format!(
        r#"{{
        "tier": "county", "lens": "value", "verified_tick": 3,
        "bands": [[null, "panel"], [1.0, "dim"], [2.0, "gold"], [null, "crimson"]],
        "overlay_absent": "{OVERLAY_ABSENT}",
        "cells": [
            {{"region_id": "26163", "value": 2.5,
             "wkt": "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))", "centroid": null}},
            {{"region_id": "01001", "value": 0.5, "wkt": null, "centroid": [14.0, 5.0]}}
        ]
    }}"#
    ));
    let terminal = draw(&mut view, 72, 24);
    let text = buffer_text(&terminal);
    assert!(text.contains("01001"), "dot label missing:\n{text}");
    assert!(any_cell_colored(&terminal, DIM), "dot pixel missing");
}
