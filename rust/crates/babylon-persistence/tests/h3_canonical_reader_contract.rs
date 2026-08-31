//! Pure RED contracts for the PER-280 canonical-reader schema epoch.

use std::path::PathBuf;

use babylon_persistence::compiled_schema_migrations;

fn crate_path(relative: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(relative)
}

#[test]
fn epoch_seven_is_the_exact_next_compiled_migration() {
    let compiled = compiled_schema_migrations().expect("compiled migrations must be valid");

    assert_eq!(compiled.len(), 7);
    assert_eq!(compiled[6].version().as_i64(), 7);
    assert_eq!(
        compiled[6].sql(),
        std::fs::read_to_string(crate_path("migrations/0007_h3_canonical_readers.sql"))
            .expect("epoch-7 canonical-reader migration must exist")
    );
}

#[test]
fn epoch_seven_replaces_only_the_ten_existing_reader_views() {
    let migration = std::fs::read_to_string(crate_path("migrations/0007_h3_canonical_readers.sql"))
        .expect("epoch-7 canonical-reader migration must exist");

    for view in [
        "public.v_county_value_aggregate",
        "public.v_hex_aid",
        "public.v_hex_economic",
        "public.v_hex_heat",
        "public.v_hex_intel",
        "public.v_hex_mobilize",
        "public.v_hex_state_asof",
        "public.v_national_value_aggregate",
        "public.v_state_value_aggregate",
        "public.view_runtime_trace_emission",
    ] {
        assert!(
            migration.contains(view),
            "migration omits governed view {view}"
        );
    }
    for required in [
        "public.dynamic_hex_state",
        "public.hex_spatial_map",
        "public.hex_latest",
        "cell_id",
        "PARTITION BY h.session_id, h.cell_id",
        "m.cell_id = h.cell_id",
    ] {
        assert!(
            migration.contains(required),
            "migration loses canonical reader shape {required}"
        );
    }
    for forbidden in [
        "v_compat_",
        "v_observer_",
        "CREATE TRIGGER",
        "DROP TABLE",
        "DROP COLUMN",
        "ALTER COLUMN",
        "RustWriterAuthority",
        "persist_committed_tick",
    ] {
        assert!(
            !migration.contains(forbidden),
            "reader migration crosses its authority boundary with {forbidden}"
        );
    }
}

#[test]
fn reader_cutover_refuses_incomplete_shadows_before_replacing_views() {
    let migration = std::fs::read_to_string(crate_path("migrations/0007_h3_canonical_readers.sql"))
        .expect("epoch-7 canonical-reader migration must exist");

    for relation in [
        "dynamic_hex_state",
        "hex_activity",
        "hex_cell",
        "hex_latest",
        "hex_map",
        "hex_r8_linear_features_reference",
        "hex_r8_reference",
        "hex_spatial_map",
        "hex_state",
        "hex_substrate",
        "hex_terrain_state",
        "immutable_reference_lodes_od_matrix",
        "infrastructure_link_state",
        "org_snapshot",
        "tick_event",
    ] {
        assert!(
            migration.contains(relation),
            "precondition omits governed relation {relation}"
        );
    }
    for required in [
        "pg_catalog.to_regclass",
        "IS NULL",
        "workplace_dest_kind",
        "RAISE EXCEPTION",
    ] {
        assert!(
            migration.contains(required),
            "reader cutover loses fail-closed precondition {required}"
        );
    }
}

#[test]
fn the_closed_backfill_stays_pinned_to_its_epoch_six_input_boundary() {
    let source = std::fs::read_to_string(crate_path("src/h3_shadow_backfill.rs"))
        .expect("the closed epoch-6 backfill implementation must remain available");

    assert!(source.contains("const H3_SHADOW_SCHEMA_EPOCH: usize = 6"));
    assert!(source.contains("actual == H3_SHADOW_SCHEMA_EPOCH"));
    assert!(source.contains("expected: H3_SHADOW_SCHEMA_EPOCH"));
}
