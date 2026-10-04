//! Narrow support facts from the authenticated detached material close.
use super::MaterialWorldError;
use babylon_material_circuit::{
    aid_commitment_id, AccountId, AidMandate, AidOutcome, AidReceipt, CircuitAccounting,
    MaterialCircuitState, MaterialCircuitTransition, MoneyLocation, MoneyTransferPurpose,
    MoneyTransferReceipt, OrderId,
};
use babylon_practice_contract::{
    organizer_aid_commitment, validate_organizer_aid_commitment, OrganizerAidCommitment,
    OrganizerAidMaterialPostings, OrganizerAidSupport, OrganizerAidSupportStatus, OrganizerChoice,
    OrganizerCommitment, OrganizerConfig, OrganizerState,
};

pub(super) fn facts(
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<Vec<OrganizerAidSupport>, MaterialWorldError> {
    let mut result = Vec::with_capacity(2);
    for pending in &organizer.pending_aid {
        validate_organizer_aid_commitment(config, &pending.gift)?;
        let row = support(&pending.gift, pending.dispatch_period, opening, transition)?;
        if row.material_commitment_id != pending.material_commitment_id
            || row.good_id != pending.good_id
            || row.unit_id != pending.unit_id
        {
            return Err(MaterialWorldError::Wire);
        }
        result.push(row);
    }
    if let Some(accepted) = accepted.filter(|row| {
        matches!(
            row.command.choice,
            OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
        )
    }) {
        let gift = organizer_aid_commitment(config, organizer, accepted)?;
        result.push(support(
            &gift,
            accepted.resolves_period,
            opening,
            transition,
        )?);
    }
    result.sort_by_key(|row| row.original_commitment_id);
    Ok(result)
}

fn support(
    gift: &OrganizerAidCommitment,
    dispatch_period: u64,
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<OrganizerAidSupport, MaterialWorldError> {
    let CircuitAccounting::Monetary(prior) = &opening.accounting else {
        return Err(MaterialWorldError::Wire);
    };
    let CircuitAccounting::Monetary(closing) = &transition.state.accounting else {
        return Err(MaterialWorldError::Wire);
    };
    let mandate = prior
        .aid
        .mandates
        .iter()
        .find(|row| row.id == gift.mandate_id)
        .ok_or(MaterialWorldError::Wire)?;
    if mandate.source_hash != gift.source_hash
        || mandate.donor_actor != gift.donor_actor_id
        || mandate.recipient_actor != gift.recipient_actor_id
        || mandate.donor_contributor_id != gift.donor_contributor_id
        || mandate.donor.as_bytes() != gift.donor_principal_id
        || mandate.recipient.as_bytes() != gift.recipient_principal_id
        || closing.aid.mandates.iter().find(|row| row.id == mandate.id) != Some(mandate)
        || dispatch_period > opening.period
    {
        return Err(MaterialWorldError::Wire);
    }
    let material_id = aid_commitment_id(mandate.id, dispatch_period);
    let matches_lot =
        |row: &&babylon_material_circuit::AidFreightLot| row.commitment_id == material_id;
    let prior_lots = prior
        .aid
        .freight
        .iter()
        .filter(matches_lot)
        .collect::<Vec<_>>();
    let surviving = closing
        .aid
        .freight
        .iter()
        .filter(matches_lot)
        .collect::<Vec<_>>();
    for row in prior_lots.iter().chain(&surviving) {
        if row.mandate_id != mandate.id
            || row.dispatch_period != dispatch_period
            || row.donor != mandate.donor
            || row.recipient != mandate.recipient
            || row.good_id != mandate.good_id
            || row.unit_id != mandate.unit_id
            || row.quantity == 0
        {
            return Err(MaterialWorldError::Wire);
        }
    }
    let mut granted = 0_u64;
    let mut lost = 0_u64;
    let mut requested = false;
    for row in transition
        .aid
        .iter()
        .filter(|row| row.commitment_id == material_id)
    {
        row.validate_against(mandate)?;
        if row.period != opening.period || row.dispatch_period != dispatch_period {
            return Err(MaterialWorldError::Wire);
        }
        match row.outcome {
            AidOutcome::Granted => {
                granted = granted
                    .checked_add(row.quantity)
                    .ok_or(MaterialWorldError::Arithmetic)?;
            }
            AidOutcome::Lost => {
                lost = lost
                    .checked_add(row.quantity)
                    .ok_or(MaterialWorldError::Arithmetic)?;
            }
            AidOutcome::Requested => requested = true,
            AidOutcome::Dispatched | AidOutcome::Unshipped => {}
        }
    }
    let current = dispatch_period == opening.period;
    if current != requested || (!current && prior_lots.is_empty()) {
        return Err(MaterialWorldError::Wire);
    }
    let status = if granted > 0 {
        if !surviving.is_empty() {
            return Err(MaterialWorldError::Wire);
        }
        let consumed = transition
            .household_consumption
            .iter()
            .filter(|row| {
                row.period == opening.period
                    && row.principal_id == mandate.recipient
                    && row.good_id == mandate.good_id
                    && row.unit_id == mandate.unit_id
            })
            .try_fold(0_u64, |sum, row| sum.checked_add(row.consumed_quantity))
            .ok_or(MaterialWorldError::Arithmetic)?;
        OrganizerAidSupportStatus::Granted {
            granted_quantity: granted,
            consumed_quantity: consumed,
        }
    } else if !surviving.is_empty() {
        OrganizerAidSupportStatus::AwaitingDelivery
    } else if current || lost > 0 {
        OrganizerAidSupportStatus::TerminalFailure
    } else {
        // Absence of a grant is not evidence that a prior obligation disappeared.
        return Err(MaterialWorldError::Wire);
    };
    Ok(OrganizerAidSupport {
        original_commitment_id: gift.commitment.commitment_id,
        material_commitment_id: material_id.as_bytes(),
        mandate_id: mandate.id,
        source_hash: mandate.source_hash,
        dispatch_period,
        period: opening.period,
        recipient_principal_id: mandate.recipient.as_bytes(),
        good_id: mandate.good_id.as_bytes(),
        unit_id: mandate.unit_id.as_bytes(),
        status,
        material_postings: actual_postings(
            mandate,
            material_id,
            dispatch_period,
            opening.period,
            &transition.aid,
            &transition.money_transfers,
        )?,
    })
}

// The detached material close remains the accounting authority. Select only the
// admitted command's receipts and transfers; do not derive costs from balances.
fn actual_postings(
    mandate: &AidMandate,
    id: OrderId,
    dispatch_period: u64,
    period: u64,
    aid: &[AidReceipt],
    money_transfers: &[MoneyTransferReceipt],
) -> Result<OrganizerAidMaterialPostings, MaterialWorldError> {
    let mut postings = OrganizerAidMaterialPostings {
        dispatched_quantity: 0,
        fulfillment_hours: 0,
        payer_cash_reserved_micros: 0,
        payer_cash_granted_micros: 0,
        payer_cash_refunded_micros: 0,
    };
    let current = dispatch_period == period;
    let mut expected_grant = 0_i128;
    let mut expected_refund = 0_i128;
    let mut expected_reservation = 0_i128;
    let mut requested = None;
    let mut outcomes = std::collections::BTreeSet::new();
    for row in aid.iter().filter(|row| row.commitment_id == id) {
        row.validate_against(mandate)?;
        if row.period != period
            || row.dispatch_period != dispatch_period
            || !outcomes.insert(row.outcome as u8)
        {
            return Err(MaterialWorldError::Wire);
        }
        let cash = row.cash_amount.micro_units();
        match row.outcome {
            AidOutcome::Requested => requested = Some(row.quantity),
            AidOutcome::Granted => {
                expected_grant = expected_grant
                    .checked_add(cash)
                    .ok_or(MaterialWorldError::Arithmetic)?;
            }
            AidOutcome::Lost | AidOutcome::Unshipped => {
                expected_refund = expected_refund
                    .checked_add(cash)
                    .ok_or(MaterialWorldError::Arithmetic)?;
            }
            AidOutcome::Dispatched => {}
        }
        if current && row.outcome != AidOutcome::Requested {
            expected_reservation = expected_reservation
                .checked_add(cash)
                .ok_or(MaterialWorldError::Arithmetic)?;
        }
        if row.outcome == AidOutcome::Dispatched || (current && row.outcome == AidOutcome::Granted)
        {
            postings.dispatched_quantity = postings
                .dispatched_quantity
                .checked_add(row.quantity)
                .ok_or(MaterialWorldError::Arithmetic)?;
            postings.fulfillment_hours = postings
                .fulfillment_hours
                .checked_add(row.contribution_hours)
                .ok_or(MaterialWorldError::Arithmetic)?;
        }
    }
    let mut movements = std::collections::BTreeSet::new();
    for row in money_transfers {
        let (tag, debit, credit, sum) = match row.purpose {
            MoneyTransferPurpose::AidReservation(command) if command == id => {
                if !current {
                    return Err(MaterialWorldError::Wire);
                }
                (
                    0,
                    MoneyLocation::Cash(mandate.payer),
                    MoneyLocation::AidReserve(id),
                    &mut postings.payer_cash_reserved_micros,
                )
            }
            MoneyTransferPurpose::AidGrant(command) if command == id => (
                1,
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(AccountId::Household(mandate.recipient)),
                &mut postings.payer_cash_granted_micros,
            ),
            MoneyTransferPurpose::AidRefund(command) if command == id => (
                2,
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(mandate.payer),
                &mut postings.payer_cash_refunded_micros,
            ),
            _ => continue,
        };
        let amount = row.credit.delta.micro_units();
        if !movements.insert(tag)
            || amount <= 0
            || row.debit.location != debit
            || row.credit.location != credit
            || row.debit.delta.micro_units()
                != amount.checked_neg().ok_or(MaterialWorldError::Arithmetic)?
        {
            return Err(MaterialWorldError::Wire);
        }
        *sum = sum
            .checked_add(amount)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    if postings.payer_cash_granted_micros != expected_grant
        || postings.payer_cash_refunded_micros != expected_refund
        || postings.payer_cash_reserved_micros != expected_reservation
    {
        return Err(MaterialWorldError::Wire);
    }
    if current {
        let price = mandate.cash_per_unit.micro_units();
        let reserved = postings.payer_cash_reserved_micros;
        if price <= 0
            || reserved % price != 0
            || u64::try_from(reserved / price).map_err(|_| MaterialWorldError::Arithmetic)?
                > requested.ok_or(MaterialWorldError::Wire)?
        {
            return Err(MaterialWorldError::Wire);
        }
    } else if postings.dispatched_quantity != 0
        || postings.fulfillment_hours != 0
        || postings.payer_cash_reserved_micros != 0
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(postings)
}

#[cfg(test)]
mod posting_tests {
    use super::*;
    use babylon_kernel::currency::Currency;
    use babylon_material_circuit::{
        AidTransport, FinalDemandPrincipalId, GoodId, MoneyPosting, OrganizationAccountId, UnitId,
    };

    fn local() -> (AidMandate, Vec<AidReceipt>, Vec<MoneyTransferReceipt>) {
        let mandate = AidMandate {
            id: [1; 32],
            source_hash: [2; 32],
            donor_actor: 101,
            donor_contributor_id: 201,
            recipient_actor: 120,
            payer: AccountId::Organization(OrganizationAccountId::from_bytes([3; 32])),
            donor: FinalDemandPrincipalId::from_bytes([4; 32]),
            recipient: FinalDemandPrincipalId::from_bytes([5; 32]),
            good_id: GoodId::from_bytes([6; 32]),
            unit_id: UnitId::from_bytes([7; 32]),
            labor_unit_id: UnitId::from_bytes([8; 32]),
            hours_per_unit: 2,
            maximum_quantity: 9,
            cash_per_unit: Currency::from_micro_units(3),
            transport: AidTransport::Local,
        };
        let id = aid_commitment_id(mandate.id, 1);
        let request = AidReceipt {
            commitment_id: id,
            mandate_id: mandate.id,
            period: 1,
            dispatch_period: 1,
            transport: mandate.transport,
            payer: mandate.payer,
            donor: mandate.donor,
            recipient: mandate.recipient,
            good_id: mandate.good_id,
            unit_id: mandate.unit_id,
            outcome: AidOutcome::Requested,
            quantity: 2,
            carrying_amount: Currency::from_micro_units(0),
            cash_amount: Currency::from_micro_units(0),
            contribution_hours: 0,
        };
        let mut grant = request.clone();
        grant.outcome = AidOutcome::Granted;
        grant.cash_amount = Currency::from_micro_units(6);
        grant.contribution_hours = 4;
        let transfer = |purpose, debit, credit| MoneyTransferReceipt {
            purpose,
            debit: MoneyPosting {
                location: debit,
                delta: Currency::from_micro_units(-6),
            },
            credit: MoneyPosting {
                location: credit,
                delta: Currency::from_micro_units(6),
            },
        };
        let transfers = vec![
            transfer(
                MoneyTransferPurpose::AidReservation(id),
                MoneyLocation::Cash(mandate.payer),
                MoneyLocation::AidReserve(id),
            ),
            transfer(
                MoneyTransferPurpose::AidGrant(id),
                MoneyLocation::AidReserve(id),
                MoneyLocation::Cash(AccountId::Household(mandate.recipient)),
            ),
        ];
        (mandate, vec![request, grant], transfers)
    }

    #[test]
    fn exact_owned_postings_reject_damaged_duplicate_and_unmatched_material_evidence() {
        let (mandate, aid, transfers) = local();
        let id = aid[0].commitment_id;
        let actual = actual_postings(&mandate, id, 1, 1, &aid, &transfers).unwrap();
        assert_eq!(actual.dispatched_quantity, 2); // Captured maximum is nine.
        assert_eq!(actual.fulfillment_hours, 4);
        assert_eq!(actual.payer_cash_reserved_micros, 6);
        assert_eq!(actual.payer_cash_granted_micros, 6);
        assert_eq!(actual.payer_cash_refunded_micros, 0);
        for defect in 0..7 {
            let mut rows = transfers.clone();
            match defect {
                0 => {
                    rows[0].debit.location =
                        MoneyLocation::Cash(AccountId::Household(mandate.donor))
                }
                1 => {
                    rows[1].credit.location =
                        MoneyLocation::Cash(AccountId::Household(mandate.donor))
                }
                2 => rows[1].debit.delta = Currency::from_micro_units(6),
                3 => rows.push(rows[0].clone()),
                4 => rows.push(rows[1].clone()),
                5 => {
                    rows.pop();
                }
                _ => rows[1].credit.delta = Currency::from_micro_units(3),
            }
            assert!(actual_postings(&mandate, id, 1, 1, &aid, &rows).is_err());
        }
        let mut duplicate = aid.clone();
        duplicate.push(aid[1].clone());
        assert!(actual_postings(&mandate, id, 1, 1, &duplicate, &transfers).is_err());
        let mut wrong_period = aid.clone();
        wrong_period[1].period = 2;
        assert!(actual_postings(&mandate, id, 1, 1, &wrong_period, &transfers).is_err());
        let mut unrelated = transfers.clone();
        unrelated.push(MoneyTransferReceipt {
            purpose: MoneyTransferPurpose::AidGrant(OrderId::from_bytes([99; 32])),
            debit: transfers[1].debit.clone(),
            credit: transfers[1].credit.clone(),
        });
        assert_eq!(
            actual_postings(&mandate, id, 1, 1, &aid, &unrelated).unwrap(),
            actual
        );
        let empty = actual_postings(&mandate, id, 1, 1, &aid[..1], &[]).unwrap();
        assert_eq!(empty.dispatched_quantity, 0);
        assert_eq!(empty.fulfillment_hours, 0);
        assert_eq!(empty.payer_cash_reserved_micros, 0);
        assert_eq!(empty.payer_cash_granted_micros, 0);
        assert_eq!(empty.payer_cash_refunded_micros, 0);
    }
}
