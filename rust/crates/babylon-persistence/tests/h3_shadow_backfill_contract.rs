//! Pure contracts for the additive H3 shadow-key and maintenance backfill boundary.

use std::path::PathBuf;

fn crate_path(relative: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(relative)
}

#[test]
fn epoch_six_adds_only_the_governed_h3_shadow_surface() {
    let migration = std::fs::read_to_string(crate_path("migrations/0006_h3_shadow_keys.sql"))
        .expect("epoch-6 H3 shadow-key migration must exist");

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
            "migration omits governed H3 relation {relation}"
        );
    }
    for shadow in [
        "cell_id",
        "ancestor_r5",
        "ancestor_r6",
        "parent_cell_id",
        "ancestor_r7",
        "home_cell_id",
        "workplace_cell_id",
        "source_cell_id",
        "target_cell_id",
    ] {
        assert!(
            migration.contains(shadow),
            "migration omits governed shadow key {shadow}"
        );
    }
    for required in [
        "BIGINT",
        "CHECK",
        "FOREIGN KEY",
        "REFERENCES babylon_ref.h3_cell(cell_id)",
        "CREATE INDEX",
        "pg_catalog.to_regclass",
    ] {
        assert!(
            migration.contains(required),
            "migration loses required additive shape {required}"
        );
    }
    for forbidden in [
        "CREATE VIEW",
        "CREATE TRIGGER",
        "DROP COLUMN",
        "ALTER COLUMN h3_index",
        "SET NOT NULL",
        "UPDATE public.",
    ] {
        assert!(
            !migration.contains(forbidden),
            "P3 migration crosses the authority boundary with {forbidden}"
        );
    }
}

#[test]
fn backfill_is_a_closed_maintenance_api_not_a_runtime_writer() {
    let lib = std::fs::read_to_string(crate_path("src/lib.rs")).unwrap();
    let backfill = std::fs::read_to_string(crate_path("src/h3_shadow_backfill.rs"))
        .expect("bounded H3 shadow backfill module must exist");

    assert!(lib.contains("mod h3_shadow_backfill;"));
    assert!(lib.contains("backfill_legacy_h3_shadow_keys"));
    for required in [
        "pub const H3_SHADOW_RELATION_COUNT: usize = 15",
        "pub const H3_SHADOW_FIELD_COUNT: usize = 21",
        "validate_legacy_connection_target",
        "acquire_lock",
        "inspect_schema_epoch_under_lock",
        "CURRENT_SCHEMA_EPOCH",
        "IsolationLevel::Serializable",
        "synchronous_commit TO on",
        "MAX_H3_SHADOW_BACKFILL_BATCH_ROWS",
        "MAX_H3_SHADOW_BACKFILL_COMMIT_ATTEMPTS",
        "MAX_H3_SHADOW_BACKFILL_ISSUES",
        "BTreeSet",
        "H3CellId",
        "sha256_of",
        "ordered_semantic_hash",
        "distinct_semantic_group_count",
        "pg_catalog.int8",
        "COALESCE",
    ] {
        assert!(
            backfill.contains(required),
            "backfill loses required maintenance contract {required}"
        );
    }
    for forbidden in [
        "std::env",
        "option_env!",
        "INSERT INTO babylon_ref.h3_cell",
        "CREATE VIEW",
        "CREATE TRIGGER",
        "RustWriterAuthority",
        "pg_catalog.bigint",
        "pg_catalog.coalesce",
    ] {
        assert!(
            !backfill.contains(forbidden),
            "backfill exposes forbidden runtime authority {forbidden}"
        );
    }
}

#[test]
fn python_copy_shapes_carry_null_shadow_slots_without_becoming_dual_writers() {
    let hydrator = std::fs::read_to_string(crate_path(
        "../../../src/babylon/persistence/hex_hydrator.py",
    ))
    .unwrap();

    let spatial = hydrator
        .split_once("CREATE TEMP TABLE _hex_spatial_map_tmp")
        .unwrap()
        .1
        .split_once("ON COMMIT DROP")
        .unwrap()
        .0;
    let state = hydrator
        .split_once("CREATE TEMP TABLE _hex_state_tmp")
        .unwrap()
        .1
        .split_once("ON COMMIT DROP")
        .unwrap()
        .0;

    assert!(spatial.contains("cell_id BIGINT"));
    assert!(state.contains("cell_id BIGINT"));
    assert!(hydrator.contains("cell_id) SELECT"));
    assert!(!hydrator.contains("int(row.h3_index"));
    assert!(!hydrator.contains("H3CellId"));
}
