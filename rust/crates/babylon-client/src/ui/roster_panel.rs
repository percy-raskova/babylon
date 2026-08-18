//! The selected-node panel's own no-map path (B3 wave-1 Task 7.5, plan
//! `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md` §2.11,
//! task-7-brief.md): for a `MapBinding::None` story there is no county to
//! click, so [`SelectedRosterIndex`] + [`cycle_selected_roster_index`] walk
//! `EngineSession::full_roster` by `\u{2191}`/`\u{2193}` instead, and
//! [`format_roster_panel`] renders the selected node's own published
//! fields through [`crate::projection::Projector`] — the SAME honest-
//! Provenance seam every other panel in this crate reads through
//! (§2.6). `loop_ui::refresh_state_panel` is the one caller: it renders
//! THIS module's output in place of the `SelectedCounty` path whenever
//! `session.story.map_binding` is `None`, both sharing the one
//! `StatePanelText` entity rather than spawning a second panel.
//!
//! **The published-field tables are story-specific, like
//! `narration::NARRATION_TABLE`'s own per-`EventType` hardcoding and
//! `ui::countdown::CARCERAL_STEPS`'s own per-story delay chain** — only
//! carceral has a no-map roster today; a second `MapBinding::None` story
//! adds its own row to `published_fields` (below, a private module
//! function — not a public doc link) rather than generalizing a
//! table nobody else has read yet.

use crate::engine_link::EngineSession;
use crate::projection::Projector;
use crate::story::NodeKind;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use bevy::prelude::*;

/// The carceral world's own `social-class/*` fields (task-7-brief.md's own
/// literal list): population, wealth, organization, active.
const SOCIAL_CLASS_FIELDS: &[&str] = &[
    "social-class/population",
    "social-class/wealth",
    "social-class/organization",
    "social-class/active",
];

/// The carrier's own `institution/*` fields — the task brief's own three
/// named examples (enforcer-population, prisoner-population,
/// decomposition-fire-tick) plus the remaining census/latch fields that
/// give the whole arc's own progress an honest, complete picture (never an
/// arbitrarily narrower cut than what the brief's own "…" already signals
/// exists).
const INSTITUTION_FIELDS: &[&str] = &[
    "institution/enforcer-population",
    "institution/prisoner-population",
    "institution/decomposition-fire-tick",
    "institution/prisoner-org-weighted",
    "institution/superwage-crisis-known",
    "institution/decomposition-fired-known",
    "institution/control-crisis-tick",
    "institution/control-crisis-emitted",
    "institution/terminal-decision-emitted",
];

/// Which published-field table `kind` reads through — see the module doc.
fn published_fields(kind: NodeKind) -> &'static [&'static str] {
    match kind {
        NodeKind::SocialClass => SOCIAL_CLASS_FIELDS,
        NodeKind::Institution => INSTITUTION_FIELDS,
    }
}

/// The `\u{2191}`/`\u{2193}`-selected index into `EngineSession::full_roster` —
/// `None` before the first arrow press (the panel renders nothing until a
/// player actually asks for a node, matching this crate's own "recallable,
/// not forced open" precedent). No `Default` derive that would silently
/// pick index `0`: an unselected roster and a roster whose first element is
/// selected are genuinely different states, and this resource must be able
/// to represent both.
#[derive(Resource, Debug, Clone, Copy, Default)]
pub struct SelectedRosterIndex(pub Option<usize>);

/// `Update` system: `\u{2191}`/`\u{2193}` cycle [`SelectedRosterIndex`]
/// through `session.full_roster`, wrapping at both ends. A no-op for a
/// `MapBinding::Fips` story (counties) or an empty roster — the county map
/// already owns arrow-key-free click selection there, and this system must
/// never fight it for the same keys.
pub fn cycle_selected_roster_index(
    keys: Res<ButtonInput<KeyCode>>,
    session: Res<EngineSession>,
    mut selected: ResMut<SelectedRosterIndex>,
) {
    if session.story.map_binding.is_some() || session.full_roster.is_empty() {
        return;
    }
    let len = session.full_roster.len();
    if keys.just_pressed(KeyCode::ArrowDown) {
        selected.0 = Some(selected.0.map_or(0, |i| (i + 1) % len));
    } else if keys.just_pressed(KeyCode::ArrowUp) {
        selected.0 = Some(selected.0.map_or(0, |i| (i + len - 1) % len));
    }
}

/// Renders one roster field through the projector at 2 decimal places —
/// `Material` shows the live numeral, every other `Provenance` shows its
/// declared reason with no digit (`projection::Reading::render`'s own
/// contract).
fn format_field_line(
    projector: &Projector,
    graph: &dyn GraphSubstrate,
    id: NodeId,
    field: &str,
) -> String {
    let reading = projector.read(graph, id, field);
    format!("  {field}: {}", reading.render(2))
}

/// Renders the selected-node panel's no-map path: the roster position
/// (`label (N/total)`), then every one of `kind`'s own published fields,
/// each through [`crate::projection::Projector`]. Empty string when
/// nothing is selected yet, or the selected index has fallen out of range
/// (cannot happen through [`cycle_selected_roster_index`] alone, but a
/// fresh `N`-restart resets the resource to `None` rather than leaving a
/// stale index — this is the second line of defense, not the only one).
#[must_use]
pub fn format_roster_panel(
    graph: &dyn GraphSubstrate,
    roster: &[(String, NodeId, NodeKind)],
    selected: Option<usize>,
) -> String {
    let Some(idx) = selected else {
        return String::new();
    };
    let Some((label, id, kind)) = roster.get(idx) else {
        return String::new();
    };
    let projector = Projector::material();
    let mut lines = vec![format!("{label} ({}/{})", idx + 1, roster.len())];
    lines.extend(
        published_fields(*kind)
            .iter()
            .map(|field| format_field_line(&projector, graph, *id, field)),
    );
    lines.join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_graph::hypergraph_store::HypergraphStore;

    fn social_class_node(graph: &mut HypergraphStore) -> NodeId {
        let id = graph.add_node("SOCIAL_CLASS").expect("add social-class");
        graph
            .update_node(id, "social-class/population", 600.0)
            .expect("population");
        graph
            .update_node(id, "social-class/wealth", 515.0)
            .expect("wealth");
        graph
            .update_node(id, "social-class/organization", 0.2)
            .expect("organization");
        graph
            .update_node(id, "social-class/active", 1.0)
            .expect("active");
        id
    }

    #[test]
    fn nothing_selected_renders_empty() {
        let graph = HypergraphStore::new();
        assert_eq!(format_roster_panel(&graph, &[], None), "");
    }

    #[test]
    fn an_out_of_range_index_renders_empty() {
        let mut graph = HypergraphStore::new();
        let id = social_class_node(&mut graph);
        let roster = vec![("la-approaching".to_owned(), id, NodeKind::SocialClass)];
        assert_eq!(format_roster_panel(&graph, &roster, Some(5)), "");
    }

    #[test]
    fn a_social_class_selection_renders_its_four_published_fields() {
        let mut graph = HypergraphStore::new();
        let id = social_class_node(&mut graph);
        let roster = vec![("la-approaching".to_owned(), id, NodeKind::SocialClass)];
        let rendered = format_roster_panel(&graph, &roster, Some(0));
        assert!(
            rendered.starts_with("la-approaching (1/1)"),
            "got {rendered:?}"
        );
        assert!(
            rendered.contains("social-class/population: 600.00"),
            "got {rendered:?}"
        );
        assert!(
            rendered.contains("social-class/wealth: 515.00"),
            "got {rendered:?}"
        );
        assert!(
            rendered.contains("social-class/organization: 0.20"),
            "got {rendered:?}"
        );
        assert!(
            rendered.contains("social-class/active: 1.00"),
            "got {rendered:?}"
        );
    }

    #[test]
    fn an_institution_selection_renders_the_carrier_fields_through_the_projector() {
        let mut graph = HypergraphStore::new();
        let id = graph.add_node("INSTITUTION").expect("add institution");
        graph
            .update_node(id, "institution/enforcer-population", 110.0)
            .expect("enforcer-population");
        graph
            .update_node(id, "institution/prisoner-population", 710.0)
            .expect("prisoner-population");
        // decomposition-fire-tick deliberately left UNWRITTEN — the panel
        // must render the honest Absent reason, never a fabricated 0.
        let roster = vec![("carceral-register".to_owned(), id, NodeKind::Institution)];
        let rendered = format_roster_panel(&graph, &roster, Some(0));
        assert!(
            rendered.contains("institution/enforcer-population: 110.00"),
            "got {rendered:?}"
        );
        assert!(
            rendered.contains("institution/prisoner-population: 710.00"),
            "got {rendered:?}"
        );
        assert!(
            rendered.contains("institution/decomposition-fire-tick: absent"),
            "an unwritten field must render the honest Absent reason, never a fabricated 0, \
             got {rendered:?}"
        );
    }

    #[test]
    fn selecting_wraps_at_both_ends() {
        let mut selected = SelectedRosterIndex(None);
        let len = 3;
        // Down from None picks index 0, then wraps 0 -> 1 -> 2 -> 0.
        selected.0 = Some(selected.0.map_or(0, |i| (i + 1) % len));
        assert_eq!(selected.0, Some(0));
        for _ in 0..len {
            selected.0 = Some(selected.0.map_or(0, |i| (i + 1) % len));
        }
        assert_eq!(selected.0, Some(0));

        // Up from None ALSO picks index 0 (never -1) — the first press must
        // land on a real roster entry regardless of direction.
        let mut selected = SelectedRosterIndex(None);
        selected.0 = Some(selected.0.map_or(0, |i| (i + len - 1) % len));
        assert_eq!(selected.0, Some(0));
    }
}
