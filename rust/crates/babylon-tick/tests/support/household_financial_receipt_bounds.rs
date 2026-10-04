//! Large, independently authored financial evidence remains complete and canonical.
use super::*;
use babylon_tick::material_world::MaterialWorldError;
const LIMIT: usize = 131_072;
fn bounded_rows(family: u8) -> Vec<Vec<u8>> {
    (0..LIMIT)
        .map(|n| {
            let mut row = if family == 25 {
                let mut row = tax();
                row[74..76].copy_from_slice(&0_u16.to_be_bytes());
                row[76..].fill(0);
                row
            } else {
                let mut row = distribution(0, 1, 0);
                row[81..89].copy_from_slice(&u64::try_from(LIMIT).unwrap().to_be_bytes());
                row[89..].fill(0);
                row
            };
            let start = if family == 25 { 9 } else { 41 };
            row[start..start + 32].fill(0);
            row[start + 24..start + 32].copy_from_slice(&u64::try_from(n).unwrap().to_be_bytes());
            row
        })
        .collect()
}
fn assert_financial_bound(family: u8) {
    let rows = bounded_rows(family);
    let decoded = decode_material_receipts(&envelope(&[(family, rows.clone())])).unwrap();
    if family == 25 {
        assert_eq!(decoded.taxes.len(), LIMIT);
        assert_eq!(decoded.taxes.last().unwrap().collected.micro_units(), 0);
    } else {
        assert_eq!(decoded.distributions.len(), LIMIT);
        assert_eq!(decoded.distributions.last().unwrap().total_shares, 131_072);
    }
    let mut duplicate = rows.clone();
    duplicate[LIMIT - 1] = duplicate[0].clone();
    assert_eq!(
        decode_material_receipts(&envelope(&[(family, duplicate)])),
        Err(MaterialWorldError::Wire)
    );
    let mut excess = rows;
    excess.push(excess[0].clone());
    assert_eq!(
        decode_material_receipts(&envelope(&[(family, excess)])),
        Err(MaterialWorldError::ByteLimit)
    );
}

#[test]
fn household_financial_receipt_bounds_preserve_every_tax_payer() {
    assert_financial_bound(25);
}

#[test]
fn household_financial_receipt_bounds_preserve_every_owner() {
    assert_financial_bound(26);
}
