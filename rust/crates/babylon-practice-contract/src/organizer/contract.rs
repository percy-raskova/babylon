use std::collections::BTreeSet;

use babylon_kernel::content_digest::sha256_of;
use serde::de::DeserializeOwned;

use super::*;

const MAX_ORGANIZER_BYTES: usize = 32 * 1024 * 1024;
const MAX_ORGANIZER_ROWS: usize = 65_536;

pub(super) fn canonical<T: Serialize>(domain: &[u8], value: &T) -> Result<Vec<u8>, OrganizerError> {
    let mut output = Vec::from(domain);
    output.push(0);
    serde_json::to_writer(&mut output, value).map_err(|_| OrganizerError::Codec)?;
    if output.len() > MAX_ORGANIZER_BYTES {
        return Err(OrganizerError::SizeLimit);
    }
    Ok(output)
}

fn decode<T: Serialize + DeserializeOwned>(
    domain: &[u8],
    bytes: &[u8],
) -> Result<T, OrganizerError> {
    if bytes.len() > MAX_ORGANIZER_BYTES {
        return Err(OrganizerError::SizeLimit);
    }
    let payload = bytes
        .strip_prefix(domain)
        .and_then(|rest| rest.strip_prefix(&[0]))
        .ok_or(OrganizerError::Codec)?;
    let value = serde_json::from_slice(payload).map_err(|_| OrganizerError::Codec)?;
    if canonical(domain, &value)? != bytes {
        return Err(OrganizerError::NonCanonical);
    }
    Ok(value)
}

pub(super) fn identity<T: Serialize>(domain: &[u8], value: &T) -> Result<[u8; 32], OrganizerError> {
    Ok(sha256_of(&canonical(domain, value)?))
}

fn label_valid(value: &str) -> bool {
    !value.is_empty() && value.len() <= 512 && !value.chars().any(char::is_control)
}

pub fn validate_organizer_config(config: &OrganizerConfig) -> Result<(), OrganizerError> {
    if config.schema_version != ORGANIZER_SCHEMA_VERSION {
        return Err(OrganizerError::UnsupportedSchema);
    }
    if config.aid_bindings.len() > 2 {
        return Err(OrganizerError::InvalidConfig);
    }
    let mut actors = vec![
        config.controlled_actor_id,
        config.workplace_partner.actor_id,
        config.neighborhood_partner.actor_id,
    ];
    let mut authorities = vec![
        config.input_authority_id,
        config.workplace_partner.authority_id,
        config.neighborhood_partner.authority_id,
    ];
    for binding in &config.aid_bindings {
        actors.push(binding.partner.actor_id);
        authorities.push(binding.partner.authority_id);
    }
    if actors.contains(&0)
        || actors.iter().copied().collect::<BTreeSet<_>>().len() != actors.len()
        || authorities.contains(&[0; 16])
        || authorities.iter().copied().collect::<BTreeSet<_>>().len() != authorities.len()
        || config.workplace_id == 0
        || config.workplace_process_id == [0; 32]
        || actors.contains(&config.workplace_id)
        || !label_valid(&config.organization_label)
        || !label_valid(&config.workplace_label)
        || !label_valid(&config.workplace_partner.label)
        || !label_valid(&config.neighborhood_partner.label)
        || config.inquiry_hours == 0
        || config.contact_hours == 0
        || config.partner_response_hours == 0
        || config.contact_renewal_periods == 0
        || config.initial_agreement_through_period == 0
        || config.participants.is_empty()
        || config.participants.len() > 16
    {
        return Err(OrganizerError::InvalidConfig);
    }
    let mut prior = None;
    for participant in &config.participants {
        if participant.contributor_id == 0
            || prior.is_some_and(|id| id >= participant.contributor_id)
            || !label_valid(&participant.label)
            || participant.concern.len() > 2048
            || participant.objection.len() > 2048
            || participant.review_condition.len() > 2048
            || participant.commitments.len() > actors.len()
        {
            return Err(OrganizerError::InvalidConfig);
        }
        prior = Some(participant.contributor_id);
        let mut previous_actor = None;
        let mut promised = 0_u64;
        for commitment in &participant.commitments {
            if !actors.contains(&commitment.actor_id)
                || commitment.hours == 0
                || previous_actor.is_some_and(|id| id >= commitment.actor_id)
            {
                return Err(OrganizerError::InvalidConfig);
            }
            previous_actor = Some(commitment.actor_id);
            promised = promised
                .checked_add(commitment.hours)
                .ok_or(OrganizerError::Arithmetic)?;
        }
        // One participant body can promise disjoint hours to several actors,
        // never the same available hour twice.
        if promised > participant.available_hours {
            return Err(OrganizerError::InvalidConfig);
        }
    }
    validate_time_binding(config)?;
    super::aid::validate_aid_bindings(config)?;
    super::collection::validate_collection_config(config)?;
    if config
        .aid_bindings
        .iter()
        .any(|row| !label_valid(&row.partner.label))
    {
        return Err(OrganizerError::InvalidConfig);
    }
    if config.initial_observations.len() > MAX_ORGANIZER_ROWS {
        return Err(OrganizerError::SizeLimit);
    }
    let mut observations = BTreeSet::new();
    for observation in &config.initial_observations {
        if observation.actor_id != config.controlled_actor_id
            || observation.subject_id != config.workplace_id
            || observation.source_actor_id != config.workplace_partner.actor_id
            || observation.observed_period != 0
            || observation.acquired_period != 0
            || observation.receipt_id.is_some()
            || !observations.insert(observation.observation_id)
        {
            return Err(OrganizerError::InvalidConfig);
        }
    }
    Ok(())
}

fn validate_time_binding(config: &OrganizerConfig) -> Result<(), OrganizerError> {
    let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding else {
        return Ok(());
    };
    if bindings.len() != config.participants.len()
        || bindings
            .iter()
            .zip(&config.participants)
            .any(|(binding, participant)| {
                binding.contributor_id != participant.contributor_id
                    || binding.principal_id == [0; 32]
            })
    {
        return Err(OrganizerError::TimeBindingMismatch);
    }
    Ok(())
}

pub fn validate_organizer_state(state: &OrganizerState) -> Result<(), OrganizerError> {
    if state.schema_version != ORGANIZER_SCHEMA_VERSION {
        return Err(OrganizerError::UnsupportedSchema);
    }
    if state.observations.len() > MAX_ORGANIZER_ROWS
        || state.receipts.len() > MAX_ORGANIZER_ROWS
        || state.aid_receipts.len() > MAX_ORGANIZER_ROWS
        || state.pending_aid.len() > 2
        || state.contact_products.len() > MAX_ORGANIZER_ROWS
        || state.consumed_product_ids.len() > MAX_ORGANIZER_ROWS
        || state.agreements.len() > 2
    {
        return Err(OrganizerError::SizeLimit);
    }
    if (state.standing.authorized && state.standing.paused_reason.is_some())
        || (!state.standing.authorized && state.standing.paused_reason.is_none())
    {
        return Err(OrganizerError::InvalidState);
    }
    let mut agreement_keys = BTreeSet::new();
    for row in &state.agreements {
        if row.valid_from_period > row.valid_through_period
            || !agreement_keys.insert((row.actor_id, row.partner_actor_id))
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    let mut receipt_ids = BTreeSet::new();
    let mut prior_period = 0;
    for receipt in &state.receipts {
        validate_organizer_receipt(receipt)?;
        if receipt.period == 0
            || receipt.period > state.period
            || receipt.period <= prior_period
            || !receipt_ids.insert(receipt.receipt_id)
        {
            return Err(OrganizerError::InvalidState);
        }
        prior_period = receipt.period;
        let own_hours = receipt
            .time_use
            .iter()
            .filter(|row| row.actor_id == receipt.actor_id)
            .try_fold(0_u64, |sum, row| {
                sum.checked_add(row.hours).ok_or(OrganizerError::Arithmetic)
            })?;
        if own_hours != receipt.hours_spent {
            return Err(OrganizerError::InvalidState);
        }
    }
    super::aid::validate_aid_state(state)?;
    super::collection::validate_collection_state_shape(state)?;
    let mut observation_ids = BTreeSet::new();
    for observation in &state.observations {
        if observation.observed_period > observation.acquired_period
            || observation.acquired_period > state.period
            || !observation_ids.insert(observation.observation_id)
            || observation
                .receipt_id
                .is_some_and(|id| !receipt_ids.contains(&id))
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    let mut product_ids = BTreeSet::new();
    for product in &state.contact_products {
        if product.produced_period == 0
            || product.produced_period > state.period
            || !receipt_ids.contains(&product.receipt_id)
            || !product_ids.insert(product.product_id)
            || !state.receipts.iter().any(|receipt| {
                receipt.receipt_id == product.receipt_id
                    && receipt.period == product.produced_period
                    && receipt.outcome == OrganizerOutcome::ContactCompleted
                    && receipt.partner_response == OrganizerPartnerResponse::Participated
                    && receipt.contact_product_id == Some(product.product_id)
                    && product.actor_id == receipt.actor_id
                    && Some(product.partner_actor_id) == receipt.partner_actor_id
            })
        {
            return Err(OrganizerError::InvalidState);
        }
        if product.product_id
            != identity(
                b"babylon.organizer-contact-product.v1",
                &(
                    product.receipt_id,
                    product.actor_id,
                    product.partner_actor_id,
                    product.produced_period,
                ),
            )?
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    let mut consumed_ids = BTreeSet::new();
    for id in &state.consumed_product_ids {
        if !product_ids.contains(id) || !consumed_ids.insert(*id) {
            return Err(OrganizerError::InvalidState);
        }
    }
    if state
        .last_workplace_facts
        .as_ref()
        .is_some_and(|facts| facts.period != state.period)
    {
        return Err(OrganizerError::InvalidState);
    }
    Ok(())
}

pub fn validate_organizer_pair(
    config: &OrganizerConfig,
    state: &OrganizerState,
) -> Result<(), OrganizerError> {
    validate_organizer_config(config)?;
    validate_organizer_state(state)?;
    let partner_ids = [
        config.workplace_partner.actor_id,
        config.neighborhood_partner.actor_id,
    ];
    if state.standing.partner_actor_id != config.neighborhood_partner.actor_id
        || state.agreements.iter().any(|row| {
            row.actor_id != config.controlled_actor_id
                || !partner_ids.contains(&row.partner_actor_id)
        })
        || state.observations.iter().any(|row| {
            row.actor_id != config.controlled_actor_id
                || row.subject_id != config.workplace_id
                || row.source_actor_id != config.workplace_partner.actor_id
        })
        || state
            .receipts
            .iter()
            .any(|row| row.actor_id != config.controlled_actor_id)
        || state
            .last_workplace_facts
            .as_ref()
            .is_some_and(|row| row.workplace_id != config.workplace_id)
    {
        return Err(OrganizerError::InvalidState);
    }
    super::collection::validate_collection_history(config, state)?;
    for pending in &state.pending_aid {
        super::aid::validate_pending(config, pending)?;
    }
    for row in &state.aid_receipts {
        super::aid::validate_pending(config, &row.authorization)?;
        super::aid::validate_resolution_allocation(config, row)?;
    }
    for receipt in state
        .receipts
        .iter()
        .chain(state.aid_receipts.iter().map(|row| &row.practice))
    {
        if let Some(kind) = super::aid::aid_kind(receipt.choice) {
            let binding = config
                .aid_bindings
                .iter()
                .find(|row| row.kind == kind)
                .ok_or(OrganizerError::InvalidState)?;
            if receipt
                .partner_actor_id
                .is_some_and(|id| id != binding.partner.actor_id)
                || receipt.time_use.iter().any(|row| {
                    (row.actor_id == config.controlled_actor_id
                        && row.contributor_id != binding.donor_contributor_id)
                        || (row.actor_id == binding.partner.actor_id
                            && row.contributor_id != binding.recipient_contributor_id)
                        || (row.actor_id != config.controlled_actor_id
                            && row.actor_id != binding.partner.actor_id)
                })
            {
                return Err(OrganizerError::InvalidState);
            }
        }
        for participant in &config.participants {
            let spent = receipt
                .time_use
                .iter()
                .filter(|row| row.contributor_id == participant.contributor_id)
                .try_fold(0_u64, |sum, row| {
                    sum.checked_add(row.hours).ok_or(OrganizerError::Arithmetic)
                })?;
            if spent > participant.available_hours {
                return Err(OrganizerError::InvalidState);
            }
        }
        if receipt.time_use.iter().any(|row| {
            !config.participants.iter().any(|participant| {
                participant.contributor_id == row.contributor_id
                    && participant.commitments.iter().any(|commitment| {
                        commitment.actor_id == row.actor_id && commitment.hours >= row.hours
                    })
            })
        }) {
            return Err(OrganizerError::InvalidState);
        }
    }
    super::aid::validate_period_allocations(config, state)?;
    Ok(())
}

pub fn encode_organizer_config(config: &OrganizerConfig) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_config(config)?;
    canonical(b"babylon.organizer-config.v6", config)
}

pub fn decode_organizer_config(bytes: &[u8]) -> Result<OrganizerConfig, OrganizerError> {
    let value = decode(b"babylon.organizer-config.v6", bytes)?;
    validate_organizer_config(&value)?;
    Ok(value)
}

pub fn encode_organizer_state(state: &OrganizerState) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_state(state)?;
    super::aid::validate_completed_aid(state)?;
    canonical(b"babylon.organizer-state.v4", state)
}

pub fn decode_organizer_state(bytes: &[u8]) -> Result<OrganizerState, OrganizerError> {
    let value = decode(b"babylon.organizer-state.v4", bytes)?;
    validate_organizer_state(&value)?;
    super::aid::validate_completed_aid(&value)?;
    Ok(value)
}

pub fn organizer_state_digest(state: &OrganizerState) -> Result<[u8; 32], OrganizerError> {
    Ok(sha256_of(&encode_organizer_state(state)?))
}

pub fn validate_organizer_receipt(receipt: &OrganizerReceipt) -> Result<(), OrganizerError> {
    let mut allocations = BTreeSet::new();
    let own_hours = receipt
        .time_use
        .iter()
        .filter(|row| row.actor_id == receipt.actor_id)
        .try_fold(0_u64, |sum, row| {
            sum.checked_add(row.hours).ok_or(OrganizerError::Arithmetic)
        })?;
    if (matches!(
        receipt.outcome,
        OrganizerOutcome::AidScheduled
            | OrganizerOutcome::AidAwaitingSupport
            | OrganizerOutcome::AidNotProvisioned
    ) && (!receipt.time_use.is_empty()
        || receipt.partner_actor_id.is_some()
        || receipt.partner_response != OrganizerPartnerResponse::NotRequested))
        || (receipt.choice == OrganizerChoice::Collect
            && (receipt.standing_work
                || receipt.commitment_id.is_none()
                || receipt.partner_actor_id.is_some()
                || receipt.partner_response != OrganizerPartnerResponse::NotRequested
                || !matches!(
                    receipt.outcome,
                    OrganizerOutcome::CollectionCompleted | OrganizerOutcome::CollectionRefused
                )))
        || (matches!(
            receipt.outcome,
            OrganizerOutcome::CollectionCompleted | OrganizerOutcome::CollectionRefused
        ) && receipt.choice != OrganizerChoice::Collect)
        || receipt.actor_id == 0
        || receipt.period == 0
        || own_hours != receipt.hours_spent
        || receipt.time_use.len() > 32
        || receipt.observation_ids.len() > 1
        || receipt.time_use.iter().any(|row| {
            row.hours == 0
                || row.actor_id == 0
                || row.contributor_id == 0
                || !allocations.insert((row.contributor_id, row.actor_id))
        })
        || (receipt.outcome == OrganizerOutcome::ContactCompleted)
            != receipt.contact_product_id.is_some()
        || (receipt.outcome == OrganizerOutcome::EvidenceObtained)
            == receipt.observation_ids.is_empty()
        || (matches!(
            receipt.outcome,
            OrganizerOutcome::ContactCompleted
                | OrganizerOutcome::EvidenceObtained
                | OrganizerOutcome::AidPracticeCompleted
        ) && receipt.partner_response != OrganizerPartnerResponse::Participated)
        || (matches!(
            receipt.outcome,
            OrganizerOutcome::StandingPaused
                | OrganizerOutcome::AidScheduled
                | OrganizerOutcome::AidAwaitingSupport
                | OrganizerOutcome::AidNotProvisioned
                | OrganizerOutcome::InsufficientTime
                | OrganizerOutcome::CollectionRefused
                | OrganizerOutcome::NoAuthorizedPractice
        ) && receipt.hours_spent != 0)
        || (super::aid::aid_kind(receipt.choice).is_some()
            && (receipt.standing_work
                || receipt.contact_product_id.is_some()
                || !receipt.observation_ids.is_empty()
                || !matches!(
                    receipt.outcome,
                    OrganizerOutcome::AidScheduled
                        | OrganizerOutcome::AidAwaitingSupport
                        | OrganizerOutcome::AidNotProvisioned
                        | OrganizerOutcome::AidPracticeCompleted
                        | OrganizerOutcome::AidPracticeUncompleted
                        | OrganizerOutcome::InsufficientTime
                )))
        || (matches!(
            receipt.outcome,
            OrganizerOutcome::AidPracticeCompleted | OrganizerOutcome::AidPracticeUncompleted
        ) && (super::aid::aid_kind(receipt.choice).is_none()
            || receipt.standing_work
            || receipt.commitment_id.is_none()))
    {
        return Err(OrganizerError::InvalidState);
    }
    Ok(())
}

pub fn encode_organizer_receipt(receipt: &OrganizerReceipt) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_receipt(receipt)?;
    canonical(b"babylon.organizer-receipt.v2", receipt)
}

pub fn decode_organizer_receipt(bytes: &[u8]) -> Result<OrganizerReceipt, OrganizerError> {
    let value = decode(b"babylon.organizer-receipt.v2", bytes)?;
    validate_organizer_receipt(&value)?;
    Ok(value)
}

pub fn organizer_resource_digest() -> Result<[u8; 32], OrganizerError> {
    crate::practice_resource_allocation_contract_digest(
        &crate::PracticeResourceAllocationContract::conservation_first(),
    )
    .map_err(|_| OrganizerError::ResourceAllocation)
}

pub fn initial_organizer_state(config: &OrganizerConfig) -> Result<OrganizerState, OrganizerError> {
    validate_organizer_config(config)?;
    let mut agreements: Vec<_> = [
        config.workplace_partner.actor_id,
        config.neighborhood_partner.actor_id,
    ]
    .into_iter()
    .map(|partner_actor_id| OrganizerAgreement {
        actor_id: config.controlled_actor_id,
        partner_actor_id,
        valid_from_period: 0,
        valid_through_period: config.initial_agreement_through_period,
        source_product_id: None,
    })
    .collect();
    agreements.sort_by_key(|row| (row.actor_id, row.partner_actor_id));
    Ok(OrganizerState {
        schema_version: ORGANIZER_SCHEMA_VERSION,
        period: 0,
        standing: OrganizerStandingWork {
            partner_actor_id: config.neighborhood_partner.actor_id,
            authorized: true,
            paused_reason: None,
        },
        agreements,
        observations: config.initial_observations.clone(),
        receipts: vec![],
        pending_aid: vec![],
        aid_receipts: vec![],
        collection_receipts: vec![],
        contact_products: vec![],
        consumed_product_ids: vec![],
        last_workplace_facts: None,
    })
}

pub(super) fn committed_hours(
    config: &OrganizerConfig,
    actor_id: u64,
) -> Result<u64, OrganizerError> {
    config
        .participants
        .iter()
        .flat_map(|participant| &participant.commitments)
        .filter(|commitment| commitment.actor_id == actor_id)
        .try_fold(0_u64, |sum, commitment| {
            sum.checked_add(commitment.hours)
                .ok_or(OrganizerError::Arithmetic)
        })
}

pub fn organizer_view(
    config: &OrganizerConfig,
    state: &OrganizerState,
    actor_id: u64,
) -> Result<OrganizerView, OrganizerError> {
    validate_organizer_pair(config, state)?;
    if actor_id != config.controlled_actor_id {
        return Err(OrganizerError::Refused(OrganizerRefusal::WrongAuthority));
    }
    let mut receipts = state
        .receipts
        .iter()
        .filter(|row| row.actor_id == actor_id)
        .collect::<Vec<_>>();
    let total_receipt_count =
        u32::try_from(receipts.len()).map_err(|_| OrganizerError::Arithmetic)?;
    receipts.sort_by_key(|row| (row.period, row.receipt_id));
    let receipts = receipts
        .into_iter()
        .rev()
        .take(ORGANIZER_RECENT_RECEIPTS)
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .cloned()
        .map(|mut receipt| {
            // Independent partners disclose participation, not their time ledger.
            receipt.time_use.retain(|row| row.actor_id == actor_id);
            receipt
        })
        .collect();
    let mut observations = state
        .observations
        .iter()
        .filter(|row| row.actor_id == actor_id)
        .collect::<Vec<_>>();
    let total_observation_count =
        u32::try_from(observations.len()).map_err(|_| OrganizerError::Arithmetic)?;
    observations.sort_by_key(|row| (row.acquired_period, row.observed_period, row.observation_id));
    // Preserve the latest materially distinct report even when it predates the recent window.
    let mut latest = std::collections::BTreeMap::new();
    for row in &observations {
        let kind = match row.report {
            OrganizerReport::Work { .. } => 0_u8,
            OrganizerReport::ReducedWork { .. } => 1,
            OrganizerReport::Maintenance { .. } => 2,
        };
        let key = (row.subject_id, row.source_actor_id, kind);
        let candidate = (row.observed_period, row.acquired_period, row.observation_id);
        if latest.get(&key).is_none_or(|old: &&OrganizerObservation| {
            candidate > (old.observed_period, old.acquired_period, old.observation_id)
        }) {
            latest.insert(key, *row);
        }
    }
    let mut selected: BTreeSet<_> = observations
        .iter()
        .rev()
        .take(ORGANIZER_RECENT_OBSERVATIONS)
        .map(|row| row.observation_id)
        .collect();
    selected.extend(latest.values().map(|row| row.observation_id));
    let observations = observations
        .into_iter()
        .filter(|row| selected.contains(&row.observation_id))
        .cloned()
        .collect();
    let positions = config
        .participants
        .iter()
        .filter_map(|participant| {
            participant
                .commitments
                .iter()
                .find(|commitment| commitment.actor_id == actor_id)
                .map(|commitment| OrganizerPosition {
                    contributor_id: participant.contributor_id,
                    label: participant.label.clone(),
                    promised_hours: commitment.hours,
                    concern: participant.concern.clone(),
                    objection: participant.objection.clone(),
                    review_condition: participant.review_condition.clone(),
                })
        })
        .collect();
    Ok(OrganizerView {
        period: state.period,
        actor_id,
        authority_id: config.input_authority_id,
        organization_label: config.organization_label.clone(),
        workplace_id: config.workplace_id,
        workplace_label: config.workplace_label.clone(),
        workplace_partner_id: config.workplace_partner.actor_id,
        workplace_partner_label: config.workplace_partner.label.clone(),
        neighborhood_partner_id: config.neighborhood_partner.actor_id,
        neighborhood_partner_label: config.neighborhood_partner.label.clone(),
        available_hours: committed_hours(config, actor_id)?,
        inquiry_hours: config.inquiry_hours,
        contact_hours: config.contact_hours,
        content_digest: config.content_digest,
        resource_digest: organizer_resource_digest()?,
        standing: state.standing.clone(),
        agreements: state
            .agreements
            .iter()
            .filter(|row| row.actor_id == actor_id)
            .cloned()
            .collect(),
        total_observation_count,
        observations,
        total_receipt_count,
        receipts,
        positions,
        aid_options: config
            .aid_bindings
            .iter()
            .filter(|binding| {
                !state
                    .pending_aid
                    .iter()
                    .any(|row| row.gift.kind == binding.kind)
            })
            .map(|row| OrganizerAidOption {
                kind: row.kind,
                partner_actor_id: row.partner.actor_id,
                partner_label: row.partner.label.clone(),
                coordination_hours: row.coordination_hours,
                receiving_consent: row.receiving_consent,
            })
            .collect(),
    })
}

pub(super) fn required_hours(
    config: &OrganizerConfig,
    state: &OrganizerState,
    choice: OrganizerChoice,
) -> u64 {
    match choice {
        OrganizerChoice::Collect => config
            .collection
            .as_ref()
            .map_or(0, |row| row.collection_hours),
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            super::aid::aid_binding(config, choice).map_or(0, |row| row.coordination_hours)
        }
        OrganizerChoice::Inquiry(_) => config.inquiry_hours,
        OrganizerChoice::Reinforce | OrganizerChoice::ResumeStanding => config.contact_hours,
        OrganizerChoice::Hold if state.standing.authorized => config.contact_hours,
        OrganizerChoice::Hold | OrganizerChoice::PauseStanding => 0,
    }
}

pub fn preview_organizer(
    config: &OrganizerConfig,
    state: &OrganizerState,
    command: &OrganizerCommand,
) -> Result<OrganizerPreview, OrganizerError> {
    validate_organizer_pair(config, state)?;
    let available_hours = committed_hours(config, config.controlled_actor_id)?;
    let cost = required_hours(config, state, command.choice);
    let resolves_period = state
        .period
        .checked_add(1)
        .ok_or(OrganizerError::Arithmetic)?;
    let refusal = if command.campaign_id != config.campaign_id {
        Some(OrganizerRefusal::WrongCampaign)
    } else if command.actor_id != config.controlled_actor_id
        || command.authority_id != config.input_authority_id
    {
        Some(OrganizerRefusal::WrongAuthority)
    } else if command.expected_period != state.period {
        Some(OrganizerRefusal::StalePeriod)
    } else if command.content_digest != config.content_digest {
        Some(OrganizerRefusal::ContentChanged)
    } else if command.resource_digest != organizer_resource_digest()? {
        Some(OrganizerRefusal::ResourceContractChanged)
    } else if state
        .pending_aid
        .iter()
        .any(|row| row.gift.commitment.command.choice == command.choice)
    {
        Some(OrganizerRefusal::PendingAidConflict)
    } else if super::aid::aid_kind(command.choice).is_some()
        && super::aid::aid_binding(config, command.choice).is_none()
    {
        Some(OrganizerRefusal::AidUnavailable)
    } else if super::aid::aid_binding(config, command.choice)
        .is_some_and(|row| row.receiving_consent == OrganizerGiftConsent::Refuse)
    {
        Some(OrganizerRefusal::AidReceivingRefused)
    } else if command.choice == OrganizerChoice::Collect {
        super::collection::collection_refusal(config)?
    } else if command.choice == OrganizerChoice::ResumeStanding && state.standing.authorized {
        Some(OrganizerRefusal::StandingWorkAlreadyActive)
    } else if super::aid::aid_kind(command.choice).is_none() && cost > available_hours {
        Some(OrganizerRefusal::InsufficientCommittedTime)
    } else {
        None
    };
    // Authorization failures carry no actor knowledge or resources.
    let authorized = !matches!(
        refusal,
        Some(OrganizerRefusal::WrongCampaign | OrganizerRefusal::WrongAuthority)
    );
    Ok(OrganizerPreview {
        choice: command.choice,
        current_period: state.period,
        resolves_period,
        available_hours: if authorized { available_hours } else { 0 },
        required_hours: if authorized { cost } else { 0 },
        replaces_standing_work: authorized
            && state.standing.authorized
            && matches!(
                command.choice,
                OrganizerChoice::Collect
                    | OrganizerChoice::Inquiry(_)
                    | OrganizerChoice::Reinforce
                    | OrganizerChoice::LocalAid
                    | OrganizerChoice::RemoteAid
            ),
        refusal,
        observations: if authorized {
            state.observations.clone()
        } else {
            vec![]
        },
    })
}

pub fn admit_organizer(
    config: &OrganizerConfig,
    state: &OrganizerState,
    command: &OrganizerCommand,
) -> Result<OrganizerCommitment, OrganizerError> {
    let preview = preview_organizer(config, state, command)?;
    if let Some(refusal) = preview.refusal {
        return Err(OrganizerError::Refused(refusal));
    }
    let commitment = OrganizerCommitment {
        command: command.clone(),
        resolves_period: preview.resolves_period,
        commitment_id: identity(b"babylon.organizer-commitment.v1", command)?,
    };
    validate_organizer_commitment(&commitment)?;
    Ok(commitment)
}

/// Verify the immutable input identity without re-admitting it against a later
/// period. Durable exact retries use this after the original action resolves.
pub fn validate_organizer_commitment(
    commitment: &OrganizerCommitment,
) -> Result<(), OrganizerError> {
    let command = &commitment.command;
    if command.actor_id == 0
        || command.authority_id == [0; 16]
        || command.expected_period.checked_add(1) != Some(commitment.resolves_period)
        || identity(b"babylon.organizer-commitment.v1", command)? != commitment.commitment_id
    {
        return Err(OrganizerError::InvalidCommitment);
    }
    Ok(())
}
