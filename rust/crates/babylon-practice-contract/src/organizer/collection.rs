//! Explicit captured voluntary cash terms and original material acknowledgments.
use super::*;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerCollectionMandate {
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub actor_id: u64,
    pub contributor_id: u64,
    pub household_principal_id: [u8; 32],
    pub organization_account_id: [u8; 32],
    pub social_class_target: [u8; 32],
    pub labor_unit_id: [u8; 32],
    pub cash_consent: OrganizerGiftConsent,
    #[serde(with = "nonnegative_decimal_i128")]
    pub maximum_cash_micros: i128,
    #[serde(with = "nonnegative_decimal_i128")]
    pub protected_cash_floor_micros: i128,
    pub collection_hours: u64,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrganizerCollectionOutcome {
    Collected,
    PartiallyCollected,
    CashConsentRefused,
    ProtectedConsumptionUnmet,
    ProtectedServiceUnmet,
    ProtectedClosingStockUnmet,
    DuePaymentUnmet,
    InsufficientCash,
    InsufficientContributionTime,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerCollectionFact {
    pub period: u64,
    pub admitted_period: u64,
    pub original_commitment_id: [u8; 32],
    pub command_nonce: [u8; 16],
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub actor_id: u64,
    pub contributor_id: u64,
    pub household_principal_id: [u8; 32],
    pub organization_account_id: [u8; 32],
    pub labor_unit_id: [u8; 32],
    #[serde(with = "nonnegative_decimal_i128")]
    pub requested_cash_micros: i128,
    #[serde(with = "nonnegative_decimal_i128")]
    pub collected_cash_micros: i128,
    pub performed_hours: u64,
    pub outcome: OrganizerCollectionOutcome,
    #[serde(deserialize_with = "required_transfer_ordinal")]
    pub transfer_ordinal: Option<u32>,
    pub contribution_use_id: [u8; 32],
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerCollectionResolution {
    pub commitment: OrganizerCommitment,
    pub fact: OrganizerCollectionFact,
    pub practice: OrganizerReceipt,
}
pub(super) fn validate_collection_config(config: &OrganizerConfig) -> Result<(), OrganizerError> {
    let Some(row) = &config.collection else {
        return Ok(());
    };
    let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding else {
        return Err(OrganizerError::TimeBindingMismatch);
    };
    if row.actor_id != config.controlled_actor_id
        || row.contributor_id == 0
        || [
            row.mandate_id,
            row.source_hash,
            row.organization_account_id,
            row.social_class_target,
            row.labor_unit_id,
        ]
        .contains(&[0; 32])
        || row.maximum_cash_micros <= 0
        || row.protected_cash_floor_micros < 0
        || row.collection_hours == 0
        || row
            .maximum_cash_micros
            .checked_add(row.protected_cash_floor_micros)
            .is_none()
        || config
            .aid_bindings
            .iter()
            .any(|aid| aid.mandate_id == row.mandate_id)
        || !config.aid_bindings.iter().any(|aid| {
            aid.donor_contributor_id == row.contributor_id
                && aid.donor_principal_id == row.household_principal_id
        })
        || !bindings.iter().any(|binding| {
            binding.contributor_id == row.contributor_id
                && binding.principal_id == row.household_principal_id
        })
    {
        return Err(OrganizerError::InvalidConfig);
    }
    Ok(())
}
pub(super) fn collection_pledge(config: &OrganizerConfig) -> Result<u64, OrganizerError> {
    let mandate = config
        .collection
        .as_ref()
        .ok_or(OrganizerError::InvalidCommitment)?;
    config
        .participants
        .iter()
        .find(|row| row.contributor_id == mandate.contributor_id)
        .ok_or(OrganizerError::TimeBindingMismatch)?
        .commitments
        .iter()
        .filter(|row| row.actor_id == mandate.actor_id)
        .try_fold(0_u64, |sum, row| {
            sum.checked_add(row.hours).ok_or(OrganizerError::Arithmetic)
        })
}
pub(super) fn collection_refusal(
    config: &OrganizerConfig,
) -> Result<Option<OrganizerRefusal>, OrganizerError> {
    let Some(row) = &config.collection else {
        return Ok(Some(OrganizerRefusal::CollectionUnavailable));
    };
    if row.cash_consent == OrganizerGiftConsent::Refuse {
        return Ok(Some(OrganizerRefusal::CollectionCashRefused));
    }
    Ok((collection_pledge(config)? < row.collection_hours)
        .then_some(OrganizerRefusal::InsufficientCommittedTime))
}
/// Original immutable identity, usable after its admission period has passed.
/// # Errors
/// Refuses a changed command, captured source, actor, account or contributor.
pub fn validate_organizer_collection_fact(
    config: &OrganizerConfig,
    commitment: &OrganizerCommitment,
    fact: &OrganizerCollectionFact,
) -> Result<(), OrganizerError> {
    validate_organizer_config(config)?;
    validate_organizer_commitment(commitment)?;
    if collection_refusal(config)?.is_some() {
        return Err(OrganizerError::CollectionSupportMismatch);
    }
    let row = config
        .collection
        .as_ref()
        .ok_or(OrganizerError::CollectionSupportMismatch)?;
    let command = &commitment.command;
    let paid = matches!(
        fact.outcome,
        OrganizerCollectionOutcome::Collected | OrganizerCollectionOutcome::PartiallyCollected
    );
    if command.choice != OrganizerChoice::Collect
        || command.campaign_id != config.campaign_id
        || command.actor_id != row.actor_id
        || command.authority_id != config.input_authority_id
        || command.content_digest != config.content_digest
        || command.resource_digest != organizer_resource_digest()?
        || fact.period != commitment.resolves_period
        || fact.admitted_period != command.expected_period
        || fact.original_commitment_id != commitment.commitment_id
        || fact.command_nonce != command.nonce
        || fact.mandate_id != row.mandate_id
        || fact.source_hash != row.source_hash
        || fact.actor_id != row.actor_id
        || fact.contributor_id != row.contributor_id
        || fact.household_principal_id != row.household_principal_id
        || fact.organization_account_id != row.organization_account_id
        || fact.labor_unit_id != row.labor_unit_id
        || fact.requested_cash_micros != row.maximum_cash_micros
        || (fact.outcome == OrganizerCollectionOutcome::Collected
            && fact.collected_cash_micros != row.maximum_cash_micros)
        || (fact.outcome == OrganizerCollectionOutcome::PartiallyCollected
            && (fact.collected_cash_micros <= 0
                || fact.collected_cash_micros >= row.maximum_cash_micros))
        || (paid
            && (row.cash_consent != OrganizerGiftConsent::Accept
                || fact.performed_hours != row.collection_hours
                || fact.transfer_ordinal.is_none()
                || fact.transfer_ordinal == Some(u32::MAX)
                || fact.contribution_use_id != contribution_id(fact)))
        || (!paid
            && (fact.collected_cash_micros != 0
                || fact.performed_hours != 0
                || fact.transfer_ordinal.is_some()
                || fact.contribution_use_id != [0; 32]))
    {
        return Err(OrganizerError::CollectionSupportMismatch);
    }
    Ok(())
}
pub(super) fn acknowledge_collection(
    config: &OrganizerConfig,
    commitment: &OrganizerCommitment,
    fact: &OrganizerCollectionFact,
    receipt: &mut OrganizerReceipt,
) -> Result<OrganizerCollectionResolution, OrganizerError> {
    validate_organizer_collection_fact(config, commitment, fact)?;
    receipt.outcome = if matches!(
        fact.outcome,
        OrganizerCollectionOutcome::Collected | OrganizerCollectionOutcome::PartiallyCollected
    ) {
        OrganizerOutcome::CollectionCompleted
    } else {
        OrganizerOutcome::CollectionRefused
    };
    receipt.hours_spent = fact.performed_hours;
    if fact.performed_hours > 0 {
        receipt.time_use.push(OrganizerTimeUse {
            contributor_id: fact.contributor_id,
            actor_id: fact.actor_id,
            hours: fact.performed_hours,
        });
    }
    Ok(OrganizerCollectionResolution {
        commitment: commitment.clone(),
        fact: fact.clone(),
        practice: receipt.clone(),
    })
}
pub(super) fn validate_collection_history(
    config: &OrganizerConfig,
    state: &OrganizerState,
) -> Result<(), OrganizerError> {
    if state.collection_receipts.len() > 65_536
        || state
            .collection_receipts
            .windows(2)
            .any(|rows| rows[0].fact.period >= rows[1].fact.period)
    {
        return Err(OrganizerError::InvalidState);
    }
    for row in &state.collection_receipts {
        validate_organizer_collection_fact(config, &row.commitment, &row.fact)?;
        let mut expected = row.practice.clone();
        expected.outcome = OrganizerOutcome::NoAuthorizedPractice;
        expected.hours_spent = 0;
        expected.time_use.clear();
        if acknowledge_collection(config, &row.commitment, &row.fact, &mut expected)?.practice
            != row.practice
            || row.practice.receipt_id
                != super::contract::identity(
                    b"babylon.organizer-receipt.v1",
                    &(
                        config.campaign_id,
                        config.controlled_actor_id,
                        row.fact.period,
                        row.commitment.commitment_id,
                    ),
                )?
            || row.practice.choice != OrganizerChoice::Collect
            || row.practice.commitment_id != Some(row.commitment.commitment_id)
            || row.practice.actor_id != row.fact.actor_id
            || row.practice.period != row.fact.period
            || row.fact.period > state.period
            || row.practice.standing_work
            || row.practice.partner_actor_id.is_some()
            || row.practice.partner_response != OrganizerPartnerResponse::NotRequested
            || !row.practice.observation_ids.is_empty()
            || row.practice.contact_product_id.is_some()
            || state
                .receipts
                .iter()
                .filter(|receipt| **receipt == row.practice)
                .count()
                != 1
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    for receipt in state
        .receipts
        .iter()
        .filter(|row| row.choice == OrganizerChoice::Collect)
    {
        if state
            .collection_receipts
            .iter()
            .filter(|row| row.practice == *receipt)
            .count()
            != 1
        {
            return Err(OrganizerError::CollectionSupportMissing);
        }
    }
    Ok(())
}
// Material capacity is already net. Only the original donor pledge is reduced
// here; ordinary and delayed political allocation then debits residual capacity.
pub(super) fn remaining_collection_pledge(
    config: &OrganizerConfig,
    state: &OrganizerState,
    period: u64,
) -> Result<OrganizerConfig, OrganizerError> {
    let mut remaining = config.clone();
    for row in state
        .collection_receipts
        .iter()
        .filter(|row| row.fact.period == period && row.fact.performed_hours > 0)
    {
        validate_organizer_collection_fact(config, &row.commitment, &row.fact)?;
        let participant = remaining
            .participants
            .iter_mut()
            .find(|p| p.contributor_id == row.fact.contributor_id)
            .ok_or(OrganizerError::TimeBindingMismatch)?;
        let pledge = participant
            .commitments
            .iter_mut()
            .find(|p| p.actor_id == row.fact.actor_id)
            .ok_or(OrganizerError::ResourceAllocation)?;
        pledge.hours = pledge
            .hours
            .checked_sub(row.fact.performed_hours)
            .ok_or(OrganizerError::ResourceAllocation)?;
        participant.commitments.retain(|p| p.hours > 0);
    }
    Ok(remaining)
}

fn contribution_id(fact: &OrganizerCollectionFact) -> [u8; 32] {
    let mut bytes = b"babylon.collection-household-contribution.v1\0".to_vec();
    bytes.extend_from_slice(&fact.original_commitment_id);
    bytes.extend_from_slice(&fact.mandate_id);
    for value in [fact.period, fact.actor_id, fact.contributor_id] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes.extend_from_slice(&fact.household_principal_id);
    bytes.extend_from_slice(&fact.labor_unit_id);
    babylon_kernel::content_digest::sha256_of(&bytes)
}

pub(super) fn required_terms<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> Result<Option<OrganizerCollectionMandate>, D::Error> {
    Option::<OrganizerCollectionMandate>::deserialize(deserializer)
}

fn required_transfer_ordinal<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> Result<Option<u32>, D::Error> {
    Option::<u32>::deserialize(deserializer)
}

pub(super) fn validate_collection_state_shape(
    state: &OrganizerState,
) -> Result<(), OrganizerError> {
    if state.collection_receipts.len() > 65_536
        || state
            .collection_receipts
            .windows(2)
            .any(|pair| pair[0].fact.period >= pair[1].fact.period)
    {
        return Err(OrganizerError::SizeLimit);
    }
    for row in &state.collection_receipts {
        validate_organizer_commitment(&row.commitment)?;
        validate_organizer_receipt(&row.practice)?;
        let fact = &row.fact;
        let paid = matches!(
            fact.outcome,
            OrganizerCollectionOutcome::Collected | OrganizerCollectionOutcome::PartiallyCollected
        );
        if row.commitment.command.choice != OrganizerChoice::Collect
            || row.practice.choice != OrganizerChoice::Collect
            || fact.period == 0
            || fact.period > state.period
            || fact.admitted_period != row.commitment.command.expected_period
            || fact.period != row.commitment.resolves_period
            || fact.original_commitment_id != row.commitment.commitment_id
            || fact.command_nonce != row.commitment.command.nonce
            || fact.actor_id != row.commitment.command.actor_id
            || fact.requested_cash_micros <= 0
            || fact.contributor_id == 0
            || [
                fact.mandate_id,
                fact.source_hash,
                fact.household_principal_id,
                fact.organization_account_id,
                fact.labor_unit_id,
            ]
            .contains(&[0; 32])
            || (fact.outcome == OrganizerCollectionOutcome::Collected
                && fact.collected_cash_micros != fact.requested_cash_micros)
            || (fact.outcome == OrganizerCollectionOutcome::PartiallyCollected
                && (fact.collected_cash_micros <= 0
                    || fact.collected_cash_micros >= fact.requested_cash_micros))
            || (paid
                && (fact.performed_hours == 0
                    || fact.transfer_ordinal.is_none()
                    || fact.transfer_ordinal == Some(u32::MAX)
                    || fact.contribution_use_id != contribution_id(fact)))
            || (!paid
                && (fact.collected_cash_micros != 0
                    || fact.performed_hours != 0
                    || fact.transfer_ordinal.is_some()
                    || fact.contribution_use_id != [0; 32]))
        {
            return Err(OrganizerError::CollectionSupportMismatch);
        }
    }
    Ok(())
}
