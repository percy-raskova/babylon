use super::aid::OrganizerAidOption;
use super::aid::OrganizerGiftConsent;
use super::OrganizerAgreement;
use super::OrganizerChoice;
use super::OrganizerCommand;
use super::OrganizerCommitment;
use super::OrganizerConfig;
use super::OrganizerError;
use super::OrganizerLearnedAuthority;
use super::OrganizerObservation;
use super::OrganizerOutcome;
use super::OrganizerPartnerResponse;
use super::OrganizerPeriodJournal;
use super::OrganizerPeriodJournalEntries;
use super::OrganizerPosition;
use super::OrganizerPreview;
use super::OrganizerReceipt;
use super::OrganizerRefusal;
use super::OrganizerReport;
use super::OrganizerStandingWork;
use super::OrganizerState;
use super::OrganizerTimeBindingMode;
use super::OrganizerView;
use super::ORGANIZER_RECENT_OBSERVATIONS;
use super::ORGANIZER_RECENT_RECEIPTS;
use super::ORGANIZER_SCHEMA_VERSION;
use serde::Serialize;

use std::collections::BTreeSet;

use babylon_kernel::content_digest;

use crate::PracticeResourceAllocationContract;
use serde::de::DeserializeOwned;
use std::collections::BTreeMap;

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
    Ok(content_digest::sha256_of(&canonical(domain, value)?))
}

fn label_valid(value: &str) -> bool {
    !value.is_empty() && value.len() <= 512 && !value.chars().any(char::is_control)
}

/// Validate the schema version and bounded contents of a captured config.
///
/// # Errors
///
/// Returns [`OrganizerError::UnsupportedSchema`] for a foreign schema version
/// and [`OrganizerError::InvalidConfig`] for a policy, partner, or binding
/// value outside its declared bounds.
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

/// Validate the schema version, size ceilings, and row invariants of a state.
///
/// Historical receipts and observations are not part of causal state; see
/// [`validate_organizer_journal`] for the exact evidence contract.
///
/// # Errors
///
/// Returns [`OrganizerError::UnsupportedSchema`] for a foreign schema version,
/// [`OrganizerError::SizeLimit`] past a row ceiling, and
/// [`OrganizerError::InvalidState`] for a malformed stored row.
#[allow(
    clippy::too_many_lines,
    reason = "one linear pass over each live causal family; splitting it would duplicate the ceiling and ordering invariants"
)]
pub fn validate_organizer_state(state: &OrganizerState) -> Result<(), OrganizerError> {
    if state.schema_version != ORGANIZER_SCHEMA_VERSION {
        return Err(OrganizerError::UnsupportedSchema);
    }
    if state.learned_authority_index.len() > MAX_ORGANIZER_ROWS
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
    super::aid::validate_aid_state(state)?;
    let mut product_ids = BTreeSet::new();
    for product in &state.contact_products {
        if product.produced_period == 0
            || product.produced_period > state.period
            || !product_ids.insert(product.product_id)
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
    // Tombstones are permanent: the live product may already be gone, but the
    // identity can never be offered again.
    let mut consumed_ids = BTreeSet::new();
    for id in &state.consumed_product_ids {
        if product_ids.contains(id) || !consumed_ids.insert(*id) {
            return Err(OrganizerError::InvalidState);
        }
    }
    let mut observation_ids = BTreeSet::new();
    let mut learned_keys = BTreeSet::new();
    for row in &state.learned_authority_index {
        if row.observed_period > row.acquired_period
            || row.acquired_period > state.period
            || !observation_ids.insert(row.observation_id)
            || !learned_keys.insert((row.subject_id, row.source_actor_id, row.report_kind()))
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    if let Some(witness) = &state.last_period_time_witness {
        if witness.period == 0
            || witness.period > state.period
            || !witness
                .contribution_use_ids
                .windows(2)
                .all(|rows| rows[0] < rows[1])
        {
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

/// Validate one period's exact evidence against the captured contracts.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidState`] for a malformed, misordered, or
/// duplicated evidence row and [`OrganizerError::SizeLimit`] past a ceiling.
pub fn validate_organizer_period_entries(
    config: &OrganizerConfig,
    entries: &OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    validate_organizer_config(config)?;
    if entries.period == 0
        || entries.observations.len() > MAX_ORGANIZER_ROWS
        || entries.receipts.len() > MAX_ORGANIZER_ROWS
        || entries.collection_receipts.len() > MAX_ORGANIZER_ROWS
        || entries.aid_receipts.len() > MAX_ORGANIZER_ROWS
    {
        return Err(OrganizerError::SizeLimit);
    }
    let mut receipt_ids = BTreeSet::new();
    for receipt in &entries.receipts {
        validate_organizer_receipt(receipt)?;
        if receipt.period != entries.period || !receipt_ids.insert(receipt.receipt_id) {
            return Err(OrganizerError::InvalidState);
        }
    }
    for row in &entries.aid_receipts {
        super::aid::validate_resolution_shape(row)?;
        if row.practice.period != entries.period || !receipt_ids.insert(row.practice.receipt_id) {
            return Err(OrganizerError::InvalidState);
        }
    }
    let mut observation_ids = BTreeSet::new();
    for observation in &entries.observations {
        if observation.actor_id != config.controlled_actor_id
            || observation.subject_id != config.workplace_id
            || observation.source_actor_id != config.workplace_partner.actor_id
            || observation.observed_period > observation.acquired_period
            || observation.acquired_period != entries.period
            || !observation_ids.insert(observation.observation_id)
            || observation
                .receipt_id
                .is_some_and(|id| !receipt_ids.contains(&id))
        {
            return Err(OrganizerError::InvalidState);
        }
    }
    super::collection::validate_collection_history(config, entries)?;
    super::aid::validate_aid_history(config, entries)?;
    super::aid::validate_period_allocations(config, entries)?;
    Ok(())
}

/// Validate the retained evidence window against the compact causal state.
///
/// # Errors
///
/// Returns each fault [`validate_organizer_pair`] reports plus
/// [`OrganizerError::InvalidState`] when a witness, tombstone, live product, or
/// learned index row has no exact retained evidence.
pub fn validate_organizer_journal(
    config: &OrganizerConfig,
    state: &OrganizerState,
    journal: &OrganizerPeriodJournal,
) -> Result<(), OrganizerError> {
    validate_organizer_pair(config, state)?;
    let mut prior = None;
    for entries in &journal.periods {
        if prior.is_some_and(|period| period >= entries.period) {
            return Err(OrganizerError::InvalidState);
        }
        prior = Some(entries.period);
        validate_organizer_period_entries(config, entries)?;
    }
    let latest = journal.latest();
    if state.period == 0 {
        if latest.is_some() {
            return Err(OrganizerError::InvalidState);
        }
        return Ok(());
    }
    let latest = latest.ok_or(OrganizerError::InvalidState)?;
    if latest.period != state.period {
        return Err(OrganizerError::InvalidState);
    }
    let receipt_ids: BTreeSet<_> = journal
        .periods
        .iter()
        .flat_map(|entries| entries.receipts().map(|row| row.receipt_id))
        .collect();
    let observations: BTreeMap<_, _> = journal
        .periods
        .iter()
        .flat_map(|entries| &entries.observations)
        .map(|row| (row.observation_id, row))
        .collect();
    for product in &state.contact_products {
        if !receipt_ids.contains(&product.receipt_id)
            || !latest.receipts.iter().any(|receipt| {
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
    }
    for row in &state.learned_authority_index {
        // The retained evidence window is still unbounded (Task 8 owns the
        // finite retention window), so every compact learned row must find its
        // exact observation in retained evidence. Task 8 must either preserve
        // the referenced evidence or amend this refusal when it prunes.
        let exact = observations
            .get(&row.observation_id)
            .is_some_and(|observation| {
                observation.subject_id == row.subject_id
                    && observation.source_actor_id == row.source_actor_id
                    && observation.observed_period == row.observed_period
                    && observation.acquired_period == row.acquired_period
                    && observation.receipt_id == row.receipt_id
                    && observation.report == row.report
            });
        let seeded = config.initial_observations.iter().any(|observation| {
            observation.observation_id == row.observation_id
                && observation.report == row.report
                && observation.receipt_id.is_none()
        });
        if !exact && !seeded {
            return Err(OrganizerError::InvalidState);
        }
    }
    if let Some(witness) = &state.last_period_time_witness {
        if witness.period == latest.period {
            let charged = charged_time_ids(latest);
            if witness
                .contribution_use_ids
                .iter()
                .any(|id| !charged.contains(id))
            {
                // An hour already debited must stay visible in exact evidence;
                // an evicted receipt can never let it be spent a second time.
                return Err(OrganizerError::InvalidState);
            }
        }
    }
    super::aid::validate_completed_aid(state, latest)?;
    super::aid::validate_aid_window(state, journal)?;
    Ok(())
}

/// Validate a config and its paired state through the two focused checks.
///
/// # Errors
///
/// Returns whatever [`validate_organizer_config`] or
/// [`validate_organizer_state`] reports for the supplied pair.
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
        || state.contact_products.iter().any(|row| {
            row.actor_id != config.controlled_actor_id
                || !partner_ids.contains(&row.partner_actor_id)
        })
        || state.learned_authority_index.iter().any(|row| {
            row.subject_id != config.workplace_id
                || row.source_actor_id != config.workplace_partner.actor_id
        })
        || state
            .last_workplace_facts
            .as_ref()
            .is_some_and(|row| row.workplace_id != config.workplace_id)
    {
        return Err(OrganizerError::InvalidState);
    }
    for pending in &state.pending_aid {
        super::aid::validate_pending(config, pending)?;
    }
    Ok(())
}

/// Encode a validated config in its canonical domain-framed form.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidConfig`] or
/// [`OrganizerError::UnsupportedSchema`] from validation, plus
/// [`OrganizerError::Codec`] or [`OrganizerError::SizeLimit`] when canonical
/// serialization fails or exceeds the encoded ceiling.
pub fn encode_organizer_config(config: &OrganizerConfig) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_config(config)?;
    canonical(b"babylon.organizer-config.v7", config)
}

/// Decode a canonical config and refuse anything that would not re-encode.
///
/// # Errors
///
/// Returns [`OrganizerError::SizeLimit`] past the encoded ceiling,
/// [`OrganizerError::Codec`] for a foreign domain frame or non-canonical body,
/// and the validation faults [`validate_organizer_config`] reports.
pub fn decode_organizer_config(bytes: &[u8]) -> Result<OrganizerConfig, OrganizerError> {
    let value = decode(b"babylon.organizer-config.v7", bytes)?;
    validate_organizer_config(&value)?;
    Ok(value)
}

/// Encode a validated state in its canonical domain-framed form.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidState`] or
/// [`OrganizerError::UnsupportedSchema`] from validation, including completed
/// aid receipts, plus [`OrganizerError::Codec`] or
/// [`OrganizerError::SizeLimit`] when canonical serialization fails or
/// exceeds the encoded ceiling.
pub fn encode_organizer_state(state: &OrganizerState) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_state(state)?;
    canonical(b"babylon.organizer-state.v6", state)
}

/// Decode a canonical state and refuse anything that would not re-encode.
///
/// # Errors
///
/// Returns [`OrganizerError::SizeLimit`] past the encoded ceiling,
/// [`OrganizerError::Codec`] for a foreign domain frame or non-canonical body,
/// and the validation faults [`validate_organizer_state`] reports.
pub fn decode_organizer_state(bytes: &[u8]) -> Result<OrganizerState, OrganizerError> {
    let value = decode(b"babylon.organizer-state.v6", bytes)?;
    validate_organizer_state(&value)?;
    Ok(value)
}

/// Encode one validated period's evidence in its canonical framed form.
///
/// # Errors
///
/// Returns the validation faults of [`validate_organizer_period_entries`] plus
/// [`OrganizerError::Codec`] or [`OrganizerError::SizeLimit`] when canonical
/// serialization fails or exceeds the encoded ceiling.
pub fn encode_organizer_period_entries(
    config: &OrganizerConfig,
    entries: &OrganizerPeriodJournalEntries,
) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_period_entries(config, entries)?;
    canonical(b"babylon.organizer-period-entries.v1", entries)
}

/// Decode one canonical period of evidence.
///
/// # Errors
///
/// Returns [`OrganizerError::Codec`] for a foreign frame or non-canonical body
/// and every fault [`validate_organizer_period_entries`] reports.
pub fn decode_organizer_period_entries(
    config: &OrganizerConfig,
    bytes: &[u8],
) -> Result<OrganizerPeriodJournalEntries, OrganizerError> {
    let value = decode(b"babylon.organizer-period-entries.v1", bytes)?;
    validate_organizer_period_entries(config, &value)?;
    Ok(value)
}

/// Encode the retained evidence window in its canonical framed form.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidState`] for a misordered or malformed
/// window plus the codec faults of [`encode_organizer_period_entries`].
pub fn encode_organizer_journal(
    config: &OrganizerConfig,
    journal: &OrganizerPeriodJournal,
) -> Result<Vec<u8>, OrganizerError> {
    let mut prior = None;
    for entries in &journal.periods {
        if prior.is_some_and(|period| period >= entries.period) {
            return Err(OrganizerError::InvalidState);
        }
        prior = Some(entries.period);
        validate_organizer_period_entries(config, entries)?;
    }
    canonical(b"babylon.organizer-journal.v1", journal)
}

/// Decode a canonical retained evidence window.
///
/// # Errors
///
/// Returns [`OrganizerError::Codec`] for a foreign frame or non-canonical body
/// and the same faults [`encode_organizer_journal`] reports.
pub fn decode_organizer_journal(
    config: &OrganizerConfig,
    bytes: &[u8],
) -> Result<OrganizerPeriodJournal, OrganizerError> {
    let value: OrganizerPeriodJournal = decode(b"babylon.organizer-journal.v1", bytes)?;
    let mut prior = None;
    for entries in &value.periods {
        if prior.is_some_and(|period| period >= entries.period) {
            return Err(OrganizerError::InvalidState);
        }
        prior = Some(entries.period);
        validate_organizer_period_entries(config, entries)?;
    }
    Ok(value)
}

/// Hash the canonical state encoding.
///
/// # Errors
///
/// Returns every fault [`encode_organizer_state`] reports; no digest exists
/// for a state that does not validate.
pub fn organizer_state_digest(state: &OrganizerState) -> Result<[u8; 32], OrganizerError> {
    Ok(content_digest::sha256_of(&encode_organizer_state(state)?))
}

/// Validate the hours, allocations, and row identity of one receipt.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidState`] when allocations repeat, exceed the
/// recorded hours, or disagree with the receipt actor.
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

/// Encode a validated receipt in its canonical domain-framed form.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidState`] from validation plus
/// [`OrganizerError::Codec`] or [`OrganizerError::SizeLimit`] when canonical
/// serialization fails or exceeds the encoded ceiling.
pub fn encode_organizer_receipt(receipt: &OrganizerReceipt) -> Result<Vec<u8>, OrganizerError> {
    validate_organizer_receipt(receipt)?;
    canonical(b"babylon.organizer-receipt.v2", receipt)
}

/// Decode a canonical receipt and refuse anything that would not re-encode.
///
/// # Errors
///
/// Returns [`OrganizerError::SizeLimit`] past the encoded ceiling,
/// [`OrganizerError::Codec`] for a foreign domain frame or non-canonical body,
/// and [`OrganizerError::InvalidState`] from receipt validation.
pub fn decode_organizer_receipt(bytes: &[u8]) -> Result<OrganizerReceipt, OrganizerError> {
    let value = decode(b"babylon.organizer-receipt.v2", bytes)?;
    validate_organizer_receipt(&value)?;
    Ok(value)
}

/// Digest the installed practice resource allocation contract.
///
/// # Errors
///
/// Returns [`OrganizerError::ResourceAllocation`] when the contract's own
/// validation refuses the conserved allocation table.
pub fn organizer_resource_digest() -> Result<[u8; 32], OrganizerError> {
    crate::practice_resource_allocation_contract_digest(
        &PracticeResourceAllocationContract::conservation_first(),
    )
    .map_err(|_| OrganizerError::ResourceAllocation)
}

/// Build the opening state for a freshly captured config.
///
/// # Errors
///
/// Returns the config faults [`validate_organizer_config`] reports and
/// [`OrganizerError::Arithmetic`] when a period or hour sum overflows.
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
        pending_aid: vec![],
        contact_products: vec![],
        consumed_product_ids: vec![],
        last_workplace_facts: None,
        learned_authority_index: learned_authority_index(&config.initial_observations),
        last_period_time_witness: None,
    })
}

/// Keep only the newest exact report per subject, source, and report kind.
pub(super) fn learned_authority_index(
    observations: &[OrganizerObservation],
) -> Vec<OrganizerLearnedAuthority> {
    let mut rows = BTreeMap::new();
    for observation in observations {
        let row = OrganizerLearnedAuthority {
            observation_id: observation.observation_id,
            receipt_id: observation.receipt_id,
            subject_id: observation.subject_id,
            source_actor_id: observation.source_actor_id,
            observed_period: observation.observed_period,
            acquired_period: observation.acquired_period,
            report: observation.report.clone(),
        };
        let key = (row.subject_id, row.source_actor_id, row.report_kind());
        let candidate = (row.observed_period, row.acquired_period, row.observation_id);
        if rows
            .get(&key)
            .is_none_or(|old: &OrganizerLearnedAuthority| {
                candidate > (old.observed_period, old.acquired_period, old.observation_id)
            })
        {
            rows.insert(key, row);
        }
    }
    rows.into_values().collect()
}

/// Exact household-hour identity charged by one organizer time use.
#[must_use]
pub fn household_contribution_use_id(
    receipt_id: &[u8; 32],
    actor_id: u64,
    contributor_id: u64,
) -> [u8; 32] {
    let mut identity = b"babylon.organizer-household-contribution.v1\0".to_vec();
    identity.extend_from_slice(receipt_id);
    identity.extend_from_slice(&actor_id.to_be_bytes());
    identity.extend_from_slice(&contributor_id.to_be_bytes());
    content_digest::sha256_of(&identity)
}

/// Exact household-hour identities charged by one period's evidence.
pub(super) fn charged_time_ids(entries: &OrganizerPeriodJournalEntries) -> BTreeSet<[u8; 32]> {
    let mut ids = BTreeSet::new();
    for receipt in entries.receipts() {
        if receipt.choice == OrganizerChoice::Collect {
            // Collection hours charge the exact fact identity below.
            continue;
        }
        for usage in &receipt.time_use {
            ids.insert(household_contribution_use_id(
                &receipt.receipt_id,
                usage.actor_id,
                usage.contributor_id,
            ));
        }
    }
    for row in &entries.collection_receipts {
        if row.fact.performed_hours > 0 {
            ids.insert(row.fact.contribution_use_id);
        }
    }
    ids
}

/// Insert or replace one compact learned row, keeping key order deterministic.
pub(super) fn upsert_learned_authority(
    index: &mut Vec<OrganizerLearnedAuthority>,
    row: OrganizerLearnedAuthority,
) {
    let key = (row.subject_id, row.source_actor_id, row.report_kind());
    if let Some(position) = index
        .iter()
        .position(|old| (old.subject_id, old.source_actor_id, old.report_kind()) == key)
    {
        if (row.observed_period, row.acquired_period, row.observation_id)
            > (
                index[position].observed_period,
                index[position].acquired_period,
                index[position].observation_id,
            )
        {
            index[position] = row;
        }
    } else {
        index.push(row);
    }
    index.sort_by_key(|old| (old.subject_id, old.source_actor_id, old.report_kind()));
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

/// Project the controlled actor's bounded view of the committed state.
///
/// # Errors
///
/// Returns the pair faults from [`validate_organizer_pair`],
/// [`OrganizerError::Refused`] with `WrongAuthority` for another actor, and
/// [`OrganizerError::Arithmetic`] when a row count exceeds its window type.
#[allow(
    clippy::too_many_lines,
    reason = "receipts and observations share one ordering pass so the visible window cannot diverge"
)]
pub fn organizer_view(
    config: &OrganizerConfig,
    state: &OrganizerState,
    journal: &OrganizerPeriodJournal,
    actor_id: u64,
) -> Result<OrganizerView, OrganizerError> {
    validate_organizer_journal(config, state, journal)?;
    if actor_id != config.controlled_actor_id {
        return Err(OrganizerError::Refused(OrganizerRefusal::WrongAuthority));
    }
    let mut receipts = journal
        .periods
        .iter()
        .flat_map(OrganizerPeriodJournalEntries::receipts)
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
    let mut observations = journal
        .periods
        .iter()
        .flat_map(|entries| &entries.observations)
        .filter(|row| row.actor_id == actor_id)
        .collect::<Vec<_>>();
    let total_observation_count =
        u32::try_from(observations.len()).map_err(|_| OrganizerError::Arithmetic)?;
    observations.sort_by_key(|row| (row.acquired_period, row.observed_period, row.observation_id));
    // Preserve the latest materially distinct report even when it predates the recent window.
    let mut latest = BTreeMap::new();
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
    for row in &state.learned_authority_index {
        selected.insert(row.observation_id);
    }
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

/// Preview one command without admitting it.
///
/// A rule refusal is a successful preview carrying a refusal reason, not an
/// error.
///
/// # Errors
///
/// Returns the pair faults from [`validate_organizer_pair`],
/// [`OrganizerError::ResourceAllocation`] for a changed resource contract, and
/// [`OrganizerError::Arithmetic`] when the resolved period overflows.
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
            state
                .learned_authority_index
                .iter()
                .map(|row| row.observation(config.controlled_actor_id))
                .collect()
        } else {
            vec![]
        },
    })
}

/// Admit one command as an immutable commitment.
///
/// # Errors
///
/// Returns every [`preview_organizer`] fault,
/// [`OrganizerError::Refused`] carrying the preview's refusal reason, and
/// [`OrganizerError::InvalidCommitment`] when the derived identity or binding
/// does not validate.
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
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidCommitment`] when the actor, authority,
/// resolved period, or derived identity does not match the captured command.
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
