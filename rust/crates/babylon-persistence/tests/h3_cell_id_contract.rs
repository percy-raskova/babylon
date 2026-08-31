//! Public H3 identity contracts pinned to checked-in language-neutral vectors.

use babylon_persistence::{H3CellId, H3CellIdError};
use std::mem::size_of;
use std::path::Path;
use std::str::FromStr;

#[path = "support/h3_cell_vectors.rs"]
mod h3_cell_vectors;

use h3_cell_vectors::{
    load_fixture, INVALID_ANCESTOR_VECTOR_COUNT, INVALID_RAW_VECTOR_COUNT,
    INVALID_SQL_VECTOR_COUNT, INVALID_TEXT_VECTOR_COUNT, PENTAGON_VECTOR_COUNT, VALID_VECTOR_COUNT,
};

const POSTGRES_DOCKERFILE: &str = include_str!("../../../../docker/postgres/Dockerfile");
const POSTGRES_INITDB: &str = concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../docker/postgres/initdb"
);
const MAX_INITDB_ENTRIES: usize = 64;

#[test]
fn postgres_test_image_pins_h3_pg_without_activating_it() {
    assert!(POSTGRES_DOCKERFILE.starts_with("# syntax=docker/dockerfile:1.6\n"));
    for required in [
        "postgis/postgis:17-3.5-alpine@sha256:08f4b1e1f4a571008c60272ceb9e0d1f9f8f643792d006b74a35b1bec44c2218",
        "https://github.com/postgis/h3-pg/archive/refs/tags/v4.5.0.tar.gz",
        "sha256:c54c119e1d9a578d5cbcce22f6c66dab2b5a45219fc2b260619807f7f061e53a",
        "https://github.com/uber/h3/archive/refs/tags/v4.5.0.tar.gz",
        "sha256:0da8a392a6ff77e76b60e6a331a49497d0935b6b7b6899da7a3e2786139b0441",
        "-DFETCHCONTENT_SOURCE_DIR_H3=/tmp/h3-core-source",
        "--component h3-pg",
    ] {
        assert!(
            POSTGRES_DOCKERFILE.contains(required),
            "PostgreSQL test image lost pinned H3 build input {required:?}"
        );
    }
    assert!(!POSTGRES_DOCKERFILE
        .to_ascii_uppercase()
        .contains("CREATE EXTENSION H3"));
    assert_initdb_does_not_activate_h3(Path::new(POSTGRES_INITDB));
}

fn assert_initdb_does_not_activate_h3(initdb: &Path) {
    let entries = std::fs::read_dir(initdb)
        .unwrap_or_else(|error| panic!("failed to read {}: {error}", initdb.display()))
        .take(MAX_INITDB_ENTRIES + 1)
        .collect::<Result<Vec<_>, _>>()
        .unwrap_or_else(|error| panic!("failed to enumerate {}: {error}", initdb.display()));
    assert!(
        entries.len() <= MAX_INITDB_ENTRIES,
        "initdb entry count exceeds the static test bound"
    );
    for entry in entries.iter().take(MAX_INITDB_ENTRIES) {
        assert!(
            entry
                .file_type()
                .expect("initdb file type must resolve")
                .is_file(),
            "initdb contract remains a bounded flat file set"
        );
        let body = std::fs::read_to_string(entry.path())
            .unwrap_or_else(|error| panic!("failed to read {}: {error}", entry.path().display()));
        assert!(
            !body.to_ascii_uppercase().contains("CREATE EXTENSION H3"),
            "initdb file {} must not activate the test-only H3 oracle",
            entry.path().display()
        );
    }
}

#[test]
fn h3_cell_id_layout_and_order_follow_unsigned_identity() {
    let fixture = load_fixture();
    let ordinary = fixture
        .valid
        .iter()
        .take(VALID_VECTOR_COUNT)
        .filter(|vector| vector.label.starts_with("ordinary_"))
        .collect::<Vec<_>>();
    assert_eq!(ordinary.len(), 16);
    assert_eq!(size_of::<H3CellId>(), 8);

    let mut ids = ordinary
        .iter()
        .take(16)
        .rev()
        .map(|vector| H3CellId::try_from(vector.raw_u64).expect("fixture cell should validate"))
        .collect::<Vec<_>>();
    ids.sort_unstable();

    let sorted_raws = ids
        .iter()
        .take(16)
        .map(|cell| cell.as_u64())
        .collect::<Vec<_>>();
    let expected_raws = ordinary
        .iter()
        .take(16)
        .map(|vector| vector.raw_u64)
        .collect::<Vec<_>>();
    assert_eq!(sorted_raws, expected_raws);

    let mut raw_order = fixture
        .valid
        .iter()
        .take(VALID_VECTOR_COUNT)
        .map(|vector| H3CellId::try_from(vector.raw_u64).expect("fixture cell should validate"))
        .collect::<Vec<_>>();
    let mut resolution_then_raw = raw_order.clone();
    raw_order.sort_unstable();
    resolution_then_raw.sort_unstable_by_key(|cell| (cell.resolution(), cell.as_u64()));

    assert_eq!(raw_order, resolution_then_raw);
    for resolution in 0_u8..16 {
        assert_eq!(
            raw_order
                .iter()
                .take(VALID_VECTOR_COUNT)
                .filter(|cell| cell.resolution() == resolution)
                .count(),
            13,
            "raw order contract must cover every ordinary and pentagon vector at resolution {resolution}"
        );
    }
}

#[test]
fn h3_cell_id_round_trips_display_bytes_sql_and_semantic_parents_from_vectors() {
    let fixture = load_fixture();
    let pentagons = fixture
        .valid
        .iter()
        .take(VALID_VECTOR_COUNT)
        .filter(|vector| vector.label.starts_with("pentagon_"))
        .count();
    assert_eq!(pentagons, PENTAGON_VECTOR_COUNT);

    for vector in fixture.valid.iter().take(VALID_VECTOR_COUNT) {
        let from_raw =
            H3CellId::try_from(vector.raw_u64).expect("fixture raw cell should validate");
        assert_eq!(from_raw.as_u64(), vector.raw_u64);
        assert_eq!(from_raw.resolution(), vector.resolution);
        assert_eq!(from_raw.to_string(), vector.text);
        assert_eq!(H3CellId::from_str(&vector.text).unwrap(), from_raw);
        assert_eq!(from_raw.to_be_bytes(), vector.bytes_be);
        assert_eq!(i64::try_from(from_raw).unwrap(), vector.sql_i64);
        assert_eq!(H3CellId::try_from(vector.sql_i64).unwrap(), from_raw);
        assert_eq!(
            vector.ancestor_chain_r0_to_self.len(),
            usize::from(vector.resolution) + 1
        );
        for (requested_resolution, expected_ancestor) in
            vector.ancestor_chain_r0_to_self.iter().take(16).enumerate()
        {
            let requested_resolution = u8::try_from(requested_resolution).unwrap();
            assert_eq!(
                vector.ancestor_at(requested_resolution),
                Some(expected_ancestor.as_str())
            );
            assert_eq!(
                from_raw
                    .ancestor_at(requested_resolution)
                    .unwrap()
                    .to_string(),
                *expected_ancestor
            );
        }

        if let Some(parent) = &vector.immediate_parent {
            assert_eq!(from_raw.immediate_parent().unwrap().to_string(), *parent);
            assert_eq!(
                from_raw
                    .ancestor_at(vector.resolution.saturating_sub(1))
                    .unwrap()
                    .to_string(),
                *parent
            );
        } else {
            assert_eq!(from_raw.immediate_parent(), None);
        }
    }
}

#[test]
fn h3_cell_id_validation_rejects_invalid_raw_vectors() {
    let fixture = load_fixture();

    for vector in fixture.invalid_raw.iter().take(INVALID_RAW_VECTOR_COUNT) {
        assert_eq!(
            H3CellId::try_from(vector.raw_u64),
            Err(H3CellIdError::InvalidCellIndex {
                raw: vector.raw_u64,
            }),
            "raw invalid vector {} should stay rejected",
            vector.label
        );
    }
}

#[test]
fn h3_cell_id_validation_rejects_invalid_sql_and_text_vectors() {
    let fixture = load_fixture();

    for vector in fixture.invalid_sql.iter().take(INVALID_SQL_VECTOR_COUNT) {
        assert_eq!(
            H3CellId::try_from(vector.sql_i64),
            Err(H3CellIdError::NegativeSqlValue {
                raw: vector.sql_i64,
            }),
            "negative SQL vector {} should stay rejected",
            vector.label
        );
    }

    for vector in fixture.invalid_text.iter().take(INVALID_TEXT_VECTOR_COUNT) {
        let expected = match vector.label.as_str() {
            "upper_case" => H3CellIdError::NonLowercaseHexText,
            "prefixed" => H3CellIdError::InvalidTextLength { actual_bytes: 17 },
            "leading_zero" | "long" => H3CellIdError::InvalidTextLength { actual_bytes: 16 },
            "short" => H3CellIdError::InvalidTextLength { actual_bytes: 14 },
            "non_ascii" => H3CellIdError::NonAsciiText,
            other => panic!("unexpected invalid text vector {other}"),
        };
        assert_eq!(
            H3CellId::from_str(&vector.text),
            Err(expected),
            "text vector {} should stay rejected",
            vector.label
        );
    }
}

#[test]
fn h3_cell_id_ancestor_requests_reject_too_fine_or_out_of_range_resolution() {
    let fixture = load_fixture();

    for vector in fixture
        .invalid_ancestor
        .iter()
        .take(INVALID_ANCESTOR_VECTOR_COUNT)
    {
        let cell = H3CellId::from_str(&vector.text).expect("fixture ancestor cell is valid");
        let error = cell.ancestor_at(vector.requested_resolution).unwrap_err();
        match vector.label.as_str() {
            "too_fine_parent" => assert_eq!(
                error,
                H3CellIdError::AncestorResolutionTooFine {
                    current: 10,
                    requested: 11,
                }
            ),
            "resolution_above_15" => {
                assert_eq!(error, H3CellIdError::ResolutionOutOfRange { requested: 16 });
            }
            other => panic!("unexpected invalid ancestor vector {other}"),
        }
    }
}
