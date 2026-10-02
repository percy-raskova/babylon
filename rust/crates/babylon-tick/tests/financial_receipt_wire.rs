//! Independent wire vectors for exact funded fiscal and ownership postings.
use babylon_tick::material_world::decode_material_receipts;
const DOMAIN: &[u8] = b"babylon.material-tick-receipts.v10\0";
fn id(out: &mut Vec<u8>, n: u8) {
    out.extend_from_slice(&[n; 32]);
}
fn account(out: &mut Vec<u8>, tag: u8, n: u8) {
    out.push(tag);
    id(out, n);
}
fn amounts(out: &mut Vec<u8>, values: &[i128]) {
    for n in values {
        out.extend_from_slice(&n.to_be_bytes());
    }
}
fn period() -> Vec<u8> {
    7_u64.to_be_bytes().to_vec()
}
fn public() -> Vec<u8> {
    let mut b = period();
    id(&mut b, 8);
    account(&mut b, 2, 9);
    b.push(1);
    b.extend_from_slice(&0_u32.to_be_bytes());
    amounts(&mut b, &[5, 3, 2]);
    assert_eq!(b.len(), 126);
    b
}
fn tax() -> Vec<u8> {
    let mut b = period();
    account(&mut b, 1, 1);
    id(&mut b, 8);
    b.push(2);
    b.extend_from_slice(&2500_u16.to_be_bytes());
    amounts(&mut b, &[9, 2, 1, 1]);
    assert_eq!(b.len(), 140);
    b
}
fn distribution(owner: u8, shares: u64, paid: i128) -> Vec<u8> {
    let mut b = period();
    id(&mut b, 1);
    account(&mut b, 3, owner);
    b.extend_from_slice(&shares.to_be_bytes());
    b.extend_from_slice(&3_u64.to_be_bytes());
    amounts(&mut b, &[7, 7, paid]);
    assert_eq!(b.len(), 137);
    b
}
fn contribution() -> Vec<u8> {
    let mut b = period();
    id(&mut b, 5);
    account(&mut b, 3, 2);
    id(&mut b, 1);
    amounts(&mut b, &[10, 5, 5]);
    assert_eq!(b.len(), 153);
    b
}
fn cash(purpose: u8, payer: (u8, u8), recipient: (u8, u8), amount: i128) -> Vec<u8> {
    let mut b = vec![7, purpose];
    id(&mut b, 0);
    b.push(1);
    account(&mut b, payer.0, payer.1);
    amounts(&mut b, &[-amount]);
    b.push(1);
    account(&mut b, recipient.0, recipient.1);
    amounts(&mut b, &[amount]);
    assert_eq!(b.len(), 134);
    b
}
fn envelope(rows: &[(u8, Vec<Vec<u8>>)]) -> Vec<u8> {
    let mut b = DOMAIN.to_vec();
    b.extend_from_slice(&10_u32.to_be_bytes());
    b.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=27 {
        let rows = rows
            .iter()
            .find(|(t, _)| *t == tag)
            .map_or(&[][..], |(_, r)| r.as_slice());
        b.push(tag);
        b.extend_from_slice(&u64::try_from(rows.len()).unwrap().to_be_bytes());
        for row in rows {
            b.extend_from_slice(row);
        }
    }
    b
}
fn rows() -> Vec<(u8, Vec<Vec<u8>>)> {
    vec![
        (
            11,
            vec![
                cash(2, (4, 8), (2, 9), 3),
                cash(1, (1, 1), (4, 8), 1),
                cash(4, (1, 1), (3, 2), 3),
                cash(4, (1, 1), (3, 3), 4),
                cash(5, (3, 2), (1, 1), 5),
            ],
        ),
        (24, vec![public()]),
        (25, vec![tax()]),
        (26, vec![distribution(2, 1, 3), distribution(3, 2, 4)]),
        (27, vec![contribution()]),
    ]
}
#[test]
fn financial_rows_preserve_shortfalls_exact_shares_and_matched_cash() {
    let decoded = decode_material_receipts(&envelope(&rows())).unwrap();
    assert_eq!(decoded.public_budgets[0].unfunded.micro_units(), 2);
    assert_eq!(decoded.taxes[0].uncollected.micro_units(), 1);
    assert_eq!(
        decoded
            .distributions
            .iter()
            .map(|r| r.paid.micro_units())
            .collect::<Vec<_>>(),
        [3, 4]
    );
    assert_eq!(decoded.contributions[0].paid.micro_units(), 5);
}
#[test]
fn financial_wire_refuses_false_partitions_rates_and_remainder_payees() {
    for (family, offset, replacement) in [
        (24, 78, (-1_i128).to_be_bytes().to_vec()),
        (24, 73, vec![9]),
        (25, 74, 10_001_u16.to_be_bytes().to_vec()),
        (25, 92, 3_i128.to_be_bytes().to_vec()),
        (26, 121, 2_i128.to_be_bytes().to_vec()),
        (27, 105, 6_i128.to_be_bytes().to_vec()),
    ] {
        let mut rows = rows();
        let r = &mut rows.iter_mut().find(|(t, _)| *t == family).unwrap().1[0];
        r[offset..offset + replacement.len()].copy_from_slice(&replacement);
        assert!(
            decode_material_receipts(&envelope(&rows)).is_err(),
            "family {family} offset {offset}"
        );
    }
}
#[test]
fn financial_wire_requires_cash_match_unique_order_and_current_version() {
    let original = rows();
    let mut missing = original.clone();
    missing[0].1.pop();
    assert!(decode_material_receipts(&envelope(&missing)).is_err());
    let mut wrong = original.clone();
    wrong[0].1[0] = cash(2, (4, 8), (2, 9), 2);
    assert!(decode_material_receipts(&envelope(&wrong)).is_err());
    let mut reversed = original.clone();
    reversed[3].1.reverse();
    assert!(decode_material_receipts(&envelope(&reversed)).is_err());
    let mut duplicate = original.clone();
    duplicate[4].1.push(contribution());
    assert!(decode_material_receipts(&envelope(&duplicate)).is_err());
    let b = envelope(&original);
    let mut old = b.clone();
    old[DOMAIN.len()..DOMAIN.len() + 4].copy_from_slice(&9_u32.to_be_bytes());
    assert!(decode_material_receipts(&old).is_err());
    for end in 0..b.len() {
        assert!(decode_material_receipts(&b[..end]).is_err());
    }
}
