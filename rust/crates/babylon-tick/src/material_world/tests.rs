use super::*;

// A merchant's two physical handoffs share the same explicit handling account.
// These bytes exercise the committed receipt boundary independently of its encoder.
fn local_handoff_receipts() -> Vec<u8> {
    let mut bytes = b"babylon.material-tick-receipts.v11\0".to_vec();
    bytes.extend_from_slice(&11_u32.to_be_bytes());
    bytes.extend_from_slice(&1_u64.to_be_bytes());
    for tag in 1..=29_u8 {
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
    // Eight family headers, the preceding handling row, then five identities.
    let quantity = RECEIPT_DOMAIN.len() + 12 + 8 * 9 + 97 + 160;
    zero_delivery[quantity..quantity + 8].copy_from_slice(&0_u64.to_be_bytes());
    assert_eq!(
        decode_material_receipts(&zero_delivery),
        Err(MaterialWorldError::Wire)
    );
}

#[test]
fn local_transfer_receipts_preserve_both_owners_without_freight() {
    use babylon_material_circuit::SiteId;
    let mut bytes = local_handoff_receipts();
    let tail = bytes.split_off(bytes.len() - (29 - 9) * 9);
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
    let end = bytes.len() - (29 - 9) * 9;
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
    bytes.extend_from_slice(&11_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=29 {
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

fn member_attendance(member: u8, site: u8) -> babylon_material_circuit::MemberLaborUseReceipt {
    use babylon_material_circuit::*;
    let money = babylon_kernel::currency::Currency::from_micro_units;
    MemberLaborUseReceipt {
        member_id: StaffingMemberId::from_bytes([member; 32]),
        site_id: SiteId::from_bytes([site; 32]),
        unit_id: UnitId::from_bytes([5; 32]),
        payee: FinalDemandPrincipalId::from_bytes([2; 32]),
        compensation: LaborCompensation::Wage(money(3)),
        period: 7,
        available_hours: 6,
        planned_hours: 6,
        unplanned_hours: 0,
        attended_hours: 4,
        unattended_hours: 2,
        production_hours: 1,
        handling_hours: 0,
        maintenance_hours: 0,
        idle_hours: 3,
        accrued_wages: money(12),
        production_wages: money(3),
        handling_wages: money(0),
        maintenance_wages: money(0),
        idle_wages: money(9),
    }
}

#[test]
fn attendance_receipt_encoding_roundtrips_without_sorting_hashed_shift_ids() {
    use babylon_material_circuit::{
        member_shift_id, AccountId, EmploymentTerms, LaborUseReceipt, WageAccrualReceipt,
    };
    let members = [member_attendance(4, 1), member_attendance(1, 2)];
    let wages: Vec<_> = members
        .iter()
        .map(|row| {
            let terms = EmploymentTerms {
                member_id: row.member_id,
                site_id: row.site_id,
                unit_id: row.unit_id,
                payee: row.payee,
                compensation: row.compensation,
            };
            WageAccrualReceipt {
                shift: member_shift_id(7, &terms),
                employer: AccountId::Site(row.site_id),
                payee: AccountId::Household(row.payee),
                period: 7,
                obligated_hours: 4,
                amount: row.accrued_wages,
            }
        })
        .collect();
    assert!(
        wages[0].shift > wages[1].shift,
        "chronological wages are deliberately not hash ordered"
    );
    let labor: Vec<_> = members
        .iter()
        .map(|row| LaborUseReceipt {
            site_id: row.site_id,
            unit_id: row.unit_id,
            period: 7,
            available_hours: 6,
            planned_hours: 6,
            unplanned_hours: 0,
            funded_hours: 4,
            unfunded_hours: 2,
            non_wage_hours: 0,
            used_hours: 1,
            paid_idle_hours: 3,
            unpaid_idle_hours: 0,
        })
        .collect();
    monetary_receipt::validate_order(&wages, &labor).unwrap();
    let mut bytes = RECEIPT_DOMAIN.to_vec();
    bytes.extend_from_slice(&11_u32.to_be_bytes());
    bytes.extend_from_slice(&7_u64.to_be_bytes());
    for tag in 1..=29 {
        bytes.push(tag);
        bytes.extend_from_slice(
            &if matches!(tag, 12 | 13 | 29) {
                2_u64
            } else {
                0
            }
            .to_be_bytes(),
        );
        if tag == 12 {
            for row in &wages {
                monetary_receipt::encode_accrual(row, 7, &mut bytes).unwrap();
            }
        } else if tag == 13 {
            for row in &labor {
                monetary_receipt::encode_labor(row, 7, &mut bytes).unwrap();
            }
        } else if tag == 29 {
            for row in &members {
                workforce_receipt::encode_attendance(row, 7, &mut bytes).unwrap();
            }
        }
    }
    let decoded = decode_material_receipts(&bytes).unwrap();
    assert_eq!(decoded.wage_accruals, wages);
    assert_eq!(decoded.labor_use, labor);
    assert_eq!(decoded.member_labor_use, members);
    let reversed = [labor[1].clone(), labor[0].clone()];
    assert_eq!(
        monetary_receipt::validate_order(&wages, &reversed),
        Err(MaterialWorldError::Wire)
    );
}
