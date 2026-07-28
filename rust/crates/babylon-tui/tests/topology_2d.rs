//! Behavior tests for `babylon_tui::views::topology`'s 2D glyph-floor
//! renderers (contract `docs/superpowers/specs/2026-07-27-m4-topology-
//! contracts.md` §1/§4, plan Task 31).
//!
//! Fixture bodies are ported from `tests/unit/tui/test_egotree_directive.py`
//! / `tests/unit/tui/test_matrix_directive.py` / `test_directives.py`'s own
//! `{paoh}` fixtures, reshaped into the §1 JSON envelopes (`community_id`/
//! `formation_tick`/`layout` are new fields those fence-body fixtures never
//! carried — filled in with representative values, since the glyph-floor
//! renderers under test never read them).
//!
//! Golden strategy per §4's ruling: explicit substring/field asserts over
//! `buffer_text` (the `wiki_view`/`chronicle_view` convention), not `insta`
//! snapshots — colors ride the `style_at_row` cell lookup below, mirroring
//! `chronicle_view.rs`'s own `style_at` helper (scoped to one row here,
//! since these grids repeat the same glyph many times per frame).

use babylon_tui::theme::{BONE, CRIMSON, DIM, GOLD};
use babylon_tui::views::topology::{
    render_adjacency, render_egotree, render_incidence, render_paoh, AdjacencyPayload,
    EgotreePayload, IncidencePayload, PaohPayload, TopologyPayload,
};
use ratatui::backend::TestBackend;
use ratatui::style::{Color, Modifier};
use ratatui::widgets::Paragraph;
use ratatui::Terminal;

/// Mirrors `topology::PANEL` (module-local there on purpose — see that
/// module's own doc comment, the `chronicle::AMBER` precedent applied to a
/// second non-§9b constant) — unreachable from this external integration-
/// test crate, so this is the one place its literal value is duplicated.
const PANEL: Color = Color::Rgb(32, 4, 4);

/// Draws a rendered `Vec<Line>` into a fresh `TestBackend` of the given size.
fn draw(
    lines: Vec<ratatui::text::Line<'static>>,
    width: u16,
    height: u16,
) -> Terminal<TestBackend> {
    let backend = TestBackend::new(width, height);
    let mut terminal = Terminal::new(backend).unwrap();
    terminal
        .draw(|frame| frame.render_widget(Paragraph::new(lines), frame.area()))
        .unwrap();
    terminal
}

/// Dumps a `TestBackend` buffer's visible text, one `String` per row.
fn buffer_lines(terminal: &Terminal<TestBackend>) -> Vec<String> {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    (area.top()..area.bottom())
        .map(|y| {
            (area.left()..area.right())
                .map(|x| buffer[(x, y)].symbol())
                .collect::<String>()
        })
        .collect()
}

/// The `(fg, modifier)` style of `needle`'s first character within row `y`
/// only — the PAOH/matrix grids repeat `●`/`·` many times per frame, so a
/// whole-buffer scan (`chronicle_view.rs`'s `style_at`) would find the
/// wrong occurrence. Panics if `needle` never appears in that row.
fn style_at_row(terminal: &Terminal<TestBackend>, y: u16, needle: &str) -> (Color, Modifier) {
    let buffer = terminal.backend().buffer();
    let area = buffer.area;
    let cells: Vec<&str> = (area.left()..area.right())
        .map(|x| buffer[(x, y)].symbol())
        .collect();
    let row = cells.concat();
    let byte_pos = row
        .find(needle)
        .unwrap_or_else(|| panic!("substring {needle:?} not found in row {y}: {row:?}"));
    let char_index = row[..byte_pos].chars().count();
    let x = area.left() + char_index as u16;
    let cell = &buffer[(x, y)];
    (cell.fg, cell.modifier)
}

// ---------------------------------------------------------------------
// paoh
// ---------------------------------------------------------------------

/// nodes a,b,c; edge0 ticked (members a,c — spans the non-member row b);
/// edge1 untimed (`formation_tick: null`, the live-today case per
/// `paoh.py`'s module docstring) with a single member b.
const PAOH_FIXTURE: &str = r#"{
    "kind": "paoh", "verified_tick": 500,
    "nodes": ["a", "b", "c"],
    "edges": [
        {"community_id": "settler", "formation_tick": 3, "members": ["a", "c"]},
        {"community_id": "women", "formation_tick": null, "members": ["b"]}
    ],
    "layout": {"a": [1.0, 0.0], "b": [0.0, 1.0], "c": [-1.0, 0.0]}
}"#;

#[test]
fn paoh_dispatches_through_the_kind_tagged_enum() {
    let payload: TopologyPayload = serde_json::from_str(PAOH_FIXTURE).unwrap();
    let lines = payload.render();
    assert_eq!(lines.len(), 4); // header + 3 node rows
}

#[test]
fn paoh_header_shows_the_ticked_column_and_the_honest_null_tick_placeholder() {
    let payload: PaohPayload = serde_json::from_str(PAOH_FIXTURE).unwrap();
    let terminal = draw(render_paoh(&payload), 40, 6);
    let text = buffer_lines(&terminal).join("\n");
    assert!(text.contains("t3"), "{text}");
    assert!(text.contains("t?"), "{text}"); // never a fabricated tick number
    assert!(!text.contains("tNone"), "{text}");

    let (fg, _) = style_at_row(&terminal, 0, "t3");
    assert_eq!(fg, BONE);
    let (fg, _) = style_at_row(&terminal, 0, "t?");
    assert_eq!(fg, BONE);
}

#[test]
fn paoh_renders_member_dots_span_connectors_and_absent_dots() {
    let payload: PaohPayload = serde_json::from_str(PAOH_FIXTURE).unwrap();
    let terminal = draw(render_paoh(&payload), 40, 6);

    // Row a (y=1): member of edge0 (●), absent from edge1's span (·).
    let (fg, modifier) = style_at_row(&terminal, 1, "●");
    assert_eq!(fg, GOLD);
    assert!(modifier.contains(Modifier::BOLD));
    let (fg, _) = style_at_row(&terminal, 1, "·");
    assert_eq!(fg, PANEL);

    // Row b (y=2): not a member of edge0 but strictly between its member
    // rows (a=0, c=2) -> the CRIMSON span connector; a member of edge1.
    let (fg, _) = style_at_row(&terminal, 2, "│");
    assert_eq!(fg, CRIMSON);
    let (fg, modifier) = style_at_row(&terminal, 2, "●");
    assert_eq!(fg, GOLD);
    assert!(modifier.contains(Modifier::BOLD));

    // Row c (y=3): member of edge0, outside edge1's single-row span.
    let (fg, _) = style_at_row(&terminal, 3, "●");
    assert_eq!(fg, GOLD);
    let (fg, _) = style_at_row(&terminal, 3, "·");
    assert_eq!(fg, PANEL);
}

#[test]
fn paoh_row_labels_are_bone() {
    let payload: PaohPayload = serde_json::from_str(PAOH_FIXTURE).unwrap();
    let terminal = draw(render_paoh(&payload), 40, 6);
    let (fg, _) = style_at_row(&terminal, 1, "a");
    assert_eq!(fg, BONE);
}

#[test]
fn paoh_with_no_edges_renders_only_the_blank_header_and_node_rows() {
    let payload = PaohPayload {
        verified_tick: 1,
        nodes: vec!["a".to_string(), "b".to_string()],
        edges: vec![],
        layout: Default::default(),
    };
    let lines = render_paoh(&payload);
    assert_eq!(lines.len(), 3); // header + 2 node rows, no columns
}

// ---------------------------------------------------------------------
// egotree
// ---------------------------------------------------------------------

/// Ported from `test_egotree_directive.py::TestRenderEgotree::
/// test_renders_the_root_and_every_child_and_grandchild`.
const EGOTREE_FIXTURE: &str = r#"{
    "kind": "egotree", "verified_tick": 500,
    "root_id": "settler", "root_side": "community",
    "children": [
        {"node_id": "C001", "neighbors": ["patriarchal", "women"]},
        {"node_id": "C002", "neighbors": []}
    ]
}"#;

#[test]
fn egotree_dispatches_through_the_kind_tagged_enum() {
    let payload: TopologyPayload = serde_json::from_str(EGOTREE_FIXTURE).unwrap();
    let lines = payload.render();
    // root + C001 + patriarchal + women + C002 = 5 lines.
    assert_eq!(lines.len(), 5);
}

#[test]
fn egotree_renders_root_bold_gold_with_dim_side_suffix() {
    let payload: EgotreePayload = serde_json::from_str(EGOTREE_FIXTURE).unwrap();
    let terminal = draw(render_egotree(&payload), 40, 6);
    let text = buffer_lines(&terminal).join("\n");
    assert!(text.contains("settler"), "{text}");
    assert!(text.contains("(community)"), "{text}");

    let (fg, modifier) = style_at_row(&terminal, 0, "settler");
    assert_eq!(fg, GOLD);
    assert!(modifier.contains(Modifier::BOLD));
    let (fg, _) = style_at_row(&terminal, 0, "(community)");
    assert_eq!(fg, DIM);
}

#[test]
fn egotree_renders_depth1_branches_crimson_and_ids_bone() {
    let payload: EgotreePayload = serde_json::from_str(EGOTREE_FIXTURE).unwrap();
    let terminal = draw(render_egotree(&payload), 40, 6);

    let (fg, _) = style_at_row(&terminal, 1, "├──");
    assert_eq!(fg, CRIMSON);
    let (fg, _) = style_at_row(&terminal, 1, "C001");
    assert_eq!(fg, BONE);

    let (fg, _) = style_at_row(&terminal, 4, "└──");
    assert_eq!(fg, CRIMSON);
    let (fg, _) = style_at_row(&terminal, 4, "C002");
    assert_eq!(fg, BONE);
}

#[test]
fn egotree_renders_depth2_prefixes_panel_and_neighbor_ids_dim() {
    let payload: EgotreePayload = serde_json::from_str(EGOTREE_FIXTURE).unwrap();
    let terminal = draw(render_egotree(&payload), 40, 6);

    let (fg, _) = style_at_row(&terminal, 2, "├──");
    assert_eq!(fg, PANEL);
    let (fg, _) = style_at_row(&terminal, 2, "patriarchal");
    assert_eq!(fg, DIM);

    let (fg, _) = style_at_row(&terminal, 3, "└──");
    assert_eq!(fg, PANEL);
    let (fg, _) = style_at_row(&terminal, 3, "women");
    assert_eq!(fg, DIM);
}

#[test]
fn egotree_root_with_no_children_renders_just_the_root_line() {
    let payload = EgotreePayload {
        verified_tick: 1,
        root_id: "C001".to_string(),
        root_side: "member".to_string(),
        children: vec![],
    };
    let lines = render_egotree(&payload);
    assert_eq!(lines.len(), 1);
}

// ---------------------------------------------------------------------
// incidence
// ---------------------------------------------------------------------

const INCIDENCE_FIXTURE: &str = r#"{
    "kind": "incidence", "verified_tick": 500,
    "nodes": ["alpha", "beta"],
    "hyperedges": ["settler", "women"],
    "cells": [[true, false], [true, true]]
}"#;

#[test]
fn incidence_dispatches_through_the_kind_tagged_enum() {
    let payload: TopologyPayload = serde_json::from_str(INCIDENCE_FIXTURE).unwrap();
    let lines = payload.render();
    assert_eq!(lines.len(), 3); // header + alpha + beta
}

#[test]
fn incidence_header_names_every_hyperedge_in_bone() {
    let payload: IncidencePayload = serde_json::from_str(INCIDENCE_FIXTURE).unwrap();
    let terminal = draw(render_incidence(&payload), 40, 6);
    let text = buffer_lines(&terminal).join("\n");
    assert!(text.contains("settler"), "{text}");
    assert!(text.contains("women"), "{text}");

    let (fg, _) = style_at_row(&terminal, 0, "settler");
    assert_eq!(fg, BONE);
    let (fg, _) = style_at_row(&terminal, 0, "women");
    assert_eq!(fg, BONE);
}

#[test]
fn incidence_renders_present_and_absent_cells() {
    let payload: IncidencePayload = serde_json::from_str(INCIDENCE_FIXTURE).unwrap();
    let terminal = draw(render_incidence(&payload), 40, 6);

    // alpha: settler present, women absent.
    let (fg, modifier) = style_at_row(&terminal, 1, "●");
    assert_eq!(fg, GOLD);
    assert!(modifier.contains(Modifier::BOLD));
    let (fg, _) = style_at_row(&terminal, 1, "·");
    assert_eq!(fg, PANEL);

    // beta: both present.
    let (fg, _) = style_at_row(&terminal, 2, "●");
    assert_eq!(fg, GOLD);
}

#[test]
fn incidence_with_no_nodes_says_so_rather_than_rendering_a_blank_grid() {
    let payload = IncidencePayload {
        verified_tick: 1,
        nodes: vec![],
        hyperedges: vec![],
        cells: vec![],
    };
    let terminal = draw(render_incidence(&payload), 40, 6);
    let text = buffer_lines(&terminal).join("\n");
    assert!(text.contains("no incidence data"), "{text}");
    let (fg, _) = style_at_row(&terminal, 1, "no incidence data");
    assert_eq!(fg, DIM);
}

// ---------------------------------------------------------------------
// adjacency
// ---------------------------------------------------------------------

const ADJACENCY_FIXTURE: &str = r#"{
    "kind": "adjacency", "verified_tick": 500,
    "nodes": ["a", "b", "c"],
    "cells": [[false, true, false], [true, false, true], [false, true, false]]
}"#;

#[test]
fn adjacency_dispatches_through_the_kind_tagged_enum() {
    let payload: TopologyPayload = serde_json::from_str(ADJACENCY_FIXTURE).unwrap();
    let lines = payload.render();
    assert_eq!(lines.len(), 4); // header + a + b + c
}

#[test]
fn adjacency_diagonal_is_never_a_false_not_adjacent_dot() {
    let payload: AdjacencyPayload = serde_json::from_str(ADJACENCY_FIXTURE).unwrap();
    let terminal = draw(render_adjacency(&payload), 40, 6);
    let text = buffer_lines(&terminal).join("\n");
    assert!(text.contains("—"), "{text}");

    let (fg, _) = style_at_row(&terminal, 1, "—");
    assert_eq!(fg, DIM);
}

#[test]
fn adjacency_renders_adjacent_and_non_adjacent_cells() {
    let payload: AdjacencyPayload = serde_json::from_str(ADJACENCY_FIXTURE).unwrap();
    let terminal = draw(render_adjacency(&payload), 40, 6);

    // row a: adjacent to b (●), not adjacent to c (·), diagonal (—).
    let (fg, modifier) = style_at_row(&terminal, 1, "●");
    assert_eq!(fg, GOLD);
    assert!(modifier.contains(Modifier::BOLD));
    let (fg, _) = style_at_row(&terminal, 1, "·");
    assert_eq!(fg, PANEL);
}

#[test]
fn adjacency_with_no_nodes_says_so_rather_than_rendering_a_blank_grid() {
    let payload = AdjacencyPayload {
        verified_tick: 1,
        nodes: vec![],
        cells: vec![],
    };
    let terminal = draw(render_adjacency(&payload), 40, 6);
    let text = buffer_lines(&terminal).join("\n");
    assert!(text.contains("no adjacency data"), "{text}");
    let (fg, _) = style_at_row(&terminal, 1, "no adjacency data");
    assert_eq!(fg, DIM);
}
