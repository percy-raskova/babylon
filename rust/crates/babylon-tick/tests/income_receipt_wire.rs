//! Language-neutral signed income rows and exact arithmetic, independent of Rust layout.
use babylon_tick::material_world::decode_material_receipts;

const DOMAIN: &[u8] = b"babylon.material-tick-receipts.v10\0";
const ROW_BYTES: usize = 441;

fn row(id: u8) -> Vec<u8> {
    let mut bytes = vec![1];
    bytes.extend_from_slice(&[id; 32]);
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for amount in [
        100_i128, -5, 3, 2, 5, 1, 20, 0, 8, 6, 2, 1, 1, 1, 1, 1, 1, 0, 2, 1, 3, 2, 4, 10, 4,
    ] {
        bytes.extend_from_slice(&amount.to_be_bytes());
    }
    assert_eq!(bytes.len(), ROW_BYTES);
    bytes
}
fn envelope(rows: &[Vec<u8>]) -> Vec<u8> {
    let mut bytes = DOMAIN.to_vec();
    bytes.extend_from_slice(&10_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=27_u8 {
        bytes.push(tag);
        bytes.extend_from_slice(&(if tag == 19 { rows.len() as u64 } else { 0 }).to_be_bytes());
        if tag == 19 {
            for row in rows {
                bytes.extend_from_slice(row);
            }
        }
    }
    bytes
}

#[test]
fn signed_retained_earnings_and_capitalization_are_distinct_from_income() {
    let decoded = decode_material_receipts(&envelope(&[row(1)])).unwrap();
    assert_eq!(decoded.income.len(), 1);
    let result = &decoded.income[0];
    assert_eq!(result.net_income.micro_units(), 10);
    assert_eq!(result.closing_retained_earnings.micro_units(), 4);
    assert_eq!(
        result.statement.productive_labor_capitalized.micro_units(),
        6
    );
}

#[test]
fn income_rows_refuse_bad_equations_negative_flows_periods_order_and_previous_schema() {
    for field in 2..=24 {
        let mut damaged = row(1);
        // Nonnegative capital and flow fields, then the two independent equation outputs.
        damaged[41 + field * 16..41 + (field + 1) * 16].copy_from_slice(&(-2_i128).to_be_bytes());
        assert!(
            decode_material_receipts(&envelope(&[damaged])).is_err(),
            "field {field}"
        );
    }
    for period in [0_u64, 2] {
        let mut damaged = row(1);
        damaged[33..41].copy_from_slice(&period.to_be_bytes());
        assert!(decode_material_receipts(&envelope(&[damaged])).is_err());
    }
    assert!(decode_material_receipts(&envelope(&[row(1), row(1)])).is_err());
    assert!(decode_material_receipts(&envelope(&[row(2), row(1)])).is_err());
    let bytes = envelope(&[row(1)]);
    let mut previous = bytes.clone();
    previous[DOMAIN.len()..DOMAIN.len() + 4].copy_from_slice(&9_u32.to_be_bytes());
    assert!(decode_material_receipts(&previous).is_err());
    previous[DOMAIN.len()..DOMAIN.len() + 4].copy_from_slice(&10_u32.to_be_bytes());
    previous[DOMAIN.len() - 2] = b'9';
    assert!(decode_material_receipts(&previous).is_err());
    for length in 0..bytes.len() {
        assert!(decode_material_receipts(&bytes[..length]).is_err());
    }
}
