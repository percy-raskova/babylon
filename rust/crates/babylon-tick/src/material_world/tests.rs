use super::*;

// A merchant's two physical handoffs share the same explicit handling account.
// These bytes exercise the committed receipt boundary independently of its encoder.
fn local_handoff_receipts() -> Vec<u8> {
    let mut bytes = b"babylon.material-tick-receipts.v6\0".to_vec();
    bytes.extend_from_slice(&6_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=13_u8 {
        bytes.push(tag);
        bytes.extend_from_slice(&u64::from(matches!(tag, 7 | 8)).to_be_bytes());
        if tag == 7 {
            bytes.extend_from_slice(&[1; 32]); // retailer
            bytes.push(2); // local final demand, not a freight order
            bytes.extend_from_slice(&[2; 32]); // order
            for value in [10_u64, 2, 20, 4] {
                bytes.extend_from_slice(&value.to_be_bytes());
            }
        } else if tag == 8 {
            for key in [2, 1, 3, 4, 5] {
                bytes.extend_from_slice(&[key; 32]);
            }
            bytes.extend_from_slice(&2_u64.to_be_bytes());
        }
    }
    bytes
}

#[test]
fn committed_receipts_admit_explicit_merchant_handling_and_local_fulfillment() {
    use babylon_material_circuit::{OrderId, OutboundOrderId};
    let receipt = decode_material_receipts(&local_handoff_receipts()).unwrap();
    assert_eq!(receipt.resolve_tick, 1);
    assert!(receipt.dispatches.is_empty());
    assert!(receipt.arrivals.is_empty());
    assert_eq!(receipt.handling.len(), 1);
    let work = &receipt.handling[0];
    assert_eq!(
        work.order,
        OutboundOrderId::LocalFinalDemand(OrderId::from_bytes([2; 32]))
    );
    assert_eq!((work.feasible_quantity, work.handled_quantity), (10, 2));
    assert_eq!((work.needed_hours, work.used_hours), (20, 4));
    assert_eq!(receipt.local_fulfillments.len(), 1);
    assert_eq!(receipt.local_fulfillments[0].quantity, 2);
    assert_eq!(receipt.local_fulfillments[0].retailer_site_id, work.site_id);
}

#[test]
fn handling_wire_refuses_unknown_kinds_overdraws_and_false_hours() {
    let canonical = local_handoff_receipts();
    let row = RECEIPT_DOMAIN.len() + 12 + 7 * 9;
    for (offset, replacement) in [
        (row + 32, vec![3]),
        (row + 65 + 8, 11_u64.to_be_bytes().to_vec()),
        (row + 65 + 24, 5_u64.to_be_bytes().to_vec()),
        (row + 65 + 16, 0_u64.to_be_bytes().to_vec()),
    ] {
        let mut changed = canonical.clone();
        changed[offset..offset + replacement.len()].copy_from_slice(&replacement);
        assert_eq!(
            decode_material_receipts(&changed),
            Err(MaterialWorldError::Wire)
        );
    }
}

#[test]
fn receipt_version_and_local_delivery_quantity_are_strict() {
    let canonical = local_handoff_receipts();
    let mut previous_version = canonical.clone();
    let version = RECEIPT_DOMAIN.len();
    previous_version[version..version + 4].copy_from_slice(&3_u32.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&previous_version),
        Err(MaterialWorldError::Wire)
    );
    let mut zero_delivery = canonical;
    let end = zero_delivery.len() - 45; // Empty transfer, maintenance and monetary families follow.
    zero_delivery[end - 8..end].copy_from_slice(&0_u64.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&zero_delivery),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn local_transfer_receipts_preserve_both_owners_without_freight() {
    use babylon_material_circuit::SiteId;
    let mut bytes = local_handoff_receipts();
    let tail = bytes.split_off(bytes.len() - 36);
    let count = bytes.len() - 8;
    bytes[count..].copy_from_slice(&1_u64.to_be_bytes());
    let row_start = bytes.len();
    for key in [6, 7, 1, 4, 5] {
        bytes.extend_from_slice(&[key; 32]);
    }
    bytes.extend_from_slice(&3_u64.to_be_bytes());
    bytes.extend_from_slice(&tail);
    let receipts = decode_material_receipts(&bytes).unwrap();
    assert_eq!(receipts.local_transfers.len(), 1);
    let transfer = &receipts.local_transfers[0];
    assert_eq!(transfer.supplier_site_id, SiteId::from_bytes([7; 32]));
    assert_eq!(transfer.buyer_site_id, SiteId::from_bytes([1; 32]));
    assert_eq!(transfer.quantity, 3);
    assert!(receipts.dispatches.is_empty());
    assert!(receipts.arrivals.is_empty());

    let mut self_transfer = bytes.clone();
    self_transfer[row_start + 64..row_start + 96].copy_from_slice(&[7; 32]);
    assert_eq!(
        decode_material_receipts(&self_transfer),
        Err(MaterialWorldError::Wire)
    );
    let end = bytes.len() - 36;
    bytes[end - 8..end].fill(0);
    assert_eq!(
        decode_material_receipts(&bytes),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn monetary_receipt_encoding_preserves_exact_cash_and_execution_order() {
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        AccountId, CashTransferPurpose, MoneyLocation, MoneyPosting, MoneyTransferPurpose,
        MoneyTransferReceipt, OrganizationAccountId, PublicAccountId,
    };
    let sender = AccountId::Organization(OrganizationAccountId::from_bytes([9; 32]));
    let recipient = AccountId::Public(PublicAccountId::from_bytes([1; 32]));
    let rows: Vec<_> = [i128::MAX, 1, (1_i128 << 100) + 3]
        .map(|amount| MoneyTransferReceipt {
            purpose: MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid),
            debit: MoneyPosting {
                location: MoneyLocation::Cash(sender),
                delta: Currency::from_micro_units(-amount),
            },
            credit: MoneyPosting {
                location: MoneyLocation::Cash(recipient),
                delta: Currency::from_micro_units(amount),
            },
        })
        .into();
    let mut bytes = RECEIPT_DOMAIN.to_vec();
    bytes.extend_from_slice(&6_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=13 {
        bytes.push(tag);
        bytes.extend_from_slice(&if tag == 11 { 3_u64 } else { 0 }.to_be_bytes());
        if tag == 11 {
            for row in &rows {
                monetary_receipt::encode_transfer(row, &mut bytes).unwrap();
            }
        }
    }
    let decoded = decode_material_receipts(&bytes).unwrap();
    assert_eq!(decoded.money_transfers, rows);
    let mut invalid = rows[0].clone();
    invalid.credit.delta = Currency::from_micro_units(1);
    let mut destination = vec![123];
    assert_eq!(
        monetary_receipt::encode_transfer(&invalid, &mut destination),
        Err(MaterialWorldError::Wire)
    );
    assert_eq!(destination, [123]);
}

#[test]
fn attendance_receipt_encoding_roundtrips_without_sorting_hashed_shift_ids() {
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        AccountId, FinalDemandPrincipalId, LaborUseReceipt, ShiftId, SiteId, UnitId,
        WageAccrualReceipt,
    };
    let payee = FinalDemandPrincipalId::from_bytes([2; 32]);
    let wages: Vec<_> = [(9, 1), (1, 2)]
        .map(|(shift, site)| WageAccrualReceipt {
            shift: ShiftId::from_bytes([shift; 32]),
            employer: AccountId::Site(SiteId::from_bytes([site; 32])),
            payee: AccountId::Household(payee),
            period: 7,
            obligated_hours: 4,
            amount: Currency::from_micro_units(12),
        })
        .into();
    let labor: Vec<_> = [1, 2]
        .map(|site| LaborUseReceipt {
            site_id: SiteId::from_bytes([site; 32]),
            unit_id: UnitId::from_bytes([5; 32]),
            payee,
            period: 7,
            available_hours: 6,
            funded_hours: 4,
            unfunded_hours: 2,
            used_hours: 1,
            paid_idle_hours: 3,
        })
        .into();
    monetary_receipt::validate_order(&wages, &labor).unwrap();
    let mut bytes = RECEIPT_DOMAIN.to_vec();
    bytes.extend_from_slice(&6_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=13 {
        bytes.push(tag);
        bytes.extend_from_slice(&if tag >= 12 { 2_u64 } else { 0 }.to_be_bytes());
        if tag == 12 {
            for row in &wages {
                monetary_receipt::encode_accrual(row, 7, &mut bytes).unwrap();
            }
        } else if tag == 13 {
            for row in &labor {
                monetary_receipt::encode_labor(row, 7, &mut bytes).unwrap();
            }
        }
    }
    let decoded = decode_material_receipts(&bytes).unwrap();
    assert_eq!(decoded.wage_accruals, wages);
    assert_eq!(decoded.labor_use, labor);
    let reversed = [labor[1].clone(), labor[0].clone()];
    assert_eq!(
        monetary_receipt::validate_order(&wages, &reversed),
        Err(MaterialWorldError::Wire)
    );
}
