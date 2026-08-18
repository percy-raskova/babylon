//! B3 wave-1 Task 3 (plan
//! `docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md` §2.6,
//! RED phase): the projection seam's own contract, exercised as a
//! consumer of `babylon_client`'s public API — `Projector::material().read`
//! for the three provenances this crate can produce today
//! (`Material`/`Absent`/`NotComputed`), the digit-free render discipline
//! (III.11), the `Redacted` variant's declared-dead sentinel (I9), and the
//! admin banner's own rendered text.

use babylon_client::projection::{Projector, Provenance};
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::substrate::{GraphSubstrate, NodeId};

#[test]
fn material_read_returns_material_provenance_and_the_written_value() {
    let mut graph = HypergraphStore::new();
    let id = graph.add_node("TERRITORY").expect("add territory");
    graph
        .update_node(id, "territory/pop-d", 2042.0)
        .expect("stamp pop-d");

    let reading = Projector::material().read(&graph, id, "territory/pop-d");
    assert_eq!(reading.value, Some(2042.0));
    assert_eq!(reading.provenance, Provenance::Material);
}

#[test]
fn an_unwritten_field_returns_absent_never_a_fabricated_zero() {
    let mut graph = HypergraphStore::new();
    let id = graph.add_node("TERRITORY").expect("add territory");
    // Nothing ever stamps territory/pop-p on this node.

    let reading = Projector::material().read(&graph, id, "territory/pop-p");
    assert_eq!(
        reading.value, None,
        "an unwritten field must read back as None — Some(0.0) would be exactly \
         the fabrication III.11 forbids"
    );
    assert!(matches!(reading.provenance, Provenance::Absent { .. }));
}

/// §2.6's I2 table: a field a port DECLARED it will never compute renders
/// its reason and contains no digit — never the numeral it would
/// otherwise read as (`decomposition.bsl:264`'s bare `0.0c`, transcribed
/// as the `SUPERWAGE_CRISIS.desired-wages` key `Projector::material`
/// declares unconditionally, checked before any graph read).
#[test]
fn a_declared_not_computed_key_renders_its_reason_with_no_digit() {
    let graph = HypergraphStore::new();
    let reading = Projector::material().read(&graph, NodeId(0), "SUPERWAGE_CRISIS.desired-wages");
    assert_eq!(reading.value, None);
    assert!(matches!(reading.provenance, Provenance::NotComputed { .. }));

    let rendered = reading.render(0);
    assert!(
        !rendered.chars().any(|c| c.is_ascii_digit()),
        "a NotComputed render must contain no digit, got {rendered:?}"
    );
    assert!(rendered.contains("not computed by this port"));
}

/// I9: `Provenance::Redacted` is declared-dead until #593.
/// `src/projection.rs` itself is exempt (it declares the variant and its
/// own exhaustive `render` match needs to name it) — the SAME
/// whole-file-exemption shape
/// `tests/unit/render/test_rust_theme_parity.py` already uses for
/// `palette.rs`'s own `Color::srgb_u8` literals. Every OTHER file under
/// `src/` must never construct this variant; the day a fixture does
/// (exactly revision 1's own corrected mistake, plan §2.6 I9), this test
/// goes red.
#[test]
fn redacted_is_declared_dead_until_593() {
    let src_root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let exempt = src_root.join("projection.rs");
    let mut offenders = Vec::new();
    scan_dir(&src_root, &exempt, &mut offenders, 0);
    assert!(
        offenders.is_empty(),
        "Provenance::Redacted must not be constructed outside src/projection.rs \
         (I9 — declared-dead until #593), found: {offenders:?}"
    );
}

/// A bounded recursive walk (Power-of-10 rule 2): `MAX_SCAN_DEPTH` is a
/// generous ceiling on this crate's own `src/` module nesting, asserted
/// loudly rather than silently exceeded — never an unbounded traversal.
const MAX_SCAN_DEPTH: usize = 8;

fn scan_dir(
    dir: &std::path::Path,
    exempt: &std::path::Path,
    offenders: &mut Vec<String>,
    depth: usize,
) {
    assert!(
        depth <= MAX_SCAN_DEPTH,
        "src/ tree deeper than MAX_SCAN_DEPTH ({MAX_SCAN_DEPTH}) at {dir:?} — raise the \
         constant deliberately, this is not meant to loop unbounded"
    );
    let entries = std::fs::read_dir(dir).unwrap_or_else(|e| panic!("read_dir {dir:?}: {e}"));
    for entry in entries {
        let entry = entry.expect("dir entry");
        let path = entry.path();
        if path.is_dir() {
            scan_dir(&path, exempt, offenders, depth + 1);
        } else if path.extension().and_then(|e| e.to_str()) == Some("rs") && path != exempt {
            let text =
                std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read {path:?}: {e}"));
            if text.contains("Provenance::Redacted") {
                offenders.push(path.display().to_string());
            }
        }
    }
}

/// A headless assertion that the admin banner entity exists and reads the
/// declared text — `ADMIN · MATERIAL TRUTH · UNFOGGED` (§2.6/§3.3): the
/// NAMED exception this wave's whole unfogged projection depends on
/// (Global Constraint 5).
#[test]
fn the_admin_banner_entity_exists_and_reads_the_declared_text() {
    use bevy::asset::AssetPlugin;
    use bevy::prelude::*;

    let mut app = App::new();
    app.add_plugins((MinimalPlugins, AssetPlugin::default()));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.update(); // Startup

    let world = app.world_mut();
    let mut query = world.query_filtered::<&Text, With<babylon_client::ui::admin::AdminBanner>>();
    let text = query
        .single(world)
        .expect("exactly one admin banner entity")
        .0
        .clone();
    assert_eq!(text, "ADMIN \u{b7} MATERIAL TRUTH \u{b7} UNFOGGED");
    assert_eq!(text, babylon_client::ui::admin::BANNER_TEXT);
}
