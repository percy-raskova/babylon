//! Exact original command → material collection → retained acknowledgment joins.
use super::{collection_receipt, MaterialWorldError};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    CircuitAccounting, CollectionOutcome, CollectionReceipt, CollectionResolveInput,
    FinalDemandPrincipalId, MaterialCircuitState, OrganizationAccountId, UnitId,
};
use babylon_practice_contract::{
    admit_organizer, validate_organizer_collection_fact, OrganizerChoice, OrganizerCollectionFact,
    OrganizerCollectionOutcome, OrganizerCommitment, OrganizerConfig, OrganizerGiftConsent,
    OrganizerState,
};

type Result<T> = std::result::Result<T, MaterialWorldError>;
pub(crate) fn input(
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
    state: &MaterialCircuitState,
) -> Result<Vec<CollectionResolveInput>> {
    let Some(accepted) = accepted.filter(|row| row.command.choice == OrganizerChoice::Collect)
    else {
        return Ok(vec![]);
    };
    if admit_organizer(config, organizer, &accepted.command)? != *accepted
        || accepted.resolves_period != state.period
    {
        return Err(MaterialWorldError::Wire);
    }
    let terms = config.collection.as_ref().ok_or(MaterialWorldError::Wire)?;
    validate_binding(config, state)?;
    let participant = config
        .participants
        .iter()
        .find(|row| row.contributor_id == terms.contributor_id)
        .ok_or(MaterialWorldError::Wire)?;
    let pledged_hours = participant
        .commitments
        .iter()
        .filter(|row| row.actor_id == terms.actor_id)
        .try_fold(0_u64, |sum, row| {
            sum.checked_add(row.hours)
                .ok_or(MaterialWorldError::Arithmetic)
        })?;
    Ok(vec![CollectionResolveInput {
        original_commitment_id: accepted.commitment_id,
        command_nonce: accepted.command.nonce,
        admitted_period: accepted.command.expected_period,
        resolve_period: accepted.resolves_period,
        mandate_id: terms.mandate_id,
        source_hash: terms.source_hash,
        actor_id: terms.actor_id,
        contributor_id: terms.contributor_id,
        donor: FinalDemandPrincipalId::from_bytes(terms.household_principal_id),
        recipient: OrganizationAccountId::from_bytes(terms.organization_account_id),
        labor_unit_id: UnitId::from_bytes(terms.labor_unit_id),
        cash_consent: terms.cash_consent == OrganizerGiftConsent::Accept,
        requested: Currency::from_micro_units(terms.maximum_cash_micros),
        protected_cash_floor: Currency::from_micro_units(terms.protected_cash_floor_micros),
        collection_hours: terms.collection_hours,
        pledged_hours,
    }])
}
pub(super) fn fact(row: &CollectionReceipt) -> OrganizerCollectionFact {
    OrganizerCollectionFact {
        period: row.period,
        admitted_period: row.admitted_period,
        original_commitment_id: row.original_commitment_id,
        command_nonce: row.command_nonce,
        mandate_id: row.mandate_id,
        source_hash: row.source_hash,
        actor_id: row.actor_id,
        contributor_id: row.contributor_id,
        household_principal_id: row.donor.as_bytes(),
        organization_account_id: row.recipient.as_bytes(),
        labor_unit_id: row.labor_unit_id.as_bytes(),
        requested_cash_micros: row.requested.micro_units(),
        collected_cash_micros: row.collected.micro_units(),
        performed_hours: row.performed_hours,
        outcome: match row.outcome {
            CollectionOutcome::Collected => OrganizerCollectionOutcome::Collected,
            CollectionOutcome::CashConsentRefused => OrganizerCollectionOutcome::CashConsentRefused,
            CollectionOutcome::ProtectedConsumptionUnmet => {
                OrganizerCollectionOutcome::ProtectedConsumptionUnmet
            }
            CollectionOutcome::ProtectedServiceUnmet => {
                OrganizerCollectionOutcome::ProtectedServiceUnmet
            }
            CollectionOutcome::ProtectedClosingStockUnmet => {
                OrganizerCollectionOutcome::ProtectedClosingStockUnmet
            }
            CollectionOutcome::DuePaymentUnmet => OrganizerCollectionOutcome::DuePaymentUnmet,
            CollectionOutcome::InsufficientCash => OrganizerCollectionOutcome::InsufficientCash,
            CollectionOutcome::InsufficientContributionTime => {
                OrganizerCollectionOutcome::InsufficientContributionTime
            }
        },
        transfer_ordinal: row.transfer_ordinal,
        contribution_use_id: row.contribution_use_id,
    }
}
pub(super) fn support(
    config: &OrganizerConfig,
    accepted: Option<&OrganizerCommitment>,
    rows: &[CollectionReceipt],
    state: &MaterialCircuitState,
) -> Result<Option<OrganizerCollectionFact>> {
    let Some(accepted) = accepted.filter(|row| row.command.choice == OrganizerChoice::Collect)
    else {
        return if rows.is_empty() {
            Ok(None)
        } else {
            Err(MaterialWorldError::Wire)
        };
    };
    if rows.len() != 1 {
        return Err(MaterialWorldError::Wire);
    }
    collection_receipt::validate_state(rows, state)?;
    let actual = fact(&rows[0]);
    validate_organizer_collection_fact(config, accepted, &actual)?;
    Ok(Some(actual))
}
/// Join authenticated stored canonical receipt and original retained resolution.
/// # Errors
/// Refuses omitted, changed or unmatched collection and material time evidence.
pub(super) fn retained(
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    rows: &[CollectionReceipt],
    state: &MaterialCircuitState,
    period: u64,
) -> Result<()> {
    babylon_practice_contract::validate_organizer_pair(config, organizer)?;
    collection_receipt::validate_state(rows, state)?;
    let retained: Vec<_> = organizer
        .collection_receipts
        .iter()
        .filter(|row| row.fact.period == period)
        .collect();
    if retained.len() != rows.len() {
        return Err(MaterialWorldError::Wire);
    }
    for (resolution, row) in retained.iter().zip(rows) {
        if resolution.fact != fact(row) {
            return Err(MaterialWorldError::Wire);
        }
    }
    Ok(())
}

pub(super) fn current(
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    material: &MaterialCircuitState,
    period: u64,
) -> Result<()> {
    if organizer
        .collection_receipts
        .iter()
        .any(|row| row.fact.period == period)
    {
        // The common adapter authenticates exact original resolution and time
        // before choosing which ordinary uses still need consuming.
        super::organizer_time::uses(config, organizer, period, material)?;
    }
    Ok(())
}

// Current register admission precedes actor-scoped cash projection, even at
// opening0. A structurally valid config cannot name another payer or unit.
pub(super) fn validate_binding(
    config: &OrganizerConfig,
    state: &MaterialCircuitState,
) -> Result<()> {
    let Some(terms) = &config.collection else {
        return Ok(());
    };
    babylon_practice_contract::validate_organizer_config(config)?;
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialWorldError::Wire);
    };
    if !e.aid.mandates.iter().any(|row| {
        row.donor.as_bytes() == terms.household_principal_id
            && row.donor_actor == terms.actor_id
            && row.donor_contributor_id == terms.contributor_id
            && row.payer
                == babylon_material_circuit::AccountId::Organization(
                    OrganizationAccountId::from_bytes(terms.organization_account_id),
                )
            && row.labor_unit_id.as_bytes() == terms.labor_unit_id
            && config.aid_bindings.iter().any(|binding| {
                binding.mandate_id == row.id
                    && binding.source_hash == row.source_hash
                    && binding.donor_principal_id == terms.household_principal_id
                    && binding.donor_contributor_id == terms.contributor_id
            })
    }) {
        return Err(MaterialWorldError::Wire);
    }
    let babylon_material_circuit::HouseholdTimeAccounting::Modeled(time) = &e.household_time else {
        return Err(MaterialWorldError::Wire);
    };
    if time
        .policies
        .iter()
        .filter(|row| {
            row.principal_id.as_bytes() == terms.household_principal_id
                && row.labor_unit_id.as_bytes() == terms.labor_unit_id
        })
        .count()
        != 1
    {
        return Err(MaterialWorldError::Wire);
    }
    e.book
        .cash(babylon_material_circuit::AccountId::Household(
            FinalDemandPrincipalId::from_bytes(terms.household_principal_id),
        ))
        .map_err(|_| MaterialWorldError::Wire)?;
    e.book
        .cash(babylon_material_circuit::AccountId::Organization(
            OrganizationAccountId::from_bytes(terms.organization_account_id),
        ))
        .map_err(|_| MaterialWorldError::Wire)?;
    Ok(())
}
