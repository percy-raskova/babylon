//! Database blob admission must follow each independently bounded native component.
use babylon_persistence::material_runtime::MAX_MATERIAL_FOUNDATION_BYTES;
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
fn database_blob_limits_match_their_native_components_without_widening_receipts() {
    assert_eq!(
        maximum("material_campaign_foundation_v3", "initial_register_bytes"),
        MAX_MATERIAL_WORLD_REGISTER_BYTES,
    );
    assert_eq!(
        maximum("material_campaign_foundation_v3", "foundation_bytes"),
        MAX_MATERIAL_FOUNDATION_BYTES,
    );
    assert_eq!(
        maximum("material_tick_v3", "register_bytes"),
        MAX_MATERIAL_WORLD_REGISTER_BYTES
    );
    assert_eq!(
        maximum("material_tick_v3", "receipt_bytes"),
        MAX_MATERIAL_TICK_RECEIPT_BYTES
    );
    assert_eq!(MAX_MATERIAL_TICK_RECEIPT_BYTES, 67_108_864);
}
