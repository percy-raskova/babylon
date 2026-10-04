//! Independent current wire bytes, rather than an encoder roundtrip alone.
use super::*;

fn time_receipts(rows: usize) -> Vec<u8> {
    let mut bytes = b"babylon.material-tick-receipts.v17\0".to_vec();
    bytes.extend_from_slice(&17_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=36_u8 {
        bytes.push(tag);
        bytes.extend_from_slice(&(if tag == 34 { rows as u64 } else { 0 }).to_be_bytes());
        if tag != 34 {
            continue;
        }
        for _ in 0..rows {
            bytes.extend_from_slice(&[1; 32]);
            bytes.extend_from_slice(&1_u64.to_be_bytes());
            bytes.extend_from_slice(&[2; 32]);
            // Gross32, attendance0, protected4, unpaid6, remaining22.
            for value in [32_u64, 0, 4, 0, 6, 6, 0, 22] {
                bytes.extend_from_slice(&value.to_be_bytes());
            }
        }
    }
    bytes
}

#[test]
fn current_household_time_receipt_retains_exact_partition_and_unit() {
    let receipts = decode_material_receipts(&time_receipts(1)).unwrap();
    assert_eq!(receipts.household_time.len(), 1);
    let row = &receipts.household_time[0];
    assert_eq!(
        row.principal_id,
        babylon_material_circuit::FinalDemandPrincipalId::from_bytes([1; 32])
    );
    assert_eq!(
        row.labor_unit_id,
        babylon_material_circuit::UnitId::from_bytes([2; 32])
    );
    assert_eq!(
        (
            row.period,
            row.endowment_hours,
            row.contribution_available_hours
        ),
        (1, 32, 22)
    );
}

#[test]
fn current_household_time_wire_refuses_duplicates_and_false_partitions() {
    assert_eq!(
        decode_material_receipts(&time_receipts(2)),
        Err(MaterialWorldError::Wire)
    );
    let mut bytes = time_receipts(1);
    let row = b"babylon.material-tick-receipts.v17\0".len() + 12 + 34 * 9;
    bytes[row + 72..row + 80].copy_from_slice(&33_u64.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&bytes),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn current_household_time_wire_refuses_unaccounted_attendance() {
    let mut bytes = time_receipts(1);
    let row = b"babylon.material-tick-receipts.v17\0".len() + 12 + 34 * 9;
    // The time equation still balances, but no member receipt attended this hour.
    bytes[row + 80..row + 88].copy_from_slice(&1_u64.to_be_bytes());
    bytes[row + 128..row + 136].copy_from_slice(&21_u64.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&bytes),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn current_household_time_wire_refuses_free_time_beside_unresolved_priority_claims() {
    let row = b"babylon.material-tick-receipts.v17\0".len() + 12 + 34 * 9;
    let mut protected = time_receipts(1);
    protected[row + 96..row + 104].copy_from_slice(&1_u64.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&protected),
        Err(MaterialWorldError::Wire)
    );
    let mut unpaid = time_receipts(1);
    unpaid[row + 104..row + 112].copy_from_slice(&7_u64.to_be_bytes());
    unpaid[row + 120..row + 128].copy_from_slice(&1_u64.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&unpaid),
        Err(MaterialWorldError::Wire)
    );
}
