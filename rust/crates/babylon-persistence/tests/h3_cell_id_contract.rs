//! Public H3 identity contracts pinned to checked-in language-neutral vectors.

use babylon_persistence::{H3CellId, H3CellIdError};
use std::mem::size_of;
use std::str::FromStr;

#[derive(Debug)]
struct ValidVector {
    label: String,
    resolution: u8,
    text: String,
    raw_u64: u64,
    sql_i64: i64,
    bytes_be: [u8; 8],
    immediate_parent: Option<String>,
    ancestor_r0: String,
}

#[derive(Debug)]
struct InvalidRawVector {
    label: String,
    raw_u64: u64,
}

#[derive(Debug)]
struct InvalidSqlVector {
    label: String,
    sql_i64: i64,
}

#[derive(Debug)]
struct InvalidTextVector {
    label: String,
    text: String,
}

#[derive(Debug)]
struct InvalidAncestorVector {
    label: String,
    text: String,
    requested_resolution: u8,
}

#[derive(Debug, Default)]
struct VectorFixture {
    valid: Vec<ValidVector>,
    invalid_raw: Vec<InvalidRawVector>,
    invalid_sql: Vec<InvalidSqlVector>,
    invalid_text: Vec<InvalidTextVector>,
    invalid_ancestor: Vec<InvalidAncestorVector>,
}

#[test]
fn h3_cell_id_layout_and_order_follow_unsigned_identity() {
    let fixture = load_fixture();
    let ordinary = fixture
        .valid
        .iter()
        .filter(|vector| vector.label.starts_with("ordinary_"))
        .collect::<Vec<_>>();
    assert_eq!(ordinary.len(), 16);
    assert_eq!(size_of::<H3CellId>(), 8);

    let mut ids = ordinary
        .iter()
        .rev()
        .map(|vector| H3CellId::try_from(vector.raw_u64).expect("fixture cell should validate"))
        .collect::<Vec<_>>();
    ids.sort_unstable();

    let sorted_raws = ids.iter().map(|cell| cell.as_u64()).collect::<Vec<_>>();
    let expected_raws = ordinary
        .iter()
        .map(|vector| vector.raw_u64)
        .collect::<Vec<_>>();
    assert_eq!(sorted_raws, expected_raws);
}

#[test]
fn h3_cell_id_round_trips_display_bytes_sql_and_semantic_parents_from_vectors() {
    let fixture = load_fixture();
    let pentagons = fixture
        .valid
        .iter()
        .filter(|vector| vector.label.starts_with("pentagon_"))
        .count();
    assert_eq!(pentagons, 12 * 16);

    for vector in &fixture.valid {
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
            from_raw.ancestor_at(0).unwrap().to_string(),
            vector.ancestor_r0
        );

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

    for vector in &fixture.invalid_raw {
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

    for vector in &fixture.invalid_sql {
        assert_eq!(
            H3CellId::try_from(vector.sql_i64),
            Err(H3CellIdError::NegativeSqlValue {
                raw: vector.sql_i64,
            }),
            "negative SQL vector {} should stay rejected",
            vector.label
        );
    }

    for vector in &fixture.invalid_text {
        assert_eq!(
            H3CellId::from_str(&vector.text),
            Err(H3CellIdError::NonCanonicalText {
                text: vector.text.clone().into_boxed_str(),
            }),
            "text vector {} should stay non-canonical",
            vector.label
        );
    }
}

#[test]
fn h3_cell_id_ancestor_requests_reject_too_fine_or_out_of_range_resolution() {
    let fixture = load_fixture();

    for vector in &fixture.invalid_ancestor {
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
                assert_eq!(error, H3CellIdError::ResolutionOutOfRange { requested: 16 })
            }
            other => panic!("unexpected invalid ancestor vector {other}"),
        }
    }
}

fn load_fixture() -> VectorFixture {
    let mut fixture = VectorFixture::default();

    for line in include_str!("fixtures/h3_cell_id_vectors_v1.txt")
        .lines()
        .filter(|line| !line.is_empty() && !line.starts_with('#'))
    {
        let fields = line.split('|').collect::<Vec<_>>();
        match fields.first().copied().unwrap_or_default() {
            "valid" => fixture.valid.push(parse_valid(&fields)),
            "invalid_raw" => fixture.invalid_raw.push(parse_invalid_raw(&fields)),
            "invalid_sql" => fixture.invalid_sql.push(parse_invalid_sql(&fields)),
            "invalid_text" => fixture.invalid_text.push(parse_invalid_text(&fields)),
            "invalid_ancestor" => fixture
                .invalid_ancestor
                .push(parse_invalid_ancestor(&fields)),
            other => panic!("unexpected fixture record kind {other}"),
        }
    }

    fixture
}

fn parse_valid(fields: &[&str]) -> ValidVector {
    assert_eq!(fields.len(), 9);
    ValidVector {
        label: fields[1].to_owned(),
        resolution: fields[2].parse().unwrap(),
        text: fields[3].to_owned(),
        raw_u64: u64::from_str_radix(fields[4], 16).unwrap(),
        sql_i64: fields[5].parse().unwrap(),
        bytes_be: parse_hex_bytes(fields[6]),
        immediate_parent: (!fields[7].is_empty()).then(|| fields[7].to_owned()),
        ancestor_r0: fields[8].to_owned(),
    }
}

fn parse_invalid_raw(fields: &[&str]) -> InvalidRawVector {
    assert_eq!(fields.len(), 3);
    InvalidRawVector {
        label: fields[1].to_owned(),
        raw_u64: u64::from_str_radix(fields[2], 16).unwrap(),
    }
}

fn parse_invalid_sql(fields: &[&str]) -> InvalidSqlVector {
    assert_eq!(fields.len(), 3);
    InvalidSqlVector {
        label: fields[1].to_owned(),
        sql_i64: fields[2].parse().unwrap(),
    }
}

fn parse_invalid_text(fields: &[&str]) -> InvalidTextVector {
    assert_eq!(fields.len(), 3);
    InvalidTextVector {
        label: fields[1].to_owned(),
        text: fields[2].to_owned(),
    }
}

fn parse_invalid_ancestor(fields: &[&str]) -> InvalidAncestorVector {
    assert_eq!(fields.len(), 4);
    InvalidAncestorVector {
        label: fields[1].to_owned(),
        text: fields[2].to_owned(),
        requested_resolution: fields[3].parse().unwrap(),
    }
}

fn parse_hex_bytes(raw_hex16: &str) -> [u8; 8] {
    assert_eq!(raw_hex16.len(), 16);
    let mut bytes = [0_u8; 8];
    for (index, chunk) in raw_hex16.as_bytes().chunks(2).enumerate() {
        let pair = std::str::from_utf8(chunk).unwrap();
        bytes[index] = u8::from_str_radix(pair, 16).unwrap();
    }
    bytes
}
