//! Independent vectors for exact monetary postings and finite attendance evidence.
use babylon_tick::material_world::{decode_material_receipts, MaterialWorldError};

const DOMAIN: &[u8] = b"babylon.material-tick-receipts.v13\0";

fn tagged(tag: u8, subtag: u8, id: u8) -> Vec<u8> {
    let mut bytes = vec![tag, subtag];
    bytes.extend_from_slice(&[id; 32]);
    bytes
}

fn transfer(debit: i128, credit: i128) -> Vec<u8> {
    let mut bytes = tagged(1, 1, 3); // reservation, routed order 3
    bytes.extend(tagged(1, 2, 2)); // household cash
    bytes.extend_from_slice(&debit.to_be_bytes());
    bytes.extend(tagged(2, 1, 3)); // the same routed order's reserve
    bytes.extend_from_slice(&credit.to_be_bytes());
    bytes
}

fn accrual() -> Vec<u8> {
    accrual_hours(4)
}
fn accrual_hours(hours: u64) -> Vec<u8> {
    let mut key = b"babylon.member-funded-attendance.v1\0".to_vec();
    key.extend_from_slice(&7_u64.to_be_bytes());
    for id in [4, 1, 5, 2] {
        key.extend_from_slice(&[id; 32]);
    }
    let mut bytes = babylon_kernel::content_digest::sha256_of(&key).to_vec();
    bytes.push(1); // employer site
    bytes.extend_from_slice(&[1; 32]);
    bytes.push(2); // payee household
    bytes.extend_from_slice(&[2; 32]);
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    bytes.extend_from_slice(&hours.to_be_bytes());
    bytes.extend_from_slice(&(i128::from(hours) * 3).to_be_bytes());
    bytes
}

fn labor(values: [u64; 8]) -> Vec<u8> {
    let [period, available, planned, unplanned, funded, unfunded, used, idle] = values;
    let mut bytes = Vec::new();
    for id in [1, 5] {
        bytes.extend_from_slice(&[id; 32]);
    }
    for value in [
        period, available, planned, unplanned, funded, unfunded, 0, used, idle, 0,
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes
}

fn member(labor: &[u8]) -> Vec<u8> {
    let hours: Vec<_> = labor[64..]
        .chunks_exact(8)
        .map(|n| u64::from_be_bytes(n.try_into().unwrap()))
        .collect();
    let mut bytes = Vec::new();
    for id in [4, 1, 5, 2] {
        bytes.extend_from_slice(&[id; 32]);
    }
    bytes.push(1);
    bytes.extend_from_slice(&3_i128.to_be_bytes());
    for value in [
        hours[0], hours[1], hours[2], hours[3], hours[4], hours[5], hours[7], 0, 0, 0, hours[8],
    ] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    for value in [hours[4], hours[7], 0, 0, 0, hours[8]] {
        bytes.extend_from_slice(&(i128::from(value) * 3).to_be_bytes());
    }
    bytes
}

fn envelope(transfers: &[Vec<u8>], wages: &[Vec<u8>], labor: &[Vec<u8>]) -> Vec<u8> {
    let members: Vec<_> = labor.iter().map(|r| member(r)).collect();
    let mut bytes = DOMAIN.to_vec();
    bytes.extend_from_slice(&13_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=32 {
        let rows = match tag {
            11 => transfers,
            12 => wages,
            13 => labor,
            29 => &members,
            _ => &[],
        };
        bytes.push(tag);
        bytes.extend_from_slice(&u64::try_from(rows.len()).unwrap().to_be_bytes());
        for row in rows {
            bytes.extend_from_slice(row);
        }
    }
    bytes
}

#[test]
fn current_receipts_admit_exact_postings_accrual_and_paid_idle_hours() {
    let bytes = envelope(
        &[transfer(-30, 30)],
        &[accrual()],
        &[labor([7, 8, 6, 2, 4, 2, 1, 3])],
    );
    let decoded = decode_material_receipts(&bytes).unwrap();
    assert_eq!(decoded.resolve_tick, 7);
    assert_eq!(decoded.money_transfers.len(), 1);
    assert_eq!(decoded.money_transfers[0].debit.delta.micro_units(), -30);
    assert_eq!(decoded.money_transfers[0].credit.delta.micro_units(), 30);
    assert_eq!(decoded.wage_accruals[0].obligated_hours, 4);
    assert_eq!(decoded.wage_accruals[0].amount.micro_units(), 12);
    assert_eq!(decoded.labor_use[0].planned_hours, 6);
    assert_eq!(decoded.labor_use[0].unplanned_hours, 2);
    assert_eq!(decoded.labor_use[0].funded_hours, 4);
    assert_eq!(decoded.labor_use[0].used_hours, 1);
    assert_eq!(decoded.labor_use[0].paid_idle_hours, 3);
}

#[test]
fn current_receipts_admit_unfunded_and_fully_idle_attendance() {
    for hours in [
        [7, 8, 6, 2, 0, 6, 0, 0],
        [7, 8, 6, 2, 6, 0, 0, 6],
        [7, 8, 0, 8, 0, 0, 0, 0],
    ] {
        let wages = if hours[4] == 0 {
            vec![]
        } else {
            vec![accrual_hours(hours[4])]
        };
        assert!(decode_material_receipts(&envelope(&[], &wages, &[labor(hours)])).is_ok());
    }
}

#[test]
fn money_postings_refuse_unbalanced_zero_reversed_and_overflowing_signs() {
    for (debit, credit) in [(-30, 29), (30, -30), (0, 0), (i128::MIN, i128::MAX)] {
        assert_eq!(
            decode_material_receipts(&envelope(&[transfer(debit, credit)], &[], &[])),
            Err(MaterialWorldError::Wire)
        );
    }
}

#[test]
fn money_postings_refuse_wrong_reserve_and_unknown_tags() {
    for (offset, value) in [(0, 8), (1, 3), (34, 4), (35, 5), (84, 3), (86, 9)] {
        let mut row = transfer(-30, 30);
        row[offset] = value;
        assert_eq!(
            decode_material_receipts(&envelope(&[row], &[], &[])),
            Err(MaterialWorldError::Wire),
            "offset {offset}"
        );
    }
}

#[test]
fn wage_and_labor_receipts_refuse_false_periods_amounts_and_partitions() {
    for (offset, bytes) in [
        (98, 8_u64.to_be_bytes().to_vec()),
        (106, 0_u64.to_be_bytes().to_vec()),
        (114, 0_i128.to_be_bytes().to_vec()),
        (114, (-1_i128).to_be_bytes().to_vec()),
    ] {
        let mut row = accrual();
        row[offset..offset + bytes.len()].copy_from_slice(&bytes);
        assert_eq!(
            decode_material_receipts(&envelope(&[], &[row], &[])),
            Err(MaterialWorldError::Wire)
        );
    }
    for hours in [
        [8, 8, 6, 2, 4, 2, 1, 3],
        [7, 7, 6, 2, 4, 2, 1, 3],
        [7, 8, 5, 3, 4, 2, 1, 3],
        [7, 8, 6, 2, 4, 2, 2, 3],
        [7, u64::MAX, u64::MAX, 1, u64::MAX, 0, 0, u64::MAX],
        [7, u64::MAX, u64::MAX, 0, u64::MAX, 1, 0, u64::MAX],
        [7, u64::MAX, u64::MAX, 0, u64::MAX, 0, u64::MAX, 1],
    ] {
        assert_eq!(
            decode_material_receipts(&envelope(&[], &[], &[labor(hours)])),
            Err(MaterialWorldError::Wire)
        );
    }
}

#[test]
fn monetary_receipts_refuse_duplicate_attendance_truncation_and_old_schema() {
    let wages = accrual();
    assert!(decode_material_receipts(&envelope(&[], &[wages.clone(), wages], &[])).is_err());
    let hours = labor([7, 8, 6, 2, 4, 2, 1, 3]);
    assert!(decode_material_receipts(&envelope(&[], &[], &[hours.clone(), hours])).is_err());
    let bytes = envelope(&[transfer(-30, 30)], &[accrual()], &[]);
    assert!(decode_material_receipts(&bytes[..bytes.len() - 1]).is_err());
    let mut trailing = bytes;
    trailing.push(0);
    assert!(decode_material_receipts(&trailing).is_err());
    let mut previous = b"babylon.material-tick-receipts.v5\0".to_vec();
    previous.extend_from_slice(&5_u32.to_be_bytes());
    previous.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=10 {
        previous.push(tag);
        previous.extend_from_slice(&0_u64.to_be_bytes());
    }
    assert!(decode_material_receipts(&previous).is_err());
}

fn movement(purpose: Vec<u8>, debit: Vec<u8>, credit: Vec<u8>) -> Vec<u8> {
    let mut row = purpose;
    row.extend(debit);
    row.extend_from_slice(&(-12_i128).to_be_bytes());
    row.extend(credit);
    row.extend_from_slice(&12_i128.to_be_bytes());
    row
}

#[test]
fn all_money_purposes_keep_account_and_reserve_namespaces_distinct() {
    let rows = [
        movement(tagged(1, 2, 3), tagged(1, 2, 2), tagged(2, 2, 3)),
        movement(tagged(2, 2, 3), tagged(2, 2, 3), tagged(1, 1, 1)),
        movement(tagged(3, 2, 3), tagged(2, 2, 3), tagged(1, 2, 2)),
        movement(tagged(4, 0, 4), tagged(1, 1, 1), tagged(3, 0, 4)),
        movement(tagged(5, 0, 4), tagged(3, 0, 4), tagged(1, 2, 2)),
        movement(tagged(6, 0, 4), tagged(3, 0, 4), tagged(1, 1, 1)),
    ];
    assert!(decode_material_receipts(&envelope(&rows, &[], &[])).is_ok());
    for purpose in [3, 6, 7] {
        let row = movement(tagged(7, purpose, 0), tagged(1, 3, 1), tagged(1, 4, 1));
        assert!(decode_material_receipts(&envelope(&[row], &[], &[])).is_ok());
    }
    // Current fiscal/ownership purposes additionally require matched policy receipts.
    // Their complete valid vectors live in financial_receipt_wire.rs.
    for purpose in [1, 2, 4, 5] {
        let orphan = movement(tagged(7, purpose, 0), tagged(1, 3, 1), tagged(1, 4, 1));
        assert!(decode_material_receipts(&envelope(&[orphan], &[], &[])).is_err());
    }
}

#[test]
fn cash_and_shift_postings_refuse_noncanonical_padding_and_self_transfers() {
    let rows = [
        movement(tagged(7, 7, 1), tagged(1, 3, 1), tagged(1, 4, 1)),
        movement(tagged(7, 8, 0), tagged(1, 3, 1), tagged(1, 4, 1)),
        movement(tagged(7, 7, 0), tagged(1, 3, 1), tagged(1, 3, 1)),
        movement(tagged(4, 1, 4), tagged(1, 1, 1), tagged(3, 0, 4)),
        movement(tagged(4, 0, 4), tagged(1, 1, 1), tagged(3, 1, 4)),
        movement(tagged(5, 0, 4), tagged(3, 0, 5), tagged(1, 2, 2)),
    ];
    for row in rows {
        assert_eq!(
            decode_material_receipts(&envelope(&[row], &[], &[])),
            Err(MaterialWorldError::Wire)
        );
    }
}

#[test]
fn transfer_family_uses_derived_movement_bound_instead_of_state_row_bound() {
    use babylon_material_circuit::{MAX_MATERIAL_CIRCUIT_ROWS, MAX_MONEY_TRANSFERS_PER_PERIOD};
    let rows = vec![transfer(-1, 1); MAX_MATERIAL_CIRCUIT_ROWS + 1];
    let bytes = envelope(&rows, &[], &[]);
    assert_eq!(
        decode_material_receipts(&bytes)
            .unwrap()
            .money_transfers
            .len(),
        rows.len()
    );
    let mut excessive = envelope(&[], &[], &[]);
    let count_offset = DOMAIN.len() + 12 + 10 * 9 + 1;
    excessive[count_offset..count_offset + 8].copy_from_slice(
        &u64::try_from(MAX_MONEY_TRANSFERS_PER_PERIOD + 1)
            .unwrap()
            .to_be_bytes(),
    );
    assert_eq!(
        decode_material_receipts(&excessive),
        Err(MaterialWorldError::ByteLimit)
    );
}
