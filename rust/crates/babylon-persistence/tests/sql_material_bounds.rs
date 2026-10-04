//! Database blob admission must follow each independently bounded native component.
use babylon_tick::material_world::{
    MAX_MATERIAL_TICK_RECEIPT_BYTES, MAX_MATERIAL_WORLD_REGISTER_BYTES,
};

const SCHEMA: &str = include_str!("../migrations/current_schema.sql");

fn maximum(table: &str, column: &str) -> usize {
    let table_start = format!("CREATE TABLE babylon_state.{table} (");
    let body = SCHEMA
        .split_once(&table_start)
        .unwrap()
        .1
        .split_once("\n);")
        .unwrap()
        .0;
    let prefix = format!("{column} bytea ");
    let declaration = body
        .lines()
        .map(str::trim)
        .find(|line| line.starts_with(&prefix))
        .unwrap();
    declaration
        .split_once(" <= ")
        .unwrap()
        .1
        .split(')')
        .next()
        .unwrap()
        .parse()
        .unwrap()
}

#[test]
fn database_blob_limits_match_their_independently_bounded_native_components() {
    assert_eq!(
        maximum("material_campaign_foundation_v3", "initial_register_bytes"),
        MAX_MATERIAL_WORLD_REGISTER_BYTES,
    );
    assert_eq!(
        maximum("material_tick_v3", "register_storage_bytes"),
        babylon_persistence::MAX_STORED_MATERIAL_REGISTER_BYTES
    );
    assert_eq!(
        maximum("material_tick_v3", "receipt_storage_bytes"),
        babylon_persistence::MAX_STORED_MATERIAL_RECEIPT_BYTES
    );
    assert_eq!(
        maximum("material_tick_v3", "lookup_delta_bytes"),
        babylon_persistence::MAX_STORED_MATERIAL_LOOKUP_DELTA_BYTES
    );
    assert!(maximum("material_tick_v3", "receipt_storage_bytes") > MAX_MATERIAL_TICK_RECEIPT_BYTES);
    assert!(
        babylon_persistence::MAX_STORED_MATERIAL_REGISTER_BYTES
            >= zstd::zstd_safe::compress_bound(MAX_MATERIAL_WORLD_REGISTER_BYTES) + 70 * 128
    );
}

#[test]
fn collection_adds_only_one_bounded_receipt_row_and_its_storage_frame() {
    use babylon_tick::material_world::{
        receipt_row_limit, RECEIPT_FAMILY_COUNT, RECEIPT_ROW_BYTES,
    };
    assert_eq!(RECEIPT_FAMILY_COUNT, 36);
    assert_eq!(RECEIPT_ROW_BYTES.last(), Some(&317));
    assert_eq!(receipt_row_limit(RECEIPT_FAMILY_COUNT - 1), 1);
    // Previous complete storage bound +9B family envelope +317B row +59B frame.
    assert_eq!(
        babylon_persistence::MAX_STORED_MATERIAL_RECEIPT_BYTES,
        872_614_379 + 9 + 317 + 59
    );
}
