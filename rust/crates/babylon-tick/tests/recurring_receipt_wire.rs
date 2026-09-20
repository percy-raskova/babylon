//! Independent vectors for recurring demand, consumption, firm plans and prices.
use babylon_tick::material_world::{decode_material_receipts, MaterialWorldError};

const DOMAIN: &[u8] = b"babylon.material-tick-receipts.v7\0";

fn words(ids: &[u8], values: &[u64]) -> Vec<u8> {
    let mut bytes = Vec::new();
    for id in ids {
        bytes.extend_from_slice(&[*id; 32]);
    }
    for value in values {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes
}

fn demand() -> Vec<u8> {
    let mut bytes = words(&[1, 2, 3, 4, 5], &[7, 2, 6, 5, 4, 3, 2, 1]);
    bytes.extend_from_slice(&11_i128.to_be_bytes());
    bytes
}

fn consumption() -> Vec<u8> {
    words(&[1, 3, 4], &[7, 6, 4, 4, 2, 0])
}

fn procurement() -> Vec<u8> {
    let mut bytes = words(&[5, 1, 2, 3, 4], &[7, 2, 3, 10, 4, 3]);
    bytes.extend_from_slice(&11_i128.to_be_bytes());
    bytes
}

fn plan() -> Vec<u8> {
    words(&[1, 2], &[7, 8, 3, 2, 1, 4, 4])
}

fn price(reason: u8, old: i128, next: i128, unserved: u64, stock: u64) -> Vec<u8> {
    let mut bytes = words(&[1, 3, 4], &[7]);
    for value in [old, next] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes.extend_from_slice(&unserved.to_be_bytes());
    bytes.extend_from_slice(&stock.to_be_bytes());
    bytes.push(reason);
    bytes
}

fn envelope(family: u8, rows: &[Vec<u8>]) -> Vec<u8> {
    let mut bytes = DOMAIN.to_vec();
    bytes.extend_from_slice(&7_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=18 {
        bytes.push(tag);
        let count = if tag == family { rows.len() as u64 } else { 0 };
        bytes.extend_from_slice(&count.to_be_bytes());
        if tag == family {
            for row in rows {
                bytes.extend_from_slice(row);
            }
        }
    }
    bytes
}

fn changed_u64(row: &[u8], offset: usize, value: u64) -> Vec<u8> {
    let mut changed = row.to_vec();
    changed[offset..offset + 8].copy_from_slice(&value.to_be_bytes());
    changed
}

#[test]
fn recurring_families_admit_complete_independent_vectors() {
    for (tag, row, width) in [
        (14, demand(), 240),
        (15, consumption(), 144),
        (16, procurement(), 224),
        (17, plan(), 120),
        (18, price(3, 11, 12, 1, 0), 153),
    ] {
        assert_eq!(row.len(), width);
        assert!(
            decode_material_receipts(&envelope(tag, &[row])).is_ok(),
            "family {tag}"
        );
    }
}

#[test]
fn zero_admission_and_unmet_need_remain_valid_evidence() {
    let mut row = demand();
    for index in 4..=7 {
        row = changed_u64(&row, 160 + index * 8, 0);
    }
    assert!(decode_material_receipts(&envelope(14, &[row])).is_ok());
    let row = words(&[1, 3, 4], &[7, 6, 0, 0, 6, 0]);
    assert!(decode_material_receipts(&envelope(15, &[row])).is_ok());
    let row = changed_u64(&procurement(), 200, 0);
    assert!(decode_material_receipts(&envelope(16, &[row])).is_ok());
    let row = words(&[1, 2], &[7, 8, 0, 0, 4, 4, 0]);
    assert!(decode_material_receipts(&envelope(17, &[row])).is_ok());
}

#[test]
fn recurring_quantities_refuse_false_partitions_periods_and_overflow() {
    for (tag, row, offset, value) in [
        (14, demand(), 160, 8),
        (14, demand(), 176, 0),
        (14, demand(), 184, 3),
        (14, demand(), 192, 6),
        (14, demand(), 200, 5),
        (14, demand(), 208, 3),
        (14, demand(), 216, u64::MAX),
        (15, consumption(), 96, 8),
        (15, consumption(), 104, 0),
        (15, consumption(), 120, 3),
        (15, consumption(), 128, 3),
        (15, consumption(), 136, u64::MAX),
        (16, procurement(), 160, 8),
        (16, procurement(), 168, u64::MAX),
        (16, procurement(), 192, 6),
        (16, procurement(), 200, 5),
        (17, plan(), 64, 8),
        (17, plan(), 72, 9),
        (17, plan(), 80, u64::MAX),
        (17, plan(), 112, 0),
        (17, plan(), 112, 9),
    ] {
        assert_eq!(
            decode_material_receipts(&envelope(tag, &[changed_u64(&row, offset, value)])),
            Err(MaterialWorldError::Wire),
            "family {tag}, offset {offset}"
        );
    }
}

#[test]
fn procurement_refuses_self_purchase_and_nonpositive_or_unpayable_prices() {
    let mut row = procurement();
    row[64..96].copy_from_slice(&[1; 32]);
    assert!(decode_material_receipts(&envelope(16, &[row])).is_err());
    for (tag, original, offset) in [(14, demand(), 224), (16, procurement(), 208)] {
        for value in [0, -1, i128::MAX] {
            let mut row = original.clone();
            row[offset..offset + 16].copy_from_slice(&value.to_be_bytes());
            assert!(decode_material_receipts(&envelope(tag, &[row])).is_err());
        }
    }
}

#[test]
fn price_reasons_preserve_direction_without_claiming_absent_policy_bounds() {
    for row in [
        price(1, 11, 11, 4, 8),
        price(2, 11, 11, 0, 8),
        price(3, 11, 12, 1, 0),
        price(3, 11, 11, 1, 0),
        price(4, 11, 10, 0, 2),
        price(4, 11, 11, 0, 2),
    ] {
        assert!(decode_material_receipts(&envelope(18, &[row])).is_ok());
    }
    for row in [
        price(0, 11, 11, 0, 0),
        price(5, 11, 11, 0, 0),
        price(1, 11, 12, 0, 0),
        price(2, 11, 10, 0, 0),
        price(3, 11, 10, 1, 0),
        price(3, 11, 12, 0, 0),
        price(4, 11, 12, 0, 2),
        price(4, 11, 10, 1, 2),
        price(4, 11, 10, 0, 0),
        price(1, 0, 0, 0, 0),
    ] {
        assert!(decode_material_receipts(&envelope(18, &[row])).is_err());
    }
}

#[test]
fn recurring_keys_are_unique_and_strictly_canonical() {
    for (tag, row) in [
        (14, demand()),
        (15, consumption()),
        (16, procurement()),
        (17, plan()),
        (18, price(1, 11, 11, 0, 0)),
    ] {
        assert!(decode_material_receipts(&envelope(tag, &[row.clone(), row.clone()])).is_err());
        let mut later = row.clone();
        let key_offset = if tag == 16 { 32 } else { 0 };
        later[key_offset..key_offset + 32].fill(9);
        if tag == 14 {
            later[128..160].fill(9);
        }
        if tag == 16 {
            later[..32].fill(9);
        }
        assert!(decode_material_receipts(&envelope(tag, &[row.clone(), later.clone()])).is_ok());
        assert!(decode_material_receipts(&envelope(tag, &[later, row])).is_err());
    }
}

#[test]
fn quoted_order_ids_remain_unique_even_under_distinct_policy_keys() {
    for (tag, row, offset) in [(14, demand(), 0), (16, procurement(), 32)] {
        let mut later = row.clone();
        later[offset..offset + 32].fill(9);
        assert!(decode_material_receipts(&envelope(tag, &[row, later])).is_err());
    }
}

#[test]
fn recurring_envelope_refuses_previous_schema_wrong_tags_and_every_truncated_prefix() {
    let bytes = envelope(14, &[demand()]);
    for end in 0..bytes.len() {
        assert!(
            decode_material_receipts(&bytes[..end]).is_err(),
            "length {end}"
        );
    }
    let mut extra = bytes.clone();
    extra.push(0);
    assert!(decode_material_receipts(&extra).is_err());
    let mut wrong_tag = bytes.clone();
    wrong_tag[DOMAIN.len() + 12 + 13 * 9] = 15;
    assert!(decode_material_receipts(&wrong_tag).is_err());
    let mut old = b"babylon.material-tick-receipts.v6\0".to_vec();
    old.extend_from_slice(&6_u32.to_be_bytes());
    old.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=13 {
        old.push(tag);
        old.extend_from_slice(&0_u64.to_be_bytes());
    }
    assert!(decode_material_receipts(&old).is_err());
    let mut old_version = bytes;
    old_version[DOMAIN.len()..DOMAIN.len() + 4].copy_from_slice(&6_u32.to_be_bytes());
    assert!(decode_material_receipts(&old_version).is_err());
}

#[test]
fn two_pass_handling_evidence_can_exceed_one_state_table() {
    use babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS;
    let rows: Vec<_> = (0..=MAX_MATERIAL_CIRCUIT_ROWS)
        .map(|index| {
            let mut row = words(&[1], &[]);
            row.push(1);
            row.extend(words(&[0], &[1, 1, 1, 1]));
            row[57..65].copy_from_slice(&(index as u64).to_be_bytes());
            row
        })
        .collect();
    assert!(decode_material_receipts(&envelope(7, &rows)).is_ok());
}

#[test]
fn every_family_keeps_its_explicit_row_and_whole_envelope_bounds() {
    use babylon_material_circuit::{MAX_MATERIAL_CIRCUIT_ROWS, MAX_MONEY_TRANSFERS_PER_PERIOD};
    use babylon_tick::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES;
    for tag in 1..=18_u8 {
        let limit = match tag {
            7 => 2 * MAX_MATERIAL_CIRCUIT_ROWS,
            11 => MAX_MONEY_TRANSFERS_PER_PERIOD,
            _ => MAX_MATERIAL_CIRCUIT_ROWS,
        };
        let mut bytes = envelope(0, &[]);
        let offset = DOMAIN.len() + 12 + usize::from(tag - 1) * 9 + 1;
        bytes[offset..offset + 8].copy_from_slice(&((limit + 1) as u64).to_be_bytes());
        assert_eq!(
            decode_material_receipts(&bytes),
            Err(MaterialWorldError::ByteLimit),
            "family {tag}"
        );
    }
    let mut bytes = envelope(0, &[]);
    bytes.resize(MAX_MATERIAL_WORLD_REGISTER_BYTES + 1, 0);
    assert!(decode_material_receipts(&bytes).is_err());
}
