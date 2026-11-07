//! Join original gift authority to independent material legs and their actual postings.
use super::MaterialWorldError;
use babylon_material_circuit::{
    AccountId, AidFreightLot, AidMandate, AidOutcome, AidReceipt, CashTransferPurpose,
    CircuitAccounting, MaterialCatalog, MaterialCircuitState, MaterialCircuitTransition,
    MoneyLocation, MoneyTransferPurpose, OrderId,
};
use babylon_practice_contract::{
    OrganizerAidCashStatus, OrganizerAidCommitment, OrganizerAidMaterialPostings,
    OrganizerAidSupport, OrganizerAidSupportStatus, OrganizerAllocation, OrganizerChoice,
    OrganizerCommitment, OrganizerConfig, OrganizerState,
};

pub(super) fn facts(
    catalog: &MaterialCatalog,
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<Vec<OrganizerAidSupport>, MaterialWorldError> {
    let mut result = Vec::new();
    for pending in &organizer.pending_aid {
        babylon_practice_contract::validate_organizer_aid_commitment(config, &pending.gift)?;
        let mut row = support(catalog, &pending.gift, opening, transition)?;
        row.cash_status = pending.dispatch_support.cash_status;
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
        let gift =
            babylon_practice_contract::organizer_aid_commitment(config, organizer, accepted)?;
        result.push(support(catalog, &gift, opening, transition)?);
    }
    result.sort_by_key(|row| row.original_commitment_id);
    Ok(result)
}

fn support(
    catalog: &MaterialCatalog,
    gift: &OrganizerAidCommitment,
    opening: &MaterialCircuitState,
    transition: &MaterialCircuitTransition,
) -> Result<OrganizerAidSupport, MaterialWorldError> {
    let (CircuitAccounting::Monetary(prior), CircuitAccounting::Monetary(closing)) =
        (&opening.accounting, &transition.state.accounting)
    else {
        return Err(MaterialWorldError::Wire);
    };
    let mandate = captured_mandate(catalog, gift, opening.period)?;
    let dispatch_period = gift.commitment.resolves_period;
    let OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = gift.commitment.command.allocation
    else {
        return Err(MaterialWorldError::Wire);
    };
    let id = babylon_material_circuit::aid_commitment_id(mandate.id, dispatch_period);
    let prior_quantity = freight_quantity(&prior.aid.freight, id)?;
    let surviving = freight_quantity(&closing.aid.freight, id)?;
    let rows: Vec<&AidReceipt> = transition
        .aid
        .iter()
        .filter(|row| row.commitment_id == id)
        .collect();
    for row in &rows {
        row.validate_against(mandate)?;
        if row.period != opening.period || row.dispatch_period != dispatch_period {
            return Err(MaterialWorldError::Wire);
        }
    }
    let current = dispatch_period == opening.period;
    check_requests(&rows, current, food_quantity, cash_micros)?;
    if !current && prior_quantity == 0 {
        return Err(MaterialWorldError::Wire);
    }
    let quantity = |outcome| {
        rows.iter()
            .filter(|r| r.outcome == outcome)
            .try_fold(0_u64, |sum, row| sum.checked_add(row.quantity))
            .ok_or(MaterialWorldError::Arithmetic)
    };
    let granted = quantity(AidOutcome::Granted)?;
    let lost = quantity(AidOutcome::Lost)?;
    let dispatched = quantity(AidOutcome::Dispatched)?
        .checked_add(if current { granted } else { 0 })
        .ok_or(MaterialWorldError::Arithmetic)?;
    if current {
        let ended = quantity(AidOutcome::Unshipped)?
            .checked_add(quantity(AidOutcome::FoodReceivingRefused)?)
            .ok_or(MaterialWorldError::Arithmetic)?;
        if dispatched.checked_add(ended) != Some(food_quantity) {
            return Err(MaterialWorldError::Wire);
        }
    } else if granted
        .checked_add(lost)
        .and_then(|q| q.checked_add(surviving))
        != Some(prior_quantity)
    {
        return Err(MaterialWorldError::Wire);
    }
    let status = food_status(
        mandate,
        transition,
        opening.period,
        food_quantity,
        surviving,
        granted,
        quantity(AidOutcome::FoodReceivingRefused)?,
    )?;
    let (cash_status, cash) = cash_support(mandate, &rows, transition, current, cash_micros)?;
    let fulfillment_hours = rows
        .iter()
        .try_fold(0_u64, |sum, row| sum.checked_add(row.contribution_hours))
        .ok_or(MaterialWorldError::Arithmetic)?;
    Ok(OrganizerAidSupport {
        original_commitment_id: gift.commitment.commitment_id,
        material_commitment_id: id.as_bytes(),
        mandate_id: mandate.id,
        source_hash: mandate.source_hash,
        dispatch_period,
        period: opening.period,
        recipient_principal_id: mandate.recipient.as_bytes(),
        good_id: mandate.good_id.as_bytes(),
        unit_id: mandate.unit_id.as_bytes(),
        status,
        cash_status,
        material_postings: OrganizerAidMaterialPostings {
            dispatched_quantity: dispatched,
            fulfillment_hours,
            payer_cash_granted_micros: cash,
            lost_quantity: lost,
        },
    })
}

fn captured_mandate<'a>(
    catalog: &'a MaterialCatalog,
    gift: &OrganizerAidCommitment,
    period: u64,
) -> Result<&'a AidMandate, MaterialWorldError> {
    let mandate = catalog
        .aid_mandates
        .iter()
        .find(|row| row.id == gift.mandate_id)
        .ok_or(MaterialWorldError::Wire)?;
    if mandate.source_hash != gift.source_hash
        || mandate.donor_actor != gift.donor_actor_id
        || mandate.recipient_actor != gift.recipient_actor_id
        || mandate.donor_contributor_id != gift.donor_contributor_id
        || mandate.donor.as_bytes() != gift.donor_principal_id
        || mandate.recipient.as_bytes() != gift.recipient_principal_id
        || gift.commitment.resolves_period > period
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(mandate)
}

fn freight_quantity(lots: &[AidFreightLot], id: OrderId) -> Result<u64, MaterialWorldError> {
    lots.iter()
        .filter(|row| row.commitment_id == id)
        .try_fold(0_u64, |sum, row| sum.checked_add(row.quantity))
        .ok_or(MaterialWorldError::Arithmetic)
}

fn check_requests(
    rows: &[&AidReceipt],
    current: bool,
    food_quantity: u64,
    cash_micros: i128,
) -> Result<(), MaterialWorldError> {
    let requested: Vec<_> = rows
        .iter()
        .filter(|r| r.outcome == AidOutcome::Requested)
        .collect();
    let cash_requested: Vec<_> = rows
        .iter()
        .filter(|r| r.outcome == AidOutcome::CashRequested)
        .collect();
    if requested.len() != usize::from(current && food_quantity > 0)
        || requested
            .first()
            .is_some_and(|r| r.quantity != food_quantity)
        || cash_requested.len() != usize::from(current && cash_micros > 0)
        || cash_requested
            .first()
            .is_some_and(|r| r.cash_amount.micro_units() != cash_micros)
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
fn food_status(
    mandate: &AidMandate,
    transition: &MaterialCircuitTransition,
    period: u64,
    food_quantity: u64,
    surviving: u64,
    granted: u64,
    refused: u64,
) -> Result<OrganizerAidSupportStatus, MaterialWorldError> {
    let status = if food_quantity == 0 {
        OrganizerAidSupportStatus::NotRequested
    } else if surviving > 0 {
        if granted != 0 {
            return Err(MaterialWorldError::Wire);
        }
        OrganizerAidSupportStatus::AwaitingDelivery
    } else if granted > 0 {
        let consumed = transition
            .household_consumption
            .iter()
            .filter(|row| {
                row.period == period
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
    } else if refused > 0 {
        OrganizerAidSupportStatus::ReceivingRefused
    } else {
        OrganizerAidSupportStatus::TerminalFailure
    };
    Ok(status)
}
fn cash_support(
    mandate: &AidMandate,
    rows: &[&AidReceipt],
    transition: &MaterialCircuitTransition,
    current: bool,
    cash_micros: i128,
) -> Result<(OrganizerAidCashStatus, i128), MaterialWorldError> {
    let cash_rows: Vec<_> = rows
        .iter()
        .filter(|r| {
            matches!(
                r.outcome,
                AidOutcome::CashGranted
                    | AidOutcome::CashUnfunded
                    | AidOutcome::CashReceivingRefused
            )
        })
        .collect();
    if cash_rows.len() != usize::from(current && cash_micros > 0) {
        return Err(MaterialWorldError::Wire);
    }
    let (cash_status, cash) = match cash_rows.first() {
        Some(row) => (
            match row.outcome {
                AidOutcome::CashGranted => OrganizerAidCashStatus::Granted,
                AidOutcome::CashUnfunded => OrganizerAidCashStatus::Unfunded,
                AidOutcome::CashReceivingRefused => OrganizerAidCashStatus::ReceivingRefused,
                _ => return Err(MaterialWorldError::Wire),
            },
            row.cash_amount.micro_units(),
        ),
        None => (OrganizerAidCashStatus::NotRequested, 0),
    };
    let transfers: Vec<_> = transition
        .money_transfers
        .iter()
        .filter(|row| {
            row.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                && row.debit.location == MoneyLocation::Cash(mandate.payer)
                && row.credit.location
                    == MoneyLocation::Cash(AccountId::Household(mandate.recipient))
        })
        .collect();
    if current
        && (transfers.len() != usize::from(cash > 0)
            || transfers.first().is_some_and(|row| {
                row.credit.delta.micro_units() != cash || row.debit.delta.micro_units() != -cash
            }))
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok((cash_status, cash))
}
